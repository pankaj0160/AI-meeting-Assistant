# core/rag/embedder.py

from typing import Optional
from sentence_transformers import SentenceTransformer

_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()

    return model.encode(
        texts,
        show_progress_bar=False,
    ).tolist()


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