"""Daily AI-minute quotas. Checked BEFORE every Claude call, recorded after."""
from fastapi import HTTPException

from . import config
from .db import pool


async def minutes_used_today(user_id: int) -> float:
    v = await pool().fetchval(
        "SELECT ai_minutes FROM usage_ledger WHERE user_id=$1 AND usage_date=CURRENT_DATE",
        user_id,
    )
    return float(v or 0)


async def check_quota(user_id: int) -> None:
    if await minutes_used_today(user_id) >= config.DAILY_AI_MINUTES:
        raise HTTPException(429, "Daily practice limit reached — see you tomorrow! Αύριο!")


async def record_usage(user_id: int, tokens_in: int, tokens_out: int,
                       minutes: float) -> None:
    await pool().execute(
        """INSERT INTO usage_ledger (user_id, llm_tokens_in, llm_tokens_out, ai_minutes)
           VALUES ($1,$2,$3,$4)
           ON CONFLICT (user_id, usage_date) DO UPDATE SET
             llm_tokens_in  = usage_ledger.llm_tokens_in  + EXCLUDED.llm_tokens_in,
             llm_tokens_out = usage_ledger.llm_tokens_out + EXCLUDED.llm_tokens_out,
             ai_minutes     = usage_ledger.ai_minutes     + EXCLUDED.ai_minutes""",
        user_id, tokens_in, tokens_out, minutes,
    )
