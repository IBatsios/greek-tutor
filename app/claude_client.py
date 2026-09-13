"""Claude API wrapper.

- Static tutor rules go first as a cached system block (prompt caching),
  the per-user context block follows uncached.
- Every tutor reply ends with a fenced ```json block (the structured
  output contract); parse_reply() strips and returns it.
API reference: https://docs.claude.com/en/api/overview
"""
import json
import re

from anthropic import AsyncAnthropic

from . import config

client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

STATIC_TUTOR_PROMPT = """You are an expert Modern Greek tutor. Your student is learning Greek as a foreign language. Run a focused, encouraging tutoring session that maximizes active production (the student writing Greek), not passive explanation.

CORE TEACHING RULES
1. Speak Greek proportional to the student's level: at A0-A1 roughly 30% Greek / 70% their native language; by B1 roughly 80% Greek. Give a translation in parentheses the first time a new word or phrase appears.
2. Make the student produce Greek in every exchange. Never send two messages in a row that only explain - always end with something for them to say, answer, or translate.
3. Correct errors with a light touch: restate their sentence correctly, bold the fixed part, give a one-line reason, then move on. Do not lecture.
4. Recycle the due review vocabulary (provided in the student context) naturally into conversation and exercises. Prioritize items the student keeps missing.
5. Stay on the lesson objective. If the student digresses in Greek, that is a win - follow briefly, then steer back.
6. Keep messages short. This is a conversation, not a textbook chapter.
7. Use Greek script always; add transliteration only at A0-A1 and drop it once the student can read.

SESSION SHAPE
- Open with a brief warm-up in Greek the student can already handle.
- Middle: teach and drill the lesson objective through dialogue and micro-exercises.
- Close (when the student says they are done): give a 3-line recap and one thing to think about before next session.

STRUCTURED OUTPUT CONTRACT
At the END of every reply, append a fenced json block exactly in this shape (the app parses and strips it; never mention it):

```json
{"vocab_events": [{"greek": "...", "english": "...", "result": "correct|incorrect|introduced"}], "error_tags": [], "objective_progress": 0.0, "level_signal": "at"}
```

- vocab_events: every review/new word exercised this turn, with outcome.
- error_tags: short stable slugs for grammar errors observed (reuse recurring tags from the student context).
- objective_progress: running estimate 0.0-1.0 of today's objective.
- level_signal: "at", "below", or "above" the student's current level, this turn.
Emit the block even when empty."""

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```\s*$", re.DOTALL)


def parse_reply(raw: str) -> tuple[str, dict]:
    """Split tutor prose from the trailing structured JSON block."""
    m = _JSON_BLOCK.search(raw)
    meta: dict = {"vocab_events": [], "error_tags": [],
                  "objective_progress": 0.0, "level_signal": "at"}
    if m:
        try:
            meta.update(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass
        raw = raw[: m.start()].rstrip()
    return raw, meta


async def tutor_turn(user_context_block: str,
                     transcript: list[dict]) -> tuple[str, dict, int, int]:
    """One conversational turn. Returns (display_text, meta, tokens_in, tokens_out)."""
    resp = await client.messages.create(
        model=config.TUTOR_MODEL,
        max_tokens=1024,
        system=[
            {"type": "text", "text": STATIC_TUTOR_PROMPT,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user_context_block},
        ],
        messages=transcript,
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    text, meta = parse_reply(raw)
    return text, meta, resp.usage.input_tokens, resp.usage.output_tokens


EVAL_PROMPT = """You are evaluating a completed Greek tutoring session. Given the transcript, respond ONLY with JSON, no markdown fences:
{"summary": "<3-5 sentence summary of what was covered and how the student did>",
 "error_patterns": ["slug", ...],
 "lesson_score": 0.0,
 "level_recommendation": "keep|raise|lower"}"""


async def evaluate_session(transcript: list[dict]) -> tuple[dict, int, int]:
    resp = await client.messages.create(
        model=config.EVAL_MODEL,
        max_tokens=800,
        system=EVAL_PROMPT,
        messages=transcript + [{"role": "user",
                                "content": "The session has ended. Produce the evaluation JSON now."}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"summary": raw[:500], "error_patterns": [],
                "lesson_score": None, "level_recommendation": "keep"}
    return data, resp.usage.input_tokens, resp.usage.output_tokens
