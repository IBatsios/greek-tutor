"""Database-backed tests for the Harada engine. Skipped unless TEST_DATABASE_URL is set.

Expects migrations 001–003 plus seed/lessons_a1.sql and seed/harada.sql applied.
Each test creates its own user and deletes it afterwards (everything cascades).
"""
import json
import os
import secrets
from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set"
)

from app import db, harada  # noqa: E402  (after the skip guard; conftest sets env)


@pytest.fixture
async def user_id():
    await db.init_pool()
    p = db.pool()
    uid = await p.fetchval(
        "INSERT INTO users (email, password_hash) VALUES ($1, 'x') RETURNING id",
        f"harada-{secrets.token_hex(4)}@test.invalid",
    )
    await p.execute("INSERT INTO profiles (user_id, display_name) VALUES ($1, 'Test')", uid)
    try:
        yield uid
    finally:
        await p.execute("DELETE FROM users WHERE id = $1", uid)
        await db.close_pool()


async def _action_id(theme: int, slot: int) -> int:
    return await db.pool().fetchval(
        "SELECT id FROM harada_actions WHERE theme_id = $1 AND slot = $2", theme, slot)


async def _lesson_id(seq: int) -> int:
    return await db.pool().fetchval(
        "SELECT id FROM lessons WHERE level = 'A1' AND seq = $1", seq)


async def _cell(uid: int, theme: int, slot: int):
    return await db.pool().fetchrow(
        """SELECT ua.state, ua.progress, ua.is_focus FROM user_harada_actions ua
           JOIN harada_actions a ON a.id = ua.action_id
           WHERE ua.user_id = $1 AND a.theme_id = $2 AND a.slot = $3""",
        uid, theme, slot,
    )


async def _score_lesson(uid: int, seq: int, score: float) -> None:
    await db.pool().execute(
        """INSERT INTO user_lessons (user_id, lesson_id, status, score, completed_at)
           VALUES ($1, $2, 'completed', $3, now())""",
        uid, await _lesson_id(seq), score,
    )


async def _ended_session(uid: int, minutes: float, errors: list[str], turns: list[str]) -> int:
    p = db.pool()
    started = datetime.now(UTC) - timedelta(minutes=minutes + 1)
    sid = await p.fetchval(
        """INSERT INTO tutor_sessions (user_id, started_at, ended_at, minutes_used, error_patterns)
           VALUES ($1, $2, now(), $3, $4) RETURNING id""",
        uid, started, minutes, json.dumps(errors),
    )
    for t in turns:
        await p.execute(
            "INSERT INTO tutor_turns (session_id, role, content) VALUES ($1, 'user', $2)", sid, t)
    return sid


# --- recompute -----------------------------------------------------------------


async def test_recompute_writes_every_computed_cell_and_no_manual_ones(user_id):
    written = await harada.recompute(user_id)

    rows = await db.pool().fetch(
        """SELECT a.metric_kind, ua.state FROM user_harada_actions ua
           JOIN harada_actions a ON a.id = ua.action_id WHERE ua.user_id = $1""", user_id)
    assert written == 40 == len(rows)
    assert all(r["state"] == "not_started" for r in rows)
    assert not any(r["metric_kind"] == "manual" for r in rows)


async def test_passing_both_lessons_completes_the_grammar_cell(user_id):
    await _score_lesson(user_id, 3, 0.95)
    await _score_lesson(user_id, 7, 0.92)

    await harada.recompute(user_id)

    cell = await _cell(user_id, 2, 0)  # είμαι / έχω: lessons 3 and 7 at ≥0.9
    assert cell["state"] == "done" and cell["progress"] == pytest.approx(1.0)


async def test_error_patterns_and_session_metrics_move_cells(user_id):
    await _ended_session(user_id, 20, ["gender agreement"], ["Γεια σου", "Είμαι καλά"])
    await _ended_session(user_id, 5, [], ["Γεια σου", "sorry what?"])

    await harada.recompute(user_id)

    gender = await _cell(user_id, 2, 3)     # error_absent over 5 sessions: 1 clean of 2
    minutes = await _cell(user_id, 4, 0)    # minutes ≥15 over 5 sessions: 1.0 + 0.33
    greek = await _cell(user_id, 3, 6)      # greek_only over 5 sessions: 1 clean of 2
    assert gender["progress"] == pytest.approx(0.2)
    assert minutes["progress"] == pytest.approx((1.0 + 5 / 15) / 5, abs=1e-6)
    assert greek["progress"] == pytest.approx(0.2)
    assert greek["state"] == "in_progress"


async def test_recompute_keeps_focus_flags_and_manual_state(user_id):
    goal_cell = await _action_id(4, 7)          # manual: THE GOAL
    focus_cell = await _action_id(2, 3)
    await harada.set_manual_state(user_id, goal_cell, "in_progress")
    await harada.set_focus(user_id, focus_cell, True)

    await harada.recompute(user_id)

    assert (await _cell(user_id, 4, 7))["state"] == "in_progress"
    assert (await _cell(user_id, 2, 3))["is_focus"] is True


# --- focus -----------------------------------------------------------------------


async def test_pick_focus_skips_habit_cells_and_maps_lessons(user_id):
    await harada.set_focus(user_id, await _action_id(7, 1), True)   # no_double_gap: not sessionable
    await harada.set_focus(user_id, await _action_id(2, 1), True)   # -ω/-άω verbs: lessons 9, 16
    await _score_lesson(user_id, 9, 0.95)
    await harada.recompute(user_id)

    pick = await harada.pick_focus(user_id)

    assert pick is not None
    assert pick.action_id == await _action_id(2, 1)
    assert pick.lesson_id == await _lesson_id(16)   # lesson 9 already passed
    assert pick.progress == pytest.approx(0.5)
    assert "CURRENT FOCUS" in harada.focus_block(pick)
    assert pick.label in harada.focus_block(pick)


async def test_pick_focus_prefers_the_weakest_cell(user_id):
    await harada.set_focus(user_id, await _action_id(2, 0), True)   # lessons 3, 7
    await harada.set_focus(user_id, await _action_id(2, 5), True)   # lesson 19
    await _score_lesson(user_id, 3, 0.95)
    await harada.recompute(user_id)

    pick = await harada.pick_focus(user_id)

    assert pick.action_id == await _action_id(2, 5)   # 0.0 beats 0.5


async def test_pick_focus_is_none_without_focus_cells(user_id):
    assert await harada.pick_focus(user_id) is None


async def test_focus_for_action_returns_the_session_cell(user_id):
    aid = await _action_id(1, 6)   # vocab_recall on the 8 topic clusters

    pick = await harada.focus_for_action(user_id, aid)

    assert pick.metric_kind == "vocab_recall" and pick.lesson_id is None
    assert "cafe, market" in harada.focus_block(pick)


async def test_focus_limit_is_enforced(user_id):
    for slot in range(harada.MAX_FOCUS):
        await harada.set_focus(user_id, await _action_id(5, slot), True)

    with pytest.raises(harada.FocusLimitError):
        await harada.set_focus(user_id, await _action_id(5, 5), True)

    await harada.set_focus(user_id, await _action_id(5, 0), False)
    await harada.set_focus(user_id, await _action_id(5, 5), True)   # room again


# --- manual state -------------------------------------------------------------------


async def test_only_manual_cells_can_be_set_by_hand(user_id):
    await harada.set_manual_state(user_id, await _action_id(7, 6), "done")
    assert (await _cell(user_id, 7, 6))["progress"] == pytest.approx(1.0)

    with pytest.raises(harada.NotManualError):
        await harada.set_manual_state(user_id, await _action_id(2, 0), "done")
    with pytest.raises(LookupError):
        await harada.set_manual_state(user_id, 10**9, "done")
