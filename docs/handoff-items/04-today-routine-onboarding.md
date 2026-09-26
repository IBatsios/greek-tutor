# Stage 04 — Onboarding, start flow & the tracker feed

**Status:** not started · **Branch:** `feature/04-onboarding-feed` · **Size:** one session
**Depends on:** 03

> **Revised 2026-09-26.** The first draft of this stage built a daily check sheet here. That
> contradicts a recorded decision: the check sheet lives in the **tracker** (the phone-first
> Today page), and this app owns only the board. Do **not** build a second checklist here.

## Goal

A new account is set up in under two minutes, opening the app makes the next action obvious,
and the 15 `routine_days` cells finally move — from ticks you make in the tracker.

## Primer — why the routine cells are stuck today

15 of the 64 cells (shadowing, 10-min listening, headlines…) are `routine_days`: they score
from `routine_log`. Only `POST /api/harada/routine` writes that table, it needs a browser
session cookie, and the board contract says the tracker **never writes back**. So nothing
writes those ticks. One of the two sides has to move data the other way.

| Option | How | Trade-off |
|---|---|---|
| **A. This app reads a tracker file** (default) | Tracker writes `habits.json` (date → routine_key → done); `recompute` reads it into `routine_log` | Same file pattern already used in the other direction; no tokens, no listener. Freshness = tracker's write frequency |
| B. Tracker calls this app | `POST /api/harada/routine` accepts a service token (`TRACKER_TOKEN`) | Instant, but a second auth path and the contract's "never writes back" rule changes |

## Tasks

### A. Tracker feed (after the decision)
- [ ] Write the reverse contract in `docs/HARADA_BOARD_CONTRACT.md` (§ "Inbound: routine ticks"):
  shape, keys = the `routine_key` values in the export, dates in `APP_TIMEZONE`.
- [ ] Option A: `TRACKER_HABITS_PATH` env; `app/routine_feed.py` (pure parser + upsert into
  `routine_log`), called at the start of `recompute` and on board load; malformed file → log,
  never fail. Docker: mount the tracker's data dir read-only.
- [ ] Tests: parser rejects unknown keys and future dates; upsert is idempotent.

### B. Start flow on `/`
- [ ] Header strip above the board: streak (from stage 02), study minutes today vs
  `daily_goal_minutes`, due SRS count, and the start button labelled with the action the
  session will work on ("Start: Final sigma ς vs σ", from `pick_focus`), falling back to
  "Continue lesson A1-n".
- [ ] "Pick 3–5 focus actions" banner when `focus.count < focus.min` (the board already
  prompts; make it the first thing a new learner sees).

### C. Onboarding (first login, no `harada_goals` row)
- [ ] Step 1: goal (pre-filled with the board's text) and first 90-day target (pre-filled:
  "Finish A1 lessons 1–12 and hold a 5-minute introduction conversation").
- [ ] Step 2: level — A0 "I can't read the alphabet" / A1 "I can read, know some words" →
  `profiles.level_estimate`. Placement test comes in stage 12.
- [ ] Step 3: daily minutes (default 45).
- [ ] Step 4: pick 3–5 focus actions; pre-select a starter set for A0: 0.1 letters,
  0.3 digraphs, 1.2 ten new words, 2.1 είμαι/έχω, 7.1 daily minutes.

## Definition of done

- [ ] A tick in the tracker moves its cell on this board after the next recompute.
- [ ] New account → onboarding → first session in under two minutes.
- [ ] Trace §3: every routine key has a path from the tracker to its cell.

## Session notes

_(fill in at the end of the session)_
