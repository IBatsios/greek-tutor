-- 004: freeze the tutor's student-context block for the length of a session.
-- The block sits in the system prompt, ahead of the conversation. Rebuilt every turn
-- it changed whenever a due word was answered (its SRS line moved), and any change
-- ahead of the conversation makes the prompt cache for the whole transcript unreadable.
-- Written once at session start; NULL for sessions started before this migration.

BEGIN;

ALTER TABLE tutor_sessions ADD COLUMN context_block TEXT;

COMMIT;
