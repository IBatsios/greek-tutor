# Stage 10 — Listening (text-to-speech)

**Status:** not started · **Branch:** `feature/10-tts` · **Size:** one to two sessions
**Depends on:** 02 · **Closes:** cells 0.8, 3.5, 3.6, audio half of 3.4; strengthens 3.8

## Goal

Give the app a voice so listening can be practised and measured inside it: hear tutor replies,
take dictation, tell δ from θ, get the gist of a short bulletin.

## Primer — TTS options

| Option | Greek quality | Cost | Ops |
|---|---|---|---|
| Piper (self-hosted, CPU) | Usable; one or two Greek voices, flat prosody | Free | One container, fast on CPU |
| Coqui XTTS / other neural (self-hosted, GPU) | Better prosody | Free | Needs the GPU box |
| Cloud TTS (Azure, Google, ElevenLabs) | Best, several native voices | Per character | API key, network dependency |

Verify the current Greek voice list before choosing; model availability changes. Whatever you
pick, put it behind `app/tts.py` with one function `synthesize(text, voice) -> bytes` so the
choice can change without touching features. Cache audio by `sha256(text+voice)` on disk —
most drill audio is reused.

## Tasks

- [ ] Compose service `tts` (per roadmap decision); `app/tts.py` client; `GET /api/tts?text=…` returns cached `audio/ogg`, auth-required, text length capped.
- [ ] Log characters to `usage_ledger.tts_chars` (column already exists).
- [ ] Session page: ▶ on every tutor message; "auto-play replies" toggle.
- [ ] **Dictation** (3.5): numbers/prices played, you type, exact-match graded. `listening_results` table.
- [ ] **Minimal pairs** (0.8): δ/θ, γ before ε/ι vs α/ο/ου — word pairs played, you choose. 20 items, target 18/20. Honest caveat: synthetic voices can blur the very contrasts you're drilling; record a native speaker for these 40 words if you can.
- [ ] **News gist** (3.6): generated 2-minute bulletin text (reuse stage 08's generator) → TTS → 5 questions, target 4/5. Transcript hidden until answered.
- [ ] Seed changes: 0.8, 3.5, 3.6 get `listening_score` metrics; 3.4 gets its audio.

## Definition of done

- [ ] Three listening drills usable daily; audio cached; TTS cost/latency acceptable on your host.
- [ ] Trace: 0.8, 3.4, 3.5, 3.6 ✅.

## Session notes

_(fill in at the end of the session)_
