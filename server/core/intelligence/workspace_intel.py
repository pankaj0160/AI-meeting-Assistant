# ═════════════════════════════════════════════════════════════════════════════
# WEEK 5 — PART 3 OF 6
# FILE: server/core/intelligence/workspace_intel.py

# WHAT THIS FILE DOES:
#   When meetings are grouped in a project workspace, you can ask:
#   - "What are all the open action items across this project?"
#   - "What recurring topics keep coming up in this project's meetings?"
#   - "What decisions has this project made so far?"
#   - "What's the trend in meeting quality over time?"
#
#   This file generates those cross-meeting insights using your existing
#   database functions. No new LLM calls are needed for most of them —
#   it's aggregation of data you already have.
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


def get_workspace_summary(workspace_id: int, user_id: int) -> dict:
    """
    Generate a full intelligence summary for a workspace.

    Pulls together data from all meetings in the workspace:
        - Total meetings, total action items, total decisions
        - All open action items (tasks not yet done)
        - All decisions made across meetings
        - Meeting health score trend
        - A Groq-generated project narrative (what is this project about,
          what has been decided, what's still outstanding)

    Args:
        workspace_id : which workspace to summarise
        user_id      : for ownership verification

    Returns a dict with all the above data. The endpoint in main.py
    returns this directly as the API response.
    """
    from server.core.database import (
        get_meetings_in_workspace,
        get_workspace_by_id,
        get_meeting_intelligence,
        get_meeting_health,
    )

    # Verify access
    workspace = get_workspace_by_id(workspace_id, user_id)
    if not workspace:
        return None

    meetings = get_meetings_in_workspace(workspace_id, user_id)

    if not meetings:
        return {
            "workspace_id":   workspace_id,
            "workspace_name": workspace["name"],
            "workspace_type": workspace["type"],
            "total_meetings": 0,
            "open_actions":   [],
            "all_decisions":  [],
            "health_trend":   [],
            "narrative":      "No meetings in this workspace yet.",
        }

    # ── Collect data from every meeting ──────────────────────────────────────
    open_actions  = []    # action items with status != 'done'
    all_decisions = []    # every decision made across all meetings
    all_summaries = []    # meeting summaries (used to generate the narrative)
    health_scores = []    # health score per meeting (for trend chart)

    for mtg in meetings:
        meeting_id = mtg["id"]
        intel  = get_meeting_intelligence(meeting_id)
        health = get_meeting_health(meeting_id)

        if intel:
            # Collect open action items, tagging which meeting they came from
            for item in intel.get("action_items", []):
                if item.get("status") != "done":
                    open_actions.append({
                        **item,
                        "meeting_id":   meeting_id,
                        "meeting_name": mtg.get("ai_title") or mtg["filename"],
                    })

            # Collect all decisions, tagging source meeting
            for d in intel.get("decisions", []):
                all_decisions.append({
                    **d,
                    "meeting_id":   meeting_id,
                    "meeting_name": mtg.get("ai_title") or mtg["filename"],
                })

            if intel.get("summary"):
                all_summaries.append(
                    f"Meeting '{mtg.get('ai_title') or mtg['filename']}':\n{intel['summary']}"
                )

        if health:
            health_scores.append({
                "meeting_id":   meeting_id,
                "meeting_name": mtg.get("ai_title") or mtg["filename"],
                "created_at":   mtg["created_at"],
                "overall":      health["overall_score"],
                "participation":health["participation"],
                "decision_quality": health["decision_quality"],
                "action_clarity":   health["action_clarity"],
            })

    # ── Generate a project narrative with Groq ────────────────────────────────
    # This is the one LLM call in this function.
    # It reads all the meeting summaries and writes a 2-3 paragraph
    # overview of what this project is about, what's been decided,
    # and what's still outstanding.
    narrative = _generate_project_narrative(
        workspace_name=workspace["name"],
        workspace_type=workspace["type"],
        summaries=all_summaries,
        open_action_count=len(open_actions),
        decision_count=len(all_decisions),
    )

    return {
        "workspace_id":   workspace_id,
        "workspace_name": workspace["name"],
        "workspace_type": workspace["type"],
        "total_meetings": len(meetings),
        "total_open_actions": len(open_actions),
        "total_decisions":    len(all_decisions),
        "open_actions":       open_actions,
        "all_decisions":      all_decisions,
        "health_trend":       health_scores,
        "narrative":          narrative,
    }


def _generate_project_narrative(
    workspace_name:    str,
    workspace_type:    str,
    summaries:         list[str],
    open_action_count: int,
    decision_count:    int,
) -> str:
    """
    Use Groq to write a 2-3 paragraph narrative about this workspace.

    If there are no summaries (no intelligence generated yet), return
    a placeholder message instead of calling the LLM.
    """
    if not summaries:
        return (
            f"This {'project' if workspace_type == 'project' else 'workspace'} "
            f"has meetings but no intelligence has been generated yet. "
            f"Open individual meetings and generate their intelligence first."
        )

    combined = "\n\n---\n\n".join(summaries[:10])  # cap at 10 to stay within token limit

    prompt = f"""You are summarising a series of meeting summaries from a workspace called "{workspace_name}".

Here are the individual meeting summaries:
{combined}

Statistics:
- Open action items still pending: {open_action_count}
- Total decisions made: {decision_count}

Write a 2-3 paragraph executive overview that covers:
1. What this workspace/project is about based on the meetings
2. What major decisions have been made
3. What the team is still working on (based on open action count)

Be specific, professional, and concise. Do not use bullet points."""

    try:
        client = _get_groq()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Narrative generation failed: {e}")
        return f"Could not generate narrative: {str(e)}"


def get_workspace_action_items(workspace_id: int, user_id: int) -> dict:
    """
    Get all action items across all meetings in a workspace.
    Filtered by status so you can see just open, just done, etc.

    This is the "project task board" view — all tasks from all meetings
    in this project in one place.
    """
    from server.core.database import get_meetings_in_workspace, get_meeting_intelligence

    meetings = get_meetings_in_workspace(workspace_id, user_id)
    if meetings is None:   # access denied
        return None

    all_items = []

    for mtg in meetings:
        intel = get_meeting_intelligence(mtg["id"])
        if not intel:
            continue

        for item in intel.get("action_items", []):
            all_items.append({
                **item,
                "meeting_id":   mtg["id"],
                "meeting_name": mtg.get("ai_title") or mtg["filename"],
                "meeting_date": mtg["created_at"],
            })

    # Sort: open first, then in_progress, then overdue, then done
    status_order = {"open": 1, "in_progress": 2, "overdue": 3, "done": 4}
    all_items.sort(key=lambda x: status_order.get(x.get("status", "open"), 5))

    return {
        "workspace_id": workspace_id,
        "total":        len(all_items),
        "open":         sum(1 for i in all_items if i.get("status") != "done"),
        "done":         sum(1 for i in all_items if i.get("status") == "done"),
        "items":        all_items,
    }