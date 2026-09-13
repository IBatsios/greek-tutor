"""Pure scoring for Harada cells: facts in, progress out. No I/O in this module.

Every metric_kind has exactly one scorer. ``score()`` returns a float in [0, 1],
or None for cells that cannot be measured automatically (``manual``), which the
learner toggles by hand. Keeping database access out of here is what makes the
engine unit-testable; ``app/harada.py`` loads the Facts and stores the results.

metric_args contracts (checked by ``validate_args``):

    lesson_score    {"level": "A1", "seqs": [3, 7], "min": 0.9}
    vocab_count     {"n": 500, "recall": 0.8, "min_seen": 2}
    vocab_recall    {"tags": ["cafe", ...], "n": 40, "recall": 0.8, "min_seen": 2}
    error_absent    {"patterns": ["gender"], "sessions": 5}
    routine_days    {"key": "listening_10", "days": 6, "window": 7}
    session_metric  {"field": "minutes_used" | "new_words" | "greek_only",
                     "min": 15, "sessions": 5}
                    {"field": "daily_minutes", "min": 45, "days": 7}
                    {"field": "no_double_gap", "days": 30}
    manual          {}

Windows are always "the last N": fewer than N sessions or days means the cell
cannot reach 1.0 yet, so a brand-new learner never sees phantom "done" cells.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

SESSIONABLE_KINDS = frozenset(
    {"lesson_score", "vocab_count", "vocab_recall", "error_absent", "session_metric"}
)
PER_SESSION_FIELDS = frozenset({"minutes_used", "new_words", "greek_only"})
LEDGER_FIELDS = frozenset({"daily_minutes", "no_double_gap"})
DEFAULT_MIN_SEEN = 2
DONE_EPSILON = 1e-9
ROUTINE_KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}\Z")
_LATIN_WORD = re.compile(r"[A-Za-z]{3,}")


@dataclass(frozen=True)
class VocabFact:
    times_seen: int
    times_correct: int
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionFact:
    """One ended tutor session, as the scorers see it."""

    minutes_used: float = 0.0
    new_words: int = 0
    greek_only: bool = False
    error_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Facts:
    """Everything the scorers may consult, loaded once per recompute."""

    today: date
    lesson_scores: dict[tuple[str, int], float | None] = field(default_factory=dict)
    vocab: tuple[VocabFact, ...] = ()
    sessions: tuple[SessionFact, ...] = ()  # ended sessions, newest first
    routine: dict[date, dict[str, bool]] = field(default_factory=dict)
    ledger: dict[date, float] = field(default_factory=dict)  # usage_date -> ai_minutes


# --- helpers ------------------------------------------------------------------


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def is_greek_only(texts: Iterable[str]) -> bool:
    """True when none of the learner's turns contain a Latin-script word.

    Runs of one or two Latin letters are ignored so "ok", "A1" and stray
    abbreviations do not count as English fallback. No turns at all is False.
    """
    turns = list(texts)
    return bool(turns) and not any(_LATIN_WORD.search(t) for t in turns)


def is_sessionable(kind: str, args: dict[str, Any]) -> bool:
    """Can a tutor session work on this cell? Habit/ledger metrics cannot."""
    if kind not in SESSIONABLE_KINDS:
        return False
    return not (kind == "session_metric" and args.get("field") in LEDGER_FIELDS)


def state_for(progress: float) -> str:
    if progress >= 1.0 - DONE_EPSILON:
        return "done"
    return "in_progress" if progress > 0 else "not_started"


# --- scorers ------------------------------------------------------------------


def score_lesson(args: dict[str, Any], facts: Facts) -> float:
    floor = float(args["min"])
    ratios = [
        _clip((facts.lesson_scores.get((args["level"], int(seq))) or 0.0) / floor)
        for seq in args["seqs"]
    ]
    return _mean(ratios)


def _held(v: VocabFact, recall: float, min_seen: int) -> bool:
    return v.times_seen >= min_seen and v.times_correct / v.times_seen >= recall


def score_vocab_count(args: dict[str, Any], facts: Facts) -> float:
    recall = float(args["recall"])
    min_seen = int(args.get("min_seen", DEFAULT_MIN_SEEN))
    held = sum(1 for v in facts.vocab if _held(v, recall, min_seen))
    return _clip(held / int(args["n"]))


def score_vocab_recall(args: dict[str, Any], facts: Facts) -> float:
    recall = float(args["recall"])
    min_seen = int(args.get("min_seen", DEFAULT_MIN_SEEN))
    n = int(args["n"])
    per_tag = [
        _clip(sum(1 for v in facts.vocab if tag in v.tags and _held(v, recall, min_seen)) / n)
        for tag in args["tags"]
    ]
    return _mean(per_tag)


def _mentions(errors: Iterable[str], patterns: list[str]) -> bool:
    lowered = [e.lower() for e in errors]
    return any(p in e for e in lowered for p in patterns)


def score_error_absent(args: dict[str, Any], facts: Facts) -> float:
    patterns = [p.lower() for p in args["patterns"]]
    window = int(args["sessions"])
    recent = facts.sessions[:window]
    clean = sum(1 for s in recent if not _mentions(s.error_patterns, patterns))
    return _clip(clean / window)


def score_routine_days(args: dict[str, Any], facts: Facts) -> float:
    key, days, window = args["key"], int(args["days"]), int(args["window"])
    start = facts.today - timedelta(days=window - 1)
    hits = sum(
        1
        for d, checks in facts.routine.items()
        if start <= d <= facts.today and checks.get(key) is True
    )
    return _clip(hits / days)


def _session_value(s: SessionFact, fld: str) -> float:
    if fld == "greek_only":
        return 1.0 if s.greek_only else 0.0
    return float(getattr(s, fld))


def _per_session(args: dict[str, Any], facts: Facts, fld: str) -> float:
    window, floor = int(args["sessions"]), float(args["min"])
    recent = facts.sessions[:window]
    return _clip(sum(_clip(_session_value(s, fld) / floor) for s in recent) / window)


def _active(facts: Facts, d: date) -> bool:
    return facts.ledger.get(d, 0.0) > 0


def _daily_minutes(args: dict[str, Any], facts: Facts) -> float:
    days, floor = int(args["days"]), float(args["min"])
    hits = sum(
        1 for b in range(days) if facts.ledger.get(facts.today - timedelta(days=b), 0.0) >= floor
    )
    return _clip(hits / days)


def _no_double_gap(args: dict[str, Any], facts: Facts) -> float:
    """Clean run since the last two consecutive inactive days, as a fraction of the window.

    Today is excluded from gap detection (it may not be over yet) but counts
    toward the clean run once it has activity. Only pairs of days that both
    lie inside the window count as a gap, so the window edge never fakes one.
    """
    days = int(args["days"])
    today_bonus = 1 if _active(facts, facts.today) else 0
    for back in range(1, days - 1):
        d = facts.today - timedelta(days=back)
        if not _active(facts, d) and not _active(facts, d - timedelta(days=1)):
            return _clip((back - 1 + today_bonus) / days)
    ever_active = any(_active(facts, facts.today - timedelta(days=b)) for b in range(days))
    return 1.0 if ever_active else 0.0


def score_session_metric(args: dict[str, Any], facts: Facts) -> float:
    fld = args["field"]
    if fld in PER_SESSION_FIELDS:
        return _per_session(args, facts, fld)
    if fld == "daily_minutes":
        return _daily_minutes(args, facts)
    if fld == "no_double_gap":
        return _no_double_gap(args, facts)
    raise ValueError(f"unknown session_metric field {fld!r}")


SCORERS: dict[str, Callable[[dict[str, Any], Facts], float]] = {
    "lesson_score": score_lesson,
    "vocab_count": score_vocab_count,
    "vocab_recall": score_vocab_recall,
    "error_absent": score_error_absent,
    "routine_days": score_routine_days,
    "session_metric": score_session_metric,
}


def score(kind: str, args: dict[str, Any], facts: Facts) -> float | None:
    """Progress in [0, 1] for one cell, or None when the cell is manual."""
    if kind == "manual":
        return None
    try:
        scorer = SCORERS[kind]
    except KeyError:
        raise ValueError(f"unknown metric_kind {kind!r}") from None
    return scorer(args, facts)


# --- validation (used by the seed test and the API) ----------------------------

_REQUIRED: dict[str, tuple[str, ...]] = {
    "lesson_score": ("level", "seqs", "min"),
    "vocab_count": ("n", "recall"),
    "vocab_recall": ("tags", "n", "recall"),
    "error_absent": ("patterns", "sessions"),
    "routine_days": ("key", "days", "window"),
    "session_metric": ("field",),
}


def _positive_int(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


def _positive_number(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be a positive number, got {value!r}")


def _fraction(value: Any, name: str) -> None:
    _positive_number(value, name)
    if value > 1:
        raise ValueError(f"{name} must be in (0, 1], got {value!r}")


def _nonempty_strs(value: Any, name: str) -> None:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
        raise ValueError(f"{name} must be a non-empty list of strings")


def _check_lesson(args: dict[str, Any]) -> None:
    if not isinstance(args["level"], str) or not args["level"]:
        raise ValueError("level must be a non-empty string")
    if not isinstance(args["seqs"], list) or not args["seqs"]:
        raise ValueError("seqs must be a non-empty list")
    for seq in args["seqs"]:
        _positive_int(seq, "seqs[]")
    _fraction(args["min"], "min")


def _check_vocab(args: dict[str, Any]) -> None:
    _positive_int(args["n"], "n")
    _fraction(args["recall"], "recall")
    if "min_seen" in args:
        _positive_int(args["min_seen"], "min_seen")
    if "tags" in args:
        _nonempty_strs(args["tags"], "tags")


def _check_error(args: dict[str, Any]) -> None:
    _nonempty_strs(args["patterns"], "patterns")
    _positive_int(args["sessions"], "sessions")


def _check_routine(args: dict[str, Any]) -> None:
    if not isinstance(args["key"], str) or not ROUTINE_KEY.match(args["key"]):
        raise ValueError(f"key must match {ROUTINE_KEY.pattern}, got {args['key']!r}")
    _positive_int(args["days"], "days")
    _positive_int(args["window"], "window")
    if args["days"] > args["window"]:
        raise ValueError("days cannot exceed window")


def _check_session(args: dict[str, Any]) -> None:
    fld = args["field"]
    if fld in PER_SESSION_FIELDS:
        _positive_int(args.get("sessions"), "sessions")
        _positive_number(args.get("min"), "min")
    elif fld == "daily_minutes":
        _positive_int(args.get("days"), "days")
        _positive_number(args.get("min"), "min")
    elif fld == "no_double_gap":
        _positive_int(args.get("days"), "days")
    else:
        raise ValueError(f"unknown session_metric field {fld!r}")


_CHECKS: dict[str, Callable[[dict[str, Any]], None]] = {
    "lesson_score": _check_lesson,
    "vocab_count": _check_vocab,
    "vocab_recall": _check_vocab,
    "error_absent": _check_error,
    "routine_days": _check_routine,
    "session_metric": _check_session,
}


def validate_args(kind: str, args: dict[str, Any]) -> None:
    """Raise ValueError unless ``args`` satisfies the contract for ``kind``."""
    if kind == "manual":
        if args:
            raise ValueError("manual cells take no metric_args")
        return
    if kind not in _REQUIRED:
        raise ValueError(f"unknown metric_kind {kind!r}")
    if not isinstance(args, dict):
        raise ValueError("metric_args must be an object")
    missing = [k for k in _REQUIRED[kind] if k not in args]
    if missing:
        raise ValueError(f"{kind}: missing {missing}")
    _CHECKS[kind](args)
