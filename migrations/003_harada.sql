-- 003: Harada Method progress engine (docs/HARADA_INTEGRATION.md §3).
-- One long-horizon goal → 8 themes → 64 measurable actions per user, plus the
-- daily routine check sheet. This layer sits ABOVE lessons; nothing is removed.
-- Definitions of the 64 actions are seeded from seed/harada.sql.

BEGIN;

-- The learner's central goal and current 90-day cycle.
CREATE TABLE harada_goals (
    user_id       BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    goal_text     TEXT NOT NULL,
    cycle_text    TEXT NOT NULL DEFAULT '',
    cycle_start   DATE NOT NULL DEFAULT CURRENT_DATE,
    cycle_days    INT  NOT NULL DEFAULT 90 CHECK (cycle_days > 0)
);

-- Eight themes at fixed positions (0..7) on the 9×9 grid.
CREATE TABLE harada_themes (
    id        SMALLINT PRIMARY KEY CHECK (id BETWEEN 0 AND 7),
    slug      TEXT NOT NULL UNIQUE,
    name_en   TEXT NOT NULL,
    name_el   TEXT NOT NULL
);

-- Sixty-four actions: 8 per theme. metric_kind + metric_args say how a cell
-- is scored from data the app already produces (see app/harada_metrics.py).
CREATE TABLE harada_actions (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    theme_id     SMALLINT NOT NULL REFERENCES harada_themes(id),
    slot         SMALLINT NOT NULL CHECK (slot BETWEEN 0 AND 7),
    label        TEXT NOT NULL,
    measure      TEXT NOT NULL DEFAULT '',        -- human-readable "measured by"
    metric_kind  TEXT NOT NULL CHECK (metric_kind IN
                   ('lesson_score','vocab_count','vocab_recall','error_absent',
                    'routine_days','session_metric','manual')),
    metric_args  JSONB NOT NULL DEFAULT '{}',
    UNIQUE (theme_id, slot)
);

-- Per-user cell state. Rows are created lazily by recompute / focus toggles.
CREATE TABLE user_harada_actions (
    user_id      BIGINT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_id    BIGINT  NOT NULL REFERENCES harada_actions(id) ON DELETE CASCADE,
    state        TEXT    NOT NULL DEFAULT 'not_started'
                 CHECK (state IN ('not_started','in_progress','done')),
    progress     REAL    NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 1),
    is_focus     BOOLEAN NOT NULL DEFAULT false,  -- one of the 3–5 active this cycle
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(), -- last time progress moved
    PRIMARY KEY (user_id, action_id)
);
CREATE INDEX idx_uha_focus ON user_harada_actions(user_id) WHERE is_focus;

-- Daily routine check sheet: one row per user per day.
-- checks keys are the routine_days metric keys, e.g. {"listening_10": true}.
CREATE TABLE routine_log (
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date   DATE   NOT NULL DEFAULT CURRENT_DATE,
    checks     JSONB  NOT NULL DEFAULT '{}',
    note       TEXT   NOT NULL DEFAULT '',          -- the Harada diary line
    PRIMARY KEY (user_id, log_date)
);

-- Which theme(s) a lesson serves, for theme-level rollups on the board.
ALTER TABLE lessons ADD COLUMN theme_ids SMALLINT[] NOT NULL DEFAULT '{}';

-- The focus cell a session was opened on. NULL = plain next-lesson session.
ALTER TABLE tutor_sessions ADD COLUMN focus_action_id BIGINT REFERENCES harada_actions(id);

COMMIT;
