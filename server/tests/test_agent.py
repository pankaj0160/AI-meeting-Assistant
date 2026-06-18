# server/tests/test_agents.py
# Tests for server/core/intelligence/agents.py
#
# We mock _call_groq() so tests run instantly without hitting Groq API.
# The agents still run their real parsing logic — we only fake the LLM response.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch
from server.core.intelligence.agents import (
    run_summary_agent,
    run_action_item_agent,
    run_decision_agent,
    run_topic_agent,
)
from server.core.intelligence.schemas import ActionItem, Decision, Topic


# ── Test 1 ────────────────────────────────────────────────────────────────────
def test_summary_agent_returns_string(sample_transcript):
    """
    Summary agent should always return a non-empty string.
    We mock _call_groq to return a fake summary instantly.
    """
    fake_summary = "The team discussed student absenteeism and agreed on a pancake breakfast."

    with patch("server.core.intelligence.agents._call_groq") as mock_groq:
        mock_groq.return_value = fake_summary

        result = run_summary_agent(sample_transcript)

    # Assertions — what we expect
    assert isinstance(result, str),       "Summary must be a string"
    assert len(result) > 10,              "Summary must not be empty"
    assert result == fake_summary,        "Summary should be exactly what _call_groq returned"


# ── Test 2 ────────────────────────────────────────────────────────────────────
def test_action_item_agent_returns_list(sample_transcript, fake_action_items_json):
    """
    Action item agent should return a list of ActionItem objects.
    Each item must have .task, .owner, .deadline, .priority attributes.
    """
    with patch("server.core.intelligence.agents._call_groq") as mock_groq:
        mock_groq.return_value = fake_action_items_json

        result = run_action_item_agent(sample_transcript)

    assert isinstance(result, list),          "Must return a list"
    assert len(result) == 1,                  "Should find 1 action item"
    assert isinstance(result[0], ActionItem), "Items must be ActionItem objects"
    assert result[0].task == "Organize pancake breakfast"
    assert result[0].owner == "Sarah"
    assert result[0].priority == "high"


# ── Test 3 ────────────────────────────────────────────────────────────────────
def test_action_item_agent_handles_bad_json(sample_transcript):
    """
    If Groq returns garbage (not valid JSON), the agent should return []
    instead of crashing. This tests the silent failure protection.
    """
    with patch("server.core.intelligence.agents._call_groq") as mock_groq:
        mock_groq.return_value = "Sorry, I cannot do that right now."  # not JSON

        result = run_action_item_agent(sample_transcript)

    assert result == [],   "Bad JSON should return empty list, not crash"


# ── Test 4 ────────────────────────────────────────────────────────────────────
def test_decision_agent_returns_list(sample_transcript, fake_decisions_json):
    """
    Decision agent should return a list of Decision objects.
    """
    with patch("server.core.intelligence.agents._call_groq") as mock_groq:
        mock_groq.return_value = fake_decisions_json

        result = run_decision_agent(sample_transcript)

    assert isinstance(result, list),           "Must return a list"
    assert len(result) == 1,                   "Should find 1 decision"
    assert isinstance(result[0], Decision),    "Items must be Decision objects"
    assert "pancake breakfast" in result[0].decision.lower()
    assert result[0].rationale is not None


# ── Test 5 ────────────────────────────────────────────────────────────────────
def test_topic_agent_returns_list(sample_transcript, fake_topics_json):
    """
    Topic agent should return a list of Topic objects with a .title attribute.
    """
    with patch("server.core.intelligence.agents._call_groq") as mock_groq:
        mock_groq.return_value = fake_topics_json

        result = run_topic_agent(sample_transcript)

    assert isinstance(result, list),       "Must return a list"
    assert len(result) == 1,               "Should find 1 topic"
    assert isinstance(result[0], Topic),   "Items must be Topic objects"
    assert result[0].title == "Student Friday Absenteeism"