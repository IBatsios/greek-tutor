# Stage 06 — Deploy & accountability

**Status:** not started · **Branch:** `feature/06-deploy` · **Size:** one session
**Depends on:** 05 · **Ends at:** Milestone M1 — daily-usable (text)

## Goal

The app runs on your homelab, reachable from your phone over HTTPS, backs itself up every
night, and nudges you when you haven't practised. "Available and remembered" is what turns a
project into a habit.

## Primer — the three pieces

| Piece | What it does | Failure it prevents |
|---|---|---|
| Reverse proxy / tunnel | Terminates HTTPS, forwards to `127.0.0.1:8080` | Secure cookies need HTTPS; the phone needs a URL |
| Nightly `pg_dump` | A restorable file of the whole DB, rotated | One bad migration erasing months of SRS history |
| Nudge | A message at your practice time if you haven't started | The streak dying because you forgot, not because you chose |

## Tasks

### A. Host it
- [ ] Target host per roadmap decision (default: homelab dev VM). `git clone`, `.env`, `docker compose up -d --build`.
- [ ] Route a hostname through the existing Cloudflare Tunnel or Caddy to `127.0.0.1:${APP_PORT}`. `COOKIE_SECURE=true`.
- [ ] `SIGNUP_ENABLED=false` env flag after your account exists (single-learner; signup is public otherwise).
- [ ] Rate-limit `POST /login`: 5 failures per email per 15 minutes, stored in Postgres (no Redis for one user).

### B. Backups
- [ ] Compose service `backup` (postgres:16 image, loop: `pg_dump -Fc` nightly to `/backups`, keep 14 daily + 8 weekly). Bind-mount `/backups` to a host path that your existing NAS/PBS backup already covers.
- [ ] `docs/RUNBOOK.md`: restore into a scratch container and run `GET /api/harada` against it. Do the restore drill once, for real.

### C. Nudges
- [ ] `scripts/nudge.py` run by a compose service every 15 min: for each user with `practice_time` passed today and no activity today, send one nudge (record in a `nudges` table so it sends once a day).
- [ ] Channel per roadmap decision. ntfy: one HTTP POST, no account. Message names today's focus action and streak: "Day 12 🔥 — 10 minutes on final sigma keeps it alive."
- [ ] Second nudge only when the streak is about to break (inactive yesterday and today).

### D. Phone
- [ ] `static/manifest.webmanifest` + icons → installable to the home screen.
- [ ] Check Today, Review and Practice at 390 px width; the Greek input helper must not cover the send button.

## Definition of done

- [ ] You used it from your phone on three consecutive days.
- [ ] A backup exists and a restore drill passed.
- [ ] A missed day produced exactly one nudge.

## Milestone M1 check

Can you open it every morning and, without thinking, know what to do and do it? If not, write
down what stopped you — that list is the next stage, ahead of 07.

## Session notes

_(fill in at the end of the session)_
