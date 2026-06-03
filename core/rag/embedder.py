# core/rag/embedder.py

from sentence_transformers import SentenceTransformer

# ─── Model ────────────────────────────────────────────────────────────────────
# Loaded once at import time — never reloaded on every call.
# all-MiniLM-L6-v2 is fast, small, and good enough for meeting transcripts.
# First run downloads ~90MB. After that it's cached locally.

_model = SentenceTransformer("all-MiniLM-L6-v2")


def get_embedding_model() -> SentenceTransformer:
    """Return the shared embedding model instance."""
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of strings into a list of embedding vectors.

    Used by:
        indexer.py  — to embed chunks before storing in ChromaDB
        retriever.py — to embed the user query before searching

    Args:
        texts: list of strings to embed

    Returns:
        list of float vectors, one per input string
    """
    return _model.encode(texts, show_progress_bar=False).tolist()


def chunk_transcript(
    transcript: str,
    chunk_size: int = 300,
    overlap: int = 50,
) -> list[str]:
    """
    Split a transcript into overlapping word-level chunks.

    WHY OVERLAP:
        A sentence like "we decided to hire Alice" might straddle two chunks.
        Overlap ensures it appears fully in at least one chunk so retrieval
        never misses it.

    Args:
        transcript : the full transcript string
        chunk_size : words per chunk (300 words ≈ ~1 min of speech)
        overlap    : words shared between consecutive chunks

    Returns:
        list of chunk strings — minimum 1 chunk even for short transcripts
    """
    words = transcript.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap  # slide forward with overlap

    return chunks