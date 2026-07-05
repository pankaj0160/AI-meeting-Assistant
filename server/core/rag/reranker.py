# server/core/rag/reranker.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# Takes the top candidates from hybrid_search (BM25 + vector fusion) and
# re-scores them with a cross-encoder — a model that looks at the query and
# a chunk TOGETHER (not as separate vectors) and outputs a single relevance
# score. This is slower per-pair than vector search, which is exactly why
# it's a second pass over a small candidate set (~20) instead of the whole
# transcript.
#
# WHY THIS HELPS (and why hybrid search alone isn't enough):
# ─────────────────────────────────────────────────────────
# Vector search compares the QUERY's embedding to each CHUNK's embedding
# independently — the two never interact. Two chunks can end up with very
# similar vector scores even when only one of them actually answers the
# question, because "similar meaning" and "actually answers this" aren't
# the same thing. A cross-encoder reads the query and chunk as a single
# input and asks the model directly "does this text answer this question",
# which is a strictly harder and more accurate signal — it's just too slow
# to run over hundreds of chunks, which is why it only sees the shortlist.
#
# In practice: BM25+vector gets you a good candidate pool fast. The
# reranker decides which 5 of those ~20 candidates actually deserve to be
# in the LLM's context window. This is usually the single biggest quality
# lever in a RAG pipeline, ahead of further fusion-weight tuning.
#
# MODEL CHOICE:
#   cross-encoder/ms-marco-MiniLM-L-6-v2
#   - Same MiniLM family as the embedding model already in use (embedder.py),
#     so no new model family / license / download surprise for the team.
#   - Trained specifically for query-passage relevance ranking (MS MARCO).
#   - ~80MB, runs on CPU in well under 100ms for a 20-candidate shortlist.
#
# THREADING / LOADING:
#   Mirrors embedder.py's double-checked-locking singleton exactly — same
#   reasoning: two simultaneous requests shouldn't both load a fresh copy
#   of the model into memory.

import logging
import threading

logger = logging.getLogger(__name__)

_model      = None
_model_lock = threading.Lock()

RERANK_MODEL          = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_CANDIDATE_POOL = 20   # how many hybrid_search results to re-score
DEFAULT_RERANK_TOP_K  = 5    # how many to keep after reranking


def get_reranker_model():
    """
    Return the CrossEncoder model, loading it on the very first call.
    Thread-safe via double-checked locking (see embedder.py for the same
    pattern with reasoning).
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:   # re-check inside lock
                logger.info("Loading reranker model: %s", RERANK_MODEL)
                from sentence_transformers import CrossEncoder
                _model = CrossEncoder(RERANK_MODEL)
                logger.info("Reranker model loaded")
    return _model


def rerank(
    query:   str,
    chunks:  list[dict],
    top_k:   int = DEFAULT_RERANK_TOP_K,
) -> list[dict]:
    """
    Re-score `chunks` against `query` with the cross-encoder and return the
    best `top_k`, sorted best-first.

    Each input chunk dict must have a "text" key (same shape hybrid_search
    already returns). The original hybrid "score" field is preserved as
    "hybrid_score" so callers/logging can see both numbers if useful; the
    "score" field is overwritten with the reranker's score so downstream
    code that already reads chunk["score"] keeps working unmodified.

    Fails open: if the reranker can't load or errors out (e.g. first-run
    model download blocked, out of memory), logs the error and falls back
    to the original hybrid-search ordering rather than breaking chat.
    """
    if not chunks:
        return []

    if len(chunks) <= top_k:
        # Nothing to actually rerank — already at or under the target size.
        return chunks

    try:
        model = get_reranker_model()
        pairs = [[query, c["text"]] for c in chunks]
        scores = model.predict(pairs)
    except Exception as e:
        logger.error("Reranking failed, falling back to hybrid order: %s", e)
        return chunks[:top_k]

    reranked = []
    for chunk, rerank_score in zip(chunks, scores):
        reranked.append({
            **chunk,
            "hybrid_score": chunk.get("score"),
            "score":        round(float(rerank_score), 4),
        })

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked[:top_k]