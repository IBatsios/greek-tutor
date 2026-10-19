import os

DATABASE_URL = os.environ["DATABASE_URL"]
# How the app reaches Claude (app/llm.py): "api" = Anthropic API key (default, any
# number of learners); "claude_cli" = the claude binary signed in with your own
# subscription (single learner only — see README).
LLM_BACKEND = os.environ.get("LLM_BACKEND", "api").strip().lower()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # required when LLM_BACKEND=api
# Only for an API key that is not scoped to a workspace: the API then needs the
# workspace to bill (sent as the anthropic-workspace-id header). Empty = not sent.
ANTHROPIC_WORKSPACE_ID = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
CLAUDE_CLI_PATH = os.environ.get("CLAUDE_CLI_PATH", "claude")
CLAUDE_CLI_TIMEOUT = float(os.environ.get("CLAUDE_CLI_TIMEOUT", "120"))
TUTOR_MODEL = os.environ.get("TUTOR_MODEL", "claude-sonnet-5-5")
EVAL_MODEL = os.environ.get("EVAL_MODEL", "claude-sonnet-5-5")
# api backend: how hard the model thinks before answering (low|medium|high|xhigh|max).
# Sonnet 5.5 thinks at "high" when unset, and thinking tokens count against max_tokens.
TUTOR_EFFORT = os.environ.get("TUTOR_EFFORT", "low")
EVAL_EFFORT = os.environ.get("EVAL_EFFORT", "medium")
DAILY_AI_MINUTES = float(os.environ.get("DAILY_AI_MINUTES", "90"))
SESSION_MAX_TURNS = int(os.environ.get("SESSION_MAX_TURNS", "120"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
SESSION_TTL_DAYS = 30
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()  # DEBUG also logs raw model replies
# IANA zone used for every "today" - in Python (app/clock.py) and on every DB
# connection (app/db.py) - so CURRENT_DATE and clock.today() never disagree.
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "UTC")
# Board export for the tracker (docs/HARADA_BOARD_CONTRACT.md). Empty = off.
HARADA_EXPORT_PATH = os.environ.get("HARADA_EXPORT_PATH", "")
# Pin the export to one users.id; unset = export only while exactly one account exists.
HARADA_EXPORT_USER_ID = int(os.environ["HARADA_EXPORT_USER_ID"]) \
    if os.environ.get("HARADA_EXPORT_USER_ID") else None
