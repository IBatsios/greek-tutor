# Stage 09 — Writing tasks

**Status:** not started · **Branch:** `feature/09-writing` · **Size:** one session
**Depends on:** 02 (taxonomy) · **Closes:** cells 6.4, 6.6, 6.8, text half of 3.4; optionally 6.1

## Goal

Chat trains short replies. The board also asks for longer writing (100 words about yourself,
a 200-word past-tense narrative) and for fixing your own flagged errors. Add assignments with a
rubric, graded by the eval model, stored so progress is visible.

## Primer — rubric grading with an LLM

A **rubric** turns "is this good?" into a few scored criteria (task done, grammar, vocabulary
range, spelling/accents). Asking the model for JSON against a fixed rubric makes grades
comparable across weeks; asking for a free-form opinion does not. Grades still drift — stage 13
checks them against your own judgement on a sample.

## Tasks

- [ ] Migration: `writing_tasks (id, slug, level, prompt_en, prompt_el, min_words, rubric JSONB)`; `writing_submissions (id, user_id, task_id, body, score REAL, feedback JSONB, error_tags JSONB, created_at)`.
- [ ] Seed tasks: `about_me_100` (6.4), `past_narrative_200` (6.8, A2), `transcribe_60s` (3.4 — text given for now, audio in stage 10), `daily_three` (6.1, optional daily task instead of a tick).
- [ ] `/write`: prompt, textarea with word count and the Greek input helper, submit → eval call → score, corrected version with diff, error slugs.
- [ ] **Error-rewrite drill** (cell 6.6): at session close, the recap offers the session's flagged sentences; you rewrite ≥5; each is checked (exact-ish match to the tutor's correction, else a cheap Haiku check). Count stored per session → new `session_metric` field `rewrites`.
- [ ] Seed changes: 6.4, 6.8 → `writing_score` metric (`{"task":"about_me_100","min":0.8}`); 6.6 → `session_metric rewrites min 5`.

## Tests

Pure: new scorers. DB: submission stored with slugs from the taxonomy only. HTTP: word-count
floor enforced server-side.

## Definition of done

- [ ] You submitted `about_me_100` and agree with the grade within ±0.1.
- [ ] Trace: 6.4, 6.6 ✅; 6.8 ✅ once A2 exists.

## Session notes

_(fill in at the end of the session)_
