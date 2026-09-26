# Harada board contract (schema 1)

The one payload other apps read from greek-tutor. It is returned by
`GET /api/harada` (session cookie) and, when `HARADA_EXPORT_PATH` is set,
written to that file after every board change. The first consumer is the
tracker (`tracker/docs/plan.md`, slice 2 "Harada boards"): its Greek board
mirrors this file through `linked` cells and never writes back.

## Ownership

| Who | Owns | Because |
|---|---|---|
| greek-tutor | Cells scored from tutor data (`lesson_score`, `vocab_count`, `vocab_recall`, `error_absent`, `session_metric`), manual cells set on this board, the goal and cycle, focus selection | Only the tutor has the lesson scores, SRS state and error patterns |
| tracker | The daily routine (habits) and the check sheet UI | It is the phone-first Today page with Hermes tools; a second checklist here would compete with it |

`routine_days` cells stay defined here with a `routine_key`, so the tracker can
map a habit to a cell by that key. Until the tracker feeds them, they read 0
and sessions never pick them (they are not "sessionable").

## Transport

- **File** (default): greek-tutor writes `HARADA_EXPORT_PATH` atomically
  (temp file + rename in the same directory), UTF-8, pretty-printed. Readers
  bind-mount it read-only, the way the tracker already reads `data/*.json`.
  It is refreshed at session close (recompute) and on every focus, manual-state
  or goal change. If the write fails, the board change still succeeds and the
  failure is logged.
- **HTTP**: `GET /api/harada` returns the identical JSON for the signed-in
  learner. There is no token-authenticated route yet; add one only if a consumer
  needs fresher-than-session-close data.
- The file holds **one learner's board**. With `HARADA_EXPORT_USER_ID` unset it
  is written only while there is exactly one account; the moment a second
  `users` row exists the export stops with a logged warning until you pin it to
  a `users.id`. One learner's goal text never lands in another learner's mirror.

## Shape

```json
{
  "schema": 1,
  "board": "greek",
  "generated_at": "2026-09-13T16:19:02.512345+00:00",
  "goal": {
    "goal_text": "Hold a real 10-minute conversation in Greek",
    "cycle_text": "Finish A1 lessons 1-12",
    "cycle_start": "2026-09-13",
    "cycle_days": 90,
    "cycle_end": "2026-12-12",
    "cycle_day": 1,
    "days_left": 90
  },
  "focus": {"count": 1, "min": 3, "max": 5},
  "totals": {"actions": 64, "done": 1, "in_progress": 0, "not_started": 63,
             "computed": 40, "manual": 24},
  "themes": [
    {
      "slot": 0, "slug": "pronunciation",
      "name_en": "Pronunciation & Script", "name_el": "Προφορά & Αλφάβητο",
      "done": 0,
      "actions": [
        {
          "id": 1, "slot": 0,
          "label": "Write all 24 letters from memory, upper and lower case",
          "measure": "Lesson A1-1 scored ≥0.9",
          "kind": "lesson_score", "is_manual": false, "routine_key": null,
          "state": "not_started", "progress": 0.0, "is_focus": false,
          "updated_at": null
        }
      ]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `schema` | Bumped only for incompatible changes. Adding a key is not a bump; removing or renaming one is. |
| `board` | Constant `"greek"`; lets a consumer that holds several boards tell files apart. |
| `generated_at` | UTC ISO-8601. Consumers should treat the payload as a snapshot as of this moment. |
| `goal` | `null` until the learner writes one. `cycle_end` is `cycle_start + cycle_days`; `cycle_day` is 1-based; `days_left` goes negative once the cycle is over. |
| `focus` | `count` of focus cells and the rule they are held to (3–5). The server refuses a 6th with 409. |
| `totals` | Counts over all 64 actions. `computed + manual = actions`; `done + in_progress + not_started = actions`. |
| `themes[].slot` | 0–7, the theme's fixed position on the 9×9 grid. Themes arrive sorted by slot. |
| `actions[].id` | Stable database id of the action definition. Use it as the join key for `linked` cells; it does not change when the seed is re-applied. |
| `actions[].slot` | 0–7 within the theme. Actions arrive sorted by slot. |
| `actions[].kind` | One of `lesson_score`, `vocab_count`, `vocab_recall`, `error_absent`, `routine_days`, `session_metric`, `manual`. Scoring details (`metric_args`) are deliberately not exported. |
| `actions[].routine_key` | Only for `routine_days` cells: the check-sheet key a habit maps to (snake_case). `null` otherwise. |
| `actions[].state` | `not_started` (progress 0), `in_progress` (0 < progress < 1), `done` (progress 1). |
| `actions[].progress` | 0.0–1.0, three decimals. |
| `actions[].updated_at` | UTC ISO-8601 of the last time progress moved, or `null` if the learner has never touched the cell. |

## Consumer rules

1. Read, never write. The only way to change this board is through greek-tutor.
2. Join on `actions[].id`, not on labels; labels are edited in `seed/harada.sql`.
3. Treat a missing or unparsable file as "no data", not as an empty board.
4. Check `schema` and refuse anything higher than you understand.

Tests pinning this shape: `tests/test_harada_export.py` (pure) and the export
section of `tests/test_harada_db.py` (against Postgres).
