# Roadmap — from "engine written" to "used every day"

**Written:** 2026-09-26, revised the same day after rebasing onto `feature/harada-board-ui`
(the board UI + tracker export MR) · **Replaces** "pick the newest handoff file" as the entry point.
**Inputs:** `greek-harada-board.html` (the requirement), `docs/HARADA_INTEGRATION.md` (the spec),
`docs/REQUIREMENTS_TRACE.md` (where the code and the board disagree, cell by cell).

## How to use this folder

1. Open this file. Take the **first stage whose status is not `done`**.
2. Open that stage file. Do its *Before you start* checks, then work the task list top to bottom.
3. A stage is one coding session (roughly 2–4 hours). If it runs over, stop at a green
   test run, write *Session notes* at the bottom of the stage file, and set status `in progress`.
4. When the stage's *Definition of done* is met: set status `done` here, update
   `docs/REQUIREMENTS_TRACE.md` for any cells that changed, and add *Session notes*.
5. Every stage: branch `feature/NN-slug`, conventional commits, `docker compose --profile test run --rm test` green before merging.

`handoff-next-phase.md` is the 2026-09-13 session log. It is history, not the plan.

## Stages

| # | Stage | Delivers | Status |
|---|---|---|---|
| 01 | [First real run](01-first-real-run.md) | Stack runs in Docker; one real session (API key **or** your Claude subscription) moves the board; HTTP-level tests | not started |
| 02 | [Honest measurement](02-honest-measurement.md) | Real study time, error taxonomy, per-turn signals stored, streaks — the numbers stop lying | not started |
| 03 | [Board UI leftovers](03-board-ui.md) | The board itself shipped in `feature/harada-board-ui`; what's left is print, download, phone check | mostly done |
| 04 | [Onboarding, start flow & tracker feed](04-today-routine-onboarding.md) | First-run setup, one-tap start, and the tracker's check-sheet ticks reaching the 15 routine cells | not started |
| 05 | [Daily practice UX](05-daily-practice-ux.md) | Flashcard SRS review (no AI cost), leech queue, a session page worth using daily | not started |
| 06 | [Deploy & accountability](06-deploy-and-nudges.md) | On your homelab behind HTTPS, nightly backups, nudges (here or in the tracker), phone-friendly | not started |
| — | **Milestone M1: daily-usable (text)** | Tracker Today page + this app's board and sessions, every day, from your phone | — |
| 07 | [Cycle close & weekly review](07-cycle-close-and-review.md) | The 90-day review, weekly error review, level-change job (step 6) | not started |
| 08 | [Reading module](08-reading-module.md) | Graded texts, tap-to-look-up, words flow into SRS, comprehension checks | not started |
| 09 | [Writing tasks](09-writing-tasks.md) | Graded writing assignments and the error-rewrite drill | not started |
| 10 | [Listening (TTS)](10-listening-tts.md) | Audio for tutor replies, dictation, minimal pairs, news-gist drills | not started |
| 11 | [Speaking (STT)](11-speaking-stt.md) | Voice sessions, speaking minutes, recordings, timed speaking drills | not started |
| — | **Milestone M2: speaks and reads** | Every theme on the board can move from real evidence | — |
| 12 | [A2 curriculum & placement](12-a2-curriculum-placement.md) | A2 lessons, gates, placement test, level job wired to lessons | not started |
| 13 | [Tutor quality evals](13-tutor-quality-evals.md) | Replayable transcripts + rubric so prompt/model changes are measured, not guessed | not started |

Stage 13 has no hard dependency; pull it forward the first time you want to change the
tutor model or prompt.

## Dependency sketch

```
01 ──► 02 ──► 03 ──► 04 ──► 05 ──► 06 ══► M1
               │                     │
               └──────► 07 ◄─────────┘
02 ──► 08 ──► 09
02 ──► 10 ──► 11 ══► M2
07 ──► 12
01 ──► 13 (any time)
```

## Cells that stay manual forever (by design)

6.5 message a real speaker · 7.3 phone in Greek · 7.7 sticky-note labels · 4.8 the goal itself.
Everything else has a stage that gives it evidence.

## Decisions already made (don't re-open without a reason)

| Decision | Where recorded |
|---|---|
| Daily routine check sheet lives in the **tracker**, not here | `docs/HARADA_BOARD_CONTRACT.md`, `CLAUDE.md` (2026-09-13) |
| greek-tutor owns the board; the tracker mirrors it read-only via the export file | same |
| Vanilla JS + JSON endpoints, no HTMX | `CLAUDE.md` |
| Two model backends: `LLM_BACKEND=api` (default) or `claude_cli` (your subscription, single-user only) | `feature/llm-backends`, README "Choosing how the app talks to Claude" |

## Decisions still owed by Yanni

| Decision | Needed by | Default if nobody decides |
|---|---|---|
| Tutor model: Haiku 4.5 (cheap) vs Sonnet 5 / Opus (better tutoring) | 01 | Haiku 4.5 for turns, Sonnet 5 for eval |
| Backend for daily use: API key or Claude subscription | 01 | API key; subscription is opt-in |
| How the tracker's check-sheet ticks reach this app (the contract says the tracker never writes back) | 04 | This app reads a tracker export file, mirroring the existing pattern |
| Who sends nudges: this app or the tracker | 06 | The tracker (it's already the phone-first page) |
| Keep root `greek-harada-board.html` or `docs/harada-board.html` as the one copy | 01 | Keep `docs/`, delete root |
| Nudge channel: email, Telegram, or ntfy | 06 | ntfy (self-hosted, no account) |
| Self-hosted TTS/STT vs a cloud API | 10 | Self-hosted (Piper, faster-whisper) |
| Where the app runs: homelab dev VM or the AI server | 06 | Homelab dev VM |
