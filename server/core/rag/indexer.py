# server/core/rag/indexer.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# After a meeting is transcribed, this file indexes the transcript into
# ChromaDB so users can later search it with natural language ("what did
# Alice say about the deadline?").
#
# The process:
#   1. chunk_transcript() splits the text into 300-word pieces
#   2. embed_texts() converts each piece to a 384-float vector
#   3. collection.upsert() stores the vectors + original text in ChromaDB
#
# ChromaDB is a "vector database" — a database optimised for finding the
# most similar vectors to a query vector. Normal databases compare exact
# values. ChromaDB compares mathematical distance between float arrays.
#
# PRODUCTION FIXES IN THIS FILE:
# ───────────────────────────────
# FIX 1: Threading lock on ChromaDB client init
#   The old code had a module-level singleton with no lock.
#   Two simultaneous uploads both see _collection=None and both
#   call chromadb.PersistentClient() at the same time.
#   ChromaDB's persistent client writes a lock file — two simultaneous
#   inits can corrupt this file and crash both workers.
#   Fix: threading.Lock() with double-checked locking (same pattern
#   as embedder.py).
#
# FIX 2: Replaced print() with structured logger calls.
#   print() output is lost in production (not captured by log aggregators).
#   logger.info() / logger.warning() goes to your log files and dashboards.
#
# FIX 3: Added explicit error handling around upsert() with logging.
#   Old code: upsert failure propagates silently as a generic exception.
#   New code: logs chunk count, meeting_id, error type for easy debugging.
#
# FIX 4: delete_meeting_index() now logs what it deletes, not just prints.

import threading
import logging
from pathlib import Path

from server.core.rag.embedder import chunk_transcript, embed_texts

logger = logging.getLogger(__name__)

# ── ChromaDB singleton ────────────────────────────────────────────────────────
# ChromaDB PersistentClient holds an open connection to the chroma_db/ folder.
# We create it once at first use and reuse it for every request.
#
# _CHROMA_PATH: where ChromaDB stores its data files on disk.
# In Docker this maps to the named volume "chroma_data" (see docker-compose.yml).
# In local dev it creates a chroma_db/ folder in your project root.

_CHROMA_PATH   = Path("chroma_db")
_client        = None
_collection    = None
_chroma_lock   = threading.Lock()   # FIX: prevents two threads from init at once


def get_collection():
    """
    Return the ChromaDB collection, creating the client on first call.

    Thread-safe via double-checked locking — same pattern as embedder.py:
      1. Fast check without lock (handles 99% of calls)
      2. Slow path: acquire lock, check again, then create if still None

    The collection "meetings" stores all transcript chunks for all users.
    We scope queries by user_id in the metadata WHERE filter.

    hnsw:space=cosine means ChromaDB uses cosine similarity for search
    (standard for sentence embeddings — better than Euclidean distance
    because it's invariant to text length).
    """
    global _client, _collection

    if _collection is None:
        with _chroma_lock:
            if _collection is None:   # re-check inside the lock
                import chromadb       # lazy import — not needed at startup
                logger.info("Initialising ChromaDB client at %s", _CHROMA_PATH)
                _client = chromadb.PersistentClient(path=str(_CHROMA_PATH))
                _collection = _client.get_or_create_collection(
                    name="meetings",
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(
                    "ChromaDB collection ready (count=%d chunks)",
                    _collection.count(),
                )

    return _collection


def index_meeting(
    meeting_id: int,
    filename:   str,
    transcript: str,
    created_at: str,
    user_id:    int = None,
) -> int:
    """
    Index a meeting transcript into ChromaDB.

    Called after transcription and intelligence are saved to PostgreSQL.
    This enables the RAG chat feature for this meeting.

    Process:
        1. Split transcript into 300-word chunks with 50-word overlap
        2. Embed all chunks in batches of 32 (see embedder.py)
        3. Upsert into ChromaDB with metadata for filtering later

    Why upsert (not insert)?
        If a meeting is re-processed (e.g. user runs /rag/reindex),
        upsert updates existing entries instead of creating duplicates.
        Same chunk ID = overwrite. New chunk ID = insert.

    Chunk ID format: "meeting_{meeting_id}_chunk_{i}"
        e.g. "meeting_42_chunk_0", "meeting_42_chunk_1", ...
        This format lets delete_meeting_index() find all chunks for
        a meeting using a WHERE filter on metadata.

    Args:
        meeting_id : PostgreSQL meeting ID
        filename   : original filename (stored in metadata for display)
        transcript : full meeting transcript text
        created_at : ISO timestamp string (stored in metadata)
        user_id    : the user who owns this meeting (for scoped search)

    Returns:
        number of chunks indexed (0 if transcript was empty or too short)
    """
    chunks = chunk_transcript(transcript)

    if not chunks:
        logger.warning(
            "No chunks generated for meeting %d (transcript length: %d chars) — skipping index.",
            meeting_id, len(transcript),
        )
        return 0

    logger.info(
        "Indexing meeting %d: %d chunks from %d-char transcript",
        meeting_id, len(chunks), len(transcript),
    )

    try:
        embeddings = embed_texts(chunks)

        ids = [f"meeting_{meeting_id}_chunk_{i}" for i in range(len(chunks))]

        metadatas = [
            {
                "meeting_id":  meeting_id,
                "filename":    filename,
                "created_at":  created_at or "",
                "chunk_index": i,
                # FIX: store user_id as 0 (not None) because ChromaDB
                # metadata values must be str, int, float, or bool —
                # None is not allowed and will raise a ValueError.
                "user_id":     user_id if user_id is not None else 0,
            }
            for i in range(len(chunks))
        ]

        collection = get_collection()
        collection.upsert(
            ids        = ids,
            embeddings = embeddings,
            documents  = chunks,
            metadatas  = metadatas,
        )

        logger.info(
            "Indexed %d chunks for meeting %d (user=%s)",
            len(chunks), meeting_id, user_id,
        )
        return len(chunks)

    except Exception as e:
        logger.error(
            "ChromaDB index failed for meeting %d: %s — %s",
            meeting_id, type(e).__name__, e,
            exc_info=True,
        )
        raise


def delete_meeting_index(meeting_id: int) -> int:
    """
    Remove all indexed chunks for a meeting from ChromaDB.

    Called when a meeting is deleted from PostgreSQL, so the
    vector index stays in sync with the database.

    Returns:
        number of chunks deleted
    """
    try:
        collection = get_collection()
        results    = collection.get(
            where={"meeting_id": meeting_id},
            include=[],   # we only need IDs, not documents/embeddings
        )

        if not results or not results["ids"]:
            logger.info("No chunks found in ChromaDB for meeting %d", meeting_id)
            return 0

        collection.delete(ids=results["ids"])
        count = len(results["ids"])
        logger.info("Deleted %d chunks from ChromaDB for meeting %d", count, meeting_id)
        return count

    except Exception as e:
        logger.error(
            "Failed to delete ChromaDB index for meeting %d: %s",
            meeting_id, e, exc_info=True,
        )
        raise


# =============================================================================
# ORPHANED-VECTOR RECONCILIATION
# =============================================================================
#
# WHY THIS EXISTS:
# ─────────────────
# ChromaDB and Postgres are two separate datastores with no foreign-key
# relationship between them. Before DELETE /meetings/{id} existed (see
# main.py), the only way to remove a meeting was deleting its row directly
# in Supabase — which never touched ChromaDB. Those meetings' transcript
# chunks are still sitting in the vector index under their old meeting_id,
# and will keep matching chat queries scoped to that id (including a
# *future* meeting that happens to get the same id after a table
# truncation/reseed). Fixing the DELETE endpoint only prevents *new*
# orphans — it does nothing for ones that already exist. These two
# functions find and remove them.

def find_orphaned_meeting_ids(valid_meeting_ids: set[int]) -> list[int]:
    """
    Return every meeting_id present in ChromaDB that no longer exists in
    Postgres. `valid_meeting_ids` should be the full set of ids currently
    in the `meetings` table (see database.get_all_meeting_ids()).
    """
    collection = get_collection()
    results = collection.get(include=["metadatas"])

    if not results or not results.get("metadatas"):
        return []

    chroma_meeting_ids = {
        m.get("meeting_id") for m in results["metadatas"]
        if m.get("meeting_id") is not None
    }
    orphaned = chroma_meeting_ids - valid_meeting_ids
    return sorted(orphaned)


def backfill_chunk_ownership(meeting_owner_map: dict) -> dict:
    """
    Repair chunks tagged `user_id: 0` ("unknown owner") by looking up their
    real owner via `meeting_owner_map` ({meeting_id: user_id}, see
    database.get_meeting_owner_map()) and correcting the tag in place.

    WHY THIS EXISTS:
    Several indexing call sites historically never passed user_id at all
    (including, ironically, the reindex path meant to fix exactly this —
    see the FIX note on get_all_meetings_for_indexing), so a lot of
    existing chunks are tagged user_id=0 rather than their real owner.
    User-scoped chat filtering treats 0 as "unknown, allow it through" as
    a safety net so this legacy data doesn't just silently stop being
    searchable — but that's a fallback, not a fix. This backfills the
    correct value so those chunks are properly scoped like any other.

    Safe to run repeatedly: a chunk whose meeting_id isn't in
    meeting_owner_map (i.e. an orphan) is left alone — pair this with
    vacuum_orphaned_chunks() to handle genuine orphans separately.
    """
    collection = get_collection()
    results = collection.get(include=["metadatas"])

    if not results or not results.get("ids"):
        return {"chunks_fixed": 0}

    ids_to_update, metadatas_to_update = [], []
    for chunk_id, meta in zip(results["ids"], results["metadatas"]):
        if meta.get("user_id", 0) != 0:
            continue  # already has a real owner tag — nothing to fix
        real_owner = meeting_owner_map.get(meta.get("meeting_id"))
        if not real_owner:
            continue  # orphaned meeting, not this function's job
        fixed_meta = dict(meta)
        fixed_meta["user_id"] = real_owner
        ids_to_update.append(chunk_id)
        metadatas_to_update.append(fixed_meta)

    if ids_to_update:
        collection.update(ids=ids_to_update, metadatas=metadatas_to_update)
        logger.info("Backfilled user_id ownership on %d chunks", len(ids_to_update))

    return {"chunks_fixed": len(ids_to_update)}


def vacuum_orphaned_chunks(valid_meeting_ids: set[int]) -> dict:
    """
    Delete all ChromaDB chunks belonging to meetings that no longer exist
    in Postgres. Safe to run any time — it only ever removes vectors whose
    meeting_id has zero matching row in `meetings`, across any user, so it
    can never affect a meeting anyone can still legitimately access.

    Returns a summary: which meeting_ids were purged and how many chunks
    were deleted in total.
    """
    orphaned_ids = find_orphaned_meeting_ids(valid_meeting_ids)

    total_deleted = 0
    for mid in orphaned_ids:
        total_deleted += delete_meeting_index(mid)

    logger.info(
        "Vacuum complete: removed %d orphaned chunks across %d meeting_ids: %s",
        total_deleted, len(orphaned_ids), orphaned_ids,
    )
    return {
        "orphaned_meeting_ids": orphaned_ids,
        "chunks_deleted":       total_deleted,
    }


def get_collection_stats() -> dict:
    """Return ChromaDB collection stats for the /health endpoint."""
    try:
        collection = get_collection()
        return {
            "status":       "ok",
            "total_chunks": collection.count(),
            "path":         str(_CHROMA_PATH),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}