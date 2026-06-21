
# HOW THIS IS DIFFERENT FROM THE WEEK 5 VERSION:
#
#   Week 5 personalized.py has generate_smart_agenda() which requires a
#   workspace_id — it only works if the meeting is inside a project.
#
#   This new version works in TWO modes:
#
#   MODE 1 — WORKSPACE MODE (meeting belongs to a project)
#     Same as before: pulls open action items + recurring topics from all
#     meetings in the workspace. Rich context, best results.
#
#   MODE 2 — STANDALONE MODE (meeting has no workspace)
#     Uses only the current meeting's own intelligence:
#     open action items, topics, decisions not yet resolved.
#     Useful for one-off meetings or when a user hasn't set up workspaces yet.
#
#   The endpoint detects which mode to use automatically.
# ═════════════════════════════════════════════════════════════════════════════
 
import json
import os
import logging
import time
 
from groq import Groq
from langfuse import Langfuse
from dotenv import load_dotenv
 
load_dotenv()
logger = logging.getLogger(__name__)
MODEL = "llama-3.3-70b-versatile"
 
_groq_client = None
_langfuse    = None
 
def _get_clients():
    global _groq_client, _langfuse
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        _langfuse    = Langfuse()
    return _groq_client, _langfuse
 
 
def generate_agenda_for_meeting(meeting_id: int, user_id: int) -> dict:
    """
    Generate a smart agenda suggestion for the NEXT meeting after this one.
 
    Automatically detects whether the meeting is in a workspace and uses
    the richest context available.
 
    Steps:
        1. Check if this meeting belongs to a workspace
        2. If yes  → collect open items + topics from ALL workspace meetings
        3. If no   → collect open items + topics from THIS meeting only
        4. Ask Groq to generate 4-6 agenda items with reasons
        5. Return the agenda
 
    Args:
        meeting_id : the meeting to generate the next agenda for
        user_id    : for ownership verification
 
    Returns:
        {
            "meeting_id"    : int,
            "mode"          : "workspace" or "standalone",
            "workspace_name": str or None,
            "agenda_items"  : [{"title": str, "reason": str, "priority": str}, ...],
            "context_source": description of what data was used,
            "open_items_used": int,
            "topics_used"    : int,
        }
    """
    from server.core.database import (
        get_meeting_by_id,
        get_meeting_intelligence,
        get_workspace_for_meeting,
        get_meetings_in_workspace,
    )
 
    # Verify meeting exists and user owns it
    meeting = get_meeting_by_id(meeting_id, user_id=user_id)
    if not meeting:
        return None
 
    # ── Detect mode ────────────────────────────────────────────────────────
    workspace_info = get_workspace_for_meeting(meeting_id)
 
    if workspace_info:
        # ── MODE 1: Workspace mode ────────────────────────────────────────
        # Pull data from all meetings in this workspace
        workspace_meetings = get_meetings_in_workspace(
            workspace_id=workspace_info["id"],
            user_id=user_id,
        )
 
        open_items = []
        all_topics = []
 
        for mtg in (workspace_meetings or []):
            intel = get_meeting_intelligence(mtg["id"])
            if not intel:
                continue
 
            meeting_label = mtg.get("ai_title") or mtg["filename"]
 
            for item in intel.get("action_items", []):
                if item.get("status") != "done":
                    open_items.append({
                        **item,
                        "from_meeting": meeting_label,
                    })
 
            for topic in intel.get("topics", []):
                all_topics.append(topic.get("title", ""))
 
        mode           = "workspace"
        context_source = f"Based on {len(workspace_meetings or [])} meetings in '{workspace_info['name']}'"
        workspace_name = workspace_info["name"]
 
    else:
        # ── MODE 2: Standalone mode ───────────────────────────────────────
        # Use only this meeting's own intelligence
        intel = get_meeting_intelligence(meeting_id)
        if not intel:
            return {
                "meeting_id":     meeting_id,
                "mode":           "standalone",
                "workspace_name": None,
                "agenda_items":   [],
                "context_source": "No intelligence generated for this meeting yet.",
                "open_items_used": 0,
                "topics_used":    0,
            }
 
        open_items = [
            {**item, "from_meeting": meeting.get("filename", "this meeting")}
            for item in intel.get("action_items", [])
            if item.get("status") != "done"
        ]
 
        all_topics = [t.get("title", "") for t in intel.get("topics", [])]
 
        mode           = "standalone"
        context_source = "Based on this meeting's open action items and topics"
        workspace_name = None
 
    # ── Build the prompt ──────────────────────────────────────────────────
    open_items_text = ""
    if open_items:
        lines = []
        for item in open_items[:15]:  # cap to avoid token overflow
            line = f"- {item['task']}"
            if item.get("owner"):
                line += f" (owner: {item['owner']})"
            if item.get("deadline"):
                line += f" (due: {item['deadline']})"
            if item.get("from_meeting"):
                line += f" [from: {item['from_meeting']}]"
            lines.append(line)
        open_items_text = "\n".join(lines)
    else:
        open_items_text = "None"
 
    unique_topics     = list(dict.fromkeys(t for t in all_topics if t))[:20]
    topics_text       = ", ".join(unique_topics) if unique_topics else "None"
 
    system = """You are an expert meeting facilitator.
Your job: generate a focused, practical agenda for the NEXT meeting.
 
Rules:
- Suggest exactly 4 to 6 agenda items
- Each item must have: title (short, action-oriented), reason (why it belongs), priority (high/medium/low)
- Base suggestions ONLY on the open action items and topics provided
- Prioritise unresolved items with owners and deadlines
- Do NOT invent topics not grounded in the data
- Return ONLY a JSON array — no markdown, no explanation, no backticks
 
Example format:
[
  {"title": "Q4 pricing decision follow-up", "reason": "Agreed last meeting, no final number yet", "priority": "high"},
  {"title": "Deploy status — Alice", "reason": "Open action item, deadline this Friday", "priority": "high"}
]"""
 
    user_content = f"""OPEN ACTION ITEMS (not yet done):
{open_items_text}
 
TOPICS DISCUSSED IN PAST MEETINGS:
{topics_text}
 
Generate the next meeting agenda:"""
 
    # ── Call Groq ─────────────────────────────────────────────────────────
    groq_client, langfuse = _get_clients()
 
    generation = langfuse.generation(
        name="smart_agenda",
        model=MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ],
        metadata={"mode": mode, "open_items": len(open_items), "topics": len(unique_topics)},
    )
 
    start = time.time()
    agenda_items = []
 
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
 
        parsed = json.loads(raw)
 
        # Validate each item has the required fields — fill defaults if missing
        for item in parsed:
            if isinstance(item, dict) and "title" in item:
                agenda_items.append({
                    "title":    str(item.get("title", "")),
                    "reason":   str(item.get("reason", "")),
                    "priority": str(item.get("priority", "medium")).lower(),
                })
 
        generation.end(
            output=str(agenda_items),
            usage={
                "input":  response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total":  response.usage.total_tokens,
            },
            metadata={"latency_seconds": round(time.time() - start, 3)},
        )
 
    except json.JSONDecodeError as e:
        logger.warning(f"[Agenda] JSON parse failed: {e} | raw: {raw[:200]}")
        generation.end(output=f"JSON_ERROR: {e}", metadata={"error": True})
        # Return a graceful fallback instead of crashing
        agenda_items = _fallback_agenda(open_items)
 
    except Exception as e:
        logger.error(f"[Agenda] Groq call failed: {e}")
        generation.end(output=f"ERROR: {e}", metadata={"error": True})
        agenda_items = _fallback_agenda(open_items)
 
    return {
        "meeting_id":      meeting_id,
        "mode":            mode,
        "workspace_name":  workspace_name,
        "agenda_items":    agenda_items,
        "context_source":  context_source,
        "open_items_used": len(open_items),
        "topics_used":     len(unique_topics),
    }
 
 
def _fallback_agenda(open_items: list[dict]) -> list[dict]:
    """
    If the LLM call fails, build a basic agenda from open items directly.
    No LLM involved — just format what we have.
    This ensures the endpoint always returns something useful.
    """
    if not open_items:
        return [{"title": "Review previous meeting outcomes", "reason": "No open items found", "priority": "medium"}]
 
    items = []
    for item in open_items[:5]:
        items.append({
            "title":    item["task"][:60],
            "reason":   f"Open action item" + (f" — owner: {item['owner']}" if item.get("owner") else ""),
            "priority": item.get("priority", "medium"),
        })
    return items
 