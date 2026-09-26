# Stage 03 — Board UI leftovers (Harada step 4)

**Status:** mostly done · **Branch:** `feature/03-board-leftovers` · **Size:** a short session
**Shipped in:** `feature/harada-board-ui` (commit `1b9466b`, 2026-09-13) — the 9×9 board on `/`,
goal/cycle form with restart, progress + focus panels, detail panel with focus toggle and
manual-state buttons, theme isolation + Esc, Rescore, *Start today's session*, and the
versioned export the tracker mirrors (`docs/HARADA_BOARD_CONTRACT.md`).

## Goal

Close the few gaps between the shipped board and the prototype, and verify the one thing
nobody has checked: how it looks on a phone.

## Interaction model (already built — keep it)

| Cell kind | Click | Detail panel |
|---|---|---|
| computed | select | Focus / Unfocus, progress %, "Measured by" |
| manual (dashed badge) | select | Focus / Unfocus + Not started / In progress / Done |

The prototype's click-to-cycle is intentionally gone: 40 cells are computed and hand-editing
them would make the board lie.

## Tasks

- [ ] **Phone width** — the `@media(max-width:700px)` layout was never seen on a device
  (the 2026-09-13 harness couldn't resize). Check at 390 px. If the grid is unreadable, show
  the theme list and open a theme's 3×3 block full-width on tap.
- [ ] **Print** — port the prototype's `@media print` block (hide rail, detail, buttons).
- [ ] **Download progress** — a header button that saves `GET /api/harada` as
  `greek-board-YYYY-MM-DD.json` (the prototype's *Export progress*; import stays out — the DB
  is the source of truth).
- [ ] **Completion %** — confirm the headline % separates measured (computed) from
  self-reported (manual) progress, per spec §9. `totals` already has `computed`/`manual`
  counts; the UI may need a second number.
- [ ] One copy of the prototype: `docs/harada-board.html` is referenced everywhere;
  `greek-harada-board.html` at the root is a duplicate (roadmap decision).

## Definition of done

- [ ] Used the board on your phone for a week without zooming.
- [ ] Trace §1 has no ❌ rows left for stage 03.

## Session notes

_(fill in at the end of the session)_
