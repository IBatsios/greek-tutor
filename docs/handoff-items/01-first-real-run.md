# Stage 01 — First real run

**Status:** not started · **Branch:** `feature/01-first-real-run` · **Size:** one session
**Depends on:** `feature/harada-board-ui` merged; `feature/docker-roadmap` and `feature/llm-backends` on top of it

## Goal

The app has never run end to end against the real Claude API. By the end of this stage it
has: in Docker, with a real account, a real session, and a board that moved because of it.
Also close the Phase 0 defects that would bite every later stage.

## Why now

Every later stage stacks UI and features on a loop nobody has watched work. Finding out now
that, say, the JSON contract breaks on Haiku costs one session; finding out in stage 05 costs three.

## Primer — what the Docker setup does

| Piece | What it is | Why |
|---|---|---|
| `db` | Postgres 16 with a named volume `pgdata` | Data survives `docker compose down` (not `down -v`) |
| `migrate` | Runs `scripts/migrate.py` once, then exits | Applies new `migrations/*.sql`, records them in `schema_migrations`, re-applies seeds |
| `app` | uvicorn on 8080, bound to `127.0.0.1` only | Starts only after `migrate` exits 0 |
| `db-test` + `test` (profile `test`) | Throwaway Postgres in RAM + an image with dev deps | `docker compose --profile test run --rm test` = ruff + every test, DB tests included |

`schema_migrations` is the new piece: before it, nothing recorded which SQL files a database had
seen, so "run the migrations" meant "remember what you ran". If you ever built a DB by hand
with psql, run `docker compose run --rm migrate python scripts/migrate.py --baseline` once.

## Before you start

- [ ] `.env` from `.env.example`: `POSTGRES_PASSWORD` (`openssl rand -hex 24`), `ANTHROPIC_API_KEY`, `COOKIE_SECRET`.
- [ ] Decide the tutor model (see roadmap decisions). Put it in `.env`, not in code.

## Tasks

### A. Bring it up (verifies the 2026-09-26 Docker work, which was written without Docker Hub access and never built)
- [ ] `docker compose up -d --build`; `docker compose logs migrate` shows 3 `apply` + 2 `seed` lines.
- [ ] `docker compose ps` — `app` is `healthy` (the HEALTHCHECK hits `/healthz`).
- [ ] `docker compose run --rm migrate` again — prints `migrations up to date`, seeds re-apply cleanly.
- [ ] `docker compose --profile test run --rm test` — ruff clean, all tests pass (183 on `feature/harada-board-ui`, plus the backend tests), DB tests **not** skipped. Also once with `APP_TIMEZONE=America/New_York` after 20:00 local.
- [ ] Fix anything the build surfaces (base image, wheels for asyncpg/argon2, file permissions for uid 10001).

### A2. Pick the backend (README → "Choosing how the app talks to Claude")
- [ ] `LLM_BACKEND=api`: set `ANTHROPIC_API_KEY`. Or `LLM_BACKEND=claude_cli`: run `claude setup-token` on your machine, put the token in `CLAUDE_CODE_OAUTH_TOKEN`, set `SIGNUP_ENABLED=false` after your account exists.
- [ ] Do the real session (B) on **both** backends once. Compare latency per turn and whether the JSON contract parses every time — the CLI path flattens the transcript, so it is the likelier one to drift.
- [ ] `docker compose exec app claude --version` matches `CLAUDE_CLI_VERSION` in the Dockerfile; if a newer CLI changed `--output-format json`, `tests/test_llm_backends.py` pins the shape we parse.

### B. Real session, by hand
- [ ] Sign up at `http://127.0.0.1:8080/login`.
- [ ] `POST /api/harada/goal` with the board's default goal and cycle text.
- [ ] Focus 3 cells on the board: 0.1 (letters, `lesson_score`), 1.2 (10 new words, `session_metric`), 2.4 (gender, `error_absent`).
- [ ] Practice ~15 turns, end the session — record which cells moved on the board **and in the export file** (`HARADA_EXPORT_PATH=/export/greek-board.json` → `./export/` on the host), and why.
- [ ] Look at the raw model output for 3 turns: does the fenced JSON parse every time? Does the tutor follow the CURRENT FOCUS block?
- [ ] Record `usage.cache_read_input_tokens`. Expected 0 (the static prompt is ~650 tokens; Haiku 4.5 needs a 4,096-token prefix). Fix: move the `cache_control` breakpoint to the last message of the transcript so the growing conversation is cached.
- [ ] Save 3 real transcripts to `tests/fixtures/transcripts/` (strip nothing personal you mind committing). Stage 13 replays them.

### C. Phase 0 defects
- [ ] `require_user`: return **401 JSON** for paths under `/api/`, keep the 303 redirect for pages. Update `session.html` and the dashboard (which works around the 303 today) to redirect to `/login` on 401.
- [ ] Pin runtime deps (`anthropic` especially) to the versions that just worked: `pip freeze` inside the image → exact pins in `requirements.txt`.
- [ ] Model ids: `.env.example` and `config.py` defaults to the ids chosen above.
- [ ] Remove `COOKIE_SECRET` and `itsdangerous` (unused; SameSite=Lax cookies already block cross-site form posts), or give them a job. Don't leave a required-but-unused secret.
- [ ] Keep one copy of the board prototype (roadmap decision) and fix references in README and the spec.

### D. HTTP-level test harness (the part skipped on 2026-09-13)
- [ ] `tests/conftest.py`: an `auth_client` fixture — `httpx.AsyncClient` over the ASGI app, signs up a fresh user, keeps the cookie. DB tests only.
- [ ] A `fake_claude` fixture that monkeypatches `claude_client.tutor_turn` / `evaluate_session` with canned replies (use a fixture transcript).
- [ ] Tests: start → turn → close round trip; 401 on `/api/*` without a cookie; focus limit 409 over HTTP; quota 429 when `DAILY_AI_MINUTES` is tiny.

## Definition of done

- [ ] Fresh clone + `.env` + `docker compose up -d --build` gives a working app with no other steps.
- [ ] One real session moved at least one cell, and you know why each moved cell moved.
- [ ] Test profile green with the new HTTP tests; `cache_read_input_tokens > 0` from the 2nd turn on.
- [ ] README "Status" section updated with what actually happened.

## Out of scope

UI work, new metrics, new tables. If the real run shows a scoring bug, log it in stage 02.

## Session notes

_(fill in at the end of the session)_
