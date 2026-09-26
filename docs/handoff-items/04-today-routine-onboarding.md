# Stage 04 — Today view, routine check sheet, onboarding (Harada step 5)

**Status:** not started · **Branch:** `feature/04-today` · **Size:** one session
**Depends on:** 03

## Goal

Opening the app answers one question: **what do I do today?** A new user gets set up in under
two minutes; a returning user sees today's checklist, this week's list, their streak, and one
button that starts the right session.

## Primer — why a check sheet and not just sessions

Harada's daily check sheet is the accountability mechanism: small, binary, done-or-not items
you tick every day. The tutor session is only one of them. 15 cells on the board are
`routine_days` — they move **only** when you tick their box. Today, no box exists for any of
them. This stage is what makes those 15 cells reachable.

## Tasks

### A. Routine items come from the seed, not from a hard-coded list
- [ ] `GET /api/today` returns `daily` and `weekly` routine items derived from `harada_actions` where `metric_kind = 'routine_days'`: `days/window ≥ 5/7` → daily; otherwise weekly. Each item: `key`, label, cell id, today's checked state, this week's count vs target.
- [ ] Label source: add a short `routine_label` to `metric_args` in `seed/harada.sql` (e.g. `shadow_5` → "Shadow 5 min of native audio") — the cell label is too long for a checkbox. Update the seed contract + test.
- [ ] "One tutor session" is not a checkbox — show today's `study_minutes` vs `daily_goal_minutes` as a progress ring (from stage 02).
- [ ] `srs_cleared` shows as automatic (ticked by the system, stage 02); still clickable if you cleared it elsewhere.
- [ ] Merge or clearly separate 6.1 (three sentences) and 6.7 (journal line) — the trace flags the overlap. Decide, then edit the seed.

### B. Diary line
- [ ] `POST /api/harada/routine` accepts `note` (writes `routine_log.note`, capped at 500 chars). One text field under the checklist: "One line about today's Greek".

### C. Today page (`/`)
- [ ] Header: streak (🔥 n days), minutes today / goal, due SRS count.
- [ ] Primary button: **Start session on ‹weakest focus action›** (label from `pick_focus`), falling back to "Continue lesson A1-n".
- [ ] Secondary: **Review n due words** (stage 05 builds the page; link it now).
- [ ] Daily checklist, weekly list, diary line.
- [ ] Nudges shown in-page: "You missed yesterday — today keeps the chain alive" when `last_active_date` = today − 2; "Pick 3–5 focus actions" when `focus_count < 3` (links to the board).
- [ ] Tabs or links: Today · Board · Practice · Review.

### D. Onboarding (first login, no `harada_goals` row)
- [ ] Step 1: the goal (pre-filled with the board's text; editable) and the 90-day target (pre-filled: "Finish A1 lessons 1–12 and hold a 5-minute introduction conversation").
- [ ] Step 2: level (A0 "I can't read the alphabet" / A1 "I can read, know some words") → `profiles.level_estimate`. Placement test comes in stage 12.
- [ ] Step 3: daily minutes (default 45) and preferred time block (stored for stage 06 nudges — add `profiles.practice_time TIME`).
- [ ] Step 4: pick 3–5 focus actions. Pre-select a sensible starter set for A0: 0.1 letters, 0.3 digraphs, 1.2 ten new words, 1.1 clear SRS, 7.1 daily minutes.

## Tests

HTTP: `/api/today` classification (daily vs weekly) for every routine key in the seed; ticking a
box then `recompute` moves its cell; onboarding writes goal, level, focus. Unit: routine
classification helper.

## Definition of done

- [ ] All 15 `routine_days` cells can move from the UI.
- [ ] New account → onboarding → first session in under two minutes.
- [ ] Trace §3 table: every key has a home.

## Session notes

_(fill in at the end of the session)_
