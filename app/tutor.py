"""Session orchestrator: assembles per-user context, runs turns, closes sessions."""
import json
import time

from fastapi import APIRouter, Depends, Form, HTTPException

from . import claude_client, config, quota, srs
from .auth import require_user
from .db import pool

router = APIRouter(prefix="/api/session")


async def build_user_context(user_id: int) -> tuple[str, int | None]:
    """Assemble the per-user system block from Postgres. Returns (block, lesson_id)."""
    p = await pool().fetchrow(
        "SELECT display_name, native_lang, level_estimate FROM profiles WHERE user_id=$1",
        user_id,
    )
    lesson = await pool().fetchrow(
        """SELECT l.id, l.topic, l.objectives FROM lessons l
           LEFT JOIN user_lessons ul ON ul.lesson_id = l.id AND ul.user_id = $1
           WHERE l.level = $2 AND COALESCE(ul.status,'not_started') != 'completed'
           ORDER BY l.seq LIMIT 1""",
        user_id, p["level_estimate"] if p["level_estimate"] != "A0" else "A1",
    )
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
    return block, lesson["id"] if lesson else None


@router.post("/start")
async def start_session(user=Depends(require_user)):
    await quota.check_quota(user["id"])
    _, lesson_id = await build_user_context(user["id"])
    sid = await pool().fetchval(
        "INSERT INTO tutor_sessions (user_id, lesson_id, mode) VALUES ($1,$2,'text') RETURNING id",
        user["id"], lesson_id,
    )
    if lesson_id:
        await pool().execute(
            """INSERT INTO user_lessons (user_id, lesson_id, status)
               VALUES ($1,$2,'in_progress')
               ON CONFLICT (user_id, lesson_id) DO UPDATE SET status='in_progress'""",
            user["id"], lesson_id,
        )
    return {"session_id": sid}


async def _load_transcript(session_id: int) -> list[dict]:
    rows = await pool().fetch(
        "SELECT role, content FROM tutor_turns WHERE session_id=$1 ORDER BY id",
        session_id,
    )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def _own_session(session_id: int, user_id: int):
    row = await pool().fetchrow(
        "SELECT id, ended_at FROM tutor_sessions WHERE id=$1 AND user_id=$2",
        session_id, user_id,
    )
    if not row:
        raise HTTPException(404, "Session not found.")
    if row["ended_at"]:
        raise HTTPException(400, "Session already closed.")


@router.post("/{session_id}/turn")
async def turn(session_id: int, message: str = Form(...), user=Depends(require_user)):
    await _own_session(session_id, user["id"])
    await quota.check_quota(user["id"])

    transcript = await _load_transcript(session_id)
    if len(transcript) >= config.SESSION_MAX_TURNS:
        raise HTTPException(400, "Session turn limit reached — please close the session.")

    context_block, _ = await build_user_context(user["id"])
    transcript.append({"role": "user", "content": message})

    t0 = time.monotonic()
    text, meta, tok_in, tok_out = await claude_client.tutor_turn(context_block, transcript)
    elapsed_min = (time.monotonic() - t0) / 60 + 0.25  # + reading/typing allowance

    async with pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO tutor_turns (session_id, role, content) VALUES ($1,'user',$2)",
            session_id, message,
        )
        await conn.execute(
            "INSERT INTO tutor_turns (session_id, role, content) VALUES ($1,'assistant',$2)",
            session_id, text,
        )
    for ev in meta.get("vocab_events", []):
        if {"greek", "english", "result"} <= ev.keys():
            await srs.apply_vocab_event(user["id"], ev["greek"], ev["english"], ev["result"])
    await quota.record_usage(user["id"], tok_in, tok_out, elapsed_min)
    await pool().execute(
        "UPDATE tutor_sessions SET minutes_used = minutes_used + $2 WHERE id=$1",
        session_id, elapsed_min,
    )
    return {"reply": text, "objective_progress": meta.get("objective_progress", 0)}


@router.post("/{session_id}/close")
async def close_session(session_id: int, user=Depends(require_user)):
    await _own_session(session_id, user["id"])
    transcript = await _load_transcript(session_id)
    if not transcript:
        await pool().execute("UPDATE tutor_sessions SET ended_at=now() WHERE id=$1", session_id)
        return {"summary": "Empty session closed."}

    data, tok_in, tok_out = await claude_client.evaluate_session(transcript)
    await quota.record_usage(user["id"], tok_in, tok_out, 0)

    async with pool().acquire() as conn:
        await conn.execute(
            """UPDATE tutor_sessions SET ended_at=now(), summary_text=$2,
                 error_patterns=$3 WHERE id=$1""",
            session_id, data.get("summary"),
            json.dumps(data.get("error_patterns", [])),
        )
        lesson_id = await conn.fetchval(
            "SELECT lesson_id FROM tutor_sessions WHERE id=$1", session_id)
        score = data.get("lesson_score")
        if lesson_id and isinstance(score, (int, float)):
            status = "completed" if score >= 0.7 else "in_progress"
            await conn.execute(
                """UPDATE user_lessons SET score=$3, status=$4,
                     completed_at = CASE WHEN $4='completed' THEN now() END
                   WHERE user_id=$1 AND lesson_id=$2""",
                user["id"], lesson_id, float(score), status,
            )
    # Level changes: deliberately NOT automatic per session. Run a periodic job
    # that raises/lowers level_estimate only after 3+ consistent recommendations.
    return {"summary": data.get("summary", "")}
