# core/intelligence/workflow.py

import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from server.core.intelligence.agents import (
    run_summary_agent,
    run_action_item_agent,
    run_decision_agent,
    run_topic_agent,
)
from server.core.intelligence.schemas import (
    MeetingIntelligence,
    ActionItem,
    Decision,
    Topic,
)

# FIX: use proper logger instead of print()
logger = logging.getLogger(__name__)


# ── Graph State ────────────────────────────────────────────────────────────────

class IntelligenceState(TypedDict):
    transcript:   str
    summary:      str
    action_items: list[ActionItem]
    decisions:    list[Decision]
    topics:       list[Topic]


# ── Nodes ──────────────────────────────────────────────────────────────────────
#
# FIX: Each node now has a try/except with a graceful fallback.
#
# Old code: if any agent failed, the whole graph crashed → meeting not saved.
# New code: if an agent fails, log the error and continue with an empty result.
#
# This means a Groq timeout on "decisions" still gives the user their
# summary, action items, and topics — not a total 500 error.
# The failed agent returns [] (or fallback text) so the meeting is always saved.

def _summary_node(state: IntelligenceState) -> IntelligenceState:
    logger.info("Running summary agent")
    try:
        summary = run_summary_agent(state["transcript"])
        logger.info("Summary agent complete (%d chars)", len(summary))
    except Exception as e:
        # FIX: graceful fallback — meeting still saves, user sees partial results
        logger.error("Summary agent failed: %s", e, exc_info=True)
        summary = "Summary unavailable — AI analysis encountered an error."
    return {**state, "summary": summary}


def _action_items_node(state: IntelligenceState) -> IntelligenceState:
    logger.info("Running action items agent")
    try:
        items = run_action_item_agent(state["transcript"])
        logger.info("Action items agent complete: found %d items", len(items))
    except Exception as e:
        # FIX: graceful fallback — empty list instead of crash
        logger.error("Action items agent failed: %s", e, exc_info=True)
        items = []
    return {**state, "action_items": items}


def _decisions_node(state: IntelligenceState) -> IntelligenceState:
    logger.info("Running decisions agent")
    try:
        decisions = run_decision_agent(state["transcript"])
        logger.info("Decisions agent complete: found %d decisions", len(decisions))
    except Exception as e:
        # FIX: graceful fallback
        logger.error("Decisions agent failed: %s", e, exc_info=True)
        decisions = []
    return {**state, "decisions": decisions}


def _topics_node(state: IntelligenceState) -> IntelligenceState:
    logger.info("Running topics agent")
    try:
        topics = run_topic_agent(state["transcript"])
        logger.info("Topics agent complete: found %d topics", len(topics))
    except Exception as e:
        # FIX: graceful fallback
        logger.error("Topics agent failed: %s", e, exc_info=True)
        topics = []
    return {**state, "topics": topics}


# ── Graph builder ──────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    graph = StateGraph(IntelligenceState)

    graph.add_node("summary",      _summary_node)
    graph.add_node("action_items", _action_items_node)
    graph.add_node("decisions",    _decisions_node)
    graph.add_node("topics",       _topics_node)

    graph.set_entry_point("summary")
    graph.add_edge("summary",      "action_items")
    graph.add_edge("action_items", "decisions")
    graph.add_edge("decisions",    "topics")
    graph.add_edge("topics",       END)

    return graph.compile()


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_transcript(transcript: str) -> MeetingIntelligence:
    """
    The only function your pipeline should call.

    Takes a raw transcript string.
    Returns a fully populated MeetingIntelligence object.

    Each agent has an individual fallback — one failure does not stop the rest.
    Always returns a result, never raises an exception to the caller.
    """
    if not transcript or len(transcript.strip()) < 50:
        logger.warning("Transcript too short to analyze (%d chars)", len(transcript))
        return MeetingIntelligence(
            summary="Transcript too short to generate intelligence.",
            action_items=[],
            decisions=[],
            topics=[],
        )

    logger.info("Starting intelligence analysis (%d chars)", len(transcript))
    graph = _build_graph()

    initial_state: IntelligenceState = {
        "transcript":   transcript,
        "summary":      "",
        "action_items": [],
        "decisions":    [],
        "topics":       [],
    }

    result = graph.invoke(initial_state)

    logger.info(
        "Intelligence analysis complete — summary: %s, actions: %d, decisions: %d, topics: %d",
        "yes" if result["summary"] else "no",
        len(result["action_items"]),
        len(result["decisions"]),
        len(result["topics"]),
    )

    return MeetingIntelligence(
        summary=      result["summary"],
        action_items= result["action_items"],
        decisions=    result["decisions"],
        topics=       result["topics"],
    )