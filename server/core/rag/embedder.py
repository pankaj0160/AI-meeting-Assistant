# server/core/rag/embedder.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# Converts text into numbers (vectors/embeddings) that ChromaDB can store
# and compare. When you ask "what did Alice say about the budget?", we
# convert that question into a vector, then find transcript chunks whose
# vectors are mathematically close to it — those are the relevant chunks.
#
# The model: "all-MiniLM-L6-v2"
#   - Small, fast sentence embedding model from HuggingFace
#   - Produces 384-dimensional vectors per chunk
#   - Runs on CPU — no GPU needed
#   - Loads in ~2 seconds on first use, then stays in memory
#
# PRODUCTION FIXES IN THIS FILE:
# ───────────────────────────────
# FIX 1: threading.Lock() on model init
#   Two simultaneous uploads both see _model=None → both try to load.
#   Without lock: RAM doubles, can crash on small servers.
#   With lock: only one thread loads, others wait, then reuse.
#
# FIX 2: Batch processing in embed_texts()
#   A 2-hour meeting = ~400 chunks. Encoding all 400 at once
#   spikes RAM to 1.5GB and can crash the Celery worker.
#   Fix: process in batches of 32. Memory stays flat.
#
# FIX 3: min_words filter in chunk_transcript()
#   Chunks like "okay yeah sure" waste index space.
#   Fix: drop chunks shorter than 20 words.
#
# FIX 4: Replaced print() with logger throughout.

import threading
import logging

logger = logging.getLogger(__name__)

# ── Model singleton ───────────────────────────────────────────────────────────
_model      = None
_model_lock = threading.Lock()

EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
EMBED_BATCH_SIZE = 32   # safe on 2GB RAM; increase to 64 on 4GB+


def get_embedding_model():
    """
    Return the SentenceTransformer model, loading it on the very first call.

    Thread-safe via double-checked locking:
      1. Quick check without lock (fast path for 99% of calls)
      2. Only acquire lock if model isn't loaded yet
      3. Check again inside lock — another thread may have loaded it
         while we were waiting
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:   # re-check inside lock
                logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(EMBEDDING_MODEL)
                logger.info(
                    "Embedding model loaded (dims=%d)",
                    _model.get_sentence_embedding_dimension(),
                )
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of text strings into 384-dimensional vectors.

    Why batching?
        Without it: encoding 400 chunks at once loads all intermediate
        activations into RAM simultaneously (~1.5GB peak). Crashes small VMs.
        With batches of 32: peak RAM stays ~200MB regardless of input size.
        Speed difference on CPU: less than 5% — totally worth it.

    Args:
        texts: strings to embed (transcript chunks or a query)

    Returns:
        list of float vectors, same order and length as input
    """
    if not texts:
        return []

    model      = get_embedding_model()
    all_embeds = []
    total      = len(texts)

    for i in range(0, total, EMBED_BATCH_SIZE):
        batch   = texts[i : i + EMBED_BATCH_SIZE]
        vectors = model.encode(batch, show_progress_bar=False)
        all_embeds.extend(vectors.tolist())

    logger.debug("Embedded %d texts in batches of %d", total, EMBED_BATCH_SIZE)
    return all_embeds


def chunk_transcript(
    transcript: str,
    chunk_size: int = 300,   # words per chunk — ~1-2 min of speech
    overlap:    int = 50,    # words shared between neighbouring chunks
    min_words:  int = 20,    # discard chunks shorter than this
) -> list[str]:
    """
    Split a transcript into overlapping word-level chunks for indexing.

    WHY CHUNK?
        ChromaDB searches efficiently over small pieces, not one giant string.
        We split into 300-word chunks and index each separately.

    WHY OVERLAP?
        Without it, a key sentence that falls at a chunk boundary gets split
        across two chunks — neither contains the full sentence.
        With 50-word overlap, neighbours share context — sentences stay intact.

        Example (chunk_size=5, overlap=2):
            words:   [A B C D E F G H I J]
            chunk 0: [A B C D E]
            chunk 1: [D E F G H]   ← shares D,E with chunk 0
            chunk 2: [G H I J]     ← shares G,H with chunk 1

    WHY MIN_WORDS?
        Short trailing chunks like "okay thanks bye" have no search value.
        Their vectors are noisy. We drop them to keep the index clean.

    Returns:
        list of text strings ready for embed_texts()
    """
    words = transcript.split()
    if not words:
        return []

    chunks = []
    start  = 0

    while start < len(words):
        end   = start + chunk_size
        piece = words[start:end]
        if len(piece) >= min_words:
            chunks.append(" ".join(piece))
        start += chunk_size - overlap

    logger.debug(
        "Chunked %d words → %d chunks (size=%d, overlap=%d, min=%d)",
        len(words), len(chunks), chunk_size, overlap, min_words,
    )
    return chunks


def get_model_info() -> dict:
    """Return embedding model metadata for the /health endpoint."""
    return {
        "model":      EMBEDDING_MODEL,
        "loaded":     _model is not None,
        "batch_size": EMBED_BATCH_SIZE,
        "dimensions": 384,
    }