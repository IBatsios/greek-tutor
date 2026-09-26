# CLAUDE.md — greek-tutor

Personal Modern Greek tutor: FastAPI + asyncpg/PostgreSQL + Claude API, with a
Harada-method progress board as the model of the learner. Single learner (Yanni)
first; multi-user schema retained. Spec: `docs/HARADA_INTEGRATION.md`. Requirement:
the board prototype (`docs/harada-board.html`); gaps vs code: `docs/REQUIREMENTS_TRACE.md`.
**Start every session at `docs/handoff-items/00-ROADMAP.md`** — take the first stage not
marked `done`, follow its file, and write its *Session notes* before stopping.

## Stack and layout

- Python 3.12+ (3.14 locally), FastAPI, asyncpg (raw parameterized SQL, no ORM),
  Jinja2 templates + vanilla JS fetch (no HTMX — decided 2026-09-13).
- `app/` — `auth` (argon2, DB sessions), `tutor` (session loop), `srs` (SM-2),
  `quota`, `claude_client` (prompt + JSON contract), `harada_metrics` (pure
  scoring), `harada` (facts → recompute → focus pick), `harada_api` (router).
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
- Cell definitions live in `seed/harada.sql`; `tests/test_harada_seed.py` checks
  all 64 against the metric contracts. A cell is `manual` unless the number it
  reads already exists in the schema — do not invent measurements.
- Business rules that must hold regardless of UI (max 5 focus cells, manual-only
  hand edits) live in `harada.py`, not in the router or templates.
- Branch per change (`feature/…`, `fix/…`), conventional commits, never commit `.env`.
- `ruff check app tests scripts` and `pytest` must pass before a merge request.
- When a stage changes how a board cell is measured, update `docs/REQUIREMENTS_TRACE.md`.

## Status snapshot (2026-09-26)

Phase 1 text tutor is written; Harada spec steps 1–3 are implemented and tested. Docker
(compose + migrator) added 2026-09-26 but **not yet built** — it was written where Docker Hub
and PyPI were unreachable. **The app has not yet been run end to end against the real Claude
API.** Next: stage 01 in `docs/handoff-items/00-ROADMAP.md`.
