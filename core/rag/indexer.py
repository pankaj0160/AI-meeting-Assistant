# core/rag/indexer.py

import chromadb
from pathlib import Path

from core.rag.embedder import chunk_transcript, embed_texts

# ─── ChromaDB client ──────────────────────────────────────────────────────────
# Persistent storage — data survives restarts.
# Stored in chroma_db/ folder in your project root.

_CHROMA_PATH = Path("chroma_db")
_client = chromadb.PersistentClient(path=str(_CHROMA_PATH))

# One collection holds ALL meetings.
# We filter by meeting_id metadata at query time.
_collection = _client.get_or_create_collection(
    name="meetings",
    metadata={"hnsw:space": "cosine"},  # cosine similarity for text
)


def get_collection():
    """Return the shared ChromaDB collection. Used by retriever and hybrid_search."""
    return _collection


def index_meeting(
    meeting_id: int,
    filename: str,
    transcript: str,
    created_at: str,
) -> int:
    """
    Chunk a transcript and store all chunks in ChromaDB.

    Each chunk is stored with:
        - its embedding vector
        - metadata: meeting_id, filename, created_at, chunk_index
        - a unique document ID: meeting_{id}_chunk_{n}

    Calling this twice for the same meeting safely overwrites
    existing chunks (upsert behaviour).

    Args:
        meeting_id  : SQLite meetings.id
        filename    : original filename (used in citations)
        transcript  : full transcript text
        created_at  : ISO timestamp string from SQLite

    Returns:
        Number of chunks indexed.
    """
    chunks = chunk_transcript(transcript)

    if not chunks:
        print(f"  ⚠ No chunks generated for meeting {meeting_id} — skipping index.")
        return 0

    embeddings = embed_texts(chunks)

    ids = [f"meeting_{meeting_id}_chunk_{i}" for i in range(len(chunks))]

    metadatas = [
        {
            "meeting_id": meeting_id,
            "filename":   filename,
            "created_at": created_at,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    _collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"  ✓ Indexed {len(chunks)} chunks for meeting {meeting_id}")
    return len(chunks)


def delete_meeting_index(meeting_id: int) -> None:
    """
    Remove all chunks for a meeting from ChromaDB.
    Useful if a meeting is deleted from SQLite.
    """
    results = _collection.get(
        where={"meeting_id": meeting_id}
    )

    if results and results["ids"]:
        _collection.delete(ids=results["ids"])
        print(f"  ✓ Deleted {len(results['ids'])} chunks for meeting {meeting_id}")