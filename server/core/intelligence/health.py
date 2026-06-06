# core/intelligence/health.py
import json
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL   = "llama-3.3-70b-versatile"

def _clean_json(raw: str) -> str:
    return raw.replace("```json", "").replace("```", "").strip()

def analyze_meeting_health(transcript: str, intelligence: dict) -> dict:
    if not transcript or len(transcript.strip()) < 50:
        return _default_health()

    system = """You are an expert meeting quality analyst.
Analyze the meeting transcript and intelligence data provided.
Return a JSON object with these exact fields:
{
  "overall_score":     integer 0-100,
  "participation":     integer 0-100,
  "decision_quality":  integer 0-100,
  "action_clarity":    integer 0-100,
  "followup_risk":     integer 0-100,
  "highlights":        string (1-2 sentences of what went well),
  "concerns":          string (1-2 sentences of what could improve)
}
Scoring guide:
- overall_score:    weighted average of the four scores
- participation:    how balanced and engaged was the discussion?
- decision_quality: were decisions clear, reasoned, and actionable?
- action_clarity:   do action items have clear owners and deadlines?
- followup_risk:    INVERSE score — high means low risk, low means high risk.
                    Consider: missing deadlines, unclear ownership, many open items.
Return ONLY valid JSON. No markdown. No explanation."""

    user_content = f"""TRANSCRIPT:
{transcript[:3000]}

INTELLIGENCE SUMMARY:
Decisions: {len(intelligence.get('decisions', []))}
Action Items: {len(intelligence.get('action_items', []))}
Topics: {len(intelligence.get('topics', []))}
Summary: {intelligence.get('summary', '')[:300]}"""

    try:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.1,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        print(f"[health] Raw LLM response: {raw[:200]}")  # debug log

        parsed = json.loads(_clean_json(raw))

        return {
            "overall_score":    int(parsed.get("overall_score",    70)),
            "participation":    int(parsed.get("participation",    70)),
            "decision_quality": int(parsed.get("decision_quality", 70)),
            "action_clarity":   int(parsed.get("action_clarity",   70)),
            "followup_risk":    int(parsed.get("followup_risk",    70)),
            "highlights":       str(parsed.get("highlights",       "")),
            "concerns":         str(parsed.get("concerns",         "")),
        }

    except json.JSONDecodeError as e:
        print(f"[health] JSON parse failed: {e} | raw was: {raw!r}")
        return _default_health()
    except Exception as e:
        print(f"[health] Groq call failed: {type(e).__name__}: {e}")
        return _default_health()

def _default_health() -> dict:
    # Returns 70 as a neutral fallback — never show 0 to the user
    return {
        "overall_score":    70,
        "participation":    70,
        "decision_quality": 70,
        "action_clarity":   70,
        "followup_risk":    70,
        "highlights":       "Analysis unavailable — using default scores.",
        "concerns":         "Re-open this meeting to regenerate health data.",
    }