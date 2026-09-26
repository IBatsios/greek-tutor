# Stage 02 — Honest measurement

**Status:** not started · **Branch:** `feature/02-honest-measurement` · **Size:** one long session, or two
**Depends on:** 01 · **Closes:** trace defects D1–D4, cells 0.2, 0.5, 1.1, 1.5, 2.4, 4.1, 4.7, 7.1, 7.2

## Goal

Make the numbers on the board mean what their labels say. Right now several cells can go
green without the learner having done the thing (absence of errors in sessions that never
practised the structure), and two can essentially never go green (study time measured as
model latency).

## Primer — why the current numbers lie

A **proxy metric** is a number you can measure standing in for a thing you can't. They fail in
two directions:

| Failure | Example in this code | Fix pattern |
|---|---|---|
| **False green** — proxy satisfied without the skill | `error_absent`: 5 sessions with no "gender" error count as mastery, even if you never produced a gendered noun | Count only sessions where the structure was *exercised* |
| **False red** — skill present, proxy can't see it | `ai_minutes` = model latency + 15 s per turn, so 45 real minutes of study logs as ~10 | Measure the learner's time, not the model's |
| **Silent mismatch** — proxy and data use different words | seed looks for substring `"gender"`; the eval model may write `noun-adj-agreement` | A fixed vocabulary both sides share |

## Tasks

### A. Migration `004_measurement.sql`
- [ ] `tutor_turns`: `error_tags JSONB DEFAULT '[]'`, `exercised JSONB DEFAULT '[]'`, `objective_progress REAL`, `level_signal TEXT`, `self_corrections INT DEFAULT 0`.
- [ ] `tutor_sessions`: `study_minutes REAL DEFAULT 0`, `level_recommendation TEXT`.
- [ ] `usage_ledger`: `study_minutes REAL DEFAULT 0` (quota stays on `ai_minutes`; habit cells move to `study_minutes`).
- [ ] `user_vocab`: `source TEXT NOT NULL DEFAULT 'session'` (`session|review|reading|writing`) — stage 08 needs it.
- [ ] `profiles.daily_goal_minutes` default → 45 to match the board's cell 7.1 (update existing row for Yanni).
- [ ] Extend the `metric_kind` CHECK if you add a kind (see D).

### B. Error taxonomy — `app/errors.py`
- [ ] A fixed tuple of slugs with one-line descriptions, e.g. `final_sigma`, `stress_accent`, `gender_agreement`, `article_case`, `verb_ending`, `verb_tense`, `word_order`, `clitic_order`, `preposition_contraction`, `spelling_vowel` (ι/η/υ/ει/οι), `english_fallback`. Start with ~12; extend by PR, never ad hoc.
- [ ] Both prompts (`STATIC_TUTOR_PROMPT`, `EVAL_PROMPT`) list the slugs verbatim and say "use only these; anything else is `other`".
- [ ] Normalise on ingest: unknown slug → `other`; store the model's raw text in the summary only.
- [ ] Seed: `error_absent` patterns become exact slugs; `_mentions` switches from substring to equality. Update `test_harada_seed.py` to assert every pattern is in the taxonomy.

### C. Store what the turn contract already returns
- [ ] Turn contract gains `"exercised": [slugs the learner produced correctly or incorrectly this turn]` and `"self_corrections": n`.
- [ ] `tutor.turn()` writes `error_tags`, `exercised`, `objective_progress`, `level_signal`, `self_corrections` onto the assistant `tutor_turns` row.
- [ ] `close_session` stores `level_recommendation`.

### D. Scoring changes (pure, in `harada_metrics.py`, each with tests)
- [ ] `SessionFact` gains `exercised`, `error_turns` (per slug), `turns`, `self_corrections`, `study_minutes`.
- [ ] `error_absent`: window = last N sessions **that exercised the pattern**; fewer than N such sessions caps progress below 1.0. Cells 0.2, 2.4.
- [ ] New `session_metric` field `error_turn_rate` `{"pattern":"stress_accent","max":0.05,"sessions":5}` → progress = share of those sessions under the rate. Cell 0.5 (board: "stress errors <5% of turns").
- [ ] New field `self_corrections` `{"min":3,"sessions":5}` → cell 4.7 leaves `manual`.
- [ ] `minutes_used` metrics read `study_minutes`. Cell 4.1.
- [ ] `daily_minutes` reads ledger `study_minutes` and the learner's `daily_goal_minutes` (load it into `Facts`), not a hard-coded 45. Cell 7.1.

### E. Study time
- [ ] At each turn: `study_minutes += min(now − previous learner turn, IDLE_CAP)` with `IDLE_CAP = 3 min`. First turn of a session counts 1 min. Write to the session and the ledger.
- [ ] Document the rule in the module docstring: it's an estimate, it can't see you reading a textbook.

### F. Streak and automatic checks
- [ ] On the first activity of a day, update `profiles.last_active_date` and `streak_count` (reset to 1 after a gap ≥2 days — Harada's "never miss two", not "never miss one").
- [ ] When the SRS due queue reaches zero (after a vocab event), upsert `routine_log.checks.srs_cleared = true` for today. Cell 1.1 becomes what the board says: computed.
- [ ] Vocab `pos`: add `"pos"` to `vocab_events`; `srs.apply_vocab_event` writes it on insert. New `vocab_form` kind, or a `vocab_count` variant, for cell 1.5: share of nouns stored with their article (`ο/η/το/οι/τα …`) ≥0.95 over ≥50 nouns. Leave 1.6 manual until stage 05.
- [ ] Add `οι` to lesson A1-1's objectives (cell 0.3 names it; the lesson doesn't).

## Tests

Pure scorer tests for every new field and the exercised-window rule (a session that did not
exercise the pattern must not count as clean). DB test: a turn writes all five new columns.
Seed test: taxonomy membership. HTTP test: turn with the fake Claude returns a contract with
`exercised` and the row lands.

## Definition of done

- [ ] `docs/REQUIREMENTS_TRACE.md`: 0.2, 0.5, 1.1, 1.5, 2.4, 4.1, 4.7, 7.1, 7.2 re-rated; D1–D4 closed.
- [ ] A real 20-minute session logs 15–25 `study_minutes` (sanity-check the idle cap).
- [ ] Test profile green.

## Out of scope

The level-change job (reads `level_recommendation`; stage 07). Any UI.

## Session notes

_(fill in at the end of the session)_
