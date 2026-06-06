# core/rag/chat.py

import os
from groq import Groq
from dotenv import load_dotenv

from server.core.rag.hybrid_search import hybrid_search

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


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

    Args:
        query      : user's question
        meeting_id : scope search to this meeting only
        top_k      : number of chunks to retrieve

    Returns:
        {
            "answer"  : str,         # Groq's answer
            "sources" : list[dict],  # chunks used as context
        }
    """
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

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()

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

    Args:
        query  : user's question
        top_k  : number of chunks to retrieve across all meetings

    Returns:
        {
            "answer"  : str,
            "sources" : list[dict],
        }
    """
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

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_message},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()

    return {
        "answer":  answer,
        "sources": chunks,
    }