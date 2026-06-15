# core/intelligence/agents.py
import os
import time

from groq import Groq
from dotenv import load_dotenv
from langfuse import Langfuse
import instructor

from server.core.intelligence.schemas import (
    ActionItem, Decision, Topic,
    ActionItemList, DecisionList, TopicList,
)

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

# ── Groq client (plain, for summary agent) ───────────────────────────────────
_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Instructor-patched Groq client (for structured extraction agents) ─────────
# instructor.from_groq() wraps the Groq client with structured output support.
# Use _instructor_client when you want a Pydantic model back.
# Use _groq_client when you want plain text back (summary agent).
_instructor_client = instructor.from_groq(
    Groq(api_key=os.getenv("GROQ_API_KEY")),
    mode=instructor.Mode.JSON,   # Groq works best in JSON mode
)

# ── Langfuse client ───────────────────────────────────────────────────────────
_langfuse = Langfuse()


# ─── Shared plain-text Groq caller (summary only) ────────────────────────────

def _call_groq(system_prompt: str, user_content: str, span_name: str = "groq-call") -> str:
    """
    Plain text Groq caller — used only by the summary agent.
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
        response = _groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.1,
            max_tokens=2048,
        )

        result = response.choices[0].message.content.strip()
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


# ─── Shared Instructor caller (extraction agents) ────────────────────────────

def _extract_structured(
    system_prompt: str,
    user_content: str,
    response_model,
    span_name: str,
):
    """
    Instructor-based structured extractor.
    Returns a validated Pydantic object — always, no exceptions for bad JSON.

    response_model: the Pydantic class to extract into (e.g. ActionItemList)
    span_name: label shown in Langfuse dashboard
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
        # This is the Instructor magic line.
        # response_model= tells Instructor what Pydantic class to return.
        # Groq is forced to match the schema — no preamble, no extra text.
        result = _instructor_client.chat.completions.create(
            model=MODEL,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.1,
            max_tokens=2048,
            max_retries=3,   # Instructor auto-retries if validation fails
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


# ─── Agent 1: Summary ────────────────────────────────────────────────────────
# Summary returns plain text — no JSON needed — so we keep using _call_groq.

def run_summary_agent(transcript: str) -> str:
    system = """You are an expert meeting analyst.
Your ONLY job: write a concise executive summary of this meeting transcript.

Rules:
- 3 to 5 sentences maximum
- Focus on what was accomplished and what was decided
- Use plain business language
- Do NOT list action items or decisions here
- Return ONLY the summary text, no labels, no headings"""

    return _call_groq(system, f"TRANSCRIPT:\n{transcript}", span_name="summary_agent")


# ─── Agent 2: Action Items ───────────────────────────────────────────────────
# NOW uses Instructor — returns list[ActionItem], always valid, never crashes.

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
        user_content=f"TRANSCRIPT:\n{transcript}",
        response_model=ActionItemList,   # ← returns ActionItemList object
        span_name="action_item_agent",
    )

    return result.items   # ← list[ActionItem], always valid


# ─── Agent 3: Decisions ──────────────────────────────────────────────────────

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
        user_content=f"TRANSCRIPT:\n{transcript}",
        response_model=DecisionList,
        span_name="decision_agent",
    )

    return result.items


# ─── Agent 4: Topics ─────────────────────────────────────────────────────────

def run_topic_agent(transcript: str) -> list[Topic]:
    system = """You are an expert meeting analyst.
Your ONLY job: identify the 3 to 6 main topics discussed in this meeting transcript.

For each topic:
- title: a short noun phrase, 3-5 words (required)
- description: one sentence explaining what was discussed (null if obvious)

Cover the main themes only — do not list every sub-point."""

    result = _extract_structured(
        system_prompt=system,
        user_content=f"TRANSCRIPT:\n{transcript}",
        response_model=TopicList,
        span_name="topic_agent",
    )

    return result.items