# Stage 01 — First real run

**Status:** done (2026-10-18) · **Branch:** `feature/01-first-real-run` · **Size:** one session
**Depends on:** `feature/harada-board-ui` merged; `feature/docker-roadmap` and `feature/llm-backends` on top of it

> **Decisions override (2026-10-18, `00-ROADMAP.md`).** Run on `LLM_BACKEND=api` with
> `TUTOR_MODEL=claude-sonnet-5-5`, and update `.env.example` from the old Haiku 4.5 / Sonnet 4.6
> IDs. Where this file assumes Haiku (e.g. the 4,096-token cache prefix), re-check the minimum
> cacheable prefix for the model you actually run.

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

- [x] `.env` from `.env.example`: `POSTGRES_PASSWORD` (`openssl rand -hex 24`), `ANTHROPIC_API_KEY` (`COOKIE_SECRET` is gone).
- [x] Decide the tutor model (see roadmap decisions). Put it in `.env`, not in code.

## Tasks

### A. Bring it up (verifies the 2026-09-26 Docker work, which was written without Docker Hub access and never built)
- [x] `docker compose up -d --build`; `docker compose logs migrate` shows 4 `apply` (004 added this stage) + 2 `seed` lines.
- [x] `docker compose ps` — `app` is `healthy` (the HEALTHCHECK hits `/healthz`).
- [x] `docker compose run --rm migrate` again — prints `migrations up to date`, seeds re-apply cleanly.
- [x] `docker compose --profile test run --rm test` — ruff clean, all tests pass (183 on `feature/harada-board-ui`, plus the backend tests), DB tests **not** skipped. Also once with `APP_TIMEZONE=America/New_York` after 20:00 local.
- [x] Fix anything the build surfaces (base image, wheels for asyncpg/argon2, file permissions for uid 10001).

### A2. Pick the backend (README → "Choosing how the app talks to Claude")
- [x] `LLM_BACKEND=api`: set `ANTHROPIC_API_KEY`. Or `LLM_BACKEND=claude_cli`: run `claude setup-token` on your machine, put the token in `CLAUDE_CODE_OAUTH_TOKEN`, set `SIGNUP_ENABLED=false` after your account exists.
> The four unchecked items below were **not done**: the 2026-10-18 decisions run this stage on
> `api` only. They move to the voice-slice task "Backend per mode" (phase 2), where text goes
> to `claude_cli`.

- [ ] Do the real session (B) on **both** backends once. Compare latency per turn and whether the JSON contract parses every time — the CLI path flattens the transcript, so it is the likelier one to drift.
- [ ] `docker compose exec app claude --version` matches `CLAUDE_CLI_VERSION`; then pin that exact version in `.env`. If a newer CLI changes `--output-format json`, `tests/test_llm_backends.py` pins the shape we parse (recorded from 2.1.283).
- [ ] CLI path, first turn: confirm the reply is the **tutor** (Greek, ends with a task, JSON block parsed), not Claude Code introducing itself. That proves `--system-prompt-file` replaced the default prompt. On 2026-09-26 this was confirmed with a clean environment (248 input tokens instead of ~10k); an environment with inherited `CLAUDE_CODE_*` variables ignored it, which is why `app/llm.py` builds the child's environment from an allowlist.
- [ ] Try signing up a second account in `claude_cli` mode — expect a 403.

### B. Real session, by hand
- [x] Sign up at `http://127.0.0.1:8080/login`.
- [x] `POST /api/harada/goal` with the board's default goal and cycle text.
- [x] Focus 3 cells on the board: 0.1 (letters, `lesson_score`), 1.2 (10 new words, `session_metric`), 2.4 (gender, `error_absent`).
- [x] Practice ~15 turns, end the session — record which cells moved on the board **and in the export file** (`HARADA_EXPORT_PATH=/export/greek-board.json` → `./export/` on the host), and why.
- [x] Look at the raw model output for 3 turns: does the fenced JSON parse every time? Does the tutor follow the CURRENT FOCUS block?
- [x] Record `usage.cache_read_input_tokens`. Expected 0 (the static prompt is ~650 tokens; Haiku 4.5 needs a 4,096-token prefix). Fix: move the `cache_control` breakpoint to the last message of the transcript so the growing conversation is cached.
- [ ] Save 3 real transcripts to `tests/fixtures/transcripts/` (strip nothing personal you mind committing). Stage 13 replays them. **1 of 3 saved** (the stage-01 session); add two of Yanni's own sessions before stage 13.

### C. Phase 0 defects
- [x] `require_user`: return **401 JSON** for paths under `/api/`, keep the 303 redirect for pages. Update `session.html` and the dashboard (which works around the 303 today) to redirect to `/login` on 401.
- [x] Pin runtime deps (`anthropic` especially) to the versions that just worked: `pip freeze` inside the image → exact pins in `requirements.txt`.
- [x] Model ids: `.env.example` and `config.py` defaults to the ids chosen above.
- [x] Remove `COOKIE_SECRET` and `itsdangerous` (unused; SameSite=Lax cookies already block cross-site form posts), or give them a job. Don't leave a required-but-unused secret.
- [x] Keep one copy of the board prototype (roadmap decision) and fix references in README and the spec.

### D. HTTP-level test harness (the part skipped on 2026-09-13)
- [x] `tests/conftest.py`: an `auth_client` fixture — `httpx.AsyncClient` over the ASGI app, signs up a fresh user, keeps the cookie. DB tests only.
- [x] A `fake_claude` fixture that monkeypatches `claude_client.tutor_turn` / `evaluate_session` with canned replies (use a fixture transcript).
- [x] Tests: start → turn → close round trip; 401 on `/api/*` without a cookie; focus limit 409 over HTTP; quota 429 when `DAILY_AI_MINUTES` is tiny.

## Definition of done

- [x] Fresh clone + `.env` + `docker compose up -d --build` gives a working app with no other steps.
- [x] One real session moved at least one cell, and you know why each moved cell moved.
- [x] Test profile green with the new HTTP tests; `cache_read_input_tokens > 0` from the 2nd turn on.
- [x] README "Status" section updated with what actually happened.

## Out of scope

UI work, new metrics, new tables. If the real run shows a scoring bug, log it in stage 02.

## Session notes

**2026-10-18 (Claude Code, branch `feature/01-first-real-run`, based on `docs/greek-plan-decisions`).**

*What the build surfaced.* The test image collected zero tests: pytest 9 dropped the rootdir
from `sys.path` (fixed with `pythonpath` in `pyproject.toml`). Everything else built first
time — `python:3.12-slim` has wheels for asyncpg and argon2, and uid 10001 had no permission
problems. On this workstation, host ports 5433 (`hilton-report-db`) and 8080 (a local
`ioannisbatsios` process) were taken, so the local `.env` uses `DB_PORT=5435`, `APP_PORT=8082`;
`.env.example` keeps the defaults. When the phase-2 deploy puts this app on the workstation,
pick those ports deliberately.

*Model and key.* `claude-sonnet-5-5` resolves on the Models API (1M input) and is used for both
`TUTOR_MODEL` and `EVAL_MODEL`. Two key traps: a `sk-ant-oat…` token from `claude setup-token`
is a subscription token for `claude_cli`, not an API key (401); and a key not scoped to a
workspace gets a 400 unless requests name one — `ANTHROPIC_WORKSPACE_ID` (new, optional) sends
the header. The run itself used a workspace-scoped key.

*Sonnet 5.5 specifics.* It thinks by default (effort `high`), and thinking tokens count against
`max_tokens`; the old 1,024 budget risked cutting off the JSON block. Now `TUTOR_EFFORT=low`,
`EVAL_EFFORT=medium`, `max_tokens` 4,096, and a `refusal` or `max_tokens` stop raises (a 502 the
student retries) instead of storing a reply without its data.

*Caching (re-checked for the model actually used).* Sonnet 5.5's minimum cacheable prefix is
512 tokens, not Haiku 4.5's 4,096, so the ~650-token static prompt caches on its own. The real
blocker was the student-context block: rebuilt every turn, it changed whenever a due word was
answered, invalidating everything after it. It is now built once at session start and stored
(migration 004), and the API backend uses top-level automatic caching so the breakpoint moves to
the end of the conversation. Measured: turn 1 `cache_read=0, cache_write=1247`; turn 2 `1247`;
turn 3 `1660` … turn 15 `6416`, each later turn writing only its own ~330–520 new tokens.

*The session.* Simulated A0 learner driving `/practice` in the browser; goal and cycle = the
board's default text; focus 0.1, 1.2, 2.4. 15 turns, ~5 minutes wall clock, ≈5 s model
latency per turn on effort `low`. The JSON block parsed on **all 15** turns (no warning logged);
the tutor followed CURRENT FOCUS (0.1 → lesson A1-1, the alphabet) the whole way, moving to café
words only when asked and returning to "all 24 letters, clean". Per-turn tags were sensible
(`delta-theta-swap`, `final-sigma`, `article-gender-agreement`) and are still dropped (D2).
Eval: lesson A1-1 0.93; five error patterns. Tokens for the day: 12,874 in / 9,436 out plus
~50k cache-read tokens — about $0.13 for the session at Sonnet 5.5 prices.

*What moved and why* — table in `docs/REQUIREMENTS_TRACE.md` §5. Short version: 0.1 and 0.3 done
from the A1-1 score (0.3 via D5); 1.2 at 20% (18 new SRS words, 1 of 5 sessions); 1.3/1.4/1.7
by a few words; 4.1 and 7.2 by one session/day; **0.5 went to 20% without τόνος ever being
practised (D3, for stage 02)**; 0.2 and 2.4 correctly stayed at 0 because the eval's slugs
contained "sigma" and "gender". The export file matched the UI cell for cell.

*Not representative.* A simulated learner types instantly, so `ai_minutes` (5.0) happened to
equal wall-clock time; D1's understatement only shows with a human. Stage 02 should measure it
on one of Yanni's sessions.

*Found, not fixed (logged).* D10: the tutor answers in Markdown (bold, tables) and the practice
page prints it raw → stage 05. The model writes `"tag": ""` for untagged words (the contract says
omit); `clean_tag` already turns that into no tag.

*Left on this install.* The learner account `stage01@greek-tutor.test` (password in the local
`.env` as a comment) holds this session and the board above. While it exists, a second account
stops the export (`HARADA_EXPORT_USER_ID` unset) and would block `claude_cli` mode: delete it, or
pin the export to your own user id, when you sign up for real.
