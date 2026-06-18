# server/tests/test_chat.py
# Tests for server/core/rag/chat.py
#
# We test _build_context() (pure function, no mocking needed)
# and chat_with_meeting() (mock hybrid_search + Groq).

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch, MagicMock
from server.core.rag.chat import _build_context, chat_with_meeting


# ── Test 9 ────────────────────────────────────────────────────────────────────
def test_build_context_formats_chunks_correctly(sample_chunks):
    """
    _build_context() takes a list of chunks and formats them into a numbered
    string for the LLM prompt. Test that it includes chunk text and source info.
    """
    context = _build_context(sample_chunks)

    # Should be a non-empty string
    assert isinstance(context, str)
    assert len(context) > 0

    # Should number the chunks [1], [2], [3]
    assert "[1]" in context
    assert "[2]" in context
    assert "[3]" in context

    # Should include actual chunk text
    assert "pancake breakfast" in context

    # Should include source filename
    assert "meeting_001.mp3" in context


# ── Test 10 ───────────────────────────────────────────────────────────────────
def test_chat_with_meeting_returns_answer_and_sources(sample_chunks):
    """
    chat_with_meeting() should return a dict with 'answer' (str) and
    'sources' (list). We mock hybrid_search and Groq so no real calls happen.
    """
    fake_answer = "Students are skipping because of low motivation on Fridays."

    # Mock 1: hybrid_search returns our fake chunks (no ChromaDB needed)
    # Mock 2: Groq client returns our fake answer (no API call needed)
    with patch("server.core.rag.chat.hybrid_search") as mock_search, \
         patch("server.core.rag.chat.get_groq_client") as mock_groq:

        mock_search.return_value = sample_chunks

        # Build a fake Groq response object that looks like the real one
        fake_response = MagicMock()
        fake_response.choices[0].message.content = fake_answer
        mock_groq.return_value.chat.completions.create.return_value = fake_response

        result = chat_with_meeting(query="Why are students skipping?", meeting_id=1)

    # Check the return structure
    assert isinstance(result, dict),          "Must return a dict"
    assert "answer"  in result,               "Dict must have 'answer' key"
    assert "sources" in result,               "Dict must have 'sources' key"
    assert isinstance(result["answer"], str), "Answer must be a string"
    assert result["answer"] == fake_answer,   "Answer must match mocked Groq response"
    assert isinstance(result["sources"], list),"Sources must be a list"
    assert len(result["sources"]) == 3,       "Should return all 3 mocked chunks"