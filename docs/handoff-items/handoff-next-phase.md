# Handoff — board UI + tracker contract shipped; cycle close next

**Date:** 2026-09-13 · **Branch:** `feature/harada-board-ui`
**Plan of record:** `docs/HARADA_INTEGRATION.md` (build order §8). Steps 1–4 are done;
step 5 is deferred to the tracker; step 6 is next.
**Previous handoff** (engine, steps 1–3): in git history of this file, commit `babb448`.

## Decisions made this session

| Decision | Choice | Why |
|---|---|---|
| Repo layout | greek-tutor and tracker stay separate repos under `Projects/` | Python/FastAPI vs TypeScript/Prisma, different auth and databases: nothing to share at code level, only a data contract |
| Integration | greek-tutor **owns** the Greek board and exports it; the tracker **mirrors** it through `linked` cells and never writes back | Only the tutor has lesson scores, SRS state and error patterns; the tracker already pulls every external source read-only |
| Transport | A JSON file (`HARADA_EXPORT_PATH`), rewritten atomically after every board change | Matches how the tracker reads `data/*.json`; no token, no second listener. An authenticated endpoint can come later if freshness matters |
| Routine check sheet | **Not built here.** Lives in the tracker (habits with `board_action_id`) | One daily checklist, on the phone-first page with Hermes tools. `routine_log`, the scorer and `POST /api/harada/routine` stay as the write path |
| Multi-user + one file | Unpinned export writes only while there is exactly one account; `HARADA_EXPORT_USER_ID` pins it after that | Review finding: otherwise one learner's board could land in another's mirror |
| Board interaction | Click selects a cell; the detail panel holds Focus/Unfocus and (manual only) the three state buttons | The handoff sketched click-to-focus; a select-then-act panel is less surprising and shows `measure` first |

## What shipped

- `app/harada_export.py` — pure payload builder (`build_payload`, `goal_dict`), atomic
  `write`, `export_target`. Schema 1, documented in **`docs/HARADA_BOARD_CONTRACT.md`**.
- `app/harada.py` — `board_payload` (the SQL moved here from the router), `set_goal`, and
  `_export` called at the end of `recompute`, `set_focus`, `set_manual_state`, `set_goal`.
  Export failure is logged and never blocks the change.
- `app/harada_api.py` — thin now: validation + delegation; `GET /api/harada` returns the
  contract payload (new keys: `schema`, `board`, `generated_at`, `focus{}`, `totals{}`,
  per-theme `slot`, per-action `routine_key` and `updated_at`; `goal` gains
  `cycle_end`, `cycle_day`, `days_left` and drops `user_id`).
- `app/config.py`, `.env.example` — `HARADA_EXPORT_PATH`, `HARADA_EXPORT_USER_ID`.
- `templates/dashboard.html` — the board: 9×9 grid from `docs/harada-board.html`, goal /
  cycle form (with *restart cycle*), progress panel, focus list with the 3–5 prompt and a
  disabled Focus button at the cap (server still 409s), detail panel with `measure`,
  Rescore button, *Start today's session*. Expired sessions bounce to `/login` (the API
  still answers a 303, see *Deferred*). Vanilla JS, no innerHTML with user text.
- `templates/login.html` — unused HTMX script removed.
- Tests: 180 passing (`tests/test_harada_export.py` new; export + goal cases added to
  `tests/test_harada_db.py`). Ran against a throwaway `postgres:16` on port 5499 with all
  migrations and seeds applied.
- Docs: README (board section, mirror, env), `HARADA_INTEGRATION.md` §7/§8 notes,
  `CLAUDE.md` conventions and status.

## Review outcome (code-reviewer agent, 2026-09-13)

APPROVE, no CRITICAL/HIGH. Two MEDIUM findings, both fixed in this branch: the export
file write now runs in a thread (`asyncio.to_thread`) instead of blocking the event loop,
and an unpinned export refuses to write once a second `users` row exists (test:
`test_unpinned_export_stops_once_a_second_learner_exists`). XSS surface checked clean
(`textContent` only, Jinja autoescape, no `|safe`).

## Verified in a browser (2026-09-13, throwaway DB, fake API key)

Sign up → board renders all 64 cells → save goal (export file written, cycle day 1 of 90)
→ focus a computed cell (ring + focus list + `focus.count` 1 in the file) → set a manual
cell to done (green, theme 1/8, `totals.done` 1 in the file) → no console errors.
**Not verified:** the phone-width layout (`@media(max-width:700px)` hides labels and
shrinks cells) — the harness could not resize the viewport. Check it on a real phone.

## Unverified — still first next session

1. **Run a real session against the Claude API.** Same list as before: fill `.env`, start
   Postgres, apply migrations and seeds, sign up, focus 3 cells on the board, start a
   session, send turns, close it, confirm cells moved on the board and in the export file.
2. Check `response.usage.cache_read_input_tokens` on a turn (prompt is probably under
   Haiku's caching minimum; the fix is a breakpoint on the last transcript message).

## Next phase: cycle close (Harada step 6)

At `cycle_start + cycle_days` (the board already shows "cycle ended N days ago"):
recompute, one Sonnet call over the cycle's `summary_text` + `error_patterns` for a review,
mark newly-done cells, carry incomplete focus cells forward, ask for the next 3–5 focus
cells pre-ranked by weakest theme, write the new `cycle_text`, reset `cycle_start`
(`set_goal(..., restart_cycle=True)` already does the last two). Also the natural home for
the level-change job. Store the review (`harada_reviews` table, or reuse `harada_goals`
with a history) so the export can carry `last_review`.

## Tracker side (not this repo)

Phase 6 in `tracker/docs/implementation.md`: read `HARADA_EXPORT_PATH` (bind-mount
read-only like `data/*.json`), seed the Greek board's cells as `linked` rows keyed by
`actions[].id`, map habits to `routine_key`s, show the mirror on `/boards/greek`. Follow the
consumer rules in `docs/HARADA_BOARD_CONTRACT.md`.

## Deferred (unchanged from the previous handoff)

- Model IDs in `.env.example` are date-suffixed; current ids are undated. Sonnet 5 is now
  cheaper than Sonnet 4.6 for eval; Opus 5 tutors better per turn. Cost call is Yanni's.
- `require_user` raises a 303 for API routes; the dashboard works around it client-side.
  Return 401 for `/api/*`.
- `COOKIE_SECRET` is required by config but unused (`itsdangerous` too).
- No rate limiting on `/login` and `/signup`; no email verification. Fine for one user.
- `profiles.streak_count` / `last_active_date` never written; per-turn `error_tags`,
  `level_signal` and close-time `level_recommendation` parsed and dropped.
- No `docker-compose.yml`; README setup is manual psql.
- No HTTP-level tests of the routers (needs an auth cookie fixture).
- No per-user rate limit on `/recompute`; `clean_tag` accepts any slug.
- Voice and the 24 audio-shaped manual cells.

## How to run the tests

`pytest` for unit tests; `ruff check app tests`. For the database tests:

```bash
docker run -d --name greek-tutor-test-db -e POSTGRES_USER=tutor -e POSTGRES_PASSWORD=tutor \
  -e POSTGRES_DB=greektutor_test -p 127.0.0.1:5499:5432 postgres:16
docker exec greek-tutor-test-db psql -U tutor -d greektutor_test -c "CREATE EXTENSION IF NOT EXISTS citext;"
for f in migrations/001_schema.sql migrations/002_tutor_turns.sql migrations/003_harada.sql \
         seed/lessons_a1.sql seed/harada.sql; do
  docker exec -i greek-tutor-test-db psql -v ON_ERROR_STOP=1 -U tutor -d greektutor_test < "$f"
done
TEST_DATABASE_URL=postgresql://tutor:tutor@127.0.0.1:5499/greektutor_test pytest
```
