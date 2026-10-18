# Roadmap — from "engine written" to "spoken every day"

**Written:** 2026-09-26 · **Revised:** 2026-10-18, reordered voice-first into four phases after
[greek-plan.md](greek-plan.md) (the 12-month learning plan) and Yanni's answers to its decisions.
**Inputs:** `docs/harada-board.html` (the requirement), `docs/HARADA_INTEGRATION.md` (the spec),
`docs/REQUIREMENTS_TRACE.md` (where the code and the board disagree, cell by cell),
`greek-plan.md` (why voice comes second, the 60-minute daily block, how the tutor should teach).

## How to use this folder

1. Open this file. Take the **first phase not done**, and inside it the first stage or task
   not marked `done`.
2. Open that stage file. Read its *Decisions override* banner if it has one: the
   decisions table below wins over anything older in the stage file. Then do its *Before
   you start* checks and work the task list top to bottom, **limited to the scope this file
   gives the stage in that phase** (stages 06, 10 and 11 run in parts).
3. A stage is one coding session (roughly 2–4 hours). If it runs over, stop at a green
   test run, write *Session notes* at the bottom of the stage file, and set status `in progress`.
4. When the stage's *Definition of done* is met: set status here, update
   `docs/REQUIREMENTS_TRACE.md` for any cells that changed, and add *Session notes*.
5. Every stage: branch `feature/NN-slug`, conventional commits, `docker compose --profile test run --rm test` green before merging.

`handoff-next-phase.md` is the 2026-09-13 session log. It is history, not the plan.

**Don't let the build eat the Greek.** The daily 60-minute block is never coding time, and
phase 1 runs on the teach skill and a human tutor, not this app (greek-plan.md, problem 6).

## Phases

### Phase 1 — The tutor runs for real

| # | Stage | Scope in this phase | Status |
|---|---|---|---|
| 01 | [First real run](01-first-real-run.md) | As written, on `LLM_BACKEND=api` with `TUTOR_MODEL=claude-sonnet-5-5`; update `.env.example` model IDs | not started |
| 02 | [Honest measurement](02-honest-measurement.md) | As written; real study time is what the 60-minute block (cell 7.1) is measured against | not started |

**Done when:** a real session moves the board and the study-time numbers are honest.

### Phase 2 — Voice slice (ends at **M1: speak with the tutor daily, from the phone**)

| # | Stage | Scope in this phase | Status |
|---|---|---|---|
| 10 | [Listening (TTS)](10-listening-tts.md) | **Tutor replies aloud only.** Cloud neural TTS (vendor from the listening test), two voices, audio cached by text hash. Dictation, minimal pairs and news-gist wait for phase 4 | not started |
| 11 | [Speaking (STT)](11-speaking-stt.md) | **Voice turns in `/practice` only.** Cloud STT (Azure `el-GR`), text as fallback, speaking minutes recorded. Recordings, shadowing and timed drills wait for phase 4 | not started |
| — | Tutor prompt for voice | greek-plan.md "How the tutor should teach" items 1–4: two-sentence replies ending in a question; prompt a retry before recasting; tell the model it reads a transcript; server-side tonos check that rejects a reply | not started |
| — | Backend per mode | `llm.backend(mode)`: voice → `api` (streams), text → `claude_cli` allowed. Keep the interface provider-neutral so an OpenAI or local backend is one new class later, gated on stage 13 | not started |
| 06 | [Deploy & accountability](06-deploy-and-nudges.md) | **Deploy and backups only**, on the workstation at `greek.ioannisbatsios.com` (a phone mic needs HTTPS). Nudges move to the tracker (phase 3) | not started |

**Gate:** measure voice latency on your phone — end of your speech to start of the reply —
and record it in stage 11's session notes. Set the target from that first number.

### Phase 3 — The whole 60-minute block runs from the tracker (ends at **M2**)

| # | Stage | Scope in this phase | Status |
|---|---|---|---|
| 05 | [Daily practice UX](05-daily-practice-ux.md) | As written, plus: audio cards (hear → say → type); validate cards before they enter the deck (article on nouns, tonos, gloss checked); seed the first 1,500 words from a frequency list | not started |
| — | `/learn` | Serve `course/lessons` and `course/reference` read-only, each lesson with a button that starts the matching session; today's reference sheet goes into the tutor's context (plan item 6) | not started |
| 04 | [Onboarding, start flow & tracker feed](04-today-routine-onboarding.md) | As written; tick feed = **a tracker export file** this app reads | not started |
| 03 | [Board UI leftovers](03-board-ui.md) | Print, download, phone check | mostly done |
| — | Tracker side (in `tracker/`) | Learning card on the home page: board mirror summary + start button. Nudges via ntfy. Tracker work, its own MR | not started |

**Done when:** the daily block (greek-plan.md "A day, a week, a month") starts from the
tracker's Learning card and every step in it lands in the board.

### Phase 4 — Review loops and the rest of voice (ends at **M3: every theme moves from evidence**)

| # | Stage | Scope in this phase | Status |
|---|---|---|---|
| 07 | [Cycle close & weekly review](07-cycle-close-and-review.md) | As written, plus: the Sunday review proposes teach-skill learning records for you to confirm; the cycle-close conversation is graded by your human tutor (cell 4.8) | not started |
| 10 | Listening (TTS) | The rest: dictation, minimal pairs with two voices, news-gist | not started |
| 11 | Speaking (STT) | The rest: shadowing record-and-compare, monthly 3-minute recording, timed drills | not started |
| 06 | Deploy & accountability | Whatever the deploy half left (restore drill) | not started |

### After phase 4

| # | Stage | Delivers | Status |
|---|---|---|---|
| 08 | [Reading module](08-reading-module.md) | Graded texts, tap-to-look-up, words flow into SRS | not started |
| 09 | [Writing tasks](09-writing-tasks.md) | Graded writing and the error-rewrite drill | not started |
| 12 | [A2 curriculum & placement](12-a2-curriculum-placement.md) | A2 lessons, gates, placement, level job | not started |
| 13 | [Tutor quality evals](13-tutor-quality-evals.md) | Replayable transcripts + rubric. **Pull forward** before switching to Haiku or adding any non-Claude backend | not started |

## Alongside the build — not code

From greek-plan.md "This week". These start now and don't wait for any phase:

- [ ] Daily 60-minute block on the calendar (shows on the tracker's Calendar card); 20-minute floor on bad days.
- [ ] Trial lesson with a Greek-speaking conversation tutor; then weekly, 30–45 minutes.
- [ ] `course/MISSION.md` from the board's goal and the 90-day target, then `/teach` for lesson A1-1.
- [ ] Voice spike: Chrome speech recognition set to `el-GR`, ten sentences, read the transcripts.
- [ ] TTS listening test: five sentences each from Chirp 3 HD, Azure and ElevenLabs; your tutor picks.

## Dependency sketch

```
Phase 1          Phase 2                         Phase 3                    Phase 4
01 ──► 02 ──┬──► 10 (replies aloud) ──► 11 (voice turns) ──┐
            │                                              ├──► 05 ──► /learn ──► 07 ──► 10/11 rest
            └──► 06 (deploy) ─────────────────────────────┘     04 ◄── tracker export file
                                                                 tracker: Learning card, ntfy
02 ──► 08 ──► 09        07 ──► 12        01 ──► 13 (any time; before any model/provider change)
```

## Cells that stay manual forever (by design)

6.5 message a real speaker · 7.3 phone in Greek · 7.7 sticky-note labels · 4.8 the goal itself
(graded by a person at each cycle close). Everything else has a stage that gives it evidence.

## Decisions

The 2026-10-18 decisions override older text in the stage files.

| Decision | Choice | Recorded |
|---|---|---|
| Daily routine check sheet lives in the **tracker**, not here | — | `HARADA_BOARD_CONTRACT.md`, `CLAUDE.md` (2026-09-13) |
| greek-tutor owns the board; the tracker mirrors it read-only via the export file | — | same |
| Front end | Vanilla JS + JSON endpoints, no HTMX | `CLAUDE.md` |
| Daily budget | 60 min, 20-minute floor; cell 7.1 → 60, tutor session → 25 | 2026-10-18 |
| How the app reaches Claude | Split by mode: `api` for voice (streaming), `claude_cli` allowed for text. Interface stays open to an OpenAI or local backend later, gated on stage 13 evals | 2026-10-18 |
| Tutor model | `claude-sonnet-5-5` for turns until stage 13 shows a cheaper model matches it | 2026-10-18 |
| Speech-to-text | Cloud (Azure `el-GR`), not faster-whisper `small` | 2026-10-18 |
| Text-to-speech | Cloud neural, two voices, cached; vendor picked by the listening test | 2026-10-18 |
| Where the app runs | The workstation, on the `ibatsios_default` network with the tracker | 2026-10-18 |
| Hostname | `greek.ioannisbatsios.com`: third nginx server block, its own Access app | 2026-10-18 |
| Human tutor | Weekly, 30–45 min, conversation and pronunciation; grades cells 4.5 and 4.8 | 2026-10-18 |
| Tracker ticks → this app | A tracker export file this app reads (mirror of the board pattern) | 2026-10-18 |
| Nudges | The tracker sends them, via ntfy | 2026-10-18 |
| Board prototype | `docs/harada-board.html` is the one copy; root copy deleted | 2026-10-18 |

## Still open

| Question | Needed by | How to settle it |
|---|---|---|
| TTS vendor | Phase 2, stage 10 | The listening test above |
| Voice latency target | Phase 2 gate | First measurement on the phone |
| Pronunciation scoring for Greek | Phase 4, stage 11 rest | Check Azure's pronunciation-assessment tab for `el-GR` |
| Default model for `EVAL_MODEL` | Stage 01 | Confirm the current Sonnet ID resolves; revisit with stage 13 |
