"""Session orchestrator: assembles per-user context, runs turns, closes sessions.

A session is opened on the learner's weakest Harada focus cell when one exists
(app/harada.py), otherwise on the next incomplete lesson at their level. Closing
a session evaluates the transcript and rescoring the Harada board.
"""
import json
import logging
import time

import asyncpg
from fastapi import APIRouter, Depends, Form, HTTPException

from . import claude_client, config, harada, quota, srs
from .auth import require_user
from .db import pool

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/session")

READING_ALLOWANCE_MIN = 0.25  # per turn, on top of model latency
LESSON_PASS_SCORE = 0.7
MAX_VOCAB_LEN = 200  # a vocab item longer than this is model noise, not a word


async def next_lesson_id(user_id: int, level: str) -> int | None:
    """The learner's next incomplete lesson at their level (A0 learners start at A1)."""
    return await pool().fetchval(
        """SELECT l.id FROM lessons l
           LEFT JOIN user_lessons ul ON ul.lesson_id = l.id AND ul.user_id = $1
           WHERE l.level = $2 AND COALESCE(ul.status,'not_started') != 'completed'
           ORDER BY l.seq LIMIT 1""",
        user_id, "A1" if level == "A0" else level,
    )


def _format_context(p: asyncpg.Record, lesson: asyncpg.Record | None, due: list[dict],
                    summaries: list[asyncpg.Record], errors: str | None,
                    focus: harada.FocusPick | None) -> str:
    due_lines = "\n".join(
        f"- {v['greek']} — {v['english']} "
        f"({v['times_correct']}/{v['times_seen']} correct)" for v in due
    ) or "(none due — introduce new words from the lesson)"
    block = f"""STUDENT CONTEXT
- Name: {p['display_name']}
- Native language: {p['native_lang']}
- Current level estimate: {p['level_estimate']}
- Today's lesson: {lesson['topic'] if lesson else 'Free conversation practice'}
- Objectives: {lesson['objectives'] if lesson else '[]'}

REVIEW VOCABULARY DUE TODAY
{due_lines}

RECENT SESSION SUMMARIES (newest first)
{chr(10).join('- ' + s['summary_text'] for s in summaries) or '(first session)'}

RECURRING ERROR PATTERNS
{errors or '(none yet)'}"""
    if focus:
        block += "\n\n" + harada.focus_block(focus)
    return block


async def build_user_context(user_id: int, lesson_id: int | None,
                             focus: harada.FocusPick | None) -> str:
    """Assemble the per-user system block from Postgres."""
    p = await pool().fetchrow(
        "SELECT display_name, native_lang, level_estimate FROM profiles WHERE user_id=$1",
        user_id,
    )
    lesson = None
    if lesson_id:
        lesson = await pool().fetchrow(
            "SELECT topic, objectives FROM lessons WHERE id=$1", lesson_id)
    due = await srs.due_vocab(user_id)
    summaries = await pool().fetch(
        """SELECT summary_text FROM tutor_sessions
           WHERE user_id=$1 AND summary_text IS NOT NULL
           ORDER BY started_at DESC LIMIT 3""",
        user_id,
    )
    errors = await pool().fetchval(
        """SELECT jsonb_agg(DISTINCT e) FROM (
             SELECT jsonb_array_elements_text(error_patterns) AS e
             FROM tutor_sessions WHERE user_id=$1
             ORDER BY started_at DESC LIMIT 10) sub""",
        user_id,
    )
    return _format_context(p, lesson, due, summaries, errors, focus)


@router.post("/start")
async def start_session(user=Depends(require_user)):
    await quota.check_quota(user["id"])
    focus = await harada.pick_focus(user["id"])
    lesson_id = focus.lesson_id if focus else None
    if lesson_id is None:
        lesson_id = await next_lesson_id(user["id"], user["level_estimate"])
    focus_action_id = focus.action_id if focus else None
    sid = await pool().fetchval(
        """INSERT INTO tutor_sessions (user_id, lesson_id, mode, focus_action_id)
           VALUES ($1, $2, 'text', $3) RETURNING id""",
        user["id"], lesson_id, focus_action_id,
    )
    if lesson_id:
        await pool().execute(
            """INSERT INTO user_lessons (user_id, lesson_id, status)
               VALUES ($1,$2,'in_progress')
               ON CONFLICT (user_id, lesson_id) DO UPDATE SET status='in_progress'""",
            user["id"], lesson_id,
        )
    return {"session_id": sid, "lesson_id": lesson_id, "focus_action_id": focus_action_id}


async def _load_transcript(session_id: int) -> list[dict]:
    rows = await pool().fetch(
        "SELECT role, content FROM tutor_turns WHERE session_id=$1 ORDER BY id",
        session_id,
    )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def _own_session(session_id: int, user_id: int) -> asyncpg.Record:
    row = await pool().fetchrow(
        """SELECT id, ended_at, lesson_id, focus_action_id
           FROM tutor_sessions WHERE id=$1 AND user_id=$2""",
        session_id, user_id,
    )
    if not row:
        raise HTTPException(404, "Session not found.")
    if row["ended_at"]:
        raise HTTPException(400, "Session already closed.")
    return row


async def _apply_vocab_events(user_id: int, events: object) -> None:
    if not isinstance(events, list):
        return
    for ev in events:
        if not (isinstance(ev, dict) and {"greek", "english", "result"} <= ev.keys()):
            continue
        greek, english = str(ev["greek"]).strip(), str(ev["english"]).strip()
        if not greek or not english or max(len(greek), len(english)) > MAX_VOCAB_LEN:
            continue
        await srs.apply_vocab_event(user_id, greek, english, str(ev["result"]), ev.get("tag"))


@router.post("/{session_id}/turn")
async def turn(session_id: int, message: str = Form(...), user=Depends(require_user)):
    sess = await _own_session(session_id, user["id"])
    await quota.check_quota(user["id"])

    transcript = await _load_transcript(session_id)
    if len(transcript) >= config.SESSION_MAX_TURNS:
        raise HTTPException(400, "Session turn limit reached — please close the session.")

    focus = None
    if sess["focus_action_id"]:
        focus = await harada.focus_for_action(user["id"], sess["focus_action_id"])
    context_block = await build_user_context(user["id"], sess["lesson_id"], focus)
    transcript.append({"role": "user", "content": message})

    t0 = time.monotonic()
    text, meta, tok_in, tok_out = await claude_client.tutor_turn(context_block, transcript)
    elapsed_min = (time.monotonic() - t0) / 60 + READING_ALLOWANCE_MIN

    async with pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO tutor_turns (session_id, role, content) VALUES ($1,'user',$2)",
            session_id, message,
        )
        await conn.execute(
            "INSERT INTO tutor_turns (session_id, role, content) VALUES ($1,'assistant',$2)",
            session_id, text,
        )
    await _apply_vocab_events(user["id"], meta.get("vocab_events"))
    await quota.record_usage(user["id"], tok_in, tok_out, elapsed_min)
    await pool().execute(
        "UPDATE tutor_sessions SET minutes_used = minutes_used + $2 WHERE id=$1",
        session_id, elapsed_min,
    )
    return {"reply": text, "objective_progress": meta.get("objective_progress", 0)}


def _clamped_score(raw: object) -> float | None:
    """The eval model's lesson_score as a fraction in [0, 1]; None if unusable.

    A percentage (e.g. 95) is the classic failure mode; treating it as 95.0 would
    mark the lesson passed and make the Harada focus picker skip it forever.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if value > 1.0 and value <= 100.0:
        value /= 100.0
    return max(0.0, min(1.0, value))


async def _store_evaluation(session_id: int, user_id: int, lesson_id: int | None,
                            data: dict) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """UPDATE tutor_sessions SET ended_at=now(), summary_text=$2,
                 error_patterns=$3 WHERE id=$1""",
            session_id, data.get("summary"),
            json.dumps(data.get("error_patterns", [])),
        )
        score = _clamped_score(data.get("lesson_score"))
        if lesson_id and score is not None:
            status = "completed" if score >= LESSON_PASS_SCORE else "in_progress"
            await conn.execute(
                """UPDATE user_lessons SET score=$3, status=$4,
                     completed_at = CASE WHEN $4='completed' THEN now() END
                   WHERE user_id=$1 AND lesson_id=$2""",
                user_id, lesson_id, score, status,
            )


async def _rescore_board(user_id: int) -> None:
    """Rescore the Harada board after a session. A scoring bug must never block closing."""
    try:
        await harada.recompute(user_id)
    except Exception:
        log.exception("harada recompute failed for user %s", user_id)


@router.post("/{session_id}/close")
async def close_session(session_id: int, user=Depends(require_user)):
    sess = await _own_session(session_id, user["id"])
    transcript = await _load_transcript(session_id)
    if not transcript:
        await pool().execute("UPDATE tutor_sessions SET ended_at=now() WHERE id=$1", session_id)
        return {"summary": "Empty session closed."}

    data, tok_in, tok_out = await claude_client.evaluate_session(transcript)
    await quota.record_usage(user["id"], tok_in, tok_out, 0)
    await _store_evaluation(session_id, user["id"], sess["lesson_id"], data)
    await _rescore_board(user["id"])
    # Level changes: deliberately NOT automatic per session. Run a periodic job
    # that raises/lowers level_estimate only after 3+ consistent recommendations.
    return {"summary": data.get("summary", "")}
