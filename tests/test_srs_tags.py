"""clean_tag guards the SQL array append against whatever the model puts in "tag"."""
import pytest

from app.srs import clean_tag


@pytest.mark.parametrize("raw,expected", [
    ("cafe", "cafe"), (" Market ", "market"), ("home-life", "home-life"),
    ("cafe\n", "cafe"),        # surrounding whitespace is stripped first
    ("ca\nfe", None),          # but nothing non-slug survives inside
    ("", None), (None, None), (42, None), ("no spaces", None),
    ("x" * 40, None), ("Ω", None),
])
def test_clean_tag(raw, expected):
    assert clean_tag(raw) == expected
