# core/rag/indexer.py

import chromadb
from pathlib import Path

from core.rag.embedder import chunk_transcript, embed_texts

_CHROMA_PATH = Path("chroma_db")
_client = chromadb.PersistentClient(path=str(_CHROMA_PATH))

_collection = _client.get_or_create_collection(
    name="meetings",
    metadata={"hnsw:space": "cosine"},
)


def get_collection():
    return _collection


def index_meeting(
    meeting_id: int,
    filename:   str,
    transcript: str,
    created_at: str,
    user_id:    int = None,       # ← ADDED
) -> int:
    chunks = chunk_transcript(transcript)

    if not chunks:
        print(f"  ⚠ No chunks generated for meeting {meeting_id} — skipping index.")
        return 0

    embeddings = embed_texts(chunks)
    ids = [f"meeting_{meeting_id}_chunk_{i}" for i in range(len(chunks))]

    metadatas = [
        {
            "meeting_id":  meeting_id,
            "filename":    filename,
            "created_at":  created_at,
            "chunk_index": i,
            "user_id":     user_id if user_id is not None else 0,  # ← ADDED
        }
        for i in range(len(chunks))
    ]

    _collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"  ✓ Indexed {len(chunks)} chunks for meeting {meeting_id} (user={user_id})")
    return len(chunks)


def delete_meeting_index(meeting_id: int) -> None:
    results = _collection.get(where={"meeting_id": meeting_id})
    if results and results["ids"]:
        _collection.delete(ids=results["ids"])
        print(f"  ✓ Deleted {len(results['ids'])} chunks for meeting {meeting_id}")