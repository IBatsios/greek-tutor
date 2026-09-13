"""The 64-action seed is data, so its contracts are checked here rather than at runtime."""
import json
import re
from pathlib import Path

import pytest

from app import harada
from app import harada_metrics as hm

ROOT = Path(__file__).resolve().parent.parent
SEED = (ROOT / "seed" / "harada.sql").read_text(encoding="utf-8")
LESSONS = (ROOT / "seed" / "lessons_a1.sql").read_text(encoding="utf-8")

_SQL_STR = r"'((?:[^']|'')*)'"
ACTION_ROW = re.compile(
    rf"\((\d),\s*(\d),\s*{_SQL_STR},\s*{_SQL_STR},\s*'(\w+)',\s*{_SQL_STR}\)"
)
THEME_ROW = re.compile(rf"\((\d),\s*{_SQL_STR},\s*{_SQL_STR},\s*{_SQL_STR}\)")
A1_SEQS = {int(m) for m in re.findall(r"\('A1',\s*(\d+),", LESSONS)}


def _actions() -> list[dict]:
    return [
        {"theme": int(t), "slot": int(s), "label": label.replace("''", "'"),
         "measure": measure, "kind": kind, "args": json.loads(args)}
        for t, s, label, measure, kind, args in ACTION_ROW.findall(SEED)
    ]


def test_seed_has_eight_themes_at_fixed_positions():
    ids = sorted(int(m[0]) for m in THEME_ROW.findall(SEED))
    assert ids == list(range(8))


def test_seed_has_all_sixty_four_cells_exactly_once():
    cells = [(a["theme"], a["slot"]) for a in _actions()]
    assert len(cells) == 64
    assert set(cells) == {(t, s) for t in range(8) for s in range(8)}


@pytest.mark.parametrize("action", _actions(), ids=lambda a: f"{a['theme']}.{a['slot']}")
def test_every_cell_has_valid_metric_args(action):
    hm.validate_args(action["kind"], action["args"])


def test_lesson_cells_only_reference_seeded_a1_lessons():
    for a in _actions():
        if a["kind"] == "lesson_score":
            assert a["args"]["level"] == "A1", a["label"]
            assert set(a["args"]["seqs"]) <= A1_SEQS, a["label"]


def test_manual_cells_are_the_honest_minority():
    manual = [a for a in _actions() if a["kind"] == "manual"]
    assert len(manual) == 24
    for a in manual:
        assert a["measure"], f"manual cell needs a 'measured by' note: {a['label']}"


def test_seed_windows_fit_inside_the_loaded_facts():
    """A window wider than what load_facts fetches would cap the cell below 1.0 forever."""
    for a in _actions():
        args = a["args"]
        assert args.get("sessions", 0) <= harada.FACT_SESSIONS, a["label"]
        assert max(args.get("days", 0), args.get("window", 0)) <= harada.FACT_DAYS, a["label"]


def test_every_cell_has_a_label_and_measure():
    for a in _actions():
        assert a["label"].strip() and a["measure"].strip()
