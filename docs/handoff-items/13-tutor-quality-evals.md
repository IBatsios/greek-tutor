# Stage 13 — Tutor quality evals

**Status:** not started · **Branch:** `feature/13-evals` · **Size:** one session, then ongoing
**Depends on:** 01 (recorded transcripts) · Pull forward the first time you change model or prompt.

## Goal

Every other stage trusts the tutor: that it follows the focus block, corrects with a light
touch, keeps Greek proportional to level, and emits valid JSON. Measure those, so a model or
prompt change is a comparison, not a vibe.

## Primer — offline evals

Replay fixed inputs (recorded learner turns) through the tutor, then score the outputs with
cheap deterministic checks where possible and an LLM grader only where needed. Keep the set
small (20–40 turns) so a run costs cents and finishes in a minute.

## Tasks

- [ ] `evals/cases/*.json`: learner turn + context block (level, focus, due words) from stage 01's transcripts plus hand-written edge cases (English-only reply, off-topic, repeated same error).
- [ ] Deterministic checks: JSON contract parses; `error_tags` ⊂ taxonomy; reply ends with something for the learner to do (question mark or imperative); Greek-script share within the level's band (A1 ≈ 30%, B1 ≈ 80%).
- [ ] LLM-graded checks (eval model, fixed rubric, JSON out): followed the CURRENT FOCUS; correction style (restate, bold, one-line reason); no lecture > N lines.
- [ ] `python -m evals.run --model … --prompt-rev …` → table + JSON report in `evals/reports/`; compare two reports side by side.
- [ ] Also evaluate the **eval model**: does `lesson_score` agree with your own grade on 10 sessions within ±0.15?
- [ ] Not in CI by default (costs money, needs the key); a `make evals` / compose profile `evals`.

## Definition of done

- [ ] A baseline report for the current model/prompt is committed.
- [ ] Changing the tutor model is a decision you can make from two reports.

## Session notes

_(fill in at the end of the session)_
