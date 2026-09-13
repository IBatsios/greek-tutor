"""Email/password auth with argon2id hashing and server-side sessions.

Raw session tokens live only in the cookie; the DB stores a SHA-256 hash,
so a DB leak doesn't leak live sessions.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from . import config
from .db import pool

router = APIRouter()
ph = PasswordHasher()  # argon2id defaults

COOKIE_NAME = "gt_session"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(user_id: int, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=config.SESSION_TTL_DAYS)
    await pool().execute(
        "INSERT INTO auth_sessions (user_id, token_hash, expires_at) VALUES ($1,$2,$3)",
        user_id, _hash_token(token), expires,
    )
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=config.SESSION_TTL_DAYS * 86400,
        httponly=True, secure=config.COOKIE_SECURE, samesite="lax",
    )


async def current_user(request: Request) -> asyncpg.Record | None:  # type: ignore[name-defined]
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    row = await pool().fetchrow(
        """SELECT u.id, u.email, p.display_name, p.level_estimate, p.native_lang
           FROM auth_sessions s
           JOIN users u ON u.id = s.user_id
           JOIN profiles p ON p.user_id = u.id
           WHERE s.token_hash = $1 AND s.expires_at > now()
             AND u.disabled_at IS NULL""",
        _hash_token(token),
    )
    if row:
        await pool().execute(
            "UPDATE auth_sessions SET last_seen_at = now() WHERE token_hash = $1",
            _hash_token(token),
        )
    return row


async def require_user(request: Request):
    user = await current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


@router.post("/signup")
async def signup(email: str = Form(...), password: str = Form(...),
                 display_name: str = Form("")):
    if len(password) < 10:
        raise HTTPException(400, "Password must be at least 10 characters.")
    email = email.strip().lower()
    async with pool().acquire() as conn:
        async with conn.transaction():
            try:
                user_id = await conn.fetchval(
                    "INSERT INTO users (email, password_hash) VALUES ($1,$2) RETURNING id",
                    email, ph.hash(password),
                )
            except Exception:
                raise HTTPException(400, "That email is already registered.")
            await conn.execute(
                "INSERT INTO profiles (user_id, display_name) VALUES ($1,$2)",
                user_id, display_name.strip() or email.split("@")[0],
            )
    resp = RedirectResponse("/", status_code=303)
    await create_session(user_id, resp)
    return resp
    # TODO Phase 3: gate AI access behind email verification (email_tokens table)


@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    row = await pool().fetchrow(
        "SELECT id, password_hash FROM users WHERE email = $1 AND disabled_at IS NULL",
        email.strip().lower(),
    )
    if not row:
        raise HTTPException(401, "Invalid email or password.")
    try:
        ph.verify(row["password_hash"], password)
    except VerifyMismatchError:
        raise HTTPException(401, "Invalid email or password.")
    if ph.check_needs_rehash(row["password_hash"]):
        await pool().execute("UPDATE users SET password_hash=$1 WHERE id=$2",
                             ph.hash(password), row["id"])
    resp = RedirectResponse("/", status_code=303)
    await create_session(row["id"], resp)
    return resp


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await pool().execute("DELETE FROM auth_sessions WHERE token_hash=$1",
                             _hash_token(token))
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp
