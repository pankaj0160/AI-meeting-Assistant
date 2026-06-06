# core/intelligence/titles.py

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL   = "llama-3.3-70b-versatile"


def generate_meeting_title(transcript: str, summary: str = "") -> str:
    """
    Generates a concise, professional meeting title from transcript + summary.

    Returns a plain string title (4-8 words).
    Falls back to 'Meeting' if generation fails.
    """
    if not transcript or len(transcript.strip()) < 50:
        return "Untitled Meeting"

    system = """You are an expert meeting analyst.
Generate a concise, professional meeting title.

Rules:
- 4 to 8 words maximum
- Use title case
- Must reflect the actual content — no generic titles
- No quotes, no punctuation at end
- Examples:
    Q3 Product Launch Planning Session
    Budget Review and Hiring Decisions
    Customer Success Weekly Team Sync
    Deployment Strategy and Risk Review

Return ONLY the title text. Nothing else."""

    content = f"""SUMMARY:
{summary[:500] if summary else 'No summary available.'}

TRANSCRIPT (first 1000 words):
{' '.join(transcript.split()[:1000])}"""

    try:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": content},
            ],
            temperature=0.3,
            max_tokens=32,
        )
        title = response.choices[0].message.content.strip()
        # Clean up any accidental quotes or punctuation
        title = title.strip('"\'').rstrip('.')
        return title if title else "Untitled Meeting"

    except Exception as e:
        print(f"  ⚠ Title generation failed: {e}")
        return "Untitled Meeting"