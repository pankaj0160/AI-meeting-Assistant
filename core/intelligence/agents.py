import json
import os

from groq import Groq
from dotenv import load_dotenv

from core.intelligence.schemas import ActionItem, Decision, Topic

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def _call_groq(system_prompt: str, user_content: str) -> str:
    """
    Single shared Groq caller used by all agents.
    temperature=0.1 keeps outputs deterministic and factual.
    If you ever switch models or add retries, change it here only.
    """
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_content},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


def _clean_json(raw: str) -> str:
    """Strip markdown code fences the model sometimes adds."""
    return raw.replace("```json", "").replace("```", "").strip()


# ─── Agent 1: Summary ─────────────────────────────────────────────────────────

def run_summary_agent(transcript: str) -> str:
    system = """You are an expert meeting analyst.
Your ONLY job: write a concise executive summary of this meeting transcript.

Rules:
- 3 to 5 sentences maximum
- Focus on what was accomplished and what was decided
- Use plain business language
- Do NOT list action items or decisions here
- Return ONLY the summary text, no labels, no headings"""

    return _call_groq(system, f"TRANSCRIPT:\n{transcript}")


# ─── Agent 2: Action Items ────────────────────────────────────────────────────

def run_action_item_agent(transcript: str) -> list[ActionItem]:
    system = """You are an expert meeting analyst.
Your ONLY job: extract all action items from this meeting transcript.

Return a JSON array. Each object must have:
  "task"     : string  (required — what needs to be done)
  "owner"    : string or null  (who is responsible)
  "deadline" : string or null  (when, e.g. "Friday", "end of week", "Q3")
  "priority" : "high", "medium", or "low"

Example output:
[
  {"task": "Send proposal to client", "owner": "Alice", "deadline": "Friday", "priority": "high"},
  {"task": "Review Q3 budget",        "owner": null,    "deadline": null,     "priority": "medium"}
]

Return ONLY a valid JSON array. No explanation. No markdown. No preamble."""

    raw = _call_groq(system, f"TRANSCRIPT:\n{transcript}")

    try:
        items = json.loads(_clean_json(raw))
        return [ActionItem(**item) for item in items]
    except Exception:
        return []


# ─── Agent 3: Decisions ───────────────────────────────────────────────────────

def run_decision_agent(transcript: str) -> list[Decision]:
    system = """You are an expert meeting analyst.
Your ONLY job: extract all decisions made in this meeting transcript.
Only include real decisions — things agreed upon, not things discussed.

Return a JSON array. Each object must have:
  "decision"  : string  (required — the actual decision made)
  "rationale" : string or null  (why, if mentioned)

Example output:
[
  {"decision": "Move deployment to Q2",       "rationale": "Team needs more time for testing"},
  {"decision": "Hire two backend engineers",  "rationale": null}
]

Return ONLY a valid JSON array. No explanation. No markdown. No preamble."""

    raw = _call_groq(system, f"TRANSCRIPT:\n{transcript}")

    try:
        items = json.loads(_clean_json(raw))
        return [Decision(**item) for item in items]
    except Exception:
        return []


# ─── Agent 4: Topics ─────────────────────────────────────────────────────────

def run_topic_agent(transcript: str) -> list[Topic]:
    system = """You are an expert meeting analyst.
Your ONLY job: identify the 3 to 6 main discussion topics from this meeting transcript.

Return a JSON array. Each object must have:
  "title"       : string  (required — 3 to 5 words, noun phrase)
  "description" : string or null  (one sentence max)

Example output:
[
  {"title": "Q3 hiring plan",         "description": "Team discussed headcount needs for next quarter"},
  {"title": "Product roadmap review", "description": null}
]

Return ONLY a valid JSON array. No explanation. No markdown. No preamble."""

    raw = _call_groq(system, f"TRANSCRIPT:\n{transcript}")

    try:
        items = json.loads(_clean_json(raw))
        return [Topic(**item) for item in items]
    except Exception:
        return []