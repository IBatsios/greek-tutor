# Greek Tutor — Phase 1 (text-only)

FastAPI + HTMX + PostgreSQL + Claude API. Email/password auth, per-user SRS
vocab, lesson curriculum, quota-enforced tutor sessions.

## Setup

```bash
# 1. Database
createdb greektutor
psql greektutor -c "CREATE EXTENSION IF NOT EXISTS citext;"
psql greektutor -f migrations/001_schema.sql     # the Phase 1 schema file
psql greektutor -f migrations/002_tutor_turns.sql
psql greektutor -f seed/lessons_a1.sql

# 2. App
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, ANTHROPIC_API_KEY, COOKIE_SECRET

# 3. Run
set -a; source .env; set +a
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Put it behind your Cloudflare Tunnel pointing at 127.0.0.1:8080.

## How a session works

1. `POST /api/session/start` — picks the user's next incomplete lesson at
   their level, opens a `tutor_sessions` row.
2. `POST /api/session/{id}/turn` — quota check → rebuild per-user context
   block from Postgres → Claude (Haiku, cached static prompt) → parse the
   trailing JSON contract → apply SRS vocab events → log usage.
3. `POST /api/session/{id}/close` — one Sonnet call over the transcript →
   summary, error patterns, lesson score → stored for next session's context.

## Not yet included (by design)

- Email verification / password reset (email_tokens table is ready; Phase 3)
- Rate limiting on auth endpoints — put Cloudflare rate rules on /login and
  /signup NOW if you expose this publicly before Phase 3
- Voice (Phase 2), dashboards/quota UI polish (Phase 3)
- Level-change job: a small cron that adjusts `profiles.level_estimate` after
  3+ consistent `level_recommendation` signals
