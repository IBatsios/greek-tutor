# Stage 07 — Cycle close, weekly review, level job (Harada step 6)

**Status:** not started · **Branch:** `feature/07-cycle-close` · **Size:** one session
**Depends on:** 02 (stored signals), 04 (Today view) · **Closes:** cells 7.4, 7.5, and the 4.8 exit-check prompt

## Goal

Close the Harada loop: a short weekly review that looks at your errors, and a 90-day review that
decides what the next cycle is about. Also the level-change job the README has flagged since Phase 1.

## Primer — why reviews matter more than sessions

Sessions produce data; reviews turn data into the next decision. Without the review, the board
just accumulates colour. The weekly review is small (5 minutes, errors + leeches). The cycle
review is the big one: what moved, what didn't, and which 3–5 cells get the next 90 days.

## Tasks

### A. Weekly review `/review/week`
- [ ] Last 7 days: sessions, study minutes vs goal, top 5 error slugs with one example each (from `tutor_turns.error_tags`), leeches, routine completion.
- [ ] "Done" writes `routine_log.checks.weekly_review = true` (cell 7.4).
- [ ] Optional: one Haiku call for a 3-sentence "what to watch next week" (cache on the row).

### B. Cycle close
- [ ] Migration: `harada_cycles (id, user_id, started, ended, goal_text, cycle_text, review_text, focus_before JSONB, focus_after JSONB, cells_done JSONB)`.
- [ ] Trigger: when Today loads and `cycle_start + cycle_days ≤ today`, show the review flow instead of Today.
- [ ] Flow: recompute → one eval-model call over the cycle's session summaries + error slugs + board deltas → review text → show newly done cells → carry unfinished focus cells forward (pre-checked) → pick new focus (pre-ranked by weakest theme) → new `cycle_text` → reset `cycle_start` → store the cycle row.
- [ ] Ask the exit question for cell 4.8 at every cycle close: "Did you hold a 10-minute unprepared conversation this cycle?" (manual, stays manual).
- [ ] Cell 7.5 becomes computed: `cycle_text` non-empty and the cycle not overdue.

### C. Level-change job
- [ ] Runs at session close: if the last 3 `level_recommendation` values are all `raise` **and** every `lesson_score` cell for the current level is done → bump `profiles.level_estimate`; all `lower` → drop one. Log every change to a `level_changes` table.
- [ ] Surface it: "You're now A2 — new lessons unlocked" on Today.

## Tests

Pure: level decision function over sequences. DB: cycle close writes a cycle row, resets the
start date, keeps carried focus. HTTP: Today redirects into the review flow when the cycle is over.

## Definition of done

- [ ] A cycle can be closed end to end with a fake-dated DB (set `cycle_start` 91 days back).
- [ ] Trace: 7.4, 7.5 ✅.

## Session notes

_(fill in at the end of the session)_
