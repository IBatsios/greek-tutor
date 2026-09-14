"""SM-2 style SRS updates driven by the tutor's per-turn vocab_events."""
import re
from datetime import timedelta

from . import clock
from .db import pool

_TAG = re.compile(r"^[a-z][a-z0-9_-]{1,29}\Z")

_UPSERT_ITEM = """
INSERT INTO vocab_items (greek, english, tags)
VALUES ($1, $2, CASE WHEN $3::text IS NULL THEN '{}'::text[] ELSE ARRAY[$3::text] END)
ON CONFLICT (greek, english) DO UPDATE SET
  tags = CASE WHEN $3::text IS NULL OR $3::text = ANY(vocab_items.tags)
              THEN vocab_items.tags ELSE vocab_items.tags || $3::text END
RETURNING id
"""


def clean_tag(tag: object) -> str | None:
    """Normalise a topic tag from the tutor's JSON; None when it is not a usable slug."""
    if not isinstance(tag, str):
        return None
    slug = tag.strip().lower()
    return slug if _TAG.match(slug) else None


async def apply_vocab_event(user_id: int, greek: str, english: str, result: str,
                            tag: object = None) -> None:
    """result: 'correct' | 'incorrect' | 'introduced'. tag: optional topic cluster slug."""
    async with pool().acquire() as conn:
        vocab_id = await conn.fetchval(
            _UPSERT_ITEM, greek.strip(), english.strip(), clean_tag(tag),
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
                clock.today() + timedelta(days=1),
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
            clock.today() + timedelta(days=interval),
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
