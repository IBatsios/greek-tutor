# Stage 03 — Board UI (Harada step 4)

**Status:** not started · **Branch:** `feature/03-board-ui` · **Size:** one session
**Depends on:** 02 (so the board shows honest numbers the first time you look at it)

## Goal

Port `greek-harada-board.html` into the app so the board you designed is the board you use,
driven by `GET /api/harada` instead of the hard-coded `THEMES` array.

## Primer — the one behaviour that changes

In the prototype, clicking any cell cycles its state. In the app, state is **computed** for
40 cells — hand-editing them would make the board lie. So a click means different things:

| Cell kind | Click | Shift-click | Detail panel buttons |
|---|---|---|---|
| computed (`is_manual: false`) | toggle **focus** (ring) | — | Focus on / off; shows progress % and "Measured by" |
| manual (`is_manual: true`) | cycle state forward | cycle back | Not started / In progress / Done (as prototype) + focus toggle |

## Tasks

### A. Serve static assets
- [ ] Mount `StaticFiles` at `/static` in `app/main.py`; add `static/` to the Dockerfile `COPY` lines.
- [ ] `static/board.css` (prototype CSS verbatim, then trimmed) and `static/board.js`.

### B. API additions (`app/harada_api.py`)
- [ ] Per cell: `routine_key` (from `metric_args.key` when kind is `routine_days`) and `theme_id`.
- [ ] Top level: `counts: {done, in_progress, not_started, focus}`, split into measured vs self-reported (spec §9: manual cells must not silently inflate the %).
- [ ] `goal`: include `cycle_day` and `cycle_days_left` computed server-side from `cycle_start` and `cycle_days`.

### C. `templates/board.html` — parity checklist against the prototype
- [ ] 9×9 mandala; centre goal cell (goal text + "Μιλάω ελληνικά"); theme cells + mirrored theme cells with x/8.
- [ ] Cell colours by state; focus cells ringed (new style — the prototype has none); number badge 1–8.
- [ ] Header: Show all · Download progress (the `/api/harada` JSON) · Print.
- [ ] Panel 1: goal textarea, 90-day target, cycle start + "Day N of M · K left" (M = `cycle_days`, not 90), Save → `POST /api/harada/goal`.
- [ ] Panel 2: % done, done / in progress counts, bar, legend, "Focus x/5" with the 3–5 rule; refuse a 6th focus client-side too.
- [ ] Rail: 8 themes with mini bars; click → isolate; Esc clears.
- [ ] Detail panel: theme · action n, label, "Measured by", progress %, buttons per the primer table.
- [ ] `@media print` from the prototype.
- [ ] Narrow screens (<700 px): the 9×9 grid is unreadable on a phone. Show the theme list; tapping a theme shows its 3×3 block full-width.
- [ ] Routine panel is **not** here — it moves to Today (stage 04). Leave a link.

### D. Wiring
- [ ] `/` keeps the greeting for now; add `/board`. Stage 04 turns `/` into Today with a Board tab.
- [ ] Every `fetch` handles 401 → `/login` and 409 → show the server's message.

## Tests

HTTP: board JSON contains the new fields; `counts` add up to 64. A DB test that a manual cell
set to `done` is counted as self-reported, not measured.
Manual: open the prototype and `/board` side by side; walk the parity checklist.

## Definition of done

- [ ] Every row in trace §1 marked stage 03 is ✅.
- [ ] Focusing a 6th cell is refused with the server's message.

## Out of scope

Today view, onboarding, routine checkboxes (04).

## Session notes

_(fill in at the end of the session)_
