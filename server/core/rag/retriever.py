# core/rag/retriever.py

from server.core.rag.embedder import embed_texts
from server.core.rag.indexer import get_collection


def retrieve_from_meeting(
    query: str,
    meeting_id: int,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve the most relevant transcript chunks for a single meeting.

    Filters ChromaDB strictly by meeting_id so results never bleed
    across meetings.

    Args:
        query      : the user's question
        meeting_id : SQLite meetings.id — search is scoped to this meeting only
        top_k      : number of chunks to return (default 5)

    Returns:
        List of dicts, each containing:
        {
            "text"       : str,   # the chunk text
            "meeting_id" : int,
            "filename"   : str,
            "created_at" : str,
            "chunk_index": int,
            "score"      : float, # cosine distance — lower is more similar
        }
        Ordered by relevance (best first).
    """
    collection = get_collection()

    query_embedding = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"meeting_id": meeting_id},  # ← scoped to this meeting only
        include=["documents", "metadatas", "distances"],
    )

    # ChromaDB returns nested lists — unwrap them
    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunks = []
    for doc, meta, dist in zip(docs, metadatas, distances):
        chunks.append({
            "text":        doc,
            "meeting_id":  meta["meeting_id"],
            "filename":    meta["filename"],
            "created_at":  meta["created_at"],
            "chunk_index": meta["chunk_index"],
            "score":       round(dist, 4),
        })

    return chunks