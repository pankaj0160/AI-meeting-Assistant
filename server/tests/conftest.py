# server/tests/conftest.py
# Shared fixtures — available to ALL test files automatically.
# A "fixture" is just a reusable piece of test data or setup.

import pytest


@pytest.fixture
def sample_transcript():
    """A short meeting transcript used across multiple tests."""
    return """
    Hello everyone, welcome to our weekly student success meeting.
    We noticed students are skipping on Fridays.
    A pancake breakfast was suggested and the team agreed to try it next week.
    John Smith has missed 7 days already. We decided he should speak to the guidance counselor.
    I will look for free childcare resources to share with his family by end of week.
    """


@pytest.fixture
def sample_chunks():
    """Fake ChromaDB chunks — used to test search functions without a real DB."""
    return [
        {
            "text":        "Students are skipping on Fridays due to low motivation.",
            "meeting_id":  1,
            "filename":    "meeting_001.mp3",
            "created_at":  "2024-01-15",
            "chunk_index": 0,
        },
        {
            "text":        "A pancake breakfast was suggested to improve Friday attendance.",
            "meeting_id":  1,
            "filename":    "meeting_001.mp3",
            "created_at":  "2024-01-15",
            "chunk_index": 1,
        },
        {
            "text":        "John Smith has missed 7 days and needs support.",
            "meeting_id":  1,
            "filename":    "meeting_001.mp3",
            "created_at":  "2024-01-15",
            "chunk_index": 2,
        },
    ]


@pytest.fixture
def fake_action_items_json():
    """Fake Groq JSON response for action item agent tests."""
    return '[{"task": "Organize pancake breakfast", "owner": "Sarah", "deadline": "next week", "priority": "high"}]'


@pytest.fixture
def fake_decisions_json():
    """Fake Groq JSON response for decision agent tests."""
    return '[{"decision": "Try pancake breakfast next week", "rationale": "Improve Friday attendance"}]'


@pytest.fixture
def fake_topics_json():
    """Fake Groq JSON response for topic agent tests."""
    return '[{"title": "Student Friday Absenteeism", "description": "Students skipping on Fridays"}]'