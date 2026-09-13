"""The eval model's lesson_score is untrusted input; it must land in [0, 1] or be dropped."""
import pytest

from app.tutor import _clamped_score


@pytest.mark.parametrize("raw,expected", [
    (0.85, 0.85), (0, 0.0), (1, 1.0), (1.0, 1.0),
    (95, 0.95),            # percentage reported as a number
    (100, 1.0),
    (250, 1.0),            # nonsense above 100 clamps rather than poisons
    (-0.3, 0.0),
    ("0.9", None), (None, None), (True, None), ([0.9], None),
])
def test_clamped_score(raw, expected):
    assert _clamped_score(raw) == (pytest.approx(expected) if expected is not None else None)
