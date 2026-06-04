# core/intelligence/quotes.py

import json
import os

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL   = "llama-3.3-70b-versatile"


def _clean_json(raw: str) -> str:
    return raw.replace("```json", "").replace("```", "").strip()


def extract_key_quotes(transcript: str) -> list[dict]:
    """
    Extracts 3-6 key business quotes from a transcript.

    Returns list of:
    {
        "quote":   str,
        "speaker": str | None,
        "context": str | None,
    }
    """
    if not transcript or len(transcript.strip()) < 100:
        return []

    system = """You are an expert meeting analyst.
Your ONLY job: extract 3 to 6 key quotes from this meeting transcript.

Select quotes that are:
- Significant decisions or commitments
- Important deadlines or targets mentioned
- Strong statements about direction or strategy
- Memorable or impactful phrases

Return a JSON array. Each object must have:
  "quote"   : string  (the exact or near-exact quote, under 25 words)
  "speaker" : string or null  (speaker name/label if identifiable)
  "context" : string or null  (one sentence explaining why this matters)

Example:
[
  {
    "quote":   "We need to ship by July 15th, no exceptions.",
    "speaker": "Sarah",
    "context": "Sets the hard deadline for the product launch."
  }
]

Return ONLY a valid JSON array. No markdown. No explanation."""

    try:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": f"TRANSCRIPT:\n{transcript[:4000]}"},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        raw    = response.choices[0].message.content.strip()
        parsed = json.loads(_clean_json(raw))
        return [
            {
                "quote":   str(item.get("quote",   "")),
                "speaker": item.get("speaker"),
                "context": item.get("context"),
            }
            for item in parsed
            if item.get("quote")
        ]
    except Exception as e:
        print(f"  ⚠ Quotes extraction failed: {e}")
        return []