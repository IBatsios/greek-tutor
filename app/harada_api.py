"""HTTP surface for the Harada board. Business rules live in app/harada.py.

All endpoints take form fields (like /api/session) and return JSON, so the
dashboard can call them with fetch + URLSearchParams exactly as session.html does.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, Form, HTTPException

from . import harada
from .auth import require_user
from .db import pool
from .harada_metrics import ROUTINE_KEY

router = APIRouter(prefix="/api/harada")
MAX_TEXT = 2000  # goal / cycle text cap

_BOARD_SQL = """
SELECT t.id AS theme_id, t.slug, t.name_en, t.name_el,
       a.id, a.slot, a.label, a.measure, a.metric_kind,
       COALESCE(ua.state, 'not_started') AS state,
       COALESCE(ua.progress, 0) AS progress,
       COALESCE(ua.is_focus, false) AS is_focus
FROM harada_actions a
JOIN harada_themes t ON t.id = a.theme_id
LEFT JOIN user_harada_actions ua ON ua.action_id = a.id AND ua.user_id = $1
ORDER BY t.id, a.slot
"""


def _cell(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"], "slot": row["slot"], "label": row["label"], "measure": row["measure"],
        "kind": row["metric_kind"], "is_manual": row["metric_kind"] == "manual",
        "state": row["state"], "progress": round(float(row["progress"]), 3),
        "is_focus": row["is_focus"],
    }


async def _board(user_id: int) -> dict[str, Any]:
    themes: dict[int, dict[str, Any]] = {}
    for row in await pool().fetch(_BOARD_SQL, user_id):
        theme = themes.setdefault(row["theme_id"], {
            "id": row["theme_id"], "slug": row["slug"], "name_en": row["name_en"],
            "name_el": row["name_el"], "done": 0, "actions": [],
        })
        cell = _cell(row)
        theme["actions"].append(cell)
        theme["done"] += cell["state"] == "done"
    goal = await pool().fetchrow("SELECT * FROM harada_goals WHERE user_id = $1", user_id)
    focus_count = sum(c["is_focus"] for t in themes.values() for c in t["actions"])
    return {
        "goal": dict(goal) if goal else None,
        "focus_count": focus_count, "min_focus": harada.MIN_FOCUS, "max_focus": harada.MAX_FOCUS,
        "themes": [themes[k] for k in sorted(themes)],
    }


@router.get("")
async def board(user=Depends(require_user)):
    return await _board(user["id"])


@router.post("/goal")
async def set_goal(goal_text: str = Form(...), cycle_text: str = Form(""),
                   cycle_days: int = Form(90), restart_cycle: bool = Form(False),
                   user=Depends(require_user)):
    """Upsert the central goal. restart_cycle=true resets cycle_start to today."""
    goal_text = goal_text.strip()
    if not goal_text:
        raise HTTPException(400, "Goal text is required.")
    if len(goal_text) > MAX_TEXT or len(cycle_text) > MAX_TEXT:
        raise HTTPException(400, f"Text fields are capped at {MAX_TEXT} characters.")
    if not 1 <= cycle_days <= 365:
        raise HTTPException(400, "cycle_days must be between 1 and 365.")
    row = await pool().fetchrow(
        """INSERT INTO harada_goals (user_id, goal_text, cycle_text, cycle_days)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (user_id) DO UPDATE SET
             goal_text = EXCLUDED.goal_text, cycle_text = EXCLUDED.cycle_text,
             cycle_days = EXCLUDED.cycle_days,
             cycle_start = CASE WHEN $5 THEN CURRENT_DATE ELSE harada_goals.cycle_start END
           RETURNING *""",
        user["id"], goal_text, cycle_text.strip(), cycle_days, restart_cycle,
    )
    return dict(row)


@router.post("/action/{action_id}/focus")
async def set_focus(action_id: int, on: bool = Form(...), user=Depends(require_user)):
    try:
        await harada.set_focus(user["id"], action_id, on)
    except harada.FocusLimitError as e:
        raise HTTPException(409, str(e)) from e
    except asyncpg.ForeignKeyViolationError as e:
        raise HTTPException(404, "No such action.") from e
    return {"action_id": action_id, "is_focus": on}


@router.post("/action/{action_id}/state")
async def set_state(action_id: int, state: str = Form(...), user=Depends(require_user)):
    if state not in harada.MANUAL_PROGRESS:
        raise HTTPException(400, "state must be not_started, in_progress or done.")
    try:
        await harada.set_manual_state(user["id"], action_id, state)
    except LookupError as e:
        raise HTTPException(404, "No such action.") from e
    except harada.NotManualError as e:
        raise HTTPException(409, str(e)) from e
    return {"action_id": action_id, "state": state}


@router.post("/routine")
async def log_routine(key: str = Form(...), checked: bool = Form(True),
                      log_date: date | None = Form(None), user=Depends(require_user)):
    if not ROUTINE_KEY.match(key):
        raise HTTPException(400, "key must be a short snake_case identifier.")
    day = log_date or date.today()
    checks = await pool().fetchval(
        """INSERT INTO routine_log (user_id, log_date, checks)
           VALUES ($1, $2, jsonb_build_object($3::text, $4::boolean))
           ON CONFLICT (user_id, log_date) DO UPDATE SET
             checks = routine_log.checks || jsonb_build_object($3::text, $4::boolean)
           RETURNING checks""",
        user["id"], day, key, checked,
    )
    return {"log_date": day.isoformat(), "checks": harada.as_json(checks)}


@router.post("/recompute")
async def recompute(user=Depends(require_user)):
    return {"cells": await harada.recompute(user["id"])}
