# server/core/agent/tools.py
#
# WHAT IS A "TOOL" IN AN AI AGENT?
# ─────────────────────────────────
# A tool is just a Python function the LLM is *allowed* to call.
# The LLM doesn't run Python — it reads descriptions of tools and decides
# which one to call and with what arguments.
# YOUR code then actually runs the function, gets the result, and feeds it
# back to the LLM so it can decide what to do next.
#
# Think of it like a restaurant kitchen:
#   LLM = the waiter who decides what to order
#   Tools = the dishes on the menu
#   Your code = the kitchen that actually cooks
#
# We define 5 tools. Each one:
#   1. Has a clear name the LLM will call by name
#   2. Has a description the LLM reads to decide whether to use it
#   3. Is a plain Python function that calls your existing database/RAG functions
#   4. Returns a plain string (the LLM can only read text)
#
# IMPORTANT: These functions call YOUR existing code exactly as-is.
# database.py functions are called directly — no wrapping, no copying.
# hybrid_search() is called directly — same as chat.py uses it.

import json
from server.core.database import (
    get_meeting_intelligence,
    get_meeting_health,
    get_meeting_by_id,
)
from server.core.rag.hybrid_search import hybrid_search


# =============================================================================
# TOOL DEFINITIONS (the "menu" for the LLM)
# =============================================================================
#
# TOOL_DEFINITIONS is a list of dicts in the exact format the Groq API expects.
# Each dict has:
#   type: always "function"
#   function:
#     name:        what the LLM will write when it wants to call this tool
#     description: what this tool does — the LLM READS this to decide
#     parameters:  what arguments the tool needs, in JSON Schema format
#
# The LLM never sees your Python code — only these descriptions.
# Write them clearly. Vague descriptions = wrong tool calls.

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_transcript",
            "description": (
                "Search the meeting transcript using hybrid BM25 + vector search. "
                "Use this when the user asks about something specific that was said, "
                "discussed, or mentioned in the meeting. Returns the most relevant "
                "transcript chunks ranked by relevance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — what to look for in the transcript",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_action_items",
            "description": (
                "Get all action items extracted from the meeting. "
                "Use this when the user asks about tasks, to-dos, follow-ups, "
                "who is responsible for what, or what needs to be done after the meeting."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_decisions",
            "description": (
                "Get all decisions made during the meeting. "
                "Use this when the user asks what was decided, agreed upon, "
                "confirmed, or resolved during the meeting."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_meeting",
            "description": (
                "Get the executive summary and key topics of the meeting. "
                "Use this when the user asks for an overview, summary, recap, "
                "what the meeting was about, or what topics were covered."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_health_score",
            "description": (
                "Get the meeting health scores: overall quality, participation balance, "
                "decision quality, action clarity, and follow-up risk. "
                "Use this when the user asks how well the meeting went, the meeting score, "
                "meeting quality, participation, or risks."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


# =============================================================================
# TOOL IMPLEMENTATIONS (the "kitchen" that actually cooks)
# =============================================================================
# Each function below maps 1-to-1 with a TOOL_DEFINITIONS entry above.
# They all receive meeting_id as a parameter (injected by the agent loop).
# They all return strings — because the LLM can only read text.

def search_transcript(meeting_id: int, query: str, top_k: int = 5) -> str:
    """
    Calls hybrid_search() — your existing BM25 + vector search.
    Returns a formatted string of the top matching chunks.
    """
    # Cap top_k at 10 so the agent can't accidentally ask for 1000 results
    top_k = min(top_k, 10)

    chunks = hybrid_search(query=query, meeting_id=meeting_id, top_k=top_k)

    if not chunks:
        return "No relevant transcript sections found for that query."

    lines = [f"Found {len(chunks)} relevant transcript sections:\n"]
    for i, chunk in enumerate(chunks, 1):
        score_pct = round(chunk.get("score", 0) * 100, 1)
        lines.append(
            f"[{i}] Relevance: {score_pct}%\n"
            f"{chunk['text']}\n"
        )

    return "\n".join(lines)


def get_action_items(meeting_id: int) -> str:
    """
    Calls get_meeting_intelligence() — your existing database function.
    Extracts and formats just the action_items list.
    """
    intel = get_meeting_intelligence(meeting_id)

    if not intel:
        return "No intelligence data found for this meeting. It may not have been processed yet."

    items = intel.get("action_items", [])

    if not items:
        return "No action items were extracted from this meeting."

    lines = [f"Found {len(items)} action item(s):\n"]
    for i, item in enumerate(items, 1):
        owner    = item.get("owner")    or "Unassigned"
        deadline = item.get("deadline") or "No deadline"
        priority = item.get("priority") or "medium"
        status   = item.get("status")   or "open"

        lines.append(
            f"{i}. [{priority.upper()}] {item['task']}\n"
            f"   Owner: {owner} | Due: {deadline} | Status: {status}"
        )

    return "\n".join(lines)


def get_decisions(meeting_id: int) -> str:
    """
    Calls get_meeting_intelligence() — your existing database function.
    Extracts and formats just the decisions list.
    """
    intel = get_meeting_intelligence(meeting_id)

    if not intel:
        return "No intelligence data found for this meeting."

    decisions = intel.get("decisions", [])

    if not decisions:
        return "No decisions were extracted from this meeting."

    lines = [f"Found {len(decisions)} decision(s):\n"]
    for i, d in enumerate(decisions, 1):
        rationale = d.get("rationale")
        lines.append(f"{i}. {d['decision']}")
        if rationale:
            lines.append(f"   Rationale: {rationale}")

    return "\n".join(lines)


def summarize_meeting(meeting_id: int) -> str:
    """
    Calls get_meeting_intelligence() and get_meeting_by_id() — your existing functions.
    Returns the summary + topics as a formatted string.
    """
    intel = get_meeting_intelligence(meeting_id)

    if not intel:
        return "No intelligence data found for this meeting."

    summary = intel.get("summary", "No summary available.")
    topics  = intel.get("topics",  [])

    lines = [f"MEETING SUMMARY:\n{summary}"]

    if topics:
        lines.append(f"\nKEY TOPICS ({len(topics)}):")
        for i, t in enumerate(topics, 1):
            desc = t.get("description", "")
            lines.append(f"  {i}. {t['title']}" + (f" — {desc}" if desc else ""))

    return "\n".join(lines)


def get_health_score(meeting_id: int) -> str:
    """
    Calls get_meeting_health() — your existing database function.
    Returns a formatted score report string.
    """
    health = get_meeting_health(meeting_id)

    if not health:
        return "No health score found for this meeting. It may not have been analyzed yet."

    def score_label(n: int) -> str:
        # Human-readable label alongside the number
        if n >= 80: return "Excellent"
        if n >= 65: return "Good"
        if n >= 50: return "Fair"
        return "Needs Improvement"

    lines = [
        "MEETING HEALTH SCORES:\n",
        f"  Overall Score:       {health['overall_score']}/100  ({score_label(health['overall_score'])})",
        f"  Participation:       {health['participation']}/100  ({score_label(health['participation'])})",
        f"  Decision Quality:    {health['decision_quality']}/100  ({score_label(health['decision_quality'])})",
        f"  Action Clarity:      {health['action_clarity']}/100  ({score_label(health['action_clarity'])})",
        f"  Follow-up Risk:      {health['followup_risk']}/100  ({score_label(health['followup_risk'])})",
    ]

    if health.get("highlights"):
        lines.append(f"\nHighlights: {health['highlights']}")
    if health.get("concerns"):
        lines.append(f"Concerns:   {health['concerns']}")

    return "\n".join(lines)


# =============================================================================
# TOOL DISPATCHER
# =============================================================================
# The agent loop calls this function with the name and arguments the LLM chose.
# This maps the name string → the actual Python function and calls it.
# Returns the string result, or an error message if something goes wrong.

def execute_tool(tool_name: str, tool_args: dict, meeting_id: int) -> str:
    """
    Dispatches a tool call from the LLM to the correct Python function.

    Args:
        tool_name  : the name field from the LLM's tool_call response
        tool_args  : the arguments dict the LLM provided (already parsed from JSON)
        meeting_id : injected by the agent — the meeting being discussed

    Returns:
        A string result to feed back to the LLM as a tool result message.
    """
    try:
        if tool_name == "search_transcript":
            return search_transcript(
                meeting_id=meeting_id,
                query=tool_args["query"],
                top_k=tool_args.get("top_k", 5),
            )

        elif tool_name == "get_action_items":
            return get_action_items(meeting_id=meeting_id)

        elif tool_name == "get_decisions":
            return get_decisions(meeting_id=meeting_id)

        elif tool_name == "summarize_meeting":
            return summarize_meeting(meeting_id=meeting_id)

        elif tool_name == "get_health_score":
            return get_health_score(meeting_id=meeting_id)

        else:
            return f"Unknown tool: '{tool_name}'. Available tools: search_transcript, get_action_items, get_decisions, summarize_meeting, get_health_score"

    except KeyError as e:
        return f"Tool '{tool_name}' missing required argument: {e}"
    except Exception as e:
        return f"Tool '{tool_name}' failed: {type(e).__name__}: {str(e)}"