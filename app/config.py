import os

DATABASE_URL = os.environ["DATABASE_URL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TUTOR_MODEL = os.environ.get("TUTOR_MODEL", "claude-haiku-4-5-20251001")
EVAL_MODEL = os.environ.get("EVAL_MODEL", "claude-sonnet-4-6")
DAILY_AI_MINUTES = float(os.environ.get("DAILY_AI_MINUTES", "90"))
SESSION_MAX_TURNS = int(os.environ.get("SESSION_MAX_TURNS", "120"))
COOKIE_SECRET = os.environ["COOKIE_SECRET"]
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
SESSION_TTL_DAYS = 30
# Board export for the tracker (docs/HARADA_BOARD_CONTRACT.md). Empty = off.
HARADA_EXPORT_PATH = os.environ.get("HARADA_EXPORT_PATH", "")
# Pin the export to one users.id; unset = export only while exactly one account exists.
HARADA_EXPORT_USER_ID = int(os.environ["HARADA_EXPORT_USER_ID"]) \
    if os.environ.get("HARADA_EXPORT_USER_ID") else None
