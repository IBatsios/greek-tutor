"""Board export: the versioned JSON payload that other apps read.

The same payload serves ``GET /api/harada`` and, when ``HARADA_EXPORT_PATH`` is
set, a file that ``app/harada.py`` rewrites after every board mutation so the
tracker can mirror the board without a session cookie or a second listener.
The shape is documented in docs/HARADA_BOARD_CONTRACT.md; bump ``SCHEMA`` when
it changes incompatibly.

``build_payload`` and ``goal_dict`` are pure so the contract is unit-tested
without a database. Nothing here touches Postgres.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from . import config

SCHEMA = 1
BOARD_SLUG = "greek"
PROGRESS_PLACES = 3


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def _args(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else json.loads(raw)


def goal_dict(row: Mapping[str, Any] | None, *, today: date) -> dict[str, Any] | None:
    """The learner's goal and cycle, with the cycle position derived for consumers."""
    if row is None:
        return None
    start: date = row["cycle_start"]
    days: int = row["cycle_days"]
    elapsed = (today - start).days
    return {
        "goal_text": row["goal_text"],
        "cycle_text": row["cycle_text"],
        "cycle_start": start.isoformat(),
        "cycle_days": days,
        "cycle_end": (start + timedelta(days=days)).isoformat(),
        "cycle_day": elapsed + 1,
        "days_left": days - elapsed,
    }


def _action(row: Mapping[str, Any]) -> dict[str, Any]:
    kind = row["metric_kind"]
    routine_key = _args(row["metric_args"]).get("key") if kind == "routine_days" else None
    return {
        "id": row["id"],
        "slot": row["slot"],
        "label": row["label"],
        "measure": row["measure"],
        "kind": kind,
        "is_manual": kind == "manual",
        "routine_key": routine_key,
        "state": row["state"],
        "progress": round(float(row["progress"]), PROGRESS_PLACES),
        "is_focus": bool(row["is_focus"]),
        "updated_at": _iso(row["updated_at"]),
    }


def build_payload(goal: Mapping[str, Any] | None, rows: Iterable[Mapping[str, Any]], *,
                  min_focus: int, max_focus: int, now: datetime) -> dict[str, Any]:
    """Assemble the board from one goal row and the joined theme/action rows."""
    themes: dict[int, dict[str, Any]] = {}
    totals = {"actions": 0, "done": 0, "in_progress": 0, "not_started": 0,
              "computed": 0, "manual": 0}
    focus_count = 0
    for row in rows:
        theme = themes.setdefault(row["theme_id"], {
            "slot": row["theme_id"], "slug": row["slug"], "name_en": row["name_en"],
            "name_el": row["name_el"], "done": 0, "actions": [],
        })
        action = _action(row)
        theme["actions"].append(action)
        theme["done"] += action["state"] == "done"
        totals["actions"] += 1
        totals[action["state"]] += 1
        totals["manual" if action["is_manual"] else "computed"] += 1
        focus_count += action["is_focus"]
    for theme in themes.values():
        theme["actions"].sort(key=lambda a: a["slot"])
    return {
        "schema": SCHEMA,
        "board": BOARD_SLUG,
        "generated_at": now.isoformat(),
        "goal": goal_dict(goal, today=now.date()),
        "focus": {"count": focus_count, "min": min_focus, "max": max_focus},
        "totals": totals,
        "themes": [themes[k] for k in sorted(themes)],
    }


def export_target(*, user_id: int) -> Path | None:
    """Where this learner's board should be written, or None when export is off.

    The file holds one board. With HARADA_EXPORT_USER_ID unset, harada._export
    additionally refuses to write once a second account exists, so the mirror
    can never carry one learner's data into another learner's tracker.
    """
    if not config.HARADA_EXPORT_PATH:
        return None
    pinned = config.HARADA_EXPORT_USER_ID
    if pinned is not None and pinned != user_id:
        return None
    return Path(config.HARADA_EXPORT_PATH)


def write(payload: Mapping[str, Any], path: Path) -> None:
    """Write the payload atomically: readers see the old file or the new one, never a partial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".harada-", suffix=".json.tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
