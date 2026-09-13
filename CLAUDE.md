# CLAUDE.md — greek-tutor

Personal Modern Greek tutor: FastAPI + asyncpg/PostgreSQL + Claude API, with a
Harada-method progress board as the model of the learner. Single learner (Yanni)
first; multi-user schema retained. Plan of record: `docs/HARADA_INTEGRATION.md`.
Pick up from the newest file in `docs/handoff-items/`.

## Stack and layout

- Python 3.12+ (3.14 locally), FastAPI, asyncpg (raw parameterized SQL, no ORM),
  Jinja2 templates + vanilla JS fetch (no HTMX — decided 2026-09-13).
- `app/` — `auth` (argon2, DB sessions), `tutor` (session loop), `srs` (SM-2),
  `quota`, `claude_client` (prompt + JSON contract), `harada_metrics` (pure
  scoring), `harada` (facts → recompute → focus pick), `harada_api` (router).
- `migrations/*.sql` applied in order by hand; `seed/*.sql` are re-runnable.
- `tests/` — pytest; DB tests skip unless `TEST_DATABASE_URL` is set (see README).

## Conventions

- Keep scoring pure: `harada_metrics.py` never touches the DB; `harada.py` does
  the I/O. New metric kinds need a scorer, a `validate_args` check, and tests.
- Cell definitions live in `seed/harada.sql`; `tests/test_harada_seed.py` checks
  all 64 against the metric contracts. A cell is `manual` unless the number it
  reads already exists in the schema — do not invent measurements.
- Business rules that must hold regardless of UI (max 5 focus cells, manual-only
  hand edits) live in `harada.py`, not in the router or templates.
- Branch per change (`feature/…`, `fix/…`), conventional commits, never commit `.env`.
- `ruff check app tests` and `pytest` must pass before a merge request.

## Status snapshot (2026-09-13)

Phase 1 text tutor is written; Harada spec steps 1–3 are implemented and tested
(schema, seed, recompute at session close, focus-driven session start, CURRENT
FOCUS prompt block). **The app has not yet been run end to end against the real
Claude API.** Next: board UI (step 4), then cycle close (step 6). Details and
known defects: `docs/handoff-items/handoff-next-phase.md`.
