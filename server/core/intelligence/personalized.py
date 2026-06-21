# ═════════════════════════════════════════════════════════════════════════════
# WEEK 5 — PART 5 OF 6
# FILE: server/core/intelligence/personalized.py
#
# Create this as a NEW file at that exact path.
#
# WHAT THIS FILE DOES:
#   When a meeting belongs to a project workspace, we can give the user
#   PERSONALIZED features based on the history of that project.
#
#   Example:
#     Meeting 1 in "Q4 Planning": "we need to decide on pricing strategy"
#     Meeting 2 in "Q4 Planning": (this meeting)
#
#     → Personalized suggestion: "Last time you discussed pricing strategy.
#       Has that been resolved or should it be on today's agenda?"
#
#   These features use the workspace context (previous meeting summaries
#   and open action items) to make the current meeting more useful.
#
#   Three personalized features:
#     1. smart_agenda  — suggested topics based on open action items
#     2. carry_forward — open items from past meetings that might be relevant
#     3. compare_health — how does this meeting's health compare to others?
# ═════════════════════════════════════════════════════════════════════════════

import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
MODEL = "llama-3.3-70b-versatile"

_client = None

def _get_groq():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def generate_smart_agenda(workspace_id: int, user_id: int) -> dict:
    """
    Generate a suggested agenda for the NEXT meeting in this workspace,
    based on what's been discussed and what's still open.

    Logic:
        1. Get all open action items from past meetings in this workspace
        2. Get all topics that have come up across meetings
        3. Ask Groq: "Given these open items and recurring topics,
                      what should be on the next meeting's agenda?"

    Returns:
        {
            "agenda_items": [
                {"title": "Review Q4 pricing decision", "reason": "Decided last meeting, needs follow-up"},
                {"title": "Status update on deploy", "reason": "Alice's action item from 2024-01-10"},
                ...
            ],
            "context_meetings": 5    (how many past meetings this is based on)
        }
    """
    from server.core.intelligence.workspace_intel import get_workspace_action_items
    from server.core.database import get_meetings_in_workspace, get_meeting_intelligence

    # Get open action items
    task_result = get_workspace_action_items(workspace_id=workspace_id, user_id=user_id)
    if task_result is None:
        return None

    open_items = [i for i in task_result["items"] if i.get("status") != "done"]

    # Get recurring topics across meetings
    meetings = get_meetings_in_workspace(workspace_id=workspace_id, user_id=user_id)
    all_topics = []
    for mtg in meetings:
        intel = get_meeting_intelligence(mtg["id"])
        if intel:
            for t in intel.get("topics", []):
                all_topics.append(t.get("title", ""))

    if not open_items and not all_topics:
        return {
            "agenda_items":    [],
            "context_meetings": len(meetings),
            "message":         "No past meeting data to generate an agenda from.",
        }

    # Format open items for the prompt
    items_text = "\n".join([
        f"- {item['task']}"
        + (f" (owner: {item['owner']})" if item.get("owner") else "")
        + (f" (from meeting: {item['meeting_name']})" if item.get("meeting_name") else "")
        for item in open_items[:15]   # cap at 15 to stay within tokens
    ])

    topics_text = ", ".join(list(dict.fromkeys(all_topics))[:20])  # unique topics, capped at 20

    prompt = f"""Based on these open action items and recurring topics from past meetings,
suggest 4-6 agenda items for the next meeting.

OPEN ACTION ITEMS:
{items_text if items_text else "None"}

RECURRING TOPICS:
{topics_text if topics_text else "None"}

Return ONLY a JSON array. No explanation, no markdown, no backticks. Example:
[
  {{"title": "Review Q4 pricing", "reason": "Ongoing discussion from past meetings"}},
  {{"title": "Deploy status update", "reason": "Action item assigned to Alice"}}
]"""

    try:
        import json
        client = _get_groq()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        # Strip any accidental markdown backticks
        raw = raw.replace("```json", "").replace("```", "").strip()
        agenda_items = json.loads(raw)
    except Exception as e:
        logger.warning(f"Smart agenda generation failed: {e}")
        agenda_items = []

    return {
        "agenda_items":    agenda_items,
        "context_meetings": len(meetings),
        "open_items_count": len(open_items),
    }


def get_carry_forward_items(workspace_id: int, meeting_id: int, user_id: int) -> dict:
    """
    Find open action items from PAST meetings in this workspace
    that are likely relevant to the current meeting (based on topic overlap).

    Use case:
        You're looking at a new meeting that was just uploaded.
        This feature says: "Hey, these 3 items from your last meeting
        are still open — did this meeting address them?"

    How it works:
        1. Get open action items from all OTHER meetings in this workspace
        2. Get the current meeting's topics and summary
        3. Return the open items (the LLM can decide relevance in the future —
           for now we return all open items from the project)
    """
    from server.core.database import (
        get_meetings_in_workspace,
        get_meeting_intelligence,
        get_meeting_by_id,
    )

    # Verify the user owns both the workspace and the meeting
    workspace_meetings = get_meetings_in_workspace(workspace_id=workspace_id, user_id=user_id)
    if workspace_meetings is None:
        return None

    current_meeting_ids = {m["id"] for m in workspace_meetings}
    if meeting_id not in current_meeting_ids:
        return {"carry_forward": [], "message": "This meeting is not in the workspace."}

    # Current meeting's intel (what topics did THIS meeting cover?)
    current_intel = get_meeting_intelligence(meeting_id)
    current_topics = set()
    if current_intel:
        for t in current_intel.get("topics", []):
            current_topics.add(t.get("title", "").lower())

    # Open items from other meetings in this workspace
    carry_forward = []
    for mtg in workspace_meetings:
        if mtg["id"] == meeting_id:
            continue   # skip the current meeting

        intel = get_meeting_intelligence(mtg["id"])
        if not intel:
            continue

        for item in intel.get("action_items", []):
            if item.get("status") != "done":
                carry_forward.append({
                    **item,
                    "source_meeting_id":   mtg["id"],
                    "source_meeting_name": mtg.get("ai_title") or mtg["filename"],
                    "source_meeting_date": mtg["created_at"],
                })

    return {
        "carry_forward": carry_forward,
        "total":         len(carry_forward),
        "current_topics": list(current_topics),
    }


def compare_meeting_health(workspace_id: int, meeting_id: int, user_id: int) -> dict:
    """
    Compare a meeting's health scores against the average for this workspace.

    Returns:
        {
            "this_meeting": {"overall": 72, "participation": 65, ...},
            "workspace_avg": {"overall": 68, "participation": 70, ...},
            "vs_average": {"overall": +4, "participation": -5, ...},
            "verdict": "This meeting was slightly better than your average."
        }

    The verdict is generated by Groq based on the numbers.
    """
    from server.core.database import get_meetings_in_workspace, get_meeting_health

    meetings = get_meetings_in_workspace(workspace_id=workspace_id, user_id=user_id)
    if meetings is None:
        return None

    # Get health for this meeting
    this_health = get_meeting_health(meeting_id)
    if not this_health:
        return {
            "error": "No health score for this meeting yet. Call GET /meetings/{id}/health first."
        }

    # Get health scores for all other meetings in this workspace
    other_scores = []
    for mtg in meetings:
        if mtg["id"] == meeting_id:
            continue
        h = get_meeting_health(mtg["id"])
        if h:
            other_scores.append(h)

    if not other_scores:
        return {
            "this_meeting":  this_health,
            "workspace_avg": None,
            "vs_average":    None,
            "verdict":       "Not enough other meetings in this workspace to compare yet.",
        }

    # Calculate averages
    def avg(key):
        return round(sum(s[key] for s in other_scores) / len(other_scores))

    workspace_avg = {
        "overall_score":    avg("overall_score"),
        "participation":    avg("participation"),
        "decision_quality": avg("decision_quality"),
        "action_clarity":   avg("action_clarity"),
        "followup_risk":    avg("followup_risk"),
    }

    vs_average = {
        k: this_health[k] - workspace_avg[k]
        for k in workspace_avg
    }

    # Quick verdict
    diff = vs_average["overall_score"]
    if diff >= 10:
        verdict = "This was one of the better meetings in this project."
    elif diff >= 0:
        verdict = "This meeting was about average for this project."
    elif diff >= -10:
        verdict = "This meeting was slightly below your project average."
    else:
        verdict = "This was one of the weaker meetings in this project."

    return {
        "this_meeting":  this_health,
        "workspace_avg": workspace_avg,
        "vs_average":    vs_average,
        "compared_to":   len(other_scores),
        "verdict":       verdict,
    }