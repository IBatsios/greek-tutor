# Stage 05 — Daily practice UX

**Status:** not started · **Branch:** `feature/05-practice-ux` · **Size:** one session
**Depends on:** 04 · **Closes:** cells 1.1 (fully), 1.8, 1.6 (optional)

## Goal

Make the two things you do every day — review words and talk to the tutor — fast, pleasant and
cheap. Today, SRS review only happens inside a Claude conversation: slow, costs tokens, and the
model decides what counts as "correct".

## Primer — SRS in one paragraph

Spaced repetition shows a word just before you would forget it. Each correct answer pushes the
next review further out (interval × ease); each miss resets it to tomorrow and lowers the ease.
`app/srs.py` already implements this (SM-2 style). A **leech** is a word you keep failing
(low ease, many misses) — re-teaching it differently beats reviewing it again.

## Tasks

### A. Review page `/review` — no AI
- [ ] `GET /api/review/next?limit=20` → due cards (`user_vocab` due ≤ today, ordered by due date then ease). Direction alternates: Greek→English (recognition) and English→Greek (production).
- [ ] `POST /api/review/answer` → grade. English→Greek compares after Unicode NFC + lowercase; an answer correct except for accents is "almost" (shown, counts as incorrect for SRS, but tagged `stress_accent` in a review log). Greek→English: self-graded (show answer, "I knew it / I didn't").
- [ ] Writes via `srs.apply_vocab_event(..., source='review')`. When the queue hits zero, stage 02 records the day as cleared (cell 1.1).
- [ ] Keyboard-first: Enter = check, 1/2 = self-grade.

### B. Leech queue
- [ ] Leech = `srs_ease ≤ 1.5` or `times_seen − times_correct ≥ 3`. `/review?leeches=1` shows them with the full example sentence and mnemonic field.
- [ ] Finishing a leech round records the date in a tutor-owned table (not `routine_log`, which the tracker feeds); cell 1.8 moves to a computed metric over it — what the board says ("surfaced every Sunday").
- [ ] The board header shows "n leeches — weekly review due" on the day you choose (default Sunday).

### C. Session page `/practice`
- [ ] Header: focus action + lesson topic; objective progress bar from `objective_progress`.
- [ ] Render tutor corrections: escape HTML, then turn `**x**` into `<strong>`. Never `innerHTML` raw model text.
- [ ] Greek input helper: buttons for ά έ ή ί ό ύ ώ ϊ ϋ ΐ ΰ ς and a toggle hint for the Windows Greek keyboard (`;` then vowel = accent).
- [ ] Resume: `GET /api/session/open` returns the open session and its transcript, so a reload doesn't orphan a session.
- [ ] Session timer (study minutes, from stage 02) and a clear "End session" → recap screen: summary, new words, errors by taxonomy slug, "what moved on your board".
- [ ] Error states: 401 → login, 429 → friendly quota message, network error → retry button that doesn't duplicate the turn.
- [ ] Auto-close sessions idle > 2 h (on next start), so evaluation always runs.

### D. Optional: conjugation drill (cell 1.6)
- [ ] Verbs with `pos='verb'` → a 6-person conjugation grid, graded by rule-free exact match against a Claude-generated key cached per verb. Log to a `drill_results` table. Only if time remains.

## Tests

Unit: answer normalisation (accents, final sigma, NFC vs NFD input). HTTP: review loop to
empty queue writes `srs_cleared`; leech round writes `leech_review`; `/api/session/open`.

## Definition of done

- [ ] 50 reviews take under 5 minutes and cost zero tokens.
- [ ] A reload mid-session loses nothing.
- [ ] Trace: 1.1 and 1.8 ✅.

## Session notes

_(fill in at the end of the session)_
