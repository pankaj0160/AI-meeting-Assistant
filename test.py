# Test the full pipeline (chunker → embedder → ChromaDB)
from core.rag.vector_store import index_meeting

success = index_meeting(
    meeting_id=999,
    transcript="Alice: We decided to move deployment to AWS. Bob: Agreed. The deadline is Friday. " * 50,
    meeting_filename="test_meeting.mp4",
    meeting_date="2025-01-01T10:00:00",
)
print(f"Indexed: {success}")  # should print True

# Then search it
from core.rag.vector_store import get_vector_store
from core.rag.embedder import get_embedder

store    = get_vector_store()
embedder = get_embedder()

query_vec = embedder.embed_query("AWS deployment decisions")
results   = store.search(query_vec, top_k=3)

for r in results:
    print(f"similarity={r['similarity']} | {r['text'][:80]}...")