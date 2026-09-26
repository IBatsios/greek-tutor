# Harada Method as the progress engine for `greek-tutor`

Spec for turning the 64-cell board from a wall poster into the app's model of the learner.
Targets the existing Phase 1 schema (`migrations/001_schema.sql`) and session loop
(`app/tutor.py`, `app/srs.py`).

---

## 1. Why this fits

The Harada Method is a goal-decomposition system: one long-horizon goal → 8 supporting
themes → 8 concrete actions per theme (64 total), plus a daily routine check sheet and a
periodic review. It fits language learning better than most subjects for three reasons:

1. **Language competence is genuinely 8-ish orthogonal axes.** Vocabulary, grammar,
   pronunciation, and the four skills fail independently. A learner at 800 words with no
   listening practice is a specific, diagnosable shape — a linear lesson sequence hides
   that; a 64-cell grid shows it as a hole.
2. **Harada's actions must be observable.** That constraint forces every cell to bind to a
   number. The app already produces those numbers.
3. **The routine check sheet is the daily loop.** That's what a tutor session already is.

The thing the app gets out of it that a lesson sequence can't give: **a reason to pick the
next session that isn't just `seq + 1`.**

---

## 2. What the app already has vs. what's missing

| Harada concept | Existing | Missing |
|---|---|---|
| Long-term goal | — | goal text + horizon per user |
| 8 themes | implied by `lessons.objectives` | not modelled |
| 64 actions | partly = `lessons.objectives` entries | no first-class row, no state |
| Action progress | `user_lessons.score`, `user_vocab`, `error_patterns` | no rollup to a cell |
| Routine check sheet | `profiles.daily_goal_minutes`, `streak_count`, `usage_ledger` | no per-item checklist |
| Periodic review | `tutor_sessions.summary_text` | no cycle boundary / reset |

Nothing needs to be thrown away. The Harada layer sits **above** lessons, not instead of them.

---

## 3. Schema additions

```sql
-- migrations/003_harada.sql
BEGIN;

CREATE TABLE harada_goals (
    user_id       BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    goal_text     TEXT NOT NULL,
    cycle_text    TEXT NOT NULL DEFAULT '',     -- current 90-day target
    cycle_start   DATE NOT NULL DEFAULT CURRENT_DATE,
    cycle_days    INT  NOT NULL DEFAULT 90
);

CREATE TABLE harada_themes (
    id        SMALLINT PRIMARY KEY,             -- 0..7, fixed positions on the grid
    slug      TEXT NOT NULL UNIQUE,             -- 'pronunciation','vocabulary',...
    name_en   TEXT NOT NULL,
    name_el   TEXT NOT NULL
);

CREATE TABLE harada_actions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    theme_id    SMALLINT NOT NULL REFERENCES harada_themes(id),
    slot        SMALLINT NOT NULL CHECK (slot BETWEEN 0 AND 7),
    label       TEXT NOT NULL,
    -- how this cell is scored. See §4.
    metric_kind TEXT NOT NULL CHECK (metric_kind IN
                  ('lesson_score','vocab_count','vocab_recall','error_absent',
                   'routine_days','session_metric','manual')),
    metric_args JSONB NOT NULL DEFAULT '{}',
    UNIQUE (theme_id, slot)
);

CREATE TABLE user_harada_actions (
    user_id     BIGINT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_id   BIGINT  NOT NULL REFERENCES harada_actions(id) ON DELETE CASCADE,
    state       TEXT    NOT NULL DEFAULT 'not_started'
                CHECK (state IN ('not_started','in_progress','done')),
    progress    REAL    NOT NULL DEFAULT 0,     -- 0.0-1.0, computed
    is_focus    BOOLEAN NOT NULL DEFAULT false, -- one of the 3-5 active this cycle
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, action_id)
);
CREATE INDEX idx_uha_focus ON user_harada_actions(user_id) WHERE is_focus;

-- Daily routine check sheet: one row per user per day.
CREATE TABLE routine_log (
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date   DATE   NOT NULL DEFAULT CURRENT_DATE,
    checks     JSONB  NOT NULL DEFAULT '{}',    -- {"srs_cleared":true,"listening_10":false,...}
    note       TEXT   NOT NULL DEFAULT '',      -- the Harada diary line
    PRIMARY KEY (user_id, log_date)
);

-- Link an existing lesson to the theme(s) it serves, so lesson completion
-- moves cells without any new bookkeeping.
ALTER TABLE lessons ADD COLUMN theme_ids SMALLINT[] NOT NULL DEFAULT '{}';

COMMIT;
```

Add `tags` conventions on `vocab_items` so `vocab_count` metrics can filter by cluster
(`cafe`, `market`, `travel`, `home`, `work`, `health`, `weather`, `family`).

---

## 4. Binding each cell to real data

`metric_kind` + `metric_args` is the whole trick. A nightly job (or an
end-of-session hook) recomputes `progress` for every action and promotes
`state` to `done` when `progress >= 1.0`.

| `metric_kind` | `metric_args` example | Computation |
|---|---|---|
| `lesson_score` | `{"lessons":[3,7],"min":0.9}` | all listed `user_lessons.score >= min` |
| `vocab_count` | `{"n":500,"recall":0.8}` | rows in `user_vocab` where `times_correct/times_seen >= recall` |
| `vocab_recall` | `{"tags":["cafe"],"n":40,"recall":0.8}` | same, filtered by `vocab_items.tags` |
| `error_absent` | `{"pattern":"gender agreement","sessions":5}` | pattern missing from the last N `tutor_sessions.error_patterns` |
| `routine_days` | `{"key":"listening_10","days":6,"window":7}` | count of `routine_log.checks->>key = true` |
| `session_metric` | `{"field":"minutes_used","min":15,"mode":"voice"}` | aggregate over recent `tutor_sessions` |
| `manual` | `{}` | user toggles it (recordings, sticky notes, one-off milestones) |

Example seed rows:

```sql
INSERT INTO harada_actions (theme_id, slot, label, metric_kind, metric_args) VALUES
(0,1,'Final sigma ς vs σ — 20 words with zero slips',
   'error_absent', '{"pattern":"σ/ς final sigma","sessions":5}'),
(1,0,'Clear the SRS due queue every day — zero overdue',
   'routine_days','{"key":"srs_cleared","days":7,"window":7}'),
(1,2,'500 words held at ≥80% recall',
   'vocab_count','{"n":500,"recall":0.8}'),
(2,0,'Conjugate είμαι and έχω with no hesitation',
   'lesson_score','{"lessons":[3,7],"min":0.9}');
```

The recompute is one function, ~120 lines, in a new `app/harada.py`:

```python
async def recompute(user_id: int) -> None:
    """Recompute progress for all 64 actions. Call at session close + nightly."""
```

---

## 5. How it changes the session loop

Today `POST /api/session/start` picks "the user's next incomplete lesson at their level."
With Harada it picks from the **weakest focus cell**:

```
1. Load the user's focus actions (is_focus = true, 3-5 of them).
2. Rank by (1 - progress), tie-break by days since last touched.
3. Take the weakest. Map it to work:
     lesson_score  -> open that lesson
     vocab_*       -> SRS-heavy drill session on the relevant tag
     error_absent  -> targeted remediation on that error pattern
     routine_days  -> nudge, not a session
4. If every focus cell is done, close the cycle (see §6) before starting.
```

`app/tutor.py` gains one block in the context it sends to Claude:

```
CURRENT FOCUS
  Theme: Grammar & Morphology
  Action: Predict gender from the ending (-ος -α -η -ι -ο -μα)
  Progress: 0.6 — "gender agreement" appeared in 2 of the last 5 sessions
  Drill this specifically. Do not move on until it is clean.
```

That single block is the highest-leverage change here: it turns a general-purpose tutor
into one with a stated objective for the turn, and it costs ~60 tokens of the cached prompt.

---

## 6. Cycle close (the Harada review)

At `cycle_start + cycle_days`:

1. Recompute all 64.
2. Generate a review from `tutor_sessions.summary_text` + `error_patterns` over the cycle
   (one Sonnet call, same shape as the existing session-close call).
3. Mark newly-`done` cells; carry incomplete focus cells forward.
4. Ask the user to pick the next 3–5 focus cells — pre-ranked by weakest theme.
5. Write a new `cycle_text` and reset `cycle_start`.

This is also the natural place for the level-change job the README already flags as missing:
`profiles.level_estimate` bumps when a theme's cells for that level are all `done`.

---

## 7. UI

`templates/dashboard.html` is the board. Two views off the same data:

- **Grid** — the 9×9 mandala, cells coloured by `state`, focus cells ringed. Same markup
  as the HTML board; the hard-coded `THEMES` array is replaced by `GET /api/harada`.
- **Today** — the routine check sheet plus one button: *Start session on <focus action>*.

> **Decided 2026-09-13.** Vanilla JS `fetch` + JSON endpoints, not HTMX: the board is one
> payload with theme rollups, which is easier to render from JSON than from out-of-band
> swaps. And the **routine check sheet is not built here**: it lives in the tracker
> (`tracker/docs/plan.md`, habits with `board_action_id`), which is the phone-first daily
> page. The dashboard keeps a *Start today's session* button; the session itself picks
> the weakest focus cell. The board is also exported as a file for the tracker to mirror —
> see `docs/HARADA_BOARD_CONTRACT.md`.

## 8. Suggested build order

| Step | Work | Payoff |
|---|---|---|
| 1 | `003_harada.sql` + seed the 8 themes and 64 actions | the model exists |
| 2 | `app/harada.py` recompute, called at session close | cells move on their own |
| 3 | Focus-cell block in the tutor prompt | sessions get an objective |
| 4 | Grid view on the dashboard | you can see the shape of your Greek |
| 5 | ~~Routine check sheet~~ — deferred to the tracker (2026-09-13); `routine_log` and the scorer stay | `routine_days` cells move once the tracker feeds them |
| 6 | Cycle close + review | the loop closes |

Steps 1–3 are the whole idea and are worth doing before any UI. Step 4 is what makes it
motivating; steps 5–6 are what make it Harada rather than just a skill tree. Steps 1–4
are done; step 5 moved to the tracker; step 6 is next.

---

## 9. Honest caveats

- **64 cells is a lot of surface for one learner.** Harada assumes a coach enforcing the
  3–5 focus rule. Without it the grid becomes a guilt board. Enforce `is_focus` limits in
  the API, not just the UI.
- **Some cells can't be measured honestly** (`manual` ones: recordings, sticky notes,
  "read every sign you meet"). Keep them — Harada's point is partly that you commit to
  unmeasurable environment changes — but don't let them count toward the completion
  percentage without a flag.
- **The 64 actions are A1→B1 shaped.** At B2+ the decomposition changes (register,
  idiom, formal/καθαρεύουσα residue). Expect to re-cut the grid once, around B1.
- **The metric layer can drift from reality.** A cell reading `done` while you still can't
  say the thing is the failure mode. The monthly self-assessment recording (cell 8.8) is
  the ground-truth check against it — keep it.
