-- 002: per-turn transcript storage.
-- Needed so the session loop works across multiple app workers (no in-memory
-- state) and so close_session can hand the full transcript to the eval model.

BEGIN;

CREATE TABLE tutor_turns (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id  BIGINT NOT NULL REFERENCES tutor_sessions(id) ON DELETE CASCADE,
    role        TEXT   NOT NULL CHECK (role IN ('user','assistant')),
    content     TEXT   NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tutor_turns_session ON tutor_turns(session_id, id);

-- Optional retention: transcripts are only needed until the session is
-- summarized. A nightly job may delete turns for sessions ended > 7 days ago.

COMMIT;
