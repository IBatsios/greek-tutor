# CLAUDE.md — greek-tutor

Personal Modern Greek tutor: FastAPI + asyncpg/PostgreSQL + Claude, with a
Harada-method progress board as the model of the learner. Single learner (Yanni)
first; multi-user schema retained. Spec: `docs/HARADA_INTEGRATION.md`. Requirement:
the board prototype (`docs/harada-board.html`); gaps vs code: `docs/REQUIREMENTS_TRACE.md`.
**Start every session at `docs/handoff-items/00-ROADMAP.md`** — take the first stage not
marked `done`, follow its file, and write its *Session notes* before stopping.
`handoff-next-phase.md` is the 2026-09-13 session log (history, not the plan).

## Stack and layout

- Python 3.12+ (3.14 locally), FastAPI, asyncpg (raw parameterized SQL, no ORM),
  Jinja2 templates + vanilla JS fetch (no HTMX — decided 2026-09-13).
- `app/` — `auth` (argon2, DB sessions), `tutor` (session loop), `srs` (SM-2),
  `quota`, `claude_client` (prompt + JSON contract), `llm` (the two backends:
  Anthropic API key or the `claude` CLI on the owner's subscription), `harada_metrics` (pure
  scoring), `harada` (facts → recompute → focus pick → export), `harada_api`
  (router), `harada_export` (the board payload + mirror file, pure), `clock`.
- `migrations/*.sql` applied in order by `scripts/migrate.py` (tracked in
  `schema_migrations`); `seed/*.sql` are re-runnable and re-applied on every migrate.
  Never edit an applied migration — add the next number.
- Docker: `docker compose up -d --build` (db → migrate → app). Tests:
  `docker compose --profile test run --rm test`. New top-level dirs the app needs at
  runtime (e.g. `static/`) must be added to the Dockerfile `COPY` lines.
- `tests/` — pytest; DB tests skip unless `TEST_DATABASE_URL` is set (the test profile sets it).

## Conventions

- Keep scoring pure: `harada_metrics.py` never touches the DB; `harada.py` does
  the I/O. New metric kinds need a scorer, a `validate_args` check, and tests.
- One calendar: `app/clock.py` (`APP_TIMEZONE`) is applied to every DB connection, so
  `CURRENT_DATE` in SQL and `clock.today()` agree. Never call `date.today()` in `app/`
  (`tests/test_clock.py` enforces it).
- Cell definitions live in `seed/harada.sql`; `tests/test_harada_seed.py` checks
  all 64 against the metric contracts. A cell is `manual` unless the number it
  reads already exists in the schema — do not invent measurements.
- Business rules that must hold regardless of UI (max 5 focus cells, manual-only
  hand edits, export after every board change) live in `harada.py`, not in the
  router or templates.
- `GET /api/harada` and the export file are one contract
  (`docs/HARADA_BOARD_CONTRACT.md`, `schema: 1`); the tracker reads it. Adding a
  key is fine, removing or renaming one bumps the schema.
- Every model call goes through `llm.backend().complete(...)`; only `app/llm.py` imports
  `anthropic` or spawns `claude`. `LLM_BACKEND=claude_cli` is single-learner by Anthropic's
  terms — keep `assert_single_learner` and the signup gate intact.
- The daily routine check sheet is the **tracker's** UI, not this app's. Do not
  build a second one here.
- Branch per change (`feature/…`, `fix/…`), conventional commits, never commit `.env`.
- `ruff check app tests scripts` and `pytest` must pass before a merge request.
- When a stage changes how a board cell is measured, update `docs/REQUIREMENTS_TRACE.md`.

## Status snapshot (2026-09-26)

Phase 1 text tutor is written; Harada steps 1–4 are implemented and tested (schema,
seed, recompute at session close, focus-driven session start, CURRENT FOCUS prompt
block, the board UI on `/`, the versioned export the tracker mirrors). Step 5 (routine
sheet) is deferred to the tracker by decision. Docker (compose + migrator) added
2026-09-26 but **not yet built** — it was written where Docker Hub and PyPI were
unreachable. **The app has not yet been run end to end against the real Claude API.**
Next: stage 01 in `docs/handoff-items/00-ROADMAP.md`.
