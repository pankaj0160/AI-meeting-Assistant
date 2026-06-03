# core/rag/hybrid_search.py

from rank_bm25 import BM25Okapi

from core.rag.embedder import embed_texts
from core.rag.indexer import get_collection


def _get_all_chunks_for_meeting(meeting_id: int) -> list[dict]:
    """
    Fetch every chunk stored in ChromaDB for a given meeting.
    Used as the BM25 corpus — BM25 needs all documents upfront.
    """
    collection = get_collection()

    results = collection.get(
        where={"meeting_id": meeting_id},
        include=["documents", "metadatas"],
    )

    if not results or not results["ids"]:
        return []

    chunks = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        chunks.append({
            "text":        doc,
            "meeting_id":  meta["meeting_id"],
            "filename":    meta["filename"],
            "created_at":  meta["created_at"],
            "chunk_index": meta["chunk_index"],
        })

    return chunks


def _get_all_chunks_cross_meeting() -> list[dict]:
    """
    Fetch every chunk across ALL meetings.
    Used for cross-meeting hybrid search.
    """
    collection = get_collection()

    results = collection.get(
        include=["documents", "metadatas"],
    )

    if not results or not results["ids"]:
        return []

    chunks = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        chunks.append({
            "text":        doc,
            "meeting_id":  meta["meeting_id"],
            "filename":    meta["filename"],
            "created_at":  meta["created_at"],
            "chunk_index": meta["chunk_index"],
        })

    return chunks


def _bm25_scores(query: str, chunks: list[dict]) -> list[float]:
    """
    Run BM25 over a list of chunks and return a score per chunk.
    Scores are normalised to [0, 1] range.
    """
    tokenized_corpus = [c["text"].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split()
    raw_scores = bm25.get_scores(tokenized_query)

    max_score = max(raw_scores) if max(raw_scores) > 0 else 1.0
    return [float(s / max_score) for s in raw_scores]


def _vector_scores(query: str, chunks: list[dict]) -> list[float]:
    """
    Run vector similarity over a list of chunks and return a score per chunk.
    ChromaDB returns cosine distance — we convert to similarity: 1 - distance.
    Scores are in [0, 1] range — higher is more similar.
    """
    collection = get_collection()

    query_embedding = embed_texts([query])[0]

    # Build the id filter — only score the chunks we were given
    chunk_ids = [
        f"meeting_{c['meeting_id']}_chunk_{c['chunk_index']}"
        for c in chunks
    ]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=len(chunks),
        where={"meeting_id": {"$in": list({c["meeting_id"] for c in chunks})}},
        include=["distances"],
    )

    # Build a lookup: chunk_id → similarity score
    returned_ids    = results["ids"][0]
    returned_dists  = results["distances"][0]

    score_map = {
        cid: round(1 - dist, 4)
        for cid, dist in zip(returned_ids, returned_dists)
    }

    # Return scores in the same order as input chunks
    return [
        score_map.get(
            f"meeting_{c['meeting_id']}_chunk_{c['chunk_index']}", 0.0
        )
        for c in chunks
    ]


def hybrid_search(
    query: str,
    meeting_id: int | None = None,
    top_k: int = 5,
    bm25_weight: float = 0.3,
    vector_weight: float = 0.7,
) -> list[dict]:
    """
    Hybrid BM25 + vector search.

    If meeting_id is provided  → search only that meeting (single meeting chat)
    If meeting_id is None      → search across ALL meetings (cross-meeting search)

    Scoring:
        final_score = (bm25_weight * bm25_score) + (vector_weight * vector_score)
        Default weights: 30% BM25, 70% vector — tuned for conversational queries.

    Args:
        query         : user question
        meeting_id    : scope to one meeting, or None for all meetings
        top_k         : number of results to return
        bm25_weight   : weight for BM25 score component
        vector_weight : weight for vector score component

    Returns:
        List of top_k chunk dicts with a "score" field added, best first.
    """
    if meeting_id is not None:
        chunks = _get_all_chunks_for_meeting(meeting_id)
    else:
        chunks = _get_all_chunks_cross_meeting()

    if not chunks:
        return []

    bm25_s   = _bm25_scores(query, chunks)
    vector_s = _vector_scores(query, chunks)

    # Combine scores
    scored = []
    for chunk, b, v in zip(chunks, bm25_s, vector_s):
        combined = round((bm25_weight * b) + (vector_weight * v), 4)
        scored.append({**chunk, "score": combined})

    # Sort best first, return top_k
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]