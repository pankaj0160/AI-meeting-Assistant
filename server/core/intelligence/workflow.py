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


# ─── Graph State ──────────────────────────────────────────────────────────────

class IntelligenceState(TypedDict):
    transcript:   str
    summary:      str
    action_items: list[ActionItem]
    decisions:    list[Decision]
    topics:       list[Topic]


# ─── Nodes ────────────────────────────────────────────────────────────────────

def _summary_node(state: IntelligenceState) -> IntelligenceState:
    print("  → Running summary agent...")
    summary = run_summary_agent(state["transcript"])
    return {**state, "summary": summary}


def _action_items_node(state: IntelligenceState) -> IntelligenceState:
    print("  → Running action items agent...")
    items = run_action_item_agent(state["transcript"])
    print(f"    Found {len(items)} action items")
    return {**state, "action_items": items}


def _decisions_node(state: IntelligenceState) -> IntelligenceState:
    print("  → Running decisions agent...")
    decisions = run_decision_agent(state["transcript"])
    print(f"    Found {len(decisions)} decisions")
    return {**state, "decisions": decisions}


def _topics_node(state: IntelligenceState) -> IntelligenceState:
    print("  → Running topics agent...")
    topics = run_topic_agent(state["transcript"])
    print(f"    Found {len(topics)} topics")
    return {**state, "topics": topics}


# ─── Graph builder ────────────────────────────────────────────────────────────

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


# ─── Public API ───────────────────────────────────────────────────────────────

def analyze_transcript(transcript: str) -> MeetingIntelligence:
    """
    The only function your pipeline should call.

    Takes a raw transcript string.
    Returns a fully populated MeetingIntelligence object.
    Returns a safe empty result if transcript is too short.
    """
    if not transcript or len(transcript.strip()) < 50:
        print("  ⚠ Transcript too short to analyze.")
        return MeetingIntelligence(
            summary="Transcript too short to generate intelligence.",
            action_items=[],
            decisions=[],
            topics=[],
        )

    graph = _build_graph()

    initial_state: IntelligenceState = {
        "transcript":   transcript,
        "summary":      "",
        "action_items": [],
        "decisions":    [],
        "topics":       [],
    }

    result = graph.invoke(initial_state)

    return MeetingIntelligence(
        summary=result["summary"],
        action_items=result["action_items"],
        decisions=result["decisions"],
        topics=result["topics"],
    )