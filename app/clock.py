"""One clock for the app and the database.

Postgres evaluates CURRENT_DATE in the connection's TimeZone; Python's
date.today() uses the OS zone. Unless both are the same zone, "today" flips a
day apart every evening (once UTC passes midnight) and the daily quota, SRS due
dates, routine log and Harada cycle drift by a day. APP_TIMEZONE is applied to
every pooled connection (app/db.py) and is the only zone this module uses.
Use clock.today() everywhere instead of date.today().
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import config

ZONE = ZoneInfo(config.APP_TIMEZONE)  # fails fast at import on an unknown zone name


def now() -> datetime:
    return datetime.now(ZONE)


def today() -> date:
    return now().date()
