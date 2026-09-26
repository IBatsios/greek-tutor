# Requirements trace — `greek-harada-board.html` vs the code

**Date:** 2026-09-26 · **Board revision:** `docs/harada-board.html` (root `greek-harada-board.html`
is a byte-identical copy) · **Code revision:** `feature/harada-board-ui` @ `fb07513` + Docker/roadmap.
§1 and §3 were revised the same day after rebasing onto the board-UI branch.

The board is the requirement. This file says, for every board feature and every one of the
64 cells, whether the code does what the board says, and which roadmap stage closes the gap.
Stage numbers refer to `docs/handoff-items/00-ROADMAP.md`.

## Verdict

| Area | Status |
|---|---|
| Goal, 8 themes, 64 action **labels** | Match. 64/64 labels identical; one cosmetic change (7.3 says "error patterns", not the column name `error_patterns`). |
| Theme order and grid positions | Match. Theme ids 0–7 are the board's `THEMES` order; slot = position within the block. |
| **How cells are measured** | 31 match the board; 9 are measured differently from what the board says; 24 are `manual` where the board describes a measurement the app cannot take yet. |
| Board **UI** | Built on `/` (`feature/harada-board-ui`): grid, goal/cycle, focus, detail panel, isolation. Left: print, download, phone check (stage 03). |
| Daily routine check sheet | **Lives in the tracker by decision** (2026-09-13). Write path `POST /api/harada/routine` exists, but nothing feeds it from the tracker yet, so the 15 routine cells read 0 (stage 04). |
| 90-day cycle | Goal/cycle fields stored; nothing happens at day 90. |

The single most important finding: **24 of 64 cells can only move by hand, and the text-only
app cannot honestly measure speaking or listening at all.** The board promises a speaking goal;
the code today is a writing tutor with a speaking goal attached.

Status key: ✅ matches the board · ⚠️ measured, but not the way the board says · ✋ manual
(learner toggles it) · ❌ missing

## 1. Board features (UI and behaviour)

| Board feature | In code? | Notes / gap | Stage |
|---|---|---|---|
| 9×9 mandala: goal centre, 8 themes around it, each theme mirrored in its block | ✅ | `templates/dashboard.html` from `GET /api/harada` | — |
| Central goal text, 90-day target, cycle length, restart | ✅ | Goal/cycle form; `cycle_days` honoured (not hard-coded 90) | — |
| "Day N of M · K left" / "Cycle ended N days ago" | ✅ | From `goal.cycle_day` / `days_left` | — |
| Actually closing the cycle (review, new focus) | ❌ | | 07 |
| Progress: % done, done / in-progress counts, bar | ✅ partial | `totals` carries computed vs manual counts; confirm the headline % doesn't mix self-reported with measured (spec §9) | 03 |
| Theme rail with x/8; click theme → isolate; Esc; Show all | ✅ | | — |
| Click cell → cycle state | ⚠️ by design | Click selects; the detail panel holds Focus/Unfocus and (manual only) the three state buttons. Computed cells can't be hand-set (409) | — |
| Detail panel: theme, action, "Measured by" | ✅ | | — |
| "Keep 3–5 actions in progress" rule | ✅ stronger | Max 5 enforced server-side; Focus button disabled at the cap | — |
| Daily routine check sheet | ➜ tracker | Decision 2026-09-13: the tracker's Today page. Inbound feed missing — see §3 | 04 |
| Export progress (JSON) | ✅ different | Versioned export file for the tracker (`HARADA_EXPORT_PATH`, schema 1). A manual download button is still missing | 03 |
| Import progress | won't do | The DB is the source of truth | — |
| Print layout | ❌ | Port the prototype's `@media print` | 03 |
| Phone layout | unverified | `@media(max-width:700px)` exists; never seen on a device | 03 |
| Footer promise: every action resolves to data already in the schema | ⚠️ | True for 40 cells. 24 are manual; see §2 | 02, 08–11 |

## 2. The 64 cells

"Board says" is the prototype's measurement column; "Code does" is `seed/harada.sql`.

### 0 · Pronunciation & Script

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 0.1 | Write all 24 letters | A1-1 objective scored ≥0.9 | A1-1 lesson score ≥0.9 | ✅ | Scores the whole lesson, not the one objective; also moves 0.3 |
| 0.2 | Final sigma ς vs σ | pattern absent 5 sessions | `error_absent` "sigma", 5 sessions | ⚠️ | Absence ≠ mastery: 5 sessions that never used ς score 100%. Model's slugs are free text, so "sigma" may never match. → 02 (error taxonomy + "exercised" check) |
| 0.3 | Vowel digraphs αι ει οι ου | A1-1 objective ≥0.9 | A1-1 lesson ≥0.9 | ✅ | A1-1 objectives list αι/ει/ου — add οι to the lesson seed → 02 |
| 0.4 | Clusters μπ ντ γκ τζ | tutor pronunciation check 10/10 | manual | ✋ | Needs voice → 11 |
| 0.5 | τόνος on 50 words | stress errors <5% of turns | pattern absent 5 sessions | ⚠️ | Per-turn `error_tags` are parsed then dropped, so a per-turn rate is impossible → 02 |
| 0.6 | Shadow 5 min daily | check sheet 6/7 | `routine_days` shadow_5 6/7 | ✅ | Tracker feed → 04 |
| 0.7 | Record a paragraph vs native | monthly recording, self-scored | manual | ✋ | Recording store → 11 |
| 0.8 | δ/θ, γ before ε/ι | minimal-pair drill 18/20 | manual | ✋ | Needs TTS audio → 10 |

### 1 · Vocabulary & SRS

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 1.1 | Clear SRS queue daily | `COUNT(overdue) = 0` (computed) | self-reported check `srs_cleared` 7/7 | ⚠️ | Can be automatic: write the check when the due queue reaches 0 → 02/05 |
| 1.2 | 10 new words per session | `introduced` events ≥10 | avg ≥10 new `user_vocab` rows, last 5 sessions | ✅ | |
| 1.3 | 500 words at ≥80% | ratio ≥0.8 over 500 rows | same, seen ≥2× | ✅ | |
| 1.4 | 1,500 words at ≥80% | same at 1,500 | same | ✅ | |
| 1.5 | Nouns with article | greek stored as "ο καφές" | manual | ✋ | Add `pos` to `vocab_events`; score share of nouns stored with article → 02 |
| 1.6 | Verbs as 1sg + conjugate | `pos='verb'` drilled | manual | ✋ | `pos` column exists, never written → 02, drill → 05 |
| 1.7 | 8 topic clusters ×40 | tags cover 8, ≥40 each | `vocab_recall` 8 tags ×40 at ≥0.8 | ✅ | Stricter than board (adds recall). Fine |
| 1.8 | Weekly leech review | `srs_ease ≤1.5` surfaced Sundays | self-reported `leech_review` 1/7 | ⚠️ | Build the leech queue; completing it writes the check → 05 |

### 2 · Grammar & Morphology

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 2.1 | είμαι, έχω | A1-3, A1-7 ≥0.9 | same | ✅ | |
| 2.2 | -ω and -άω present | A1-9, A1-16 ≥0.9 | same | ✅ | |
| 2.3 | Nom/acc/gen with article | A1-5, 13, 21 ≥0.85 | same | ✅ | |
| 2.4 | Gender from ending | pattern absent 5 sessions | same ("gender") | ⚠️ | Same vacuous-truth + slug problem as 0.2 → 02 |
| 2.5 | δεν/μην, questions | A1-9 objective | A1-9 lesson ≥0.85 | ✅ | |
| 2.6 | θα and να | A1-19 ≥0.85 | same | ✅ | |
| 2.7 | Aorist of 30 verbs | A2 gate; drill 27/30 | manual | ✋ | No A2 lessons → 12 |
| 2.8 | Clitic order | B1 marker, error pattern | manual | ✋ | Deliberately manual (absence at A1 proves nothing) → 12 |

### 3 · Listening

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 3.1 | 10 min audio daily | check sheet 6/7 | `listening_10` 6/7 | ✅ | Tracker feed → 04 |
| 3.2 | Radio/podcast 3×/week | check sheet | `radio` 3/7 | ✅ | Tracker feed → 04 |
| 3.3 | Series episode weekly | weekly log | `episode` 1/7 | ✅ | Tracker feed → 04 |
| 3.4 | Transcribe 60 s | tutor-graded ≥0.8 | manual | ✋ | Graded task + audio → 09/10 |
| 3.5 | Numbers dictation 20/20 | A1-15 objective; 18/20 | A1-15 lesson ≥0.9 | ⚠️ | Text lesson ≠ dictation; real dictation needs TTS → 10 |
| 3.6 | News gist 4/5 | tutor comprehension check | manual | ✋ | → 10 |
| 3.7 | No English fallback | sessions with zero English turns | no 3+ letter Latin word in learner turns, last 5 | ✅ | Same metric drives 4.6 and 6.3 — three cells move together |
| 3.8 | Contractions στο/στη | A1-14 objective | A1-14 lesson ≥0.85 | ✅ | Written only until TTS → 10 |

### 4 · Speaking

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 4.1 | 15 min unscripted per session | `minutes_used` **in speaking mode** | avg ≥15 "AI minutes" per text session | ⚠️ | Wrong mode, and AI minutes ≈ 0.3 per turn, so 15 min ≈ 50 turns — barely inside the 60-turn cap. → 02 (real study time), 11 (voice) |
| 4.2 | Narrate day, past tense | A1-22 then A2 aorist | A1-22 ≥0.85 | ✅ | A2 half → 12 |
| 4.3 | Order, shop, directions | A1-8/14/15 role-plays | same lessons ≥0.85 | ✅ | Typed, not spoken, until 11 |
| 4.4 | Describe a photo 90 s | timed drill, no pause >4 s | manual | ✋ | → 11 |
| 4.5 | Weekly native conversation | weekly log | `native_convo` 1/7 | ✅ | Tracker feed → 04 |
| 4.6 | English fillers to zero | English-token count = 0 | same metric as 3.7 | ✅ | |
| 4.7 | Self-correct gender | self-corrections ≥3/session | manual | ✋ | Add `self_corrections` to the turn contract → 02 |
| 4.8 | 10-min unprepared conversation | THE GOAL — exit check | manual | ✋ | Always a human judgement; cycle review asks for it → 07 |

### 5 · Reading

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 5.1 | Read signs aloud | daily habit | `signs_aloud` 6/7 | ✅ | Tracker feed → 04 |
| 5.2 | A1 graded reader | logged completion | manual | ✋ | Reading module logs completions → 08 |
| 5.3 | Headlines daily | check sheet | `headlines` 6/7 | ✅ | Tracker feed → 04 |
| 5.4 | Children's book | logged completion | manual | ✋ | → 08 |
| 5.5 | Read aloud 5 min | check sheet 6/7 | `read_aloud_5` 6/7 | ✅ | Tracker feed → 04 |
| 5.6 | 10 unknown words per text into SRS | `vocab_events` sourced from reading | manual | ✋ | Tap-to-add in reader writes a `source` → 08 |
| 5.7 | Greek subtitles | weekly log | `greek_subs` 1/7 | ✅ | Tracker feed → 04 |
| 5.8 | A2 story, <10 lookups | A2 gate | manual | ✋ | Reader counts lookups → 08/12 |

### 6 · Writing

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 6.1 | Three sentences daily | check sheet | `three_sentences` 6/7 | ✅ | Could be a graded daily task instead of a tick → 09 |
| 6.2 | Café order + shopping list | A1-8, A1-15 | same ≥0.85 | ✅ | |
| 6.3 | Greek keyboard, accents | typed input in sessions | greek_only, last 3 | ✅ | Doesn't check accents; fine for now |
| 6.4 | 100 words about yourself | tutor-graded ≥0.8 | manual | ✋ | Graded writing tasks → 09 |
| 6.5 | Message a real Greek speaker | logged once | manual | ✋ | Stays manual |
| 6.6 | Rewrite 5 flagged errors | `error_patterns` worked per session | manual | ✋ | Error-rewrite drill at session end → 09 |
| 6.7 | Greek line in journal | check sheet | `journal_line` 6/7 | ✅ | Overlaps 6.1 — merge the tracker habits or the cells → 04 |
| 6.8 | 200-word past narrative | A2 gate | manual | ✋ | → 09/12 |

### 7 · Habit & Environment

| # | Action | Board says | Code does | St. | Gap → stage |
|---|---|---|---|---|---|
| 7.1 | 45 min/day, same block | `profiles.daily_goal_minutes` met | ≥45 **AI** minutes on each of last 7 days | ⚠️ | Hard-codes 45 while `daily_goal_minutes` defaults to 60. 45 AI minutes ≈ 130+ turns/day — effectively unreachable. → 02 |
| 7.2 | Never miss two days | `profiles.streak_count` | no two idle days in 30, from `usage_ledger` | ⚠️ | Scoring is fine; `streak_count` / `last_active_date` are never written, so no streak can be shown → 02 |
| 7.3 | Phone/OS in Greek | one-time | manual | ✋ | Stays manual |
| 7.4 | Weekly error review | weekly ritual | `weekly_review` 1/7 | ✅ | A review screen that writes the check → 07 |
| 7.5 | Visible 90-day target | the cycle field | manual | ✋ | Could auto-score "cycle_text set and cycle not expired" → 07 |
| 7.6 | Greek playlist | passive, daily | `playlist` 5/7 | ✅ | Tracker feed → 04 |
| 7.7 | 20 sticky-note labels | one-time | manual | ✋ | Stays manual |
| 7.8 | Monthly self-assessment recording | 12 a year | manual | ✋ | Recording store → 11 |

Cell numbers here are 1-based within each theme, as the board displays them; the database
`slot` is 0-based (board cell 0.1 = theme 0, slot 0).

## 3. Daily routine check sheet (owned by the tracker)

The prototype's six daily items, and where each one's tick must come from:

| Prototype item | Seed key | Cell(s) it moves | Source after the roadmap |
|---|---|---|---|
| Clear the SRS due queue | `srs_cleared` | 1.1 | **This app** — computed from the SRS queue (stage 02); the key leaves the export |
| One tutor session (45 min) | — | 7.1, 7.2 | This app — study minutes (stage 02) |
| 10 min listening, no subtitles | `listening_10` | 3.1 | Tracker habit |
| Read aloud for 5 minutes | `read_aloud_5` | 5.5 | Tracker habit |
| Three sentences written in Greek | `three_sentences` | 6.1 | Tracker habit |
| Shadow 5 minutes of native audio | `shadow_5` | 0.6 | Tracker habit |

Keys the prototype's sheet had no place for; the tracker needs a habit for each:
`radio`, `episode`, `native_convo`, `signs_aloud`, `headlines`, `greek_subs`, `journal_line`,
`playlist`. Two move to this app because the activity happens here: `leech_review` (stage 05)
and `weekly_review` (stage 07).

**The gap:** the board contract says the tracker never writes back, and
`POST /api/harada/routine` needs a browser session. Until stage 04 adds an inbound path, every
tracker-owned routine cell reads 0 no matter what you tick.

## 4. Defects found during this review (not board mismatches)

| # | Defect | Effect | Stage |
|---|---|---|---|
| D1 | `ai_minutes` = model latency + 0.25 min per turn | Understates real study time 3–5×; cells 4.1 and 7.1 are unreachable in practice | 02 |
| D2 | Per-turn `error_tags`, `level_signal`, close-time `level_recommendation` parsed then dropped | No error rate, no level job | 02 |
| D3 | `error_absent` treats "not practised" as "clean" | Cells 0.2, 0.5, 2.4 go green without evidence | 02 |
| D4 | No controlled error vocabulary; seed matches substrings of free-text slugs | Cells may never match what the eval model writes | 02 |
| D5 | One lesson score satisfies several cells (A1-1 → 0.1 and 0.3; A1-15 → 3.5, 4.3, 6.2) | Board progress moves in jumps | accepted; note in UI |
| D6 | Duplicate board file (`greek-harada-board.html` = `docs/harada-board.html`) | Two copies will drift | 03 — keep one |
| D9 | Tracker ticks have no path into `routine_log` | 15 routine cells stuck at 0 | 04 |
| D7 | `require_user` returns 303 to API callers | `fetch().json()` fails on expired sessions | 01 |
| D8 | Session never "exercises" a vocab-cell focus when the model ignores the focus block | Focus is a prompt hint, not enforced | 02 (measure) / 13 (evals) |
