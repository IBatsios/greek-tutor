# Stage 08 — Reading module

**Status:** not started · **Branch:** `feature/08-reading` · **Size:** one to two sessions
**Depends on:** 02 (`user_vocab.source`) · **Closes:** cells 5.2, 5.4, 5.6, 5.8 (with 12)

## Goal

Reading is half of what you asked this app to teach, and today it has no reading material at
all — only chat. Add graded texts you read in the app, where every unknown word is one tap
from your SRS deck.

## Primer — graded reading

A **graded reader** is text written inside a vocabulary budget for a level, so ~95% of words are
known and the rest are learnable from context. Below ~90% known, reading becomes decoding and
stops building fluency. The app knows your vocabulary (`user_vocab`), so it can measure
coverage per text before you open it.

## Tasks

### A. Content
- [ ] Migration: `reading_texts (id, level, topic_tag, title, body, glossary JSONB, questions JSONB, source TEXT, reviewed BOOL)`; `reading_attempts (user_id, text_id, started_at, finished_at, lookups INT, score REAL)`.
- [ ] `scripts/gen_reading.py`: the eval model writes A1 texts (120–250 words) per topic cluster × lesson range, with glossary and 4 comprehension questions, as JSON. Store with `reviewed=false`. Generate once, reuse forever; never generate on page load.
- [ ] Review 5 texts yourself before trusting the generator; add `reviewed` gating if quality is uneven.

### B. Reader `/read`
- [ ] List: texts at your level with **coverage %** (share of tokens already in `user_vocab`); default sort puts 90–98% first.
- [ ] Reader: tokenised body; tap a word → gloss (glossary, else vocab_items, else one cached Claude lookup) → "Add to SRS" writes `source='reading'`.
- [ ] Finish → comprehension questions → `reading_attempts` row (lookups counted automatically).
- [ ] "I finished a real book" form: title + date → logged completion for 5.2/5.4 outside the app.

### C. Metrics
- [ ] New `session_metric` fields or a `reading` kind: texts finished at level, words added from reading per text (cell 5.6: ≥10), lookups on an A2 text (cell 5.8: <10, gated by stage 12's A2 texts).
- [ ] Reading minutes count toward `study_minutes` (cell 7.1).

## Tests

Unit: tokeniser (punctuation, final sigma, elision like σ' αυτό), coverage calc. DB: add-to-SRS
writes source. Seed/contract tests for new metric args.

## Definition of done

- [ ] 20 reviewed A1 texts; reading one and adding words moves 5.6.
- [ ] Trace: 5.2, 5.4, 5.6 ✅ (5.8 after stage 12).

## Session notes

_(fill in at the end of the session)_
