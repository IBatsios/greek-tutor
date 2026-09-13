-- Greek Tutor Platform — Phase 1 Schema (PostgreSQL 15+)
-- Text-only tutor: auth, profiles, SRS vocab, lessons, sessions, usage quotas.
-- Voice columns are included where cheap (mode enum) so Phase 2 needs no migration.

BEGIN;

-- ---------------------------------------------------------------
-- Auth
-- ---------------------------------------------------------------
CREATE TABLE users (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           CITEXT NOT NULL UNIQUE,          -- CREATE EXTENSION citext;
    password_hash   TEXT   NOT NULL,                 -- argon2id
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at     TIMESTAMPTZ,                     -- NULL until email verified
    disabled_at     TIMESTAMPTZ                      -- soft-disable for abuse
);

CREATE TABLE auth_sessions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT   NOT NULL UNIQUE,          -- store hash, never raw token
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_auth_sessions_user    ON auth_sessions(user_id);
CREATE INDEX idx_auth_sessions_expires ON auth_sessions(expires_at);

CREATE TABLE email_tokens (                          -- verification + password reset
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose         TEXT   NOT NULL CHECK (purpose IN ('verify','reset')),
    token_hash      TEXT   NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ
);

-- ---------------------------------------------------------------
-- Learner profile
-- ---------------------------------------------------------------
CREATE TABLE profiles (
    user_id             BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name        TEXT NOT NULL DEFAULT '',
    native_lang         TEXT NOT NULL DEFAULT 'en',
    level_estimate      TEXT NOT NULL DEFAULT 'A0'
                        CHECK (level_estimate IN ('A0','A1','A2','B1','B2','C1')),
    daily_goal_minutes  INT  NOT NULL DEFAULT 60,
    streak_count        INT  NOT NULL DEFAULT 0,
    last_active_date    DATE
);

-- ---------------------------------------------------------------
-- Vocabulary + SRS
-- ---------------------------------------------------------------
CREATE TABLE vocab_items (                           -- shared corpus, seeded + grown by tutor
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    greek           TEXT NOT NULL,
    translit        TEXT NOT NULL DEFAULT '',
    english         TEXT NOT NULL,
    pos             TEXT NOT NULL DEFAULT '',        -- noun/verb/adj/phrase/...
    level           TEXT NOT NULL DEFAULT 'A1',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    UNIQUE (greek, english)
);
CREATE INDEX idx_vocab_level ON vocab_items(level);
CREATE INDEX idx_vocab_tags  ON vocab_items USING GIN (tags);

CREATE TABLE user_vocab (                            -- per-user SRS state (SM-2 style)
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocab_id        BIGINT NOT NULL REFERENCES vocab_items(id) ON DELETE CASCADE,
    srs_ease        REAL   NOT NULL DEFAULT 2.5,
    srs_interval_d  INT    NOT NULL DEFAULT 0,       -- days
    srs_due_date    DATE   NOT NULL DEFAULT CURRENT_DATE,
    times_seen      INT    NOT NULL DEFAULT 0,
    times_correct   INT    NOT NULL DEFAULT 0,
    introduced_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, vocab_id)
);
CREATE INDEX idx_user_vocab_due ON user_vocab(user_id, srs_due_date);

-- ---------------------------------------------------------------
-- Curriculum
-- ---------------------------------------------------------------
CREATE TABLE lessons (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    level           TEXT NOT NULL,
    seq             INT  NOT NULL,                   -- ordering within level
    topic           TEXT NOT NULL,                   -- e.g. 'Greetings & introductions'
    objectives      JSONB NOT NULL DEFAULT '[]',     -- ["use είμαι", "numbers 1-10"]
    UNIQUE (level, seq)
);

CREATE TABLE user_lessons (
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id       BIGINT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'not_started'
                    CHECK (status IN ('not_started','in_progress','completed')),
    score           REAL,                            -- 0.0–1.0 tutor-assessed
    completed_at    TIMESTAMPTZ,
    PRIMARY KEY (user_id, lesson_id)
);

-- ---------------------------------------------------------------
-- Tutor sessions (the memory of the tutor)
-- ---------------------------------------------------------------
CREATE TABLE tutor_sessions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id       BIGINT REFERENCES lessons(id),
    mode            TEXT NOT NULL DEFAULT 'text' CHECK (mode IN ('text','voice')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    minutes_used    REAL NOT NULL DEFAULT 0,
    summary_text    TEXT,                            -- written at session close
    error_patterns  JSONB NOT NULL DEFAULT '[]'      -- ["gender agreement", "σ/ς final sigma"]
);
CREATE INDEX idx_tutor_sessions_user ON tutor_sessions(user_id, started_at DESC);

-- ---------------------------------------------------------------
-- Usage ledger — quotas + cost visibility. One row per user per day.
-- ---------------------------------------------------------------
CREATE TABLE usage_ledger (
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_date      DATE   NOT NULL DEFAULT CURRENT_DATE,
    llm_tokens_in   BIGINT NOT NULL DEFAULT 0,
    llm_tokens_out  BIGINT NOT NULL DEFAULT 0,
    stt_seconds     REAL   NOT NULL DEFAULT 0,       -- Phase 2
    tts_chars       BIGINT NOT NULL DEFAULT 0,       -- Phase 2
    ai_minutes      REAL   NOT NULL DEFAULT 0,       -- the quota you enforce
    PRIMARY KEY (user_id, usage_date)
);

-- Atomic upsert used after every tutor turn:
--   INSERT INTO usage_ledger (user_id, llm_tokens_in, llm_tokens_out, ai_minutes)
--   VALUES ($1,$2,$3,$4)
--   ON CONFLICT (user_id, usage_date) DO UPDATE SET
--     llm_tokens_in  = usage_ledger.llm_tokens_in  + EXCLUDED.llm_tokens_in,
--     llm_tokens_out = usage_ledger.llm_tokens_out + EXCLUDED.llm_tokens_out,
--     ai_minutes     = usage_ledger.ai_minutes     + EXCLUDED.ai_minutes;

COMMIT;
