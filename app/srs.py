"""SM-2 style SRS updates driven by the tutor's per-turn vocab_events."""
from datetime import date, timedelta

from .db import pool


async def apply_vocab_event(user_id: int, greek: str, english: str, result: str) -> None:
    """result: 'correct' | 'incorrect' | 'introduced'"""
    async with pool().acquire() as conn:
        vocab_id = await conn.fetchval(
            """INSERT INTO vocab_items (greek, english)
               VALUES ($1,$2)
               ON CONFLICT (greek, english) DO UPDATE SET greek = EXCLUDED.greek
               RETURNING id""",
            greek.strip(), english.strip(),
        )
        row = await conn.fetchrow(
            "SELECT srs_ease, srs_interval_d FROM user_vocab WHERE user_id=$1 AND vocab_id=$2",
            user_id, vocab_id,
        )
        if row is None:
            await conn.execute(
                """INSERT INTO user_vocab (user_id, vocab_id, times_seen, times_correct,
                                           srs_due_date)
                   VALUES ($1,$2,1,$3,$4)""",
                user_id, vocab_id, 1 if result == "correct" else 0,
                date.today() + timedelta(days=1),
            )
            return

        ease, interval = row["srs_ease"], row["srs_interval_d"]
        if result == "correct":
            interval = 1 if interval == 0 else max(1, round(interval * ease))
            ease = min(3.0, ease + 0.05)
        elif result == "incorrect":
            interval = 1
            ease = max(1.3, ease - 0.2)
        else:  # re-introduced
            interval = max(1, interval)

        await conn.execute(
            """UPDATE user_vocab SET
                 srs_ease=$3, srs_interval_d=$4, srs_due_date=$5,
                 times_seen = times_seen + 1,
                 times_correct = times_correct + $6
               WHERE user_id=$1 AND vocab_id=$2""",
            user_id, vocab_id, ease, interval,
            date.today() + timedelta(days=interval),
            1 if result == "correct" else 0,
        )


async def due_vocab(user_id: int, limit: int = 15) -> list[dict]:
    rows = await pool().fetch(
        """SELECT v.greek, v.english, uv.times_seen, uv.times_correct
           FROM user_vocab uv JOIN vocab_items v ON v.id = uv.vocab_id
           WHERE uv.user_id=$1 AND uv.srs_due_date <= CURRENT_DATE
           ORDER BY uv.srs_due_date, uv.srs_ease
           LIMIT $2""",
        user_id, limit,
    )
    return [dict(r) for r in rows]
