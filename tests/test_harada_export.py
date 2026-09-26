"""The board export is the contract other apps read (docs/HARADA_BOARD_CONTRACT.md).

build_payload is pure, so the shape is pinned here without a database; the
file writer is exercised against a temp directory.
"""
import json
from datetime import UTC, date, datetime

import pytest

from app import harada_export as hx

NOW = datetime(2026, 9, 13, 14, 30, tzinfo=UTC)
TODAY = date(2026, 9, 13)


def _row(theme=0, slot=0, action_id=1, kind="lesson_score", args=None, state="not_started",
         progress=0.0, is_focus=False, updated_at=None):
    return {
        "theme_id": theme, "slug": f"theme{theme}", "name_en": f"Theme {theme}",
        "name_el": f"Θέμα {theme}", "id": action_id, "slot": slot, "label": f"Action {action_id}",
        "measure": "measured somehow", "metric_kind": kind,
        "metric_args": json.dumps(args if args is not None else {}),
        "state": state, "progress": progress, "is_focus": is_focus, "updated_at": updated_at,
    }


def _goal(**over):
    base = {"user_id": 7, "goal_text": "Speak Greek", "cycle_text": "Finish A1",
            "cycle_start": date(2026, 9, 1), "cycle_days": 90}
    return {**base, **over}


def _payload(rows, goal=None):
    return hx.build_payload(goal, rows, min_focus=3, max_focus=5, now=NOW)


# --- shape -----------------------------------------------------------------------


def test_payload_is_versioned_and_stamped():
    p = _payload([_row()])

    assert p["schema"] == hx.SCHEMA == 1
    assert p["board"] == "greek"
    assert p["generated_at"] == "2026-09-13T14:30:00+00:00"
    assert p["focus"] == {"count": 0, "min": 3, "max": 5}


def test_themes_are_ordered_by_slot_with_their_actions():
    rows = [_row(theme=1, slot=0, action_id=9), _row(theme=0, slot=1, action_id=2),
            _row(theme=0, slot=0, action_id=1)]

    themes = _payload(rows)["themes"]

    assert [t["slot"] for t in themes] == [0, 1]
    assert themes[0]["slug"] == "theme0" and themes[0]["name_el"] == "Θέμα 0"
    assert [a["slot"] for a in themes[0]["actions"]] == [0, 1]
    assert [a["id"] for a in themes[1]["actions"]] == [9]


def test_action_fields_and_json_safe_types():
    stamp = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
    row = _row(kind="routine_days", args={"key": "listening_10", "days": 6, "window": 7},
               state="in_progress", progress=0.66666, is_focus=True, updated_at=stamp)

    action = _payload([row])["themes"][0]["actions"][0]

    assert action == {
        "id": 1, "slot": 0, "label": "Action 1", "measure": "measured somehow",
        "kind": "routine_days", "is_manual": False, "routine_key": "listening_10",
        "state": "in_progress", "progress": 0.667, "is_focus": True,
        "updated_at": "2026-09-12T08:00:00+00:00",
    }
    json.dumps(_payload([row]))  # nothing left that json cannot serialize


def test_routine_key_is_only_set_for_routine_cells():
    rows = [_row(action_id=1, kind="manual"), _row(action_id=2, slot=1, kind="lesson_score",
                                                    args={"level": "A1", "seqs": [1], "min": 0.9})]

    actions = _payload(rows)["themes"][0]["actions"]

    assert actions[0]["is_manual"] is True and actions[0]["routine_key"] is None
    assert actions[1]["routine_key"] is None
    assert "metric_args" not in actions[1]  # internal scoring detail stays internal


def test_totals_and_theme_done_counts():
    rows = [_row(action_id=1, slot=0, state="done", progress=1.0, is_focus=True),
            _row(action_id=2, slot=1, state="in_progress", progress=0.4, is_focus=True),
            _row(action_id=3, slot=2, kind="manual"),
            _row(action_id=4, theme=1, slot=0, state="done", progress=1.0)]

    p = _payload(rows)

    assert p["totals"] == {"actions": 4, "done": 2, "in_progress": 1, "not_started": 1,
                           "computed": 3, "manual": 1}
    assert p["focus"]["count"] == 2
    assert [t["done"] for t in p["themes"]] == [1, 1]


# --- goal --------------------------------------------------------------------------


def test_goal_is_null_until_set():
    assert _payload([_row()])["goal"] is None


def test_goal_dates_are_iso_and_cycle_is_derived():
    goal = hx.goal_dict(_goal(), today=TODAY)

    assert goal == {
        "goal_text": "Speak Greek", "cycle_text": "Finish A1",
        "cycle_start": "2026-09-01", "cycle_days": 90, "cycle_end": "2026-11-30",
        "cycle_day": 13, "days_left": 78,
    }
    assert "user_id" not in goal


def test_cycle_past_its_end_reports_negative_days_left():
    goal = hx.goal_dict(_goal(cycle_start=date(2026, 1, 1), cycle_days=30), today=TODAY)

    assert goal["cycle_end"] == "2026-01-31"
    assert goal["days_left"] < 0


# --- file ----------------------------------------------------------------------------


def test_write_creates_parent_and_leaves_no_temp_file(tmp_path):
    target = tmp_path / "mirror" / "harada-greek.json"

    hx.write({"schema": 1, "board": "greek"}, target)

    assert json.loads(target.read_text(encoding="utf-8")) == {"schema": 1, "board": "greek"}
    assert [p.name for p in target.parent.iterdir()] == ["harada-greek.json"]


def test_write_replaces_the_previous_export(tmp_path):
    target = tmp_path / "harada-greek.json"
    hx.write({"v": 1}, target)

    hx.write({"v": 2}, target)

    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 2}


def test_write_keeps_greek_readable(tmp_path):
    target = tmp_path / "x.json"

    hx.write({"name_el": "Λεξιλόγιο"}, target)

    assert "Λεξιλόγιο" in target.read_text(encoding="utf-8")


def test_export_is_skipped_without_a_path(monkeypatch):
    monkeypatch.setattr(hx.config, "HARADA_EXPORT_PATH", "")

    assert hx.export_target(user_id=1) is None


def test_export_is_pinned_to_one_learner_when_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(hx.config, "HARADA_EXPORT_PATH", str(tmp_path / "b.json"))
    monkeypatch.setattr(hx.config, "HARADA_EXPORT_USER_ID", 42)

    assert hx.export_target(user_id=42) == tmp_path / "b.json"
    assert hx.export_target(user_id=43) is None


def test_export_follows_any_learner_when_not_pinned(monkeypatch, tmp_path):
    monkeypatch.setattr(hx.config, "HARADA_EXPORT_PATH", str(tmp_path / "b.json"))
    monkeypatch.setattr(hx.config, "HARADA_EXPORT_USER_ID", None)

    assert hx.export_target(user_id=43) == tmp_path / "b.json"


@pytest.mark.parametrize("progress, expected", [(0, 0.0), (1, 1.0), (0.12345, 0.123)])
def test_progress_is_rounded_to_three_places(progress, expected):
    assert _payload([_row(progress=progress)])["themes"][0]["actions"][0]["progress"] == expected
