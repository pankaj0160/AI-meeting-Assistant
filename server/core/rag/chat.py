# core/rag/chat.py
#
# What changed from the original:
#   - Added stream_chat_with_meeting() — a generator that yields SSE-formatted tokens
#   - Added stream_chat_across_meetings() — same but across all meetings
#   - The original chat_with_meeting() and chat_across_meetings() are 100% UNCHANGED
#     Your existing /chat/meeting and /chat/search endpoints keep working exactly as before.
#
# How streaming works (plain English):
#   Normal call:  Groq generates the full answer → sends it all at once → you wait 3-5 seconds
#   Streaming:    Groq sends each word/token as it generates it → you see text appearing live
#
#   The secret is stream=True in the Groq call. Instead of one response object,
#   you get a generator. Each item in that generator is a small chunk of text.
#   We yield each chunk formatted as an SSE event (a simple text protocol browsers understand).

import os
import time

from groq import Groq
from dotenv import load_dotenv
from langfuse import Langfuse
from typing import Generator

from server.core.rag.hybrid_search import hybrid_search

load_dotenv()

_client = None
_langfuse = Langfuse()   # shared Langfuse client

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


# =============================================================================
# ORIGINAL FUNCTIONS — COMPLETELY UNCHANGED
# Your existing /chat/meeting and /chat/search endpoints use these.
# Do not modify them.
# =============================================================================

def chat_with_meeting(
    query: str,
    meeting_id: int,
    top_k: int = 5,
) -> dict:
    """
    Answer a question grounded in a single meeting's transcript.
    Traced with Langfuse — records retrieval + LLM steps separately.
    """
    trace = _langfuse.trace(
        name="chat_with_meeting",
        input={"query": query, "meeting_id": meeting_id},
        metadata={"top_k": top_k},
    )

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
    Traced with Langfuse.
    """
    trace = _langfuse.trace(
        name="chat_across_meetings",
        input={"query": query},
        metadata={"top_k": top_k},
    )

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


# =============================================================================
# NEW: STREAMING FUNCTIONS
# These are new additions — they don't touch anything above.
# =============================================================================

def stream_chat_with_meeting(
    query: str,
    meeting_id: int,
    top_k: int = 5,
) -> Generator[str, None, None]:
    """
    Stream an answer about a single meeting, token by token.

    HOW STREAMING WORKS:
        1. We run hybrid_search exactly like before — that part isn't streamed
           (retrieval is fast, ~100ms, no need to stream it)
        2. We call Groq with stream=True — this returns a generator instead of
           a complete response object
        3. We iterate over that generator — each item is a small chunk of text
           (usually 1-4 tokens, roughly 1-4 words)
        4. We yield each chunk formatted as an SSE event (see below)

    WHAT IS SSE (Server-Sent Events)?
        SSE is a simple text protocol for one-way streaming from server to browser.
        Each event looks like:
            data: {"token": "Hello"}\n\n
        The double newline (\n\n) is the event separator — the browser knows
        one event ended and the next begins.
        Browsers have a built-in EventSource API that reads these automatically.

    WHAT IS A GENERATOR?
        A Python generator is a function that uses "yield" instead of "return".
        Instead of computing everything and returning it all at once, it produces
        values one at a time on demand. The caller gets each value as it arrives.
        This is what makes streaming possible — we yield tokens as Groq sends them.

    Args:
        query      : the user's question
        meeting_id : which meeting to search in
        top_k      : how many transcript chunks to retrieve

    Yields:
        SSE-formatted strings:  'data: {"token": "Hello"}\n\n'
        Final event:            'data: {"done": true, "sources": [...]}\n\n'
    """
    import json

    # ── Step 1: Retrieval (not streamed — fast enough) ───────────────────────
    # Same hybrid_search call as the non-streaming version.
    # We get the context chunks before starting the LLM call.
    chunks = hybrid_search(query=query, meeting_id=meeting_id, top_k=top_k)
    context = _build_context(chunks)

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

    # ── Step 2: Streaming LLM call ───────────────────────────────────────────
    # The ONLY difference from the non-streaming version is stream=True.
    # Without stream=True:  response = the full completion object (arrives after ~3s)
    # With stream=True:     response = a generator that yields chunks as they're generated
    client = get_groq_client()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
        stream=True,   # ← This is the only change from the non-streaming version
    )

    # ── Step 3: Yield each token as an SSE event ─────────────────────────────
    # The stream object is a generator. Each iteration gives us one chunk.
    # chunk.choices[0].delta.content is the new text in this chunk.
    # It can be None for the first/last chunk (metadata-only chunks), so we check.
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token is not None:
            # Format as SSE: "data: <json>\n\n"
            # The double \n\n is REQUIRED — it's the SSE event boundary.
            # Without it, the browser won't recognize separate events.
            yield f"data: {json.dumps({'token': token})}\n\n"

    # ── Step 4: Send the "done" event with sources ────────────────────────────
    # After all tokens are sent, we send one final event that tells the client:
    # "streaming is complete, here are the source chunks used."
    # The client can use this to show citations.
    #
    # We serialize sources carefully — chunk dicts may have int keys (meeting_id)
    # that need to be JSON-serializable.
    safe_sources = [
        {
            "text":        c.get("text", ""),
            "meeting_id":  c.get("meeting_id"),
            "filename":    c.get("filename", ""),
            "chunk_index": c.get("chunk_index"),
            "score":       c.get("score"),
        }
        for c in chunks
    ]
    yield f"data: {json.dumps({'done': True, 'sources': safe_sources})}\n\n"


def stream_chat_across_meetings(
    query: str,
    top_k: int = 5,
) -> Generator[str, None, None]:
    """
    Stream an answer by searching across ALL meetings, token by token.
    Same pattern as stream_chat_with_meeting but without meeting_id filter.

    Yields:
        SSE-formatted strings:  'data: {"token": "Hello"}\n\n'
        Final event:            'data: {"done": true, "sources": [...]}\n\n'
    """
    import json

    # Search across all meetings (meeting_id=None means no filter in hybrid_search)
    chunks = hybrid_search(query=query, meeting_id=None, top_k=top_k)
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

    client = get_groq_client()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
        stream=True,
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token is not None:
            yield f"data: {json.dumps({'token': token})}\n\n"

    safe_sources = [
        {
            "text":        c.get("text", ""),
            "meeting_id":  c.get("meeting_id"),
            "filename":    c.get("filename", ""),
            "chunk_index": c.get("chunk_index"),
            "score":       c.get("score"),
        }
        for c in chunks
    ]
    yield f"data: {json.dumps({'done': True, 'sources': safe_sources})}\n\n"