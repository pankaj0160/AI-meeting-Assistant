# server/tests/test_hybrid_search.py
# Tests for server/core/rag/hybrid_search.py
#
# We test the BM25 scoring logic and the hybrid_search function.
# For hybrid_search we mock ChromaDB and the embedder so tests
# don't need a running database.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch, MagicMock
from server.core.rag.hybrid_search import _bm25_scores, hybrid_search


# ── Test 6 ────────────────────────────────────────────────────────────────────
def test_bm25_scores_returns_correct_length(sample_chunks):
    """
    _bm25_scores() should return one score per chunk — same length as input.
    This verifies the BM25 function handles our chunk format correctly.
    """
    query  = "pancake breakfast Friday attendance"
    scores = _bm25_scores(query, sample_chunks)

    assert len(scores) == len(sample_chunks), \
        "Should return one score per chunk"
    assert all(isinstance(s, float) for s in scores), \
        "All scores must be floats"
    assert all(0.0 <= s <= 1.0 for s in scores), \
        "Scores must be between 0 and 1 (normalised)"


# ── Test 7 ────────────────────────────────────────────────────────────────────
def test_bm25_scores_ranks_relevant_chunk_higher(sample_chunks):
    """
    The chunk containing 'pancake breakfast' should score highest
    when we query for 'pancake breakfast'.
    This proves BM25 keyword matching actually works.
    """
    query  = "pancake breakfast"
    scores = _bm25_scores(query, sample_chunks)

    # chunk index 1 contains "pancake breakfast" — should be highest score
    pancake_score = scores[1]
    other_scores  = [scores[0], scores[2]]

    assert pancake_score == max(scores), \
        "Chunk mentioning 'pancake breakfast' should rank highest for that query"
    assert pancake_score > max(other_scores), \
        "Relevant chunk must score higher than irrelevant chunks"


# ── Test 8 ────────────────────────────────────────────────────────────────────
def test_hybrid_search_returns_empty_when_no_chunks():
    """
    hybrid_search() should return [] when ChromaDB has no chunks for a meeting.
    This tests the empty-database edge case — no crashes, just empty list.
    """
    # Mock _get_all_chunks_for_meeting to return empty (simulates no data in DB)
    with patch("server.core.rag.hybrid_search._get_all_chunks_for_meeting") as mock_get:
        mock_get.return_value = []   # empty database

        result = hybrid_search(query="What was discussed?", meeting_id=999)

    assert result == [], \
        "Should return empty list when no chunks exist for this meeting"