# core/rag/chat.py
import os
import time

from groq import Groq
from dotenv import load_dotenv
from langfuse import Langfuse

from server.core.rag.hybrid_search import hybrid_search

load_dotenv()

_client = None
_langfuse = Langfuse()   # ← shared Langfuse client

MODEL = "llama-3.3-70b-versatile"


def get_groq_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def _build_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a numbered context block for the prompt.
    Each chunk shows its source filename so the model can cite it.
    """
    if not chunks:
        return "No relevant context found."

    lines = []
    for i, chunk in enumerate(chunks, 1):
        lines.append(
            f"[{i}] (Source: {chunk['filename']}, Meeting ID: {chunk['meeting_id']})\n"
            f"{chunk['text']}"
        )
    return "\n\n".join(lines)


def chat_with_meeting(
    query: str,
    meeting_id: int,
    top_k: int = 5,
) -> dict:
    """
    Answer a question grounded in a single meeting's transcript.
    Now traced with Langfuse — records retrieval + LLM steps separately.
    """
    # ── Create a trace for this entire user query ────────────────────
    # A trace groups everything that happens for one user action.
    trace = _langfuse.trace(
        name="chat_with_meeting",
        input={"query": query, "meeting_id": meeting_id},
        metadata={"top_k": top_k},
    )

    # ── Step 1: Retrieval span ───────────────────────────────────────
    # We record the hybrid search as its own span so we can see
    # how long retrieval takes vs LLM generation.
    retrieval_span = trace.span(
        name="hybrid_search",
        input={"query": query, "meeting_id": meeting_id, "top_k": top_k},
    )
    chunks = hybrid_search(query=query, meeting_id=meeting_id, top_k=top_k)
    retrieval_span.end(
        output={"num_chunks": len(chunks)},
        metadata={"chunk_ids": [c.get("id") for c in chunks]},
    )

    context = _build_context(chunks)

    # ── Step 2: LLM generation span ─────────────────────────────────
    system = """You are a helpful meeting assistant.
You answer questions strictly based on the meeting transcript context provided.

Rules:
- Only use information from the provided context
- If the answer is not in the context, say "I could not find that in this meeting."
- Be concise and direct
- Do not make up information
- You may quote short phrases from the transcript"""

    user_message = f"""MEETING CONTEXT:
{context}

QUESTION:
{query}"""

    generation = trace.generation(
        name="rag_llm_call",
        model=MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
    )

    start_time = time.time()
    client = get_groq_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()
    elapsed = time.time() - start_time

    generation.end(
        output=answer,
        usage={
            "input":  response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
            "total":  response.usage.total_tokens,
        },
        metadata={"latency_seconds": round(elapsed, 3)},
    )

    # Mark the full trace as complete
    trace.update(output={"answer": answer})

    return {
        "answer":  answer,
        "sources": chunks,
    }


def chat_across_meetings(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Answer a question by searching across ALL meetings.
    Now traced with Langfuse.
    """
    trace = _langfuse.trace(
        name="chat_across_meetings",
        input={"query": query},
        metadata={"top_k": top_k},
    )

    # Retrieval span
    retrieval_span = trace.span(
        name="hybrid_search_all",
        input={"query": query, "meeting_id": None, "top_k": top_k},
    )
    chunks = hybrid_search(query=query, meeting_id=None, top_k=top_k)
    retrieval_span.end(output={"num_chunks": len(chunks)})

    context = _build_context(chunks)

    system = """You are a helpful meeting assistant with access to multiple meeting transcripts.
You answer questions strictly based on the meeting context provided.

Rules:
- Only use information from the provided context
- Always mention which meeting the information came from
- If the answer is not in the context, say "I could not find that across any meeting."
- Be concise and direct
- Do not make up information"""

    user_message = f"""MEETINGS CONTEXT:
{context}

QUESTION:
{query}"""

    generation = trace.generation(
        name="rag_llm_call_all",
        model=MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
    )

    start_time = time.time()
    client = get_groq_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()
    elapsed = time.time() - start_time

    generation.end(
        output=answer,
        usage={
            "input":  response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
            "total":  response.usage.total_tokens,
        },
        metadata={"latency_seconds": round(elapsed, 3)},
    )

    trace.update(output={"answer": answer})

    return {
        "answer":  answer,
        "sources": chunks,
    }