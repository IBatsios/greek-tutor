# Stage 12 — A2 curriculum & placement

**Status:** not started · **Branch:** `feature/12-a2` · **Size:** one session (plus content review time)
**Depends on:** 07 (level job) · **Closes:** cells 2.7, 4.2 (A2 half), 5.8, 6.8

## Goal

The curriculum stops at A1-24. The board's gate cells and the central goal sit at A2–B1. Add
A2 lessons, gate the A2 cells on them, and give new users a placement test instead of a
self-reported level.

## Tasks

- [ ] `seed/lessons_a2.sql`: ~24 lessons. Must include: aorist of the 30 most common verbs (2.7), past narration (4.2), passive/‑ομαι verbs, comparatives, object pronouns & clitic order (2.8 groundwork), imperative, future continuous vs simple, relative clauses with που. Review the list against a published A2 syllabus for Greek before seeding.
- [ ] `theme_ids` for each A2 lesson (as in `seed/harada.sql`).
- [ ] Seed changes: 2.7 → `lesson_score` on the aorist lessons; 4.2 → A1-22 **and** the A2 past-narration lesson; 5.8 → reading metric on A2 texts (stage 08); 6.8 → writing task at A2 (stage 09).
- [ ] A2 reading texts (stage 08 generator) and A2 writing task.
- [ ] **Placement test** (`/placement`): ~25 items stepping A0 → A2 (alphabet reading, gender, cases, present, past); stop after 4 consecutive misses; sets `level_estimate` and marks earlier lessons `completed` with the placement score.
- [ ] Spec §9 note: at B1 the grid needs re-cutting (register, idiom). Write `docs/B1_RECUT.md` as a stub when the first A2 cycle closes — not before.

## Definition of done

- [ ] An A1-complete learner is offered A2 lessons by `next_lesson_id` and the focus picker.
- [ ] Trace: 2.7 ✅; 4.2, 5.8, 6.8 ✅.

## Session notes

_(fill in at the end of the session)_
