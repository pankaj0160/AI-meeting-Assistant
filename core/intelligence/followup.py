# core/intelligence/followup.py

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL   = "llama-3.3-70b-versatile"


def generate_followup_email(
    meeting_title: str,
    intelligence:  dict,
) -> str:
    """
    Generates a professional follow-up email from meeting intelligence.

    Returns a plain text email string ready to copy.
    """
    summary      = intelligence.get("summary",      "")
    decisions    = intelligence.get("decisions",    [])
    action_items = intelligence.get("action_items", [])
    topics       = intelligence.get("topics",       [])

    if not summary and not decisions and not action_items:
        return "No meeting intelligence available to generate a follow-up email."

    # Build context for the AI
    decisions_text = "\n".join([
        f"- {d['decision']}" for d in decisions
    ]) or "No decisions recorded."

    actions_text = "\n".join([
        f"- {a['task']}"
        + (f" (Owner: {a['owner']})" if a.get('owner') else "")
        + (f" (Due: {a['deadline']})" if a.get('deadline') else "")
        for a in action_items
    ]) or "No action items recorded."

    topics_text = ", ".join([
        t["title"] for t in topics
    ]) or "General discussion."

    system = """You are a professional business writer.
Write a concise, professional follow-up email for a meeting.

Format:
Subject: [subject line]

Hi team,

[Opening sentence referencing the meeting]

[Summary paragraph — 2-3 sentences]

Key Decisions:
[bullet list]

Action Items:
[bullet list with owners and deadlines]

[Closing sentence]

Best regards,
[Your Name]

Rules:
- Professional but warm tone
- Concise — no unnecessary filler
- Use the exact decisions and action items provided
- Do NOT invent information not in the context
- Return the complete email as plain text"""

    user_content = f"""Meeting Title: {meeting_title}

Summary:
{summary}

Topics Discussed: {topics_text}

Decisions Made:
{decisions_text}

Action Items:
{actions_text}"""

    try:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": user_content},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"  ⚠ Follow-up email generation failed: {e}")
        return "Failed to generate follow-up email. Please try again."