# core/intelligence/agents.py

import os
import time
import logging

from groq import Groq
from dotenv import load_dotenv
from langfuse import Langfuse
import instructor

from server.core.intelligence.schemas import (
    ActionItem, Decision, Topic,
    ActionItemList, DecisionList, TopicList,
)

load_dotenv()

# FIX: use proper logger instead of print()
logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

# FIX: Transcript length cap.
#
# Groq's llama-3.3-70b supports 128k tokens but very long transcripts
# make responses slow, expensive, and sometimes fail entirely.
# 48,000 characters ≈ 12,000 words ≈ 60 minutes of speech — enough for
# any normal meeting. Longer meetings get the first 60 minutes analysed.
MAX_TRANSCRIPT_CHARS = 48_000


def _cap_transcript(transcript: str) -> str:
    """
    Trim transcript to MAX_TRANSCRIPT_CHARS if needed.
    Adds a note so the AI knows the text was trimmed.
    """
    if len(transcript) <= MAX_TRANSCRIPT_CHARS:
        return transcript
    trimmed = transcript[:MAX_TRANSCRIPT_CHARS]
    logger.warning(
        "Transcript trimmed from %d to %d chars for LLM analysis",
        len(transcript), MAX_TRANSCRIPT_CHARS,
    )
    return (
        trimmed
        + "\n\n[NOTE: Transcript was trimmed to the first ~60 minutes for analysis.]"
    )


# ── Groq clients ──────────────────────────────────────────────────────────────
#
# We create two clients:
#   _groq_client       — plain text responses (summary agent)
#   _instructor_client — structured Pydantic responses (all other agents)
#
# Both are created once at module load and reused for every call.
# Creating a new client per call would add overhead and waste connections.

_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_instructor_client = instructor.from_groq(
    Groq(api_key=os.getenv("GROQ_API_KEY")),
    mode=instructor.Mode.JSON,
)

_langfuse = Langfuse()

# FIX: Timeout constant — applied to every single Groq API call.
#
# Without a timeout, a slow Groq response hangs the worker thread forever.
# 4 concurrent uploads = 4 frozen threads = server appears completely down.
#
# 60 seconds is generous — normal Groq responses take 3–15 seconds.
# If it takes longer than 60s something is wrong and we should give up,
# log the error, and return a graceful fallback to the user.
LLM_TIMEOUT_SECONDS = 60.0


# ── Shared plain-text caller ──────────────────────────────────────────────────

def _call_groq(system_prompt: str, user_content: str, span_name: str = "groq-call") -> str:
    """
    Plain text Groq caller — used by the summary agent.
    Returns raw string. Traced with Langfuse.
    """
    generation = _langfuse.generation(
        name=span_name,
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
    )

    start_time = time.time()

    try:
        # FIX: timeout=LLM_TIMEOUT_SECONDS added.
        # Old code had no timeout — could hang the worker thread forever.
        # Now if Groq takes longer than 60s, httpx raises a Timeout exception.
        # The worker thread is freed, other users are unaffected.
        response = _groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.1,
            max_tokens=2048,
            timeout=LLM_TIMEOUT_SECONDS,   # FIX: added
        )

        result  = response.choices[0].message.content.strip()
        elapsed = time.time() - start_time

        generation.end(
            output=result,
            usage={
                "input":  response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total":  response.usage.total_tokens,
            },
            metadata={"latency_seconds": round(elapsed, 3)},
        )

        return result

    except Exception as e:
        generation.end(output=f"ERROR: {str(e)}", metadata={"error": True})
        raise


# ── Shared Instructor caller ──────────────────────────────────────────────────

def _extract_structured(
    system_prompt: str,
    user_content: str,
    response_model,
    span_name: str,
):
    """
    Instructor-based structured extractor.
    Returns a validated Pydantic object — always matches the schema.
    """
    generation = _langfuse.generation(
        name=span_name,
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        metadata={"mode": "instructor_structured"},
    )

    start_time = time.time()

    try:
        # FIX: timeout=LLM_TIMEOUT_SECONDS added to instructor call too.
        result = _instructor_client.chat.completions.create(
            model=MODEL,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.1,
            max_tokens=2048,
            max_retries=3,
            timeout=LLM_TIMEOUT_SECONDS,   # FIX: added
        )

        elapsed = time.time() - start_time

        generation.end(
            output=str(result.model_dump()),
            metadata={"latency_seconds": round(elapsed, 3)},
        )

        return result

    except Exception as e:
        generation.end(output=f"ERROR: {str(e)}", metadata={"error": True})
        raise


# ── Agent 1: Summary ──────────────────────────────────────────────────────────

def run_summary_agent(transcript: str) -> str:
    system = """You are an expert meeting analyst.
Your ONLY job: write a concise executive summary of this meeting transcript.

Rules:
- 3 to 5 sentences maximum
- Focus on what was accomplished and what was decided
- Use plain business language
- Do NOT list action items or decisions here
- Return ONLY the summary text, no labels, no headings"""

    # FIX: cap transcript before sending
    return _call_groq(system, f"TRANSCRIPT:\n{_cap_transcript(transcript)}", span_name="summary_agent")


# ── Agent 2: Action Items ─────────────────────────────────────────────────────

def run_action_item_agent(transcript: str) -> list[ActionItem]:
    system = """You are an expert meeting analyst.
Your ONLY job: extract ALL action items from this meeting transcript.

For each action item identify:
- task: what exactly needs to be done (required)
- owner: who is responsible (null if not mentioned)
- deadline: when it's due (null if not mentioned)
- priority: high / medium / low based on urgency language used

Extract every action item mentioned, even implicit ones."""

    result = _extract_structured(
        system_prompt=system,
        user_content=f"TRANSCRIPT:\n{_cap_transcript(transcript)}",
        response_model=ActionItemList,
        span_name="action_item_agent",
    )
    return result.items


# ── Agent 3: Decisions ────────────────────────────────────────────────────────

def run_decision_agent(transcript: str) -> list[Decision]:
    system = """You are an expert meeting analyst.
Your ONLY job: extract all DECISIONS made in this meeting transcript.

A decision is something the team AGREED upon or CONFIRMED — not just discussed.
Examples: "we decided to", "the team agreed", "it was confirmed that"

For each decision identify:
- decision: the actual decision made (required)
- rationale: the reason given, if mentioned (null if not mentioned)

Only include real decisions, not options being considered."""

    result = _extract_structured(
        system_prompt=system,
        user_content=f"TRANSCRIPT:\n{_cap_transcript(transcript)}",
        response_model=DecisionList,
        span_name="decision_agent",
    )
    return result.items


# ── Agent 4: Topics ───────────────────────────────────────────────────────────

def run_topic_agent(transcript: str) -> list[Topic]:
    system = """You are an expert meeting analyst.
Your ONLY job: identify the 3 to 6 main topics discussed in this meeting transcript.

For each topic:
- title: a short noun phrase, 3-5 words (required)
- description: one sentence explaining what was discussed (null if obvious)

Cover the main themes only — do not list every sub-point."""

    result = _extract_structured(
        system_prompt=system,
        user_content=f"TRANSCRIPT:\n{_cap_transcript(transcript)}",
        response_model=TopicList,
        span_name="topic_agent",
    )
    return result.items