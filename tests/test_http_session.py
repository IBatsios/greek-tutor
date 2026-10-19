"""HTTP-level tests: the real routes, auth and DB, with the model calls faked.

Skipped unless TEST_DATABASE_URL is set. Fixtures (auth_client, anon_client,
fake_claude) live in conftest.py.
"""
import json
import os
import secrets
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set"
)

from app import config, db  # noqa: E402  (after the skip guard; conftest sets env)

_TRANSCRIPTS = Path(__file__).parent / "fixtures" / "transcripts"
_FIXTURE = _TRANSCRIPTS / "2026-10-18-a1-alphabet-sonnet-5-5.json"
FIRST_REAL_RUN = json.loads(_FIXTURE.read_text(encoding="utf-8"))

GOAL = {"goal_text": "Hold a 10-minute conversation in Greek", "cycle_text": "90 days"}


async def _start(client) -> int:
    r = await client.post("/api/session/start")
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


async def test_start_turn_close_round_trip(auth_client, fake_claude):
    assert (await auth_client.post("/api/harada/goal", data=GOAL)).status_code == 200
    sid = await _start(auth_client)

    first = next(m for m in FIRST_REAL_RUN["messages"] if m["role"] == "assistant")
    r = await auth_client.post(f"/api/session/{sid}/turn", data={"message": "Γεια σου!"})
    assert r.status_code == 200, r.text
    assert r.json()["reply"] == first["content"]          # JSON block stripped, prose intact
    assert r.json()["objective_progress"] == first["meta"]["objective_progress"]

    r = await auth_client.post(f"/api/session/{sid}/close")
    assert r.status_code == 200 and r.json()["summary"] == fake_claude.evaluation["summary"]

    p = db.pool()
    assert await p.fetchval("SELECT count(*) FROM tutor_turns WHERE session_id=$1", sid) == 2
    row = await p.fetchrow("SELECT ended_at, summary_text FROM tutor_sessions WHERE id=$1", sid)
    assert row["ended_at"] is not None and row["summary_text"] == "Practised greetings and letters."
    # A closed session takes no more turns.
    r = await auth_client.post(f"/api/session/{sid}/turn", data={"message": "Ακόμα;"})
    assert r.status_code == 400


async def test_context_block_is_frozen_for_the_session_so_the_prompt_stays_cacheable(
        auth_client, fake_claude):
    word = f"λέξη-{secrets.token_hex(3)}"
    fake_claude.vocab_events = [{"greek": word, "english": "word", "result": "introduced"}]
    sid = await _start(auth_client)
    try:
        for msg in ("Γεια!", "Καλά, εσύ;"):
            r = await auth_client.post(f"/api/session/{sid}/turn", data={"message": msg})
            assert r.status_code == 200, r.text
    finally:
        await db.pool().execute("DELETE FROM vocab_items WHERE greek=$1", word)
    # The first turn added a word to the learner's SRS; the second turn's prompt must
    # still be byte-identical ahead of the conversation.
    assert len(fake_claude.contexts) == 2
    assert fake_claude.contexts[0] == fake_claude.contexts[1]
    assert fake_claude.transcripts[1][-1] == {"role": "user", "content": "Καλά, εσύ;"}


@pytest.mark.parametrize("method,path", [
    ("post", "/api/session/start"),
    ("post", "/api/session/1/turn"),
    ("post", "/api/session/1/close"),
    ("get", "/api/harada"),
    ("post", "/api/harada/recompute"),
])
async def test_api_without_a_cookie_is_a_401_json(anon_client, method, path):
    kwargs = {"data": {"message": "x"}} if path.endswith("/turn") else {}
    r = await anon_client.request(method.upper(), path, **kwargs)
    assert r.status_code == 401
    assert r.json() == {"detail": "Not signed in."}


async def test_pages_without_a_cookie_still_redirect_to_login(anon_client):
    r = await anon_client.get("/practice")
    assert r.status_code == 303 and r.headers["location"] == "/login"


async def test_a_sixth_focus_cell_is_a_409(auth_client):
    assert (await auth_client.post("/api/harada/goal", data=GOAL)).status_code == 200
    ids = [r["id"] for r in await db.pool().fetch(
        "SELECT id FROM harada_actions ORDER BY theme_id, slot LIMIT 6")]
    for action_id in ids[:5]:
        r = await auth_client.post(f"/api/harada/action/{action_id}/focus", data={"on": "true"})
        assert r.status_code == 200, r.text
    r = await auth_client.post(f"/api/harada/action/{ids[5]}/focus", data={"on": "true"})
    assert r.status_code == 409 and "at most 5" in r.json()["detail"]


async def test_daily_quota_is_a_429_once_the_minutes_are_used(auth_client, fake_claude,
                                                              monkeypatch):
    monkeypatch.setattr(config, "DAILY_AI_MINUTES", 0.1)  # one turn costs >= 0.25 min
    sid = await _start(auth_client)
    r = await auth_client.post(f"/api/session/{sid}/turn", data={"message": "Γεια!"})
    assert r.status_code == 200, r.text
    r = await auth_client.post(f"/api/session/{sid}/turn", data={"message": "Πάλι!"})
    assert r.status_code == 429
    assert (await auth_client.post("/api/session/start")).status_code == 429
