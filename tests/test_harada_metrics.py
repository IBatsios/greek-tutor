"""Unit tests for the pure Harada scorers. No database, no network."""
from datetime import date, timedelta

import pytest

from app import harada_metrics as hm

TODAY = date(2026, 9, 13)


def _facts(**kwargs) -> hm.Facts:
    return hm.Facts(today=TODAY, **kwargs)


def _days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


# --- greek-only detection ------------------------------------------------------


def test_greek_only_when_no_latin_words():
    assert hm.is_greek_only(["Γεια σου! Τι κάνεις;", "Είμαι καλά, ευχαριστώ."]) is True


def test_not_greek_only_when_an_english_word_appears():
    assert hm.is_greek_only(["Γεια σου", "sorry, what does that mean?"]) is False


def test_short_latin_runs_are_ignored():
    assert hm.is_greek_only(["ok Γεια σου A1"]) is True


def test_no_turns_is_not_greek_only():
    assert hm.is_greek_only([]) is False


# --- lesson_score ----------------------------------------------------------------


def test_lesson_score_is_zero_with_no_scores():
    args = {"level": "A1", "seqs": [3, 7], "min": 0.9}
    assert hm.score("lesson_score", args, _facts()) == 0.0


def test_lesson_score_averages_clipped_ratios_across_lessons():
    facts = _facts(lesson_scores={("A1", 3): 0.95, ("A1", 7): 0.45})
    args = {"level": "A1", "seqs": [3, 7], "min": 0.9}
    assert hm.score("lesson_score", args, facts) == pytest.approx(0.75)


def test_lesson_score_done_only_when_every_lesson_meets_min():
    facts = _facts(lesson_scores={("A1", 3): 0.9, ("A1", 7): 1.0})
    args = {"level": "A1", "seqs": [3, 7], "min": 0.9}
    assert hm.state_for(hm.score("lesson_score", args, facts)) == "done"


def test_lesson_score_ignores_other_levels():
    facts = _facts(lesson_scores={("A2", 3): 1.0})
    assert hm.score("lesson_score", {"level": "A1", "seqs": [3], "min": 0.9}, facts) == 0.0


# --- vocab_count / vocab_recall ----------------------------------------------------


def test_vocab_count_counts_only_words_held_at_recall_and_seen_enough():
    facts = _facts(vocab=(
        hm.VocabFact(times_seen=5, times_correct=5),   # held
        hm.VocabFact(times_seen=4, times_correct=3),   # 75% < 80%
        hm.VocabFact(times_seen=1, times_correct=1),   # seen once: not "held"
        hm.VocabFact(times_seen=0, times_correct=0),
    ))
    assert hm.score("vocab_count", {"n": 4, "recall": 0.8}, facts) == pytest.approx(0.25)


def test_vocab_count_clips_at_one():
    facts = _facts(vocab=tuple(hm.VocabFact(3, 3) for _ in range(10)))
    assert hm.score("vocab_count", {"n": 5, "recall": 0.8}, facts) == 1.0


def test_vocab_recall_averages_progress_per_tag():
    facts = _facts(vocab=(
        hm.VocabFact(3, 3, tags=("cafe",)),
        hm.VocabFact(3, 3, tags=("cafe", "market")),
        hm.VocabFact(3, 1, tags=("market",)),
    ))
    args = {"tags": ["cafe", "market"], "n": 2, "recall": 0.8}
    assert hm.score("vocab_recall", args, facts) == pytest.approx(0.75)


# --- error_absent ------------------------------------------------------------------


def test_error_absent_cannot_complete_with_fewer_sessions_than_window():
    facts = _facts(sessions=(hm.SessionFact(), hm.SessionFact()))
    assert hm.score("error_absent", {"patterns": ["gender"], "sessions": 5}, facts) == 0.4


def test_error_absent_matches_case_insensitive_substrings():
    facts = _facts(sessions=(
        hm.SessionFact(error_patterns=("Gender Agreement",)),
        hm.SessionFact(error_patterns=("final sigma",)),
    ))
    assert hm.score("error_absent", {"patterns": ["gender"], "sessions": 2}, facts) == 0.5


def test_error_absent_only_looks_at_the_most_recent_sessions():
    old_slip = hm.SessionFact(error_patterns=("gender",))
    facts = _facts(sessions=(hm.SessionFact(), hm.SessionFact(), old_slip))
    assert hm.score("error_absent", {"patterns": ["gender"], "sessions": 2}, facts) == 1.0


# --- routine_days ------------------------------------------------------------------


def test_routine_days_counts_true_checks_inside_the_window():
    routine = {_days_ago(i): {"listening_10": True} for i in range(6)}
    routine[_days_ago(6)] = {"listening_10": False}
    routine[_days_ago(9)] = {"listening_10": True}  # outside 7-day window
    args = {"key": "listening_10", "days": 6, "window": 7}
    assert hm.score("routine_days", args, _facts(routine=routine)) == 1.0


def test_routine_days_partial_progress():
    routine = {_days_ago(0): {"radio": True}, _days_ago(2): {"radio": True}}
    assert hm.score("routine_days", {"key": "radio", "days": 3, "window": 7},
                    _facts(routine=routine)) == pytest.approx(2 / 3)


# --- session_metric ----------------------------------------------------------------


def test_session_metric_minutes_averages_over_window_even_when_short():
    facts = _facts(sessions=(hm.SessionFact(minutes_used=30), hm.SessionFact(minutes_used=7.5)))
    args = {"field": "minutes_used", "min": 15, "sessions": 5}
    assert hm.score("session_metric", args, facts) == pytest.approx((1.0 + 0.5) / 5)


def test_session_metric_greek_only_counts_clean_sessions():
    facts = _facts(sessions=(hm.SessionFact(greek_only=True), hm.SessionFact(greek_only=False)))
    args = {"field": "greek_only", "min": 1, "sessions": 2}
    assert hm.score("session_metric", args, facts) == 0.5


def test_session_metric_new_words():
    facts = _facts(sessions=(hm.SessionFact(new_words=10), hm.SessionFact(new_words=5)))
    args = {"field": "new_words", "min": 10, "sessions": 2}
    assert hm.score("session_metric", args, facts) == pytest.approx(0.75)


def test_session_metric_daily_minutes_counts_days_meeting_the_floor():
    ledger = {_days_ago(0): 50.0, _days_ago(1): 44.9, _days_ago(3): 90.0}
    args = {"field": "daily_minutes", "min": 45, "days": 7}
    assert hm.score("session_metric", args, _facts(ledger=ledger)) == pytest.approx(2 / 7)


def test_no_double_gap_is_full_when_never_two_days_missed():
    ledger = {_days_ago(i): 10.0 for i in range(0, 30, 2)}  # every other day
    args = {"field": "no_double_gap", "days": 30}
    assert hm.score("session_metric", args, _facts(ledger=ledger)) == 1.0


def test_no_double_gap_counts_clean_days_since_the_last_gap():
    ledger = {_days_ago(i): 10.0 for i in range(0, 30) if i not in (5, 6)}
    args = {"field": "no_double_gap", "days": 30}
    assert hm.score("session_metric", args, _facts(ledger=ledger)) == pytest.approx(5 / 30)


def test_no_double_gap_for_a_learner_who_started_today():
    args = {"field": "no_double_gap", "days": 30}
    assert hm.score("session_metric", args, _facts(ledger={TODAY: 20.0})) == pytest.approx(1 / 30)


def test_no_double_gap_is_zero_with_no_activity():
    assert hm.score("session_metric", {"field": "no_double_gap", "days": 30}, _facts()) == 0.0


def test_session_metric_rejects_unknown_field():
    with pytest.raises(ValueError):
        hm.score("session_metric", {"field": "nope", "min": 1, "sessions": 1}, _facts())


# --- score / state / sessionable ------------------------------------------------------


def test_manual_cells_are_never_scored():
    assert hm.score("manual", {}, _facts()) is None


def test_unknown_kind_raises():
    with pytest.raises(ValueError):
        hm.score("telepathy", {}, _facts())


@pytest.mark.parametrize("progress,state", [
    (0.0, "not_started"), (0.01, "in_progress"), (0.999, "in_progress"), (1.0, "done"),
])
def test_state_thresholds(progress, state):
    assert hm.state_for(progress) == state


def test_ledger_metrics_are_not_session_objectives():
    assert hm.is_sessionable("session_metric", {"field": "no_double_gap"}) is False
    assert hm.is_sessionable("session_metric", {"field": "minutes_used"}) is True
    assert hm.is_sessionable("routine_days", {"key": "radio"}) is False
    assert hm.is_sessionable("manual", {}) is False
    assert hm.is_sessionable("error_absent", {"patterns": ["gender"]}) is True


# --- validate_args ----------------------------------------------------------------------


@pytest.mark.parametrize("kind,args", [
    ("lesson_score", {"level": "A1", "seqs": [3, 7], "min": 0.9}),
    ("vocab_count", {"n": 500, "recall": 0.8}),
    ("vocab_recall", {"tags": ["cafe"], "n": 40, "recall": 0.8, "min_seen": 3}),
    ("error_absent", {"patterns": ["gender"], "sessions": 5}),
    ("routine_days", {"key": "listening_10", "days": 6, "window": 7}),
    ("session_metric", {"field": "minutes_used", "min": 15, "sessions": 5}),
    ("session_metric", {"field": "daily_minutes", "min": 45, "days": 7}),
    ("session_metric", {"field": "no_double_gap", "days": 30}),
    ("manual", {}),
])
def test_valid_args_pass(kind, args):
    hm.validate_args(kind, args)


@pytest.mark.parametrize("kind,args", [
    ("manual", {"n": 1}),
    ("lesson_score", {"level": "A1", "seqs": [], "min": 0.9}),
    ("lesson_score", {"level": "A1", "seqs": [3], "min": 1.5}),
    ("vocab_count", {"n": 0, "recall": 0.8}),
    ("vocab_recall", {"tags": [], "n": 40, "recall": 0.8}),
    ("error_absent", {"patterns": ["gender"]}),
    ("routine_days", {"key": "Bad Key", "days": 6, "window": 7}),
    ("routine_days", {"key": "radio", "days": 8, "window": 7}),
    ("session_metric", {"field": "minutes_used", "sessions": 5}),
    ("session_metric", {"field": "nope", "days": 7}),
    ("telepathy", {}),
])
def test_invalid_args_raise(kind, args):
    with pytest.raises(ValueError):
        hm.validate_args(kind, args)


def test_routine_key_rejects_trailing_newline():
    assert hm.ROUTINE_KEY.match("signs_aloud") is not None
    assert hm.ROUTINE_KEY.match("signs_aloud\n") is None
