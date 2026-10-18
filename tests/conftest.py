"""Test bootstrap and the HTTP-level fixtures.

app.config reads its settings from the environment at import time, so the
required variables are filled in here before any test imports the app.
Set TEST_DATABASE_URL to a Postgres with every migration and both seeds
applied to run the database-backed tests; without it they are skipped.
"""
import os
import secrets
from dataclasses import dataclass, field

import pytest

_test_db = os.environ.get("TEST_DATABASE_URL")
if _test_db:
    os.environ["DATABASE_URL"] = _test_db
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost:1/unused")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-never-sent")

TEST_PASSWORD = "correct horse battery"


async def _client():
    """An httpx client over the ASGI app. https, because the session cookie is Secure."""
    import httpx

    from app.main import app

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test")


@pytest.fixture
async def anon_client():
    """No cookie. DB tests only (the pool is opened here; lifespan does not run)."""
    from app import db

    await db.init_pool()
    try:
        async with await _client() as client:
            yield client
    finally:
        await db.close_pool()


@pytest.fixture
async def auth_client(anon_client):
    """A freshly signed-up user's client, cookie kept. The user is deleted afterwards."""
    from app import db

    email = f"http-{secrets.token_hex(4)}@test.invalid"
    r = await anon_client.post("/signup", data={"email": email, "password": TEST_PASSWORD})
    assert r.status_code == 303, r.text
    anon_client.user_id = await db.pool().fetchval("SELECT id FROM users WHERE email=$1", email)
    try:
        yield anon_client
    finally:
        await db.pool().execute("DELETE FROM users WHERE email=$1", email)


# A tutor reply in the contract's shape: prose, then the JSON block parse_reply strips.
CANNED_TUTOR_REPLY = (
    "Γεια σου! (Hello!) Ας ξεκινήσουμε με το αλφάβητο. Διάβασε αυτή τη λέξη: **καφές**.\n\n"
    '```json\n{"vocab_events": [], "error_tags": [], "objective_progress": 0.1, '
    '"level_signal": "at"}\n```'
)
CANNED_EVALUATION = {"summary": "Practised greetings and letters.", "error_patterns": [],
                     "lesson_score": 0.5, "level_recommendation": "keep"}


@dataclass
class FakeClaude:
    """Records what the app sent; replies with canned text. Edit the fields per test."""
    reply: str = CANNED_TUTOR_REPLY
    vocab_events: list[dict] = field(default_factory=list)
    evaluation: dict = field(default_factory=lambda: dict(CANNED_EVALUATION))
    contexts: list[str] = field(default_factory=list)
    transcripts: list[list[dict]] = field(default_factory=list)


@pytest.fixture
def fake_claude(monkeypatch):
    """Replace both model calls in app.claude_client; nothing reaches a backend."""
    from app import claude_client

    fake = FakeClaude()

    async def tutor_turn(context_block, transcript):
        fake.contexts.append(context_block)
        fake.transcripts.append(list(transcript))
        text, meta = claude_client.parse_reply(fake.reply)
        meta["vocab_events"] = fake.vocab_events
        return text, meta, 100, 20

    async def evaluate_session(transcript):
        return fake.evaluation, 200, 40

    monkeypatch.setattr(claude_client, "tutor_turn", tutor_turn)
    monkeypatch.setattr(claude_client, "evaluate_session", evaluate_session)
    return fake
