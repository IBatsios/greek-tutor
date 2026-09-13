"""Harada engine: load facts from Postgres, rescore the 64 cells, pick the session focus.

Scoring itself is pure and lives in ``harada_metrics``; this module is the I/O
around it plus the business rules that must hold regardless of UI:
at most MAX_FOCUS focus cells, only manual cells can be set by hand, and every
board mutation refreshes the export file the tracker mirrors (``harada_export``).
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import asyncpg

from . import config, harada_export
from . import harada_metrics as hm
from .db import pool

log = logging.getLogger(__name__)

FACT_SESSIONS = 10  # newest ended sessions loaded for scoring
FACT_DAYS = 60  # routine + usage history loaded for scoring
MAX_FOCUS = 5  # Harada's rule: 3–5 live actions. Enforced here, not just in the UI.
MIN_FOCUS = 3
MANUAL_PROGRESS = {"not_started": 0.0, "in_progress": 0.5, "done": 1.0}


class FocusLimitError(ValueError):
    """Raised when a learner tries to focus more than MAX_FOCUS cells."""


class NotManualError(ValueError):
    """Raised when a computed cell's state is set by hand."""


def as_json(value: Any) -> Any:
    """asyncpg hands JSONB back as text unless a codec is installed; accept both."""
    return value if isinstance(value, (dict, list)) else json.loads(value)


# --- board payload + export -------------------------------------------------

_BOARD_SQL = """
SELECT t.id AS theme_id, t.slug, t.name_en, t.name_el,
       a.id, a.slot, a.label, a.measure, a.metric_kind, a.metric_args,
       COALESCE(ua.state, 'not_started') AS state,
       COALESCE(ua.progress, 0) AS progress,
       COALESCE(ua.is_focus, false) AS is_focus,
       ua.updated_at
FROM harada_actions a
JOIN harada_themes t ON t.id = a.theme_id
LEFT JOIN user_harada_actions ua ON ua.action_id = a.id AND ua.user_id = $1
ORDER BY t.id, a.slot
"""
_GOAL_SQL = "SELECT * FROM harada_goals WHERE user_id = $1"


async def board_payload(user_id: int) -> dict[str, Any]:
    """The whole board for one learner: what GET /api/harada and the export file return."""
    async with pool().acquire() as conn:
        goal = await conn.fetchrow(_GOAL_SQL, user_id)
        rows = await conn.fetch(_BOARD_SQL, user_id)
    return harada_export.build_payload(
        goal, rows, min_focus=MIN_FOCUS, max_focus=MAX_FOCUS, now=datetime.now(UTC),
    )


async def _other_learners_exist(user_id: int) -> bool:
    return await pool().fetchval("SELECT EXISTS (SELECT 1 FROM users WHERE id <> $1)", user_id)


async def _export(user_id: int) -> None:
    """Refresh the mirror file after a board change. Best effort: never fails the change.

    The file holds one learner's board. Unpinned, it is only written while this is
    the sole account; otherwise one learner's goal and progress would land in a file
    another learner's tracker reads.
    """
    target = harada_export.export_target(user_id=user_id)
    if target is None:
        return
    try:
        if config.HARADA_EXPORT_USER_ID is None and await _other_learners_exist(user_id):
            log.warning(
                "harada: export skipped — more than one learner exists; "
                "set HARADA_EXPORT_USER_ID to the learner whose board %s should hold", target,
            )
            return
        payload = await board_payload(user_id)
        await asyncio.to_thread(harada_export.write, payload, target)
    except Exception:
        log.exception("harada: export to %s failed for user %s", target, user_id)


# --- facts ------------------------------------------------------------------

_SESSIONS_SQL = """
SELECT id, minutes_used, error_patterns
FROM tutor_sessions
WHERE user_id = $1 AND ended_at IS NOT NULL
ORDER BY ended_at DESC LIMIT $2
"""
_TURNS_SQL = """
SELECT session_id, content FROM tutor_turns
WHERE session_id = ANY($1::bigint[]) AND role = 'user'
"""
_NEW_WORDS_SQL = """
SELECT s.id, count(uv.vocab_id) AS n
FROM tutor_sessions s
LEFT JOIN user_vocab uv ON uv.user_id = s.user_id
     AND uv.introduced_at BETWEEN s.started_at AND s.ended_at
WHERE s.id = ANY($1::bigint[])
GROUP BY s.id
"""


async def _session_facts(conn: asyncpg.Connection, user_id: int) -> tuple[hm.SessionFact, ...]:
    sessions = await conn.fetch(_SESSIONS_SQL, user_id, FACT_SESSIONS)
    ids = [s["id"] for s in sessions]
    turns_by_session: dict[int, list[str]] = defaultdict(list)
    for t in await conn.fetch(_TURNS_SQL, ids):
        turns_by_session[t["session_id"]].append(t["content"])
    new_words = {r["id"]: int(r["n"]) for r in await conn.fetch(_NEW_WORDS_SQL, ids)}
    return tuple(
        hm.SessionFact(
            minutes_used=float(s["minutes_used"]),
            new_words=new_words.get(s["id"], 0),
            greek_only=hm.is_greek_only(turns_by_session.get(s["id"], [])),
            error_patterns=tuple(str(e) for e in as_json(s["error_patterns"])),
        )
        for s in sessions
    )


async def load_facts(user_id: int) -> hm.Facts:
    """Everything the scorers need for one learner, in a handful of queries."""
    today = date.today()
    since = today - timedelta(days=FACT_DAYS)
    async with pool().acquire() as conn:
        lessons = await conn.fetch(
            """SELECT l.level, l.seq, ul.score FROM user_lessons ul
               JOIN lessons l ON l.id = ul.lesson_id WHERE ul.user_id = $1""",
            user_id,
        )
        vocab = await conn.fetch(
            """SELECT uv.times_seen, uv.times_correct, v.tags FROM user_vocab uv
               JOIN vocab_items v ON v.id = uv.vocab_id WHERE uv.user_id = $1""",
            user_id,
        )
        sessions = await _session_facts(conn, user_id)
        routine = await conn.fetch(
            "SELECT log_date, checks FROM routine_log WHERE user_id = $1 AND log_date >= $2",
            user_id, since,
        )
        ledger = await conn.fetch(
            """SELECT usage_date, ai_minutes FROM usage_ledger
               WHERE user_id = $1 AND usage_date >= $2""",
            user_id, since,
        )
    return hm.Facts(
        today=today,
        lesson_scores={(r["level"], r["seq"]): r["score"] for r in lessons},
        vocab=tuple(
            hm.VocabFact(r["times_seen"], r["times_correct"], tuple(r["tags"] or ())) for r in vocab
        ),
        sessions=sessions,
        routine={r["log_date"]: as_json(r["checks"]) for r in routine},
        ledger={r["usage_date"]: float(r["ai_minutes"]) for r in ledger},
    )


# --- recompute --------------------------------------------------------------

_UPSERT_PROGRESS = """
INSERT INTO user_harada_actions (user_id, action_id, progress, state)
VALUES ($1, $2, $3, $4)
ON CONFLICT (user_id, action_id) DO UPDATE SET
  progress = EXCLUDED.progress,
  state = EXCLUDED.state,
  updated_at = CASE WHEN user_harada_actions.progress <> EXCLUDED.progress
                    THEN now() ELSE user_harada_actions.updated_at END
"""


async def recompute(user_id: int) -> int:
    """Rescore every computed cell for one learner. Returns the number of cells written.

    Manual cells are skipped (the learner owns them) and is_focus is never touched.
    A cell whose metric_args cannot be scored is logged and skipped rather than
    failing the whole board.
    """
    facts = await load_facts(user_id)
    actions = await pool().fetch(
        "SELECT id, theme_id, slot, metric_kind, metric_args FROM harada_actions"
    )
    rows: list[tuple[int, int, float, str]] = []
    for a in actions:
        try:
            progress = hm.score(a["metric_kind"], as_json(a["metric_args"]), facts)
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            log.exception(
                "harada: cannot score action %s (theme %s, slot %s)",
                a["id"], a["theme_id"], a["slot"],
            )
            continue
        if progress is None:
            continue
        rows.append((user_id, a["id"], progress, hm.state_for(progress)))
    if rows:
        await pool().executemany(_UPSERT_PROGRESS, rows)
    await _export(user_id)
    return len(rows)


# --- focus ------------------------------------------------------------------


@dataclass(frozen=True)
class FocusPick:
    action_id: int
    theme: str
    label: str
    measure: str
    metric_kind: str
    metric_args: dict[str, Any]
    progress: float
    lesson_id: int | None  # set when the cell maps to a specific lesson to open


_FOCUS_SQL = """
SELECT a.id, a.label, a.measure, a.metric_kind, a.metric_args, t.name_en,
       COALESCE(ua.progress, 0) AS progress
FROM user_harada_actions ua
JOIN harada_actions a ON a.id = ua.action_id
JOIN harada_themes t ON t.id = a.theme_id
WHERE ua.user_id = $1 AND ua.is_focus AND ua.state <> 'done'
ORDER BY ua.progress ASC, ua.updated_at ASC, a.theme_id, a.slot
"""
_ACTION_SQL = """
SELECT a.id, a.label, a.measure, a.metric_kind, a.metric_args, t.name_en,
       COALESCE(ua.progress, 0) AS progress
FROM harada_actions a
JOIN harada_themes t ON t.id = a.theme_id
LEFT JOIN user_harada_actions ua ON ua.action_id = a.id AND ua.user_id = $1
WHERE a.id = $2
"""
_LESSON_FOR_SQL = """
SELECT l.id FROM lessons l
LEFT JOIN user_lessons ul ON ul.lesson_id = l.id AND ul.user_id = $1
WHERE l.level = $2 AND l.seq = ANY($3::int[]) AND COALESCE(ul.score, 0) < $4
ORDER BY l.seq LIMIT 1
"""


async def _lesson_for(user_id: int, args: dict[str, Any]) -> int | None:
    """First lesson in a lesson_score cell the learner has not yet passed."""
    return await pool().fetchval(
        _LESSON_FOR_SQL, user_id, args["level"], [int(s) for s in args["seqs"]], float(args["min"])
    )


async def _to_pick(user_id: int, row: asyncpg.Record) -> FocusPick:
    args = as_json(row["metric_args"])
    lesson_id = await _lesson_for(user_id, args) if row["metric_kind"] == "lesson_score" else None
    return FocusPick(
        action_id=row["id"], theme=row["name_en"], label=row["label"], measure=row["measure"],
        metric_kind=row["metric_kind"], metric_args=args,
        progress=float(row["progress"]), lesson_id=lesson_id,
    )


async def pick_focus(user_id: int) -> FocusPick | None:
    """The weakest focus cell a session can work on, or None (caller falls back to next lesson).

    Ranked by progress ascending, then by how long the cell has been untouched.
    Routine, habit and manual cells are focus targets but never session objectives.
    """
    for row in await pool().fetch(_FOCUS_SQL, user_id):
        if hm.is_sessionable(row["metric_kind"], as_json(row["metric_args"])):
            return await _to_pick(user_id, row)
    return None


async def focus_for_action(user_id: int, action_id: int) -> FocusPick | None:
    """The FocusPick for a specific action, e.g. the one a session was opened on."""
    row = await pool().fetchrow(_ACTION_SQL, user_id, action_id)
    return await _to_pick(user_id, row) if row else None


_KIND_GUIDANCE = {
    "lesson_score": "Work through today's lesson; its score at session close moves this cell.",
    "vocab_count": (
        "Run an SRS-heavy session: review every due word, introduce new ones, "
        "and recycle each at least twice."
    ),
    "vocab_recall": (
        "Drill vocabulary for these topics specifically: {tags}. "
        "Tag every vocab_event with its topic."
    ),
    "error_absent": (
        "Targeted remediation: elicit sentences that force this structure, "
        "correct every slip, and repeat until it is clean."
    ),
}
_FIELD_GUIDANCE = {
    "minutes_used": "Keep the conversation going; a longer session moves this cell.",
    "new_words": "Introduce at least {min} new words this session and log each as 'introduced'.",
    "greek_only": (
        "Zero English this session. If the student slips into English, "
        "restate in Greek and ask them to try again in Greek."
    ),
}


def _guidance(pick: FocusPick) -> str:
    args = pick.metric_args
    if pick.metric_kind == "session_metric":
        template = _FIELD_GUIDANCE.get(args.get("field", ""), "")
    else:
        template = _KIND_GUIDANCE.get(pick.metric_kind, "")
    return template.format(tags=", ".join(args.get("tags", [])), min=args.get("min", ""))


def focus_block(pick: FocusPick) -> str:
    """The CURRENT FOCUS block appended to the tutor's per-user context."""
    return (
        "CURRENT FOCUS (Harada cell — today's primary objective; the lesson is the vehicle)\n"
        f"- Theme: {pick.theme}\n"
        f"- Action: {pick.label}\n"
        f"- Measured by: {pick.measure}\n"
        f"- Progress so far: {pick.progress:.0%}\n"
        f"- Instruction: {_guidance(pick)}\n"
        "Do not move on until this is clean."
    )


# --- learner-driven writes (business rules) ---------------------------------


async def set_focus(user_id: int, action_id: int, on: bool) -> None:
    """Toggle a focus cell. Raises FocusLimitError past MAX_FOCUS live cells."""
    async with pool().acquire() as conn, conn.transaction():
        if on:
            live = await conn.fetchval(
                """SELECT count(*) FROM user_harada_actions
                   WHERE user_id = $1 AND is_focus AND action_id <> $2""",
                user_id, action_id,
            )
            if live >= MAX_FOCUS:
                raise FocusLimitError(f"Harada rule: at most {MAX_FOCUS} focus actions at once.")
        await conn.execute(
            """INSERT INTO user_harada_actions (user_id, action_id, is_focus)
               VALUES ($1, $2, $3)
               ON CONFLICT (user_id, action_id) DO UPDATE SET is_focus = EXCLUDED.is_focus""",
            user_id, action_id, on,
        )
    await _export(user_id)


async def set_goal(user_id: int, goal_text: str, cycle_text: str, cycle_days: int,
                   restart_cycle: bool) -> dict[str, Any]:
    """Upsert the central goal and cycle; restart_cycle resets cycle_start to today."""
    row = await pool().fetchrow(
        """INSERT INTO harada_goals (user_id, goal_text, cycle_text, cycle_days)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (user_id) DO UPDATE SET
             goal_text = EXCLUDED.goal_text, cycle_text = EXCLUDED.cycle_text,
             cycle_days = EXCLUDED.cycle_days,
             cycle_start = CASE WHEN $5 THEN CURRENT_DATE ELSE harada_goals.cycle_start END
           RETURNING *""",
        user_id, goal_text, cycle_text, cycle_days, restart_cycle,
    )
    await _export(user_id)
    goal = harada_export.goal_dict(row, today=date.today())
    assert goal is not None  # RETURNING * on an upsert always yields the row
    return goal


async def set_manual_state(user_id: int, action_id: int, state: str) -> None:
    """Set a manual cell's state by hand. Raises NotManualError for computed cells."""
    if state not in MANUAL_PROGRESS:
        raise ValueError(f"unknown state {state!r}")
    kind = await pool().fetchval("SELECT metric_kind FROM harada_actions WHERE id = $1", action_id)
    if kind is None:
        raise LookupError(f"no action {action_id}")
    if kind != "manual":
        raise NotManualError("This cell is scored from your sessions; it cannot be set by hand.")
    await pool().execute(
        """INSERT INTO user_harada_actions (user_id, action_id, state, progress)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (user_id, action_id) DO UPDATE SET
             state = EXCLUDED.state, progress = EXCLUDED.progress, updated_at = now()""",
        user_id, action_id, state, MANUAL_PROGRESS[state],
    )
    await _export(user_id)
