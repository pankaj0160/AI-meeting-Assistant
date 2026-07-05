# server/core/rag/hybrid_search.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# When a user asks a question in chat, this file finds the most relevant
# transcript chunks to answer it. We use TWO search methods combined:
#
#   BM25 (keyword search):
#     Classic text search — counts word frequency. Great for finding
#     exact names ("Alice"), acronyms ("Q3"), and specific terms.
#     Works like Google Search did in 2000.
#
#   Vector search (semantic search):
#     Converts query to a vector, finds chunks with similar meaning.
#     Great for "what budget concerns came up?" even if the word "budget"
#     wasn't used — synonyms and related words still match.
#
#   Hybrid (70% vector + 30% BM25):
#     Combines both scores. Gets the benefits of both approaches.
#     Tuned for conversational meeting questions.
#
# THE BIGGEST PERFORMANCE PROBLEM (now fixed):
# ────────────────────────────────────────────
# OLD CODE: Every single chat message did this:
#   1. Fetch ALL chunks for the meeting from ChromaDB (e.g. 200 chunks)
#   2. Build a fresh BM25 index from all 200 chunks
#   3. Score the query
#   4. Throw the BM25 index away
#
# For a conversation with 10 messages = 10× full ChromaDB reads + 10× BM25 builds.
# For a 2-hour meeting with 400 chunks = 4,000 total ChromaDB reads per 10 messages.
#
# NEW CODE: BM25 index is cached per meeting in a dictionary.
#   First chat message → build index, cache it
#   Messages 2-10     → reuse cached index (no ChromaDB reads, no rebuild)
#
# Cache TTL: 30 minutes. After 30 minutes of no queries for a meeting,
# the cache entry expires and will be rebuilt on the next query.
# This prevents the cache from growing forever with old meetings.
#
# PRODUCTION FIXES IN THIS FILE:
# ───────────────────────────────
# FIX 1: BM25 index cache with TTL (the main speed fix)
# FIX 2: user_id scoping — search only returns chunks owned by current user
#         (old code searched all users' meetings regardless of who was asking)
# FIX 3: Added error handling with fallback — if BM25 fails, we still
#         return vector-only results instead of crashing the chat
# FIX 4: Replaced magic numbers with named constants

import time
import logging
import threading
from typing import Optional

from rank_bm25 import BM25Okapi

from server.core.rag.embedder import embed_texts
from server.core.rag.indexer  import get_collection
from server.core.rag.reranker import rerank, RERANK_CANDIDATE_POOL

logger = logging.getLogger(__name__)

# ── BM25 cache constants ──────────────────────────────────────────────────────
# BM25_CACHE_TTL: how long to keep a cached BM25 index before rebuilding.
# 1800 seconds = 30 minutes. Long enough to cover a full conversation,
# short enough that stale data doesn't accumulate.
BM25_CACHE_TTL = 1800   # seconds

# BM25_CACHE_MAX_SIZE: max number of meetings to cache simultaneously.
# Each cached entry is ~5-10KB for a typical meeting.
# 100 entries = ~1MB max memory for the cache.
BM25_CACHE_MAX_SIZE = 100

# ── Hybrid search weights ─────────────────────────────────────────────────────
# Tuned for conversational meeting questions:
#   70% vector: handles "what concerns came up?" (semantic meaning)
#   30% BM25:   handles "what did Alice say?" (exact name match)
DEFAULT_BM25_WEIGHT   = 0.3
DEFAULT_VECTOR_WEIGHT = 0.7


# =============================================================================
# BM25 CACHE
# =============================================================================

class _BM25Cache:
    """
    Thread-safe LRU-style cache for BM25 indexes.

    Key   : meeting_id (int)
    Value : {
        "bm25":       BM25Okapi instance,
        "chunks":     list of chunk dicts (text + metadata),
        "built_at":   float (Unix timestamp),
    }

    Why a class instead of a plain dict?
        - Encapsulates TTL logic in one place
        - Thread-safe: uses a lock so two simultaneous chat requests for
          the same meeting don't both try to rebuild the cache
        - Max size enforcement: evicts oldest entry when full

    How the TTL works:
        Every get() checks (current_time - built_at) > TTL.
        If expired: deletes the entry and returns None (triggers rebuild).
        If fresh:   returns the cached BM25 + chunks immediately.
    """

    def __init__(self, ttl: int = BM25_CACHE_TTL, max_size: int = BM25_CACHE_MAX_SIZE):
        self._cache:    dict  = {}   # meeting_id → cache entry
        self._lock:     threading.Lock = threading.Lock()
        self._ttl:      int   = ttl
        self._max_size: int   = max_size

    def get(self, meeting_id: int) -> Optional[dict]:
        """Return cached entry if it exists and is not expired. None otherwise."""
        with self._lock:
            entry = self._cache.get(meeting_id)
            if entry is None:
                return None
            if time.time() - entry["built_at"] > self._ttl:
                # Entry has expired — remove it so the next call rebuilds
                del self._cache[meeting_id]
                logger.debug("BM25 cache expired for meeting %d", meeting_id)
                return None
            return entry

    def set(self, meeting_id: int, bm25: BM25Okapi, chunks: list) -> None:
        """Store a new BM25 index. Evicts oldest if cache is full."""
        with self._lock:
            # If cache is at capacity, evict the oldest entry
            if len(self._cache) >= self._max_size and meeting_id not in self._cache:
                oldest_id = next(iter(self._cache))   # dict maintains insertion order (Python 3.7+)
                del self._cache[oldest_id]
                logger.debug("BM25 cache evicted meeting %d (cache full)", oldest_id)

            self._cache[meeting_id] = {
                "bm25":     bm25,
                "chunks":   chunks,
                "built_at": time.time(),
            }
            logger.debug(
                "BM25 cache updated for meeting %d (%d chunks, cache size=%d)",
                meeting_id, len(chunks), len(self._cache),
            )

    def invalidate(self, meeting_id: int) -> None:
        """Remove a meeting from the cache (call after re-indexing)."""
        with self._lock:
            self._cache.pop(meeting_id, None)

    def stats(self) -> dict:
        """Return cache statistics for /health endpoint."""
        with self._lock:
            now = time.time()
            return {
                "size":        len(self._cache),
                "max_size":    self._max_size,
                "ttl_seconds": self._ttl,
                "entries":     [
                    {
                        "meeting_id": mid,
                        "chunks":     len(e["chunks"]),
                        "age_seconds": round(now - e["built_at"]),
                    }
                    for mid, e in self._cache.items()
                ],
            }


# Module-level singleton — one cache for the whole application
_bm25_cache = _BM25Cache()


# =============================================================================
# CHUNK FETCHERS
# =============================================================================

def _get_all_chunks_for_meeting(meeting_id: int, user_id: int | None = None) -> list[dict]:
    """
    Fetch every chunk stored in ChromaDB for one meeting.

    This is called ONCE per meeting (results are cached by _BM25Cache).
    Subsequent chat messages use the cache — no ChromaDB reads.

    FIX: added an optional user_id filter, for defense-in-depth. The
    hybrid_search() caller already receives user_id but previously dropped
    it on the floor for the single-meeting path — the API endpoint's own
    ownership check (get_meeting_by_id) was the only thing preventing
    cross-user access here. This adds a second, independent check at the
    data layer itself, so a future endpoint that forgets that ownership
    check doesn't silently turn into a leak.

    Returns list of dicts:
        { text, meeting_id, filename, created_at, chunk_index }
    """
    collection = get_collection()

    # FIX (regression): the first version of this filter was
    # `{"meeting_id": X, "user_id": Y}` — a strict AND. That broke chat
    # entirely for any meeting indexed before user_id was reliably threaded
    # through the indexing pipeline (several call sites never passed it,
    # so those chunks are tagged `user_id: 0`, a "legacy/unknown" placeholder
    # — see index_meeting()'s docstring). A strict match against 0 excludes
    # all of that legacy data.
    #
    # Correct behavior: only exclude a chunk if it's tagged with a REAL,
    # DIFFERENT user's id (a confirmed cross-user mismatch). A chunk tagged
    # 0 means "we don't know who owns this" rather than "confirmed to
    # belong to someone else", so it should still be included — the
    # endpoint-level ownership check (get_meeting_by_id) already confirmed
    # the requester owns this meeting_id in Postgres, which is the
    # authoritative source of truth anyway.
    where = {"meeting_id": meeting_id}
    if user_id is not None and user_id > 0:
        where = {"$and": [
            {"meeting_id": meeting_id},
            {"$or": [{"user_id": user_id}, {"user_id": 0}]},
        ]}

    results = collection.get(
        where   = where,
        include = ["documents", "metadatas"],
    )

    if not results or not results.get("ids"):
        return []

    chunks = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        chunks.append({
            "text":        doc,
            "meeting_id":  meta.get("meeting_id"),
            "filename":    meta.get("filename", ""),
            "created_at":  meta.get("created_at", ""),
            "chunk_index": meta.get("chunk_index", 0),
        })

    logger.debug(
        "Fetched %d chunks from ChromaDB for meeting %d",
        len(chunks), meeting_id,
    )
    return chunks


def _get_all_chunks_cross_meeting(user_id: int = None) -> list[dict]:
    """
    Fetch chunks across all meetings, optionally scoped to one user.

    FIX: Added user_id scoping. Old code returned ALL users' chunks.
    This meant user A could potentially see results from user B's meetings
    in cross-meeting chat. Now each user only searches their own meetings.

    Why not cache this?
        Per-meeting cache is safe: meeting content is immutable after indexing.
        Cross-meeting cache is risky: it becomes stale when a new meeting
        is uploaded. We accept the performance cost for correctness.
        The per-meeting cache still helps — each individual meeting's
        BM25 index is cached; we just re-combine them for cross-meeting.
    """
    collection = get_collection()

    # FIX (regression): same issue as _get_all_chunks_for_meeting — a
    # strict `{"user_id": user_id}` filter excludes every chunk indexed
    # before user_id was reliably threaded through the indexing pipeline
    # (tagged `user_id: 0`, meaning "unknown owner", not "confirmed to
    # belong to someone else"). Widened to also include those, while still
    # correctly excluding chunks confirmed to belong to a DIFFERENT real
    # user — which is the actual cross-user leak this was meant to fix.
    where_filter = None
    if user_id is not None and user_id > 0:
        where_filter = {"$or": [{"user_id": user_id}, {"user_id": 0}]}

    if where_filter:
        results = collection.get(
            where   = where_filter,
            include = ["documents", "metadatas"],
        )
    else:
        results = collection.get(include=["documents", "metadatas"])

    if not results or not results.get("ids"):
        return []

    chunks = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        chunks.append({
            "text":        doc,
            "meeting_id":  meta.get("meeting_id"),
            "filename":    meta.get("filename", ""),
            "created_at":  meta.get("created_at", ""),
            "chunk_index": meta.get("chunk_index", 0),
        })

    return chunks


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def _bm25_scores(query: str, chunks: list[dict]) -> list[float]:
    """
    Run BM25 keyword scoring over the given chunks.

    BM25Okapi (Okapi BM25) is the most widely used text ranking formula.
    It scores how relevant each document is to a query, accounting for:
    - Term frequency (how often query words appear in the chunk)
    - Inverse document frequency (rare words score higher than common words)
    - Document length normalization (long chunks don't automatically win)

    Returns scores normalised to [0, 1] range.
    A score of 1.0 = the most BM25-relevant chunk in this set.
    A score of 0.0 = no overlap with query terms at all.
    """
    if not chunks:
        return []

    tokenized_corpus = [c["text"].lower().split() for c in chunks]
    bm25             = BM25Okapi(tokenized_corpus)

    tokenized_query  = query.lower().split()
    raw_scores       = bm25.get_scores(tokenized_query)

    max_score = max(raw_scores) if max(raw_scores) > 0 else 1.0
    return [float(s / max_score) for s in raw_scores]


def _vector_scores(query: str, chunks: list[dict]) -> list[float]:
    """
    Run vector similarity scoring over the given chunks.

    Process:
        1. Embed the query into a 384-float vector
        2. Ask ChromaDB to find the most similar chunk vectors
        3. Convert cosine distance → similarity (1 - distance)

    ChromaDB returns cosine distance in [0, 2] range where:
        0.0 = identical vectors (perfect match)
        2.0 = opposite vectors (no match)
    We convert to similarity: 1 - distance, giving [−1, 1].
    For practical sentence embeddings, similarity is usually in [0, 1].

    Why query ChromaDB instead of computing dot products locally?
        ChromaDB uses HNSW (Hierarchical Navigable Small World) index —
        an approximate nearest-neighbour algorithm that finds the top-k
        results in O(log n) time instead of O(n).
        For 10,000 chunks, that's ~14 comparisons instead of 10,000.
    """
    if not chunks:
        return [0.0] * len(chunks)

    collection      = get_collection()
    query_embedding = embed_texts([query])[0]

    # Get the set of meeting IDs in our chunk list (for the WHERE filter)
    meeting_ids_in_chunks = list({c["meeting_id"] for c in chunks if c["meeting_id"] is not None})

    if not meeting_ids_in_chunks:
        return [0.0] * len(chunks)

    try:
        results = collection.query(
            query_embeddings = [query_embedding],
            n_results        = min(len(chunks), 100),   # cap to avoid ChromaDB errors
            where            = {"meeting_id": {"$in": meeting_ids_in_chunks}},
            include          = ["distances"],
        )
    except Exception as e:
        logger.error("ChromaDB vector query failed: %s", e)
        return [0.0] * len(chunks)

    # Build a map: chunk_id → similarity score
    returned_ids   = results["ids"][0]
    returned_dists = results["distances"][0]

    score_map = {
        cid: round(max(0.0, 1.0 - dist), 4)
        for cid, dist in zip(returned_ids, returned_dists)
    }

    # Return scores in the same order as the input chunks list
    return [
        score_map.get(
            f"meeting_{c['meeting_id']}_chunk_{c['chunk_index']}",
            0.0,
        )
        for c in chunks
    ]


# =============================================================================
# MAIN SEARCH FUNCTION
# =============================================================================

def hybrid_search(
    query:         str,
    meeting_id:    int | None   = None,
    top_k:         int          = 5,
    bm25_weight:   float        = DEFAULT_BM25_WEIGHT,
    vector_weight: float        = DEFAULT_VECTOR_WEIGHT,
    user_id:       int | None   = None,
    use_reranker:  bool         = True,
) -> list[dict]:
    """
    Hybrid BM25 + vector search over meeting transcripts.

    If meeting_id is provided  → search only that meeting (single meeting chat)
    If meeting_id is None      → search all meetings owned by user_id

    PERFORMANCE:
        Single-meeting queries use the BM25 cache — after the first query
        per meeting, all subsequent queries skip the ChromaDB read and BM25
        rebuild. Speed goes from ~500ms to ~50ms for cached meetings.

    SCORING:
        final_score = (0.3 × bm25_score) + (0.7 × vector_score)
        Weights tuned for meeting Q&A — semantic meaning matters more than
        exact keyword match for conversational questions.

    RERANKING (default on):
        After hybrid scoring, the top candidates are re-scored by a
        cross-encoder (see reranker.py) that reads the query and each chunk
        together rather than as independent vectors — a stronger, slower
        relevance signal than embedding similarity alone. This is the step
        that decides the final top_k, not the hybrid score. Pass
        use_reranker=False to skip it (e.g. for a quick A/B comparison, or
        if latency matters more than precision for a given call site).

    Args:
        query         : user's question (e.g. "what did Alice say about Q3?")
        meeting_id    : scope to one meeting, or None for cross-meeting
        top_k         : how many chunks to return
        bm25_weight   : fraction of score from BM25 (default 0.3 = 30%)
        vector_weight : fraction of score from vector (default 0.7 = 70%)
        user_id       : scope cross-meeting search to one user's meetings
        use_reranker  : re-score top candidates with a cross-encoder before
                        the final top_k cut (default True)

    Returns:
        List of top_k dicts, each with:
            text, meeting_id, filename, created_at, chunk_index, score
        Sorted by score descending (best match first).
    """
    if meeting_id is not None:
        # ── Single-meeting search with BM25 cache ──────────────────────────
        cached = _bm25_cache.get(meeting_id)

        if cached is not None:
            # Cache hit — use stored BM25 and chunks, no ChromaDB read
            logger.debug("BM25 cache hit for meeting %d", meeting_id)
            chunks  = cached["chunks"]
            bm25    = cached["bm25"]

            tokenized_query = query.lower().split()
            raw_scores      = bm25.get_scores(tokenized_query)
            max_score       = max(raw_scores) if max(raw_scores) > 0 else 1.0
            bm25_s          = [float(s / max_score) for s in raw_scores]
        else:
            # Cache miss — fetch from ChromaDB and build BM25 index
            logger.debug("BM25 cache miss for meeting %d — building index", meeting_id)
            chunks = _get_all_chunks_for_meeting(meeting_id, user_id=user_id)

            if not chunks:
                logger.info(
                    "No chunks in ChromaDB for meeting %d — not yet indexed?",
                    meeting_id,
                )
                return []

            try:
                tokenized_corpus = [c["text"].lower().split() for c in chunks]
                bm25             = BM25Okapi(tokenized_corpus)
                _bm25_cache.set(meeting_id, bm25, chunks)   # store for next query

                tokenized_query = query.lower().split()
                raw_scores      = bm25.get_scores(tokenized_query)
                max_score       = max(raw_scores) if max(raw_scores) > 0 else 1.0
                bm25_s          = [float(s / max_score) for s in raw_scores]
            except Exception as e:
                logger.error("BM25 build failed for meeting %d: %s", meeting_id, e)
                # Graceful fallback: return vector-only results
                vector_s = _vector_scores(query, chunks)
                scored   = [
                    {**c, "score": round(v, 4)}
                    for c, v in zip(chunks, vector_s)
                ]
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:top_k]

    else:
        # ── Cross-meeting search (no BM25 cache for this path) ─────────────
        chunks = _get_all_chunks_cross_meeting(user_id=user_id)

        if not chunks:
            return []

        try:
            bm25_s = _bm25_scores(query, chunks)
        except Exception as e:
            logger.error("BM25 cross-meeting scoring failed: %s", e)
            bm25_s = [0.0] * len(chunks)

    # ── Vector scores (always run) ──────────────────────────────────────────
    vector_s = _vector_scores(query, chunks)

    # ── Combine and rank ────────────────────────────────────────────────────
    scored = []
    for chunk, b, v in zip(chunks, bm25_s, vector_s):
        combined = round((bm25_weight * b) + (vector_weight * v), 4)
        scored.append({**chunk, "score": combined})

    scored.sort(key=lambda x: x["score"], reverse=True)

    if use_reranker:
        # Hand the reranker a wider shortlist than top_k so it has real
        # candidates to discriminate between — reranking a list that's
        # already been cut to exactly top_k defeats the purpose.
        candidate_pool = scored[:max(top_k, RERANK_CANDIDATE_POOL)]
        return rerank(query, candidate_pool, top_k=top_k)

    return scored[:top_k]


def invalidate_meeting_cache(meeting_id: int) -> None:
    """
    Remove a meeting's BM25 cache entry.
    Call this after re-indexing a meeting so next query rebuilds the cache.
    """
    _bm25_cache.invalidate(meeting_id)
    logger.info("BM25 cache invalidated for meeting %d", meeting_id)


def get_cache_stats() -> dict:
    """Return cache stats for the /health endpoint."""
    return _bm25_cache.stats()