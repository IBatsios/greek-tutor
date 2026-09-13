"""Test bootstrap.

app.config reads its settings from the environment at import time, so the
required variables are filled in here before any test imports the app.
Set TEST_DATABASE_URL to a Postgres with migrations 001–003 and both seeds
applied to run the database-backed tests; without it they are skipped.
"""
import os

_test_db = os.environ.get("TEST_DATABASE_URL")
if _test_db:
    os.environ["DATABASE_URL"] = _test_db
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost:1/unused")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-never-sent")
os.environ.setdefault("COOKIE_SECRET", "test-cookie-secret")
