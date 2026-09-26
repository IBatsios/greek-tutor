# Stage 11 — Speaking (speech-to-text)

**Status:** not started · **Branch:** `feature/11-stt` · **Size:** two sessions
**Depends on:** 10 · **Ends at:** Milestone M2 — speaks and reads
**Closes:** cells 0.4, 0.7, 4.1 (voice), 4.4, 7.8

## Goal

The central goal is a spoken conversation. Until now the app could only practise it in writing.
Add voice sessions: you speak, it transcribes, the tutor answers aloud.

## Primer — what STT can and cannot tell you

A speech-to-text model (e.g. Whisper, run locally with faster-whisper) turns your audio into the
text it thinks you said. That gives two honest signals:
1. **Intelligibility** — if the transcript matches what you meant to say, a machine understood you.
2. **Fluency** — pause lengths and words per minute from timestamps.
It does **not** give phoneme-level pronunciation scoring. A bad accent that is still
intelligible scores well. Say so in the UI; the monthly self-recording (7.8) stays the ground truth.

## Tasks

### A. Plumbing
- [ ] Compose service `stt` (faster-whisper; `small` or `medium` model, int8 on CPU, or on the AI server's GPU). `app/stt.py: transcribe(audio) -> {text, words:[{w,start,end}]}`.
- [ ] Browser: push-to-talk with `MediaRecorder` → `POST /api/session/{id}/voice` (size/length capped) → STT → existing `turn()` path with the transcript → reply text + TTS URL.
- [ ] `tutor_sessions.mode = 'voice'` (the enum already exists); `usage_ledger.stt_seconds`.
- [ ] Voice sessions tell the tutor (context block) that input is a transcript: don't correct punctuation, do correct words.

### B. Speaking drills
- [ ] **Clusters check** (0.4): read 10 target words aloud; pass if the transcript matches ≥10/10 (intelligibility proxy).
- [ ] **Photo description** (4.4): an image, 90 s recording, pass if no inter-word gap > 4 s (from word timestamps) and ≥ N words.
- [ ] **Speaking minutes** (4.1): voice-session `study_minutes`; metric filtered by `mode='voice'` as the board says.

### C. Recordings
- [ ] `recordings (id, user_id, kind, path, created_at, self_score, note)`; files on a volume, not in Postgres. Retention: keep monthly self-assessments forever, drill audio 30 days.
- [ ] **Monthly self-assessment** (7.8): the same prompt every month; play this month next to last month; self-score. 12 a year.
- [ ] **Read a paragraph vs native** (0.7): record, then play your version next to the TTS/native one.

## Definition of done

- [ ] A 15-minute voice session works on your phone.
- [ ] Trace: 0.4, 0.7, 4.1, 4.4, 7.8 ✅ (4.1 now in speaking mode).
- [ ] **M2:** every theme has at least 6 of 8 cells movable from evidence in the app.

## Session notes

_(fill in at the end of the session)_
