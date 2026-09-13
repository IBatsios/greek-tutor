# Handoff — Harada engine shipped; board UI next

**Date:** 2026-09-13 · **Branch:** `feature/harada-engine` (uncommitted at time of writing)
**Plan of record:** `docs/HARADA_INTEGRATION.md` (build order §8). Steps 1–3 are done here.

## Decisions made this session

| Decision | Choice | Why |
|---|---|---|
| Audience | Single learner first; keep multi-user schema | Email verification, rate limiting and quota UI only matter when a second person signs up |
| Sequencing | Skipped the "make Phase 1 run + test harness" phase, went straight to the engine | Yanni's call. Consequence: the app has never been run end to end against the real Claude API — see *Unverified* below |
| Voice | Parked through the first 90-day cycle | 24 of 64 cells are audio-shaped; they are `manual` or `routine_days` for now |
| Frontend | Vanilla JS fetch + JSON endpoints; no HTMX | Board prototype already renders in plain JS; session page already uses fetch; theme rollups are easier from one JSON payload than out-of-band swaps |
| Models | Unchanged (Haiku for turns, Sonnet 4.6 for eval) | Not decided yet — see *Deferred* |

## What shipped

- `migrations/003_harada.sql` — goals, themes, actions, per-user cell state, routine log,
  `lessons.theme_ids`, `tutor_sessions.focus_action_id`.
- `seed/harada.sql` — 8 themes + 64 actions ported from `docs/harada-board.html`, with a
  measurability audit: 40 computed, 24 `manual`. Re-runnable (ON CONFLICT updates).
  Lesson cells reference lessons by `(level, seq)`, never by id.
- `app/harada_metrics.py` — pure scorers, one per `metric_kind`, plus `validate_args`,
  `is_greek_only`, `is_sessionable`, `state_for`. Windows are always "the last N", so a
  new learner never sees phantom done cells.
- `app/harada.py` — `load_facts`, `recompute`, `pick_focus`, `focus_for_action`,
  `focus_block`, `set_focus` (max 5), `set_manual_state` (manual cells only).
- `app/harada_api.py` — `GET /api/harada`, `POST goal | action/{id}/focus |
  action/{id}/state | routine | recompute`. Form fields in, JSON out.
- `app/tutor.py` — session start picks the weakest sessionable focus cell (falls back to
  next lesson); per-turn context appends a `CURRENT FOCUS` block; close rescores the board
  (failures logged, never block closing).
- `app/srs.py` + `app/claude_client.py` — optional `"tag"` on `vocab_events` (one of the 8
  topic clusters) so `vocab_recall` cells can actually move; tutor rule 5 now says the
  focus block overrides the generic lesson objective.
- Tooling: `.gitignore`, `pyproject.toml` (ruff, pytest asyncio auto), `requirements-dev.txt`.
  `httpx` is in dev requirements for Starlette's TestClient (the optional-date form field
  on `/api/harada/routine` was verified with it: omitted/empty → None, ISO → date, junk → 422).
- Tests: 132 passing (`tests/test_harada_metrics.py`, `test_harada_seed.py`,
  `test_harada_db.py`, `test_app_wiring.py`). DB tests ran against a throwaway
  `postgres:16` container on port 5499 with all migrations and seeds applied; the seed
  was also re-applied to confirm idempotency.
- Small fixes in `app/auth.py` found by ruff: missing `asyncpg` import on a return
  annotation (only worked because 3.14 evaluates annotations lazily), unused import,
  exception chaining, narrowed the signup duplicate-email catch to `UniqueViolationError`.

## Review outcome (code-reviewer + security-reviewer agents, 2026-09-13)

No CRITICAL findings. Fixed in this branch: the eval model's `lesson_score` is now clamped to
0–1 (a percentage like 95 would have marked the lesson passed and made the focus picker skip
it forever); `POST /api/harada/goal` takes `restart_cycle=true` to reset `cycle_start`;
routine-key and tag regexes anchor with `\Z` (Python's `$` admits a trailing newline);
goal/cycle text capped at 2000 chars; vocab strings from the model capped at 200 chars and
blank ones dropped; a seed test pins every metric window under `FACT_SESSIONS`/`FACT_DAYS`.
Left as LOW: no per-user rate limit on `/recompute`; `clean_tag` accepts any slug rather
than only the 8 seeded clusters (off-list tags are stored but never scored).

## Unverified — do this first next session

1. **Run a real session.** Copy `.env.example` → `.env`, start Postgres, apply migrations
   and seeds, sign up, set 3 focus cells via the API, start a session, send a few turns,
   close it, then `GET /api/harada` and confirm cells moved. Watch for
   `anthropic` 1.5.0 behaviour (requirements say `>=0.40`; pin it once confirmed).
2. Check `response.usage.cache_read_input_tokens` on a turn. The static prompt is ~650
   tokens and Haiku 4.5 needs a 4096-token prefix to cache, so it is almost certainly 0.
   The fix is a cache breakpoint on the last transcript message, not on the system prompt.

## Next phase: board UI (Harada step 4) and check sheet (step 5)

- Port `docs/harada-board.html` into `templates/dashboard.html`. Replace the hard-coded
  `THEMES` array with `fetch('/api/harada')`; cell click → `POST action/{id}/focus` for
  computed cells, cycle state for `is_manual` cells; show `measure` in the detail panel.
  Show `focus_count / max_focus` and refuse a 6th focus client-side too (server already 409s).
- "Today" view: routine checkboxes for the `routine_days` keys of the current focus cells
  (`key` lives in each action's `metric_args` — expose it in the board JSON), posting to
  `/api/harada/routine`. One button: *Start session on &lt;focus action&gt;*.
- A "set your 3–5 focus cells" prompt when `focus_count < min_focus`.
- Drop the unused HTMX `<script>` from `templates/login.html`.

Then step 6 (cycle close): at `cycle_start + cycle_days`, recompute, one Sonnet review call
over the cycle's summaries, carry incomplete focus cells forward, ask for new focus cells,
reset `cycle_start`. Also the natural home for the level-change job.

## Deferred (Phase 0 items Yanni chose to skip for now)

- Model IDs: `.env.example` pins a date-suffixed Haiku id; current ids are undated
  (`claude-haiku-4-5`). Sonnet 5 (`claude-sonnet-5`) is now cheaper than Sonnet 4.6 for eval.
  Opus 5 would tutor noticeably better per turn; cost call is Yanni's.
- `require_user` raises a 303 for API routes; fetch follows it to HTML and `r.json()` fails.
  Return 401 for `/api/*`.
- `COOKIE_SECRET` is required by config but unused (`itsdangerous` too).
- No rate limiting on `/login` and `/signup`; no email verification. Fine for one user.
- `profiles.streak_count` / `last_active_date` are never written. Per-turn `error_tags` and
  `level_signal`, and the close-time `level_recommendation`, are parsed and dropped.
- No `docker-compose.yml`; README setup is manual psql.
- No HTTP-level tests of the routers (needs an auth cookie fixture); engine is tested at the
  function level.
- Voice (Phase 2) and everything under "audio-shaped cells" above.

## How to run the tests

See README → Development. Short version: `pytest` for unit tests; export
`TEST_DATABASE_URL` pointing at a seeded database to include `tests/test_harada_db.py`.
