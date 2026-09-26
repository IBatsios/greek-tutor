# Greek Tutor — Ελληνικά, every day

A personal Modern Greek tutor that decides what you should practise today, holds you to a
daily routine, and shows you — on one board — exactly where your Greek is strong and where
it has holes.

> **Status (2026-09-26):** the tutor engine, progress model and board UI are written and
> tested, but the app has **not yet been run end to end against the real Claude API**, and it
> is **text-only** — speaking and listening practice arrive with voice (roadmap stages 10–11).
> The daily check sheet lives in the companion tracker app, which mirrors this board. The plan to a daily-usable product is in
> [`docs/handoff-items/00-ROADMAP.md`](docs/handoff-items/00-ROADMAP.md).

---

## What it is

| | |
|---|---|
| **Who** | Adult English speakers learning Modern Greek from zero or near zero, who want structure and honest feedback more than streak confetti. Built for one learner first; the schema already supports more. |
| **What** | An AI conversation tutor (Claude) plus a spaced-repetition vocabulary deck, an A1 lesson sequence, and a **Harada Method board**: one goal, 8 themes, 64 concrete actions that score themselves from your practice. |
| **Goal it trains for** | *Hold a real, unscripted 10-minute conversation in Greek on everyday topics without switching to English.* |
| **Where** | A self-hosted web app (Docker) you open on your laptop or phone. |
| **When** | 45 minutes a day, in 90-day cycles. |
| **Why this and not a streak app** | Language skill fails along independent axes — you can know 800 words and still not follow a waiter. A linear course hides that; the board shows it as a hole and the tutor works on it next. |

## How it teaches

1. **Every session has an objective.** When you press *Start*, the app looks at the 3–5 actions
   you chose to focus on this cycle, picks the weakest one, and tells the tutor to work on it
   ("Predict gender from the ending — 'gender agreement' appeared in 2 of your last 5 sessions.
   Drill this specifically.").
2. **You produce Greek every turn.** The tutor is instructed never to send two explanations in a
   row: each message ends with something for you to say, answer or translate. Greek-to-English
   ratio grows with your level (about 30% Greek at A1, 80% by B1).
3. **Corrections are light and immediate.** Your sentence restated correctly, the fix in bold,
   one line of why, then back to the conversation.
4. **Vocabulary is recycled on a schedule.** Every word you meet goes into a spaced-repetition
   deck (SM-2). Words due today are woven into the conversation; words you keep missing come
   back sooner.
5. **The session is graded when it ends.** A second, stronger model reads the transcript and
   writes a summary, the error patterns it saw, and a lesson score. Those feed the board.

## How it holds you accountable

| Mechanism | What you see | What it does |
|---|---|---|
| **The board** (8 × 8 actions) | Every action coloured not started / in progress / done | 25 actions score themselves from session data (lesson scores, recall rates, errors, time) — you can't tick them to feel good. 15 move from your daily check sheet. 24 are honest self-assessment and are marked as such. |
| **Focus limit** | "Focus 4/5" | At most 5 actions in play at once (Harada's rule). The server refuses a 6th. Too many goals is how none move. |
| **Daily check sheet** (in the tracker app) | Today's short list: clear your review queue, 10 min listening, 5 min reading aloud, 3 sentences written, shadowing | Each tick feeds a board action with a target like "6 of the last 7 days". The tracker is your phone-first daily page; this app owns the board it mirrors. |
| **Never miss two days** | Streak, and a nudge at your practice time if you haven't started | Missing one day is life; missing two is a new habit. The board's habit action measures exactly this. |
| **Proof, not feelings** | "Measured by …" on every action | Each action says how it's scored — a lesson score, recall rate on a word cluster, an error that has stopped appearing, days practised. |
| **90-day review** | A review at the end of each cycle | What moved, what didn't, which actions carry over, and the next target. |
| **Monthly recording** | You, speaking, month by month | The ground-truth check that the numbers aren't drifting from reality. |

## How long until you're adequate?

"Adequate" here means the board's goal: a 10-minute unscripted conversation on everyday
topics. That sits at roughly **CEFR A2+/B1**.

The US Foreign Service Institute puts Greek in its Category III ("significant differences from
English"), at about **1,100 class hours** to professional working proficiency — far beyond this
goal. For the everyday-conversation level, a realistic budget at **45 minutes a day, every day**
(~275 hours a year) looks like this:

| Milestone | What you can do | Approx. cumulative hours | At 45 min/day |
|---|---|---|---|
| Alphabet & sounds | Read any Greek word aloud, slowly | 10–15 | 2–3 weeks |
| **A1** (lessons A1-1 → A1-24) | Introduce yourself, order, shop, ask directions, simple present | 100–150 | **4–6 months** (cycles 1–2) |
| **A2** | Talk about the past and plans, handle routine exchanges | 250–350 | **9–15 months** (cycles 3–5) |
| **The goal** — 10-min unscripted chat | Sustain a real conversation without English | 350–500 | **~15–20 months** |
| B1 | Handle most travel and everyday situations with some fluency | 500–650 | ~2 years |

These are estimates, not promises: they assume daily practice, that the app's hours are real
study (not only tutor chat but listening, reading and review), and — for speaking — a weekly
conversation with a real person, which no app replaces. Missing weeks stretch the table
proportionally. Hour ranges are derived from FSI's Category III figure and CEFR guided-learning
estimates, scaled for Greek's new alphabet and case system.

A 90-day cycle is the unit of planning. Cycle 1's default target: *finish A1 lessons 1–12 and
hold a 5-minute introduction conversation.*

## A day with the app

| Time | You do | The app does |
|---|---|---|
| 5 min | Review due words (flashcards) | Reschedules each word; ticks "SRS cleared" automatically at zero |
| 25 min | One tutor session on today's focus action | Chooses the objective, drills it, grades the session, rescores the board |
| 10 min | Listen to Greek audio, no subtitles | You tick it on the tracker's check sheet |
| 5 min | Read aloud; write three sentences about your day | You tick them in the tracker |
| Weekly | 5-minute error review; one real conversation | Shows your top recurring errors and leech words |

Some of this (flashcard review, nudges, audio, the tracker feeding check-sheet ticks back
into the board) is on the roadmap rather than in the code yet — see the status note at the top.

## The eight themes

| # | Theme | Examples of the 8 actions |
|---|---|---|
| 1 | Pronunciation & Script — Προφορά | 24 letters from memory; final ς vs σ; τόνος on 50 words; shadowing |
| 2 | Vocabulary & SRS — Λεξιλόγιο | Clear the queue daily; 500 → 1,500 words at 80% recall; 8 topic clusters |
| 3 | Grammar — Γραμματική | είμαι/έχω; -ω/-άω verbs; cases with the article; gender from ending; θα/να |
| 4 | Listening — Ακρόαση | 10 min audio daily; numbers dictation; sessions with no English fallback |
| 5 | Speaking — Ομιλία | 15 min unscripted per session; order/shop/directions unprompted; the 10-minute goal |
| 6 | Reading — Ανάγνωση | Signs and menus aloud; graded readers; 10 new words per text into the deck |
| 7 | Writing — Γραφή | Three sentences daily; Greek keyboard; 100 words about yourself |
| 8 | Habit & Environment — Συνήθεια | 45 min/day in the same block; never miss two days; phone in Greek |

The board lives at `/` once you sign in. The original prototype with every action and how
it's measured: `docs/harada-board.html` (open it in a browser). Where the code does and doesn't yet match it: `docs/REQUIREMENTS_TRACE.md`.

---

## Run it (Docker)

```bash
cp .env.example .env
#   POSTGRES_PASSWORD   openssl rand -hex 24
#   ANTHROPIC_API_KEY   your Claude API key
#   COOKIE_SECRET       any long random string
docker compose up -d --build
#   APP_TIMEZONE        where you practise, so "today" matches your evenings
# → http://127.0.0.1:8080  (sign up, set your goal and 3–5 focus cells, start a session)
```

| Service | Role |
|---|---|
| `db` | PostgreSQL 16, data in the `pgdata` volume |
| `migrate` | One-shot: applies new `migrations/*.sql` (tracked in `schema_migrations`), re-applies `seed/*.sql`, exits |
| `app` | FastAPI on port 8080, bound to `127.0.0.1` only; starts after `migrate` succeeds |

Everyday commands:

```bash
docker compose logs -f app                         # follow the app
docker compose run --rm migrate                     # after pulling new migrations
docker compose --profile test run --rm test         # ruff + full test suite on a throwaway DB
docker compose down                                 # stop (data kept); add -v to wipe the DB
```

The app listens on localhost only. Put it behind Caddy or your Cloudflare Tunnel for HTTPS
and phone access. `COOKIE_SECURE=true` works on `https://` and on `http://localhost`; set it to
`false` only when testing over plain http on a LAN address.

Database built by hand before `scripts/migrate.py` existed? Run once:
`docker compose run --rm migrate python scripts/migrate.py --baseline`.

### Without Docker

```bash
# PostgreSQL 15+ with a `greektutor` database; Python 3.12+
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # set DATABASE_URL too
set -a; source .env; set +a
python scripts/migrate.py                                # migrations + seeds
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

## How it works (for developers)

FastAPI + asyncpg (raw SQL) + PostgreSQL + the Claude API. Jinja2 templates with vanilla JS
`fetch`; no front-end framework. Conventions and layout: `CLAUDE.md`.

### A session, request by request

1. `POST /api/session/start` — picks the learner's **weakest focus cell** on the Harada board
   (`app/harada.py::pick_focus`). A lesson-scored cell opens that lesson; vocabulary, error and
   session-metric cells ride along on the next incomplete lesson. With no focus cells set, it
   falls back to the next lesson at the learner's level.
2. `POST /api/session/{id}/turn` — quota check → rebuild per-user context from Postgres (plus a
   `CURRENT FOCUS` block when the session has one) → Claude (tutor model, static prompt first)
   → parse the trailing JSON contract → apply SRS vocab events (with optional topic tags) → log usage.
3. `POST /api/session/{id}/close` — one eval-model call over the transcript → summary, error
   patterns, lesson score → stored → **board rescored**.

### The Harada board engine

Spec: `docs/HARADA_INTEGRATION.md`. The dashboard (`/`) **is** the board: the 9×9 mandala from
`docs/harada-board.html` rendered from `GET /api/harada`, with the goal/cycle form, the focus
list, and a detail panel per cell. Cell definitions: `seed/harada.sql` (40 cells score
automatically, 24 are manual). Scoring is pure Python in `app/harada_metrics.py`; the contract
for each `metric_kind` is in its module docstring.

| Endpoint | Form fields | Notes |
|---|---|---|
| `GET /api/harada` | — | The board payload (`docs/HARADA_BOARD_CONTRACT.md`) |
| `POST /api/harada/goal` | `goal_text`, `cycle_text`, `cycle_days`, `restart_cycle?` | Upsert the central goal / 90-day cycle |
| `POST /api/harada/action/{id}/focus` | `on=true\|false` | Max 5 focus cells, enforced server-side (409) |
| `POST /api/harada/action/{id}/state` | `state=not_started\|in_progress\|done` | Manual cells only (409 otherwise) |
| `POST /api/harada/routine` | `key`, `checked`, `log_date?` | Check-sheet write path; the sheet UI lives in the tracker |
| `POST /api/harada/recompute` | — | Rescore now (also runs at every session close) |
| `GET /healthz` | — | Liveness + DB check (Docker healthcheck) |

### Mirror for the tracker

Set `HARADA_EXPORT_PATH` and the same payload is written to that file, atomically, after
every board change (session close, focus, manual state, goal). The tracker bind-mounts it
read-only and mirrors the Greek board through `linked` cells; it never writes back. Contract,
ownership split and consumer rules: `docs/HARADA_BOARD_CONTRACT.md`. With one learner leave
`HARADA_EXPORT_USER_ID` empty; once a second account exists the export stops (logged) until
you pin it to a `users.id`. In Docker, the path is inside the container: compose mounts
`./export` at `/export`, so use `HARADA_EXPORT_PATH=/export/greek-board.json`.

### Tests

```bash
docker compose --profile test run --rm test     # everything, including DB tests
# or locally:
pip install -r requirements-dev.txt
ruff check app tests scripts
pytest                                          # DB tests skip unless TEST_DATABASE_URL is set
```

### Project docs

| File | What it's for |
|---|---|
| `docs/handoff-items/00-ROADMAP.md` | **Start here** — staged plan, one file per coding session |
| `docs/REQUIREMENTS_TRACE.md` | Board vs code, cell by cell |
| `docs/HARADA_INTEGRATION.md` | The spec for the progress engine |
| `docs/HARADA_BOARD_CONTRACT.md` | The board payload the tracker reads (schema 1) |
| `docs/harada-board.html` | The board prototype — the requirement |
| `CLAUDE.md` | Conventions for anyone (or any agent) changing the code |
