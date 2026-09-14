"""The app has one calendar: app.clock. Naive date.today() must not creep back in."""
import re
from datetime import date
from pathlib import Path

from app import clock, config

APP = Path(__file__).resolve().parent.parent / "app"
NAIVE_TODAY = re.compile(r"\bdate\.today\(\)")


def test_today_is_the_configured_zone_date():
    assert clock.today() == clock.now().date()
    assert str(clock.now().tzinfo) == config.APP_TIMEZONE


def test_no_naive_today_in_app_code():
    offenders = [
        p.name for p in APP.glob("*.py")
        if p.name != "clock.py" and NAIVE_TODAY.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"use app.clock.today() instead of date.today() in {offenders}"


def test_today_is_a_date():
    assert isinstance(clock.today(), date)
