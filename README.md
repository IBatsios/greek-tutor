# Greek Tutor — text tutor + Harada progress engine

FastAPI + PostgreSQL + Claude API. Email/password auth, per-user SRS vocab,
an A1 lesson curriculum, quota-enforced tutor sessions, and a Harada-method
board (8 themes × 8 actions) that scores itself from session data and decides
what each session should work on. Built single-learner first; the multi-user
schema is kept so a second account costs nothing later.

## Setup

```bash
# 1. Database (PostgreSQL 15+)
createdb greektutor
psql greektutor -c "CREATE EXTENSION IF NOT EXISTS citext;"
psql greektutor -f migrations/001_schema.sql
psql greektutor -f migrations/002_tutor_turns.sql
psql greektutor -f migrations/003_harada.sql
psql greektutor -f seed/lessons_a1.sql
psql greektutor -f seed/harada.sql       # re-runnable: edit it to re-cut the board

# 2. App (Python 3.12+; uv or plain venv)
uv venv .venv && source .venv/bin/activate      # Windows: .venv/Scripts/activate
uv pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, ANTHROPIC_API_KEY, COOKIE_SECRET

# 3. Run
set -a; source .env; set +a
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Put it behind your Cloudflare Tunnel pointing at 127.0.0.1:8080.

## How a session works

1. `POST /api/session/start` — picks the learner's **weakest focus cell** on the
   Harada board (`app/harada.py::pick_focus`). A lesson-scored cell opens that
   lesson; vocabulary, error and session-metric cells ride along on the next
   incomplete lesson. With no focus cells set, it falls back to the next lesson
   at the learner's level, exactly as before.
2. `POST /api/session/{id}/turn` — quota check → rebuild per-user context from
   Postgres (plus a `CURRENT FOCUS` block when the session has one) → Claude
   (Haiku, static prompt first) → parse the trailing JSON contract → apply SRS
   vocab events (with optional topic tags) → log usage.
3. `POST /api/session/{id}/close` — one Sonnet call over the transcript →
   summary, error patterns, lesson score → stored → **board rescored**.

## The Harada board

Spec: `docs/HARADA_INTEGRATION.md`. Prototype UI: `docs/harada-board.html`.
Cell definitions: `seed/harada.sql` (40 cells score automatically, 24 are
manual because a text tutor cannot measure them honestly). Scoring is pure
Python in `app/harada_metrics.py`; the contracts for each `metric_kind` are in
its module docstring.

| Endpoint | Form fields | Notes |
|---|---|---|
| `GET /api/harada` | — | Board JSON: themes → actions with state, progress, is_focus |
| `POST /api/harada/goal` | `goal_text`, `cycle_text`, `cycle_days` | Upsert the central goal / 90-day cycle |
| `POST /api/harada/action/{id}/focus` | `on=true\|false` | Max 5 focus cells, enforced server-side (409) |
| `POST /api/harada/action/{id}/state` | `state=not_started\|in_progress\|done` | Manual cells only (409 otherwise) |
| `POST /api/harada/routine` | `key`, `checked`, `log_date?` | Daily check sheet; keys are the `routine_days` metric keys |
| `POST /api/harada/recompute` | — | Rescore now (also runs at every session close) |

Until the board UI lands, drive it with fetch from the browser console or curl
with your session cookie, e.g. `curl -b gt_session=… -d on=true
localhost:8080/api/harada/action/12/focus`.

## Development

```bash
uv pip install -r requirements-dev.txt
ruff check app tests
pytest                                   # unit tests; no database needed

# Database-backed tests against a throwaway Postgres:
docker run -d --name greek-tutor-test-db -e POSTGRES_USER=tutor -e POSTGRES_PASSWORD=tutor \
  -e POSTGRES_DB=greektutor_test -p 127.0.0.1:5499:5432 postgres:16
docker exec greek-tutor-test-db psql -U tutor -d greektutor_test -c "CREATE EXTENSION IF NOT EXISTS citext;"
for f in migrations/001_schema.sql migrations/002_tutor_turns.sql migrations/003_harada.sql \
         seed/lessons_a1.sql seed/harada.sql; do
  docker exec -i greek-tutor-test-db psql -v ON_ERROR_STOP=1 -U tutor -d greektutor_test < "$f"
done
TEST_DATABASE_URL=postgresql://tutor:tutor@127.0.0.1:5499/greektutor_test pytest
```

## Not yet included (by design)

- Board UI on the dashboard (next phase — see `docs/handoff-items/`)
- Cycle close / 90-day review (Harada step 6)
- Voice — parked until the first 90-day cycle closes
- Email verification / password reset, rate limiting on `/login` and `/signup`
  — single-learner deployment; add before exposing signup publicly
- Level-change job: adjust `profiles.level_estimate` after 3+ consistent
  `level_recommendation` signals (the signal is not stored yet)
