
# WHAT THIS FILE DOES:
#
#   Two features live here:
#
#   1. SENTIMENT ANALYSIS
#      Reads the diarized transcript (the one with SPEAKER_00 labels)
#      and figures out how each speaker felt during the meeting.
#      Was Alice enthusiastic? Was Bob frustrated? Was there tension?
#      Uses Instructor + Pydantic exactly like agents.py does.
#
#   2. TALK-TIME ANALYSIS
#      The diarization module (speaker_diarization.py) already computes
#      raw seconds per speaker. This module goes further:
#      - Labels each speaker's share as "dominant", "balanced", or "quiet"
#      - Detects if the meeting was one person talking too much
#      - Generates a plain-English balance verdict
#      - Combines it with sentiment so the health score can use it
#
#   WHY SEPARATE FROM agents.py?
#      agents.py runs on every meeting automatically as part of the pipeline.
#      Sentiment is an ON-DEMAND feature — it requires diarization first,
#      which is itself optional. So it lives in its own file and is called
#      from its own endpoint, not the main pipeline.
# ═════════════════════════════════════════════════════════════════════════════
 
import os
import time
import logging
 
import instructor
from groq import Groq
from langfuse import Langfuse
from dotenv import load_dotenv
 
from server.core.intelligence.schemas import (
    SpeakerSentimentList,
    MeetingSentimentSummary,
)
 
load_dotenv()
logger = logging.getLogger(__name__)
 
MODEL = "llama-3.3-70b-versatile"
 
# ── Clients — same lazy init pattern as agents.py ─────────────────────────────
_groq_client        = None
_instructor_client  = None
_langfuse           = None
 
 
def _get_clients():
    global _groq_client, _instructor_client, _langfuse
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        _instructor_client = instructor.from_groq(
            Groq(api_key=os.getenv("GROQ_API_KEY")),
            mode=instructor.Mode.JSON,
        )
        _langfuse = Langfuse()
    return _groq_client, _instructor_client, _langfuse
 
 
# =============================================================================
# PART 1 — SENTIMENT ANALYSIS
# =============================================================================
 
def analyze_sentiment(diarized_transcript: str) -> MeetingSentimentSummary:
    """
    Analyse the sentiment and emotion of each speaker in a diarized transcript.
 
    WHAT IS A DIARIZED TRANSCRIPT?
        A transcript where each line is prefixed with the speaker label:
            SPEAKER_00 [0:00]: let's move on the deploy this week.
            SPEAKER_01 [0:14]: i'm worried we haven't tested edge cases.
            SPEAKER_00 [0:22]: fair point. let's add two days for QA.
 
        This comes from speaker_diarization.py and is stored in
        meeting_diarization.transcript in the database.
 
    WHY DOES DIARIZATION COME FIRST?
        Without speaker labels, the model can only say "the meeting was positive".
        With labels, it can say "SPEAKER_00 was enthusiastic, SPEAKER_01 was concerned".
        Per-speaker insight is dramatically more useful than a single score.
 
    WHAT INSTRUCTOR DOES HERE:
        We use _instructor_client.chat.completions.create() with
        response_model=SpeakerSentimentList — same pattern as run_action_item_agent().
        Instructor guarantees we get a valid, validated Pydantic object back.
        No JSON parsing, no try/except around json.loads(), no risk of crashes.
 
    Args:
        diarized_transcript: the full SPEAKER_XX [m:ss]: text transcript string
 
    Returns:
        MeetingSentimentSummary with overall scores and per-speaker breakdown
    """
    _, instructor_client, langfuse = _get_clients()
 
    # ── Step 1: Extract per-speaker sentiment ─────────────────────────────────
    # We ask Instructor to return a SpeakerSentimentList — one entry per speaker.
    system_per_speaker = """You are an expert meeting sentiment analyst.
Analyse the emotional tone of each speaker in this diarized meeting transcript.
 
Rules:
- Each line starts with SPEAKER_XX [timestamp]: text
- Identify ALL distinct speakers (SPEAKER_00, SPEAKER_01, etc.)
- For each speaker analyse their overall sentiment across ALL their lines
- sentiment must be exactly: "positive", "neutral", or "negative"
- dominant_emotion: one word like enthusiastic, concerned, frustrated, calm, confident, uncertain
- key_phrases: pick up to 3 short direct quotes that best show their tone
- confidence: how certain you are about the sentiment, 0.0 to 1.0
- Base analysis ONLY on what is said — not on who speaks most"""
 
    generation = langfuse.generation(
        name="sentiment_per_speaker",
        model=MODEL,
        input=[{"role": "system", "content": system_per_speaker},
               {"role": "user",   "content": f"TRANSCRIPT:\n{diarized_transcript[:4000]}"}],
    )
 
    start = time.time()
    try:
        speaker_result = instructor_client.chat.completions.create(
            model=MODEL,
            response_model=SpeakerSentimentList,
            messages=[
                {"role": "system", "content": system_per_speaker},
                {"role": "user",   "content": f"TRANSCRIPT:\n{diarized_transcript[:4000]}"},
            ],
            temperature=0.1,
            max_tokens=1500,
            max_retries=3,
        )
        generation.end(
            output=str(speaker_result.model_dump()),
            metadata={"latency_seconds": round(time.time() - start, 3)},
        )
    except Exception as e:
        generation.end(output=f"ERROR: {e}", metadata={"error": True})
        logger.error(f"[Sentiment] Per-speaker extraction failed: {e}")
        # Return a safe fallback — never crash the endpoint
        return _default_sentiment()
 
    # ── Step 2: Generate meeting-level summary ─────────────────────────────────
    # Now we ask for the overall meeting tone, energy, and whether there was tension.
    # We do this as a plain Groq call (not Instructor) because it's free-form prose.
    groq_client, _, _ = _get_clients()
 
    speaker_summary = "\n".join([
        f"- {s.speaker}: {s.sentiment} ({s.dominant_emotion})"
        for s in speaker_result.speakers
    ])
 
    system_overall = """You are an expert meeting analyst.
Given the per-speaker sentiment breakdown below, assess the overall meeting tone.
Return ONLY a JSON object with these exact fields — no markdown, no explanation:
{
  "overall_sentiment":  "positive" or "neutral" or "negative",
  "meeting_energy":     "high" or "medium" or "low",
  "tension_detected":   true or false,
  "sentiment_shift":    "one sentence describing mood change, or null if none"
}"""
 
    user_overall = f"""Per-speaker sentiment:
{speaker_summary}
 
Transcript excerpt:
{diarized_transcript[:1500]}"""
 
    import json
 
    generation2 = langfuse.generation(
        name="sentiment_overall",
        model=MODEL,
        input=[{"role": "system", "content": system_overall},
               {"role": "user",   "content": user_overall}],
    )
 
    start2 = time.time()
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_overall},
                {"role": "user",   "content": user_overall},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        overall = json.loads(raw)
        generation2.end(
            output=raw,
            metadata={"latency_seconds": round(time.time() - start2, 3)},
        )
    except Exception as e:
        generation2.end(output=f"ERROR: {e}", metadata={"error": True})
        logger.warning(f"[Sentiment] Overall summary failed: {e}")
        overall = {
            "overall_sentiment": "neutral",
            "meeting_energy":    "medium",
            "tension_detected":  False,
            "sentiment_shift":   None,
        }
 
    return MeetingSentimentSummary(
        overall_sentiment  = overall.get("overall_sentiment", "neutral"),
        meeting_energy     = overall.get("meeting_energy",    "medium"),
        tension_detected   = bool(overall.get("tension_detected", False)),
        sentiment_shift    = overall.get("sentiment_shift"),
        speakers           = speaker_result.speakers,
    )
 
 
def _default_sentiment() -> MeetingSentimentSummary:
    """Safe fallback when sentiment analysis fails completely."""
    return MeetingSentimentSummary(
        overall_sentiment = "neutral",
        meeting_energy    = "medium",
        tension_detected  = False,
        sentiment_shift   = None,
        speakers          = [],
    )
 
 
# =============================================================================
# PART 2 — TALK-TIME ANALYSIS
# =============================================================================
 
def analyze_talk_time(talk_time_data: dict) -> dict:
    """
    Takes the raw talk_time dict from speaker_diarization.py and adds:
      - A participation label per speaker: "dominant", "balanced", or "quiet"
      - A balance_score: 0-100 (100 = perfectly equal, 0 = one person spoke everything)
      - A plain-English verdict about the participation balance
      - A flag for whether the meeting was dominated by one speaker
 
    WHY DO WE NEED THIS ON TOP OF RAW SECONDS?
        Raw seconds tells you "SPEAKER_00 talked for 142s".
        This function tells you what that MEANS:
        "SPEAKER_00 dominated the meeting with 72% of talk time,
         while SPEAKER_02 contributed only 8%."
 
    HOW balance_score IS CALCULATED:
        We use the Gini coefficient — a standard measure of inequality.
        A Gini of 0 means everyone spoke exactly equally (score = 100).
        A Gini of 1 means one person spoke everything (score = 0).
        We invert and scale it so higher = more balanced.
 
    Args:
        talk_time_data: dict returned by compute_talk_time() in speaker_diarization.py
        Format:
            {
                "SPEAKER_00": {"seconds": 142.3, "percentage": 58.2, "segments": 14},
                "SPEAKER_01": {"seconds": 102.1, "percentage": 41.8, "segments": 11},
            }
 
    Returns:
        {
            "speakers": [
                {
                    "speaker":     "SPEAKER_00",
                    "seconds":     142.3,
                    "percentage":  58.2,
                    "segments":    14,
                    "label":       "dominant",   ← new
                },
                ...
            ],
            "balance_score":  41,          ← 0-100, higher = more equal
            "is_dominated":   True,        ← True if one speaker > 60%
            "dominant_speaker": "SPEAKER_00",  ← who dominated (or None)
            "verdict":  "SPEAKER_00 dominated the meeting with 58% of talk time..."
        }
    """
    if not talk_time_data:
        return {
            "speakers":        [],
            "balance_score":   0,
            "is_dominated":    False,
            "dominant_speaker": None,
            "verdict":         "No talk-time data available.",
        }
 
    num_speakers = len(talk_time_data)
    speakers_list = []
 
    for speaker, data in talk_time_data.items():
        pct = data.get("percentage", 0)
 
        # Label logic:
        # "dominant"  → this speaker has significantly more than their fair share
        # "balanced"  → within a reasonable range of equal participation
        # "quiet"     → significantly less than their fair share
        fair_share = 100 / num_speakers if num_speakers > 0 else 100
 
        if pct >= fair_share * 1.5:
            label = "dominant"
        elif pct <= fair_share * 0.5:
            label = "quiet"
        else:
            label = "balanced"
 
        speakers_list.append({
            "speaker":    speaker,
            "seconds":    data.get("seconds", 0),
            "percentage": pct,
            "segments":   data.get("segments", 0),
            "label":      label,
        })
 
    # Sort by most to least talkative
    speakers_list.sort(key=lambda x: x["percentage"], reverse=True)
 
    # ── Calculate balance score using Gini coefficient ─────────────────────
    percentages = [s["percentage"] for s in speakers_list]
    n = len(percentages)
 
    if n <= 1:
        # Only one speaker — can't assess balance
        balance_score = 0
    else:
        # Gini coefficient formula
        sorted_pcts = sorted(percentages)
        total = sum(sorted_pcts) or 1
        gini_numerator = sum(
            abs(sorted_pcts[i] - sorted_pcts[j])
            for i in range(n)
            for j in range(n)
        )
        gini = gini_numerator / (2 * n * total)
        # Convert: Gini 0 → score 100, Gini 1 → score 0
        balance_score = round((1 - gini) * 100)
 
    # ── Detect domination ─────────────────────────────────────────────────
    top_speaker    = speakers_list[0] if speakers_list else None
    is_dominated   = top_speaker["percentage"] > 60 if top_speaker else False
    dominant_speaker = top_speaker["speaker"] if is_dominated else None
 
    # ── Plain-English verdict ──────────────────────────────────────────────
    verdict = _build_verdict(speakers_list, balance_score, is_dominated, num_speakers)
 
    return {
        "speakers":         speakers_list,
        "balance_score":    balance_score,
        "is_dominated":     is_dominated,
        "dominant_speaker": dominant_speaker,
        "verdict":          verdict,
    }
 
 
def _build_verdict(
    speakers:      list[dict],
    balance_score: int,
    is_dominated:  bool,
    num_speakers:  int,
) -> str:
    """
    Build a plain-English one-to-two sentence verdict about participation balance.
    No LLM call — this is pure logic, fast and free.
    """
    if num_speakers == 0:
        return "No speakers detected."
 
    if num_speakers == 1:
        return f"{speakers[0]['speaker']} was the only speaker ({speakers[0]['seconds']:.0f}s)."
 
    top = speakers[0]
    bottom = speakers[-1]
 
    if is_dominated:
        verdict = (
            f"{top['speaker']} dominated the meeting with {top['percentage']:.0f}% of talk time "
            f"({top['seconds']:.0f}s). "
        )
        if bottom["percentage"] < 10:
            verdict += f"{bottom['speaker']} had very little opportunity to contribute ({bottom['percentage']:.0f}%)."
        else:
            verdict += "Consider giving other participants more speaking time."
    elif balance_score >= 75:
        verdict = (
            f"Talk time was well balanced across {num_speakers} speakers "
            f"(balance score: {balance_score}/100). "
            f"{top['speaker']} led slightly with {top['percentage']:.0f}%."
        )
    else:
        verdict = (
            f"Talk time was somewhat uneven across {num_speakers} speakers "
            f"(balance score: {balance_score}/100). "
            f"{top['speaker']} spoke most at {top['percentage']:.0f}%, "
            f"{bottom['speaker']} least at {bottom['percentage']:.0f}%."
        )
 
    return verdict
 
 
# =============================================================================
# COMBINED ENTRY POINT
# =============================================================================
 
def run_full_analysis(meeting_id: int) -> dict:
    """
    Single function that runs BOTH sentiment and talk-time analysis for a meeting.
    Called by the endpoint in main.py.
 
    Steps:
        1. Fetch the diarization data from the database
        2. Run sentiment analysis on the diarized transcript
        3. Run talk-time analysis on the talk_time dict
        4. Combine everything into one response dict
        5. Save to the database
 
    Returns:
        The full analysis dict (same shape as the API response).
        Returns None if diarization hasn't been run yet for this meeting.
    """
    from server.core.database import get_diarization, save_sentiment_analysis
 
    diarization = get_diarization(meeting_id)
 
    if not diarization:
        return None   # Caller should return 404 with "run diarization first" message
 
    diarized_transcript = diarization["transcript"]
    talk_time_data      = diarization["talk_time"]
    num_speakers        = diarization["num_speakers"]
 
    # Run both analyses
    logger.info(f"[Sentiment] Running sentiment analysis for meeting {meeting_id}...")
    sentiment_result = analyze_sentiment(diarized_transcript)
 
    logger.info(f"[TalkTime] Running talk-time analysis for meeting {meeting_id}...")
    talk_time_result = analyze_talk_time(talk_time_data)
 
    # Build the combined result
    result = {
        "meeting_id":   meeting_id,
        "num_speakers": num_speakers,
        # ── Sentiment fields ─────────────────────────────────
        "overall_sentiment":  sentiment_result.overall_sentiment,
        "meeting_energy":     sentiment_result.meeting_energy,
        "tension_detected":   sentiment_result.tension_detected,
        "sentiment_shift":    sentiment_result.sentiment_shift,
        "speaker_sentiments": [s.model_dump() for s in sentiment_result.speakers],
        # ── Talk-time fields ─────────────────────────────────
        "talk_time":          talk_time_result,
    }
 
    # Save to database
    save_sentiment_analysis(
        meeting_id=meeting_id,
        result=result,
    )
 
    logger.info(f"[Sentiment] Done for meeting {meeting_id}")
    return result