"""HTTP surface for the Harada board. Business rules and SQL live in app/harada.py.

All endpoints take form fields (like /api/session) and return JSON, so the
dashboard can call them with fetch + URLSearchParams exactly as session.html does.
GET /api/harada returns the same payload the export file holds
(docs/HARADA_BOARD_CONTRACT.md).
"""
from __future__ import annotations

from datetime import date

import asyncpg
from fastapi import APIRouter, Depends, Form, HTTPException

from . import harada
from .auth import require_user
from .db import pool
from .harada_metrics import ROUTINE_KEY

router = APIRouter(prefix="/api/harada")
MAX_TEXT = 2000  # goal / cycle text cap
MAX_CYCLE_DAYS = 365


@router.get("")
async def board(user=Depends(require_user)):
    return await harada.board_payload(user["id"])


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
    if not 1 <= cycle_days <= MAX_CYCLE_DAYS:
        raise HTTPException(400, f"cycle_days must be between 1 and {MAX_CYCLE_DAYS}.")
    return await harada.set_goal(user["id"], goal_text, cycle_text.strip(), cycle_days,
                                 restart_cycle)


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
    """Daily check sheet. The sheet UI lives in the tracker; this stays as the write path."""
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
