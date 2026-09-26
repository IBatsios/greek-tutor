"""claude_cli mode serves one learner: signup closes after the first account, and a
second account (e.g. inserted by hand) stops sessions from starting.
Skipped unless TEST_DATABASE_URL is set.
"""
import os
import secrets

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set"
)

from fastapi import HTTPException  # noqa: E402

from app import auth, config, db, tutor  # noqa: E402


async def _make_user() -> int:
    uid = await db.pool().fetchval(
        "INSERT INTO users (email, password_hash) VALUES ($1, 'x') RETURNING id",
        f"cli-{secrets.token_hex(4)}@test.invalid",
    )
    await db.pool().execute(
        "INSERT INTO profiles (user_id, display_name) VALUES ($1, 'Test')", uid)
    return uid


@pytest.fixture
async def two_users():
    await db.init_pool()
    ids = [await _make_user(), await _make_user()]
    try:
        yield ids
    finally:
        await db.pool().execute("DELETE FROM users WHERE id = ANY($1::bigint[])", ids)
        await db.close_pool()


async def test_signup_is_closed_in_subscription_mode_once_an_account_exists(
        two_users, monkeypatch):
    monkeypatch.setattr(config, "LLM_BACKEND", "claude_cli")
    before = await db.pool().fetchval("SELECT count(*) FROM users")
    with pytest.raises(HTTPException) as exc:
        await auth.signup(email=f"new-{secrets.token_hex(4)}@test.invalid",
                          password="long-enough-password", display_name="")
    assert exc.value.status_code == 403
    assert await db.pool().fetchval("SELECT count(*) FROM users") == before


async def test_signup_stays_open_with_an_api_key(two_users, monkeypatch):
    monkeypatch.setattr(config, "LLM_BACKEND", "api")
    email = f"new-{secrets.token_hex(4)}@test.invalid"
    try:
        resp = await auth.signup(email=email, password="long-enough-password", display_name="")
        assert resp.status_code == 303
    finally:
        await db.pool().execute("DELETE FROM users WHERE email = $1", email)


async def test_a_second_account_stops_sessions_in_subscription_mode(two_users, monkeypatch):
    monkeypatch.setattr(config, "LLM_BACKEND", "claude_cli")
    user = {"id": two_users[0], "level_estimate": "A0"}
    with pytest.raises(HTTPException) as exc:
        await tutor.start_session(user=user)
    assert exc.value.status_code == 403
    assert "LLM_BACKEND=api" in exc.value.detail
