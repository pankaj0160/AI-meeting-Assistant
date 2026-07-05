# server/core/transcription/speaker_diarization.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# Takes an audio file and figures out WHO spoke WHEN.
# This is called "speaker diarization" — splitting audio into labeled speaker turns.
#
# The pipeline has 3 stages:
#
#   Stage 1 — pyannote.audio (diarize_audio)
#     Deep learning model that analyses the audio waveform.
#     Finds every voice change and assigns IDs: SPEAKER_00, SPEAKER_01, ...
#     Returns: [(0.0s–14.3s: SPEAKER_00), (14.3s–27.8s: SPEAKER_01), ...]
#     No text yet — just time ranges and speaker IDs.
#
#   Stage 2 — faster-whisper (transcribe_audio_with_timestamps)
#     Converts speech to text WITH per-segment timestamps.
#     Returns: [{"start": 0.0, "end": 4.2, "text": "let's ship it"}, ...]
#
#   Stage 3 — merge_with_transcript
#     Combines Stage 1 and Stage 2: for each whisper text segment,
#     finds which pyannote speaker was talking during those timestamps.
#     Result: SPEAKER_00 [0:00]: "let's ship it"
#
# ══════════════════════════════════════════════════════════════════════════════
# ROOT CAUSE OF THE ORIGINAL BUG — READ THIS:
# ══════════════════════════════════════════════════════════════════════════════
#
# The old endpoint in main.py passed this as "whisper segments":
#   pseudo_segments = [{"start": 0.0, "end": 9999.0, "text": full_transcript}]
#
# ONE fake segment spanning 9999 seconds.
#
# Then merge_with_transcript() tried to match pyannote segments to this one blob.
# Since the fake segment spans the entire audio, EVERY pyannote speaker's time range
# overlaps with it. But the loop assigns text to whichever speaker has the MOST overlap
# with the fake segment — which is always the first speaker found, because it covers
# everything. Result: all text → SPEAKER_00. All other speakers disappear.
#
# THE FIX:
# The endpoint now calls transcribe_audio_with_timestamps() first to get REAL
# per-sentence timestamps (e.g. 200 segments for a 1-hour meeting), THEN
# passes those to run_diarization(). Each sentence maps to the correct speaker
# based on actual timing.
#
# PRODUCTION FIXES ALSO IN THIS FILE:
# ─────────────────────────────────────
# FIX 1: pyannote pipeline is now a module-level singleton with a threading.Lock().
#   Old code: Pipeline.from_pretrained() called every time diarize_audio() runs.
#   Loading takes 8-15 seconds + downloads 1.5GB on first run.
#   With singleton: loads once, reused for all subsequent calls.
#
# FIX 2: Response shape now matches what the frontend SpeakersTab expects.
#   The frontend expects:
#     { speakers: [{id, label, total_time, percentage}],
#       segments: [{speaker, speaker_label, start, end, text}],
#       total_duration: float }
#   Old code returned a different shape — frontend rendered nothing.
#
# FIX 3: Speaker labels (SPEAKER_00 → "Speaker 1") applied at the source.
#   The frontend showed raw "SPEAKER_00" which is confusing.
#   We now map: SPEAKER_00 → "Speaker 1", SPEAKER_01 → "Speaker 2", etc.
#   The raw pyannote IDs are preserved as 'id' for internal use.

import os
import threading
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── pyannote pipeline singleton ───────────────────────────────────────────────
# Loading Pipeline.from_pretrained() takes 8-15 seconds and downloads ~1.5GB.
# We load once and reuse. Thread lock prevents two simultaneous loads.
_pipeline      = None
_pipeline_lock = threading.Lock()


def _get_pipeline():
    """
    Return the pyannote pipeline, loading it on first call.
    Thread-safe via double-checked locking.
    """
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                hf_token = os.getenv("HF_TOKEN")
                if not hf_token:
                    raise RuntimeError(
                        "HF_TOKEN is not set in your .env file.\n"
                        "You need a HuggingFace token AND must accept the model terms at:\n"
                        "  https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                        "  https://huggingface.co/pyannote/segmentation-3.0"
                    )
                try:
                    from pyannote.audio import Pipeline
                    import torch
                except ImportError:
                    raise ImportError(
                        "pyannote.audio is not installed.\n"
                        "Run: pip install pyannote.audio"
                    )

                device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
                logger.info("Loading pyannote pipeline on %s (first call only)...", device)

                # FIX: pyannote.audio >= 3.0 uses token= not use_auth_token=
                # Try new API first, fall back to old API for older versions
                try:
                    pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        token=hf_token,
                    )
                except TypeError:
                    # Older pyannote.audio — use deprecated parameter name
                    pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=hf_token,
                    )
                pipeline.to(__import__("torch").device(device))
                _pipeline = pipeline
                logger.info("pyannote pipeline loaded and cached.")
    return _pipeline


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class SpeakerSegment:
    """One block of speech attributed to one speaker."""
    start:         float          # seconds from audio start
    end:           float          # seconds from audio end
    speaker:       str            # raw pyannote ID: "SPEAKER_00"
    speaker_label: str = ""       # human label: "Speaker 1"
    text:          str = ""       # transcript text for this segment


# ── Stage 1: pyannote diarization ────────────────────────────────────────────

def diarize_audio(audio_path: str) -> list[SpeakerSegment]:
    """
    Run pyannote speaker diarization on a WAV file.

    Returns time-labeled segments with speaker IDs. NO text yet — text
    is added in Stage 3 by merge_with_transcript().

    First call: downloads the model (~1.5GB) from HuggingFace and caches it.
    Subsequent calls: loads from ~/.cache/huggingface/ (much faster).

    CPU timing: ~4 minutes for a 1-hour meeting.
    GPU timing: ~12 seconds for the same meeting.
    """
    pipeline = _get_pipeline()
    logger.info("Running pyannote diarization on: %s", audio_path)

    result = pipeline(audio_path)

    # FIX: newer pyannote.audio returns DiarizeOutput with .speaker_diarization
    # attribute containing the actual Annotation object.
    # Older versions return the Annotation directly.
    if hasattr(result, 'speaker_diarization'):
        diarization = result.speaker_diarization
    elif hasattr(result, 'annotation'):
        diarization = result.annotation
    else:
        diarization = result   # already an Annotation

    segments = [
        SpeakerSegment(
            start=round(turn.start, 3),
            end=round(turn.end, 3),
            speaker=speaker,
        )
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]

    unique = sorted(set(s.speaker for s in segments))
    logger.info(
        "pyannote done: %d segments, %d speakers (%s)",
        len(segments), len(unique), unique,
    )
    return sorted(segments, key=lambda s: s.start)


# ── Stage 3: merge whisper text + pyannote labels ────────────────────────────

def merge_with_transcript(
    whisper_segments:     list[dict],
    diarization_segments: list[SpeakerSegment],
) -> list[SpeakerSegment]:
    """
    Assign each Whisper text segment to the speaker with the most time overlap.

    WHY REAL TIMESTAMPS MATTER (the core bug fix):
        Whisper returns segments like:
            {"start": 0.0,  "end": 4.2,  "text": "let's ship it"}
            {"start": 14.3, "end": 18.1, "text": "agreed, what about testing"}
            {"start": 22.0, "end": 26.4, "text": "good point"}

        For each whisper segment, we find which pyannote speaker was
        talking during those specific timestamps. The overlap comparison
        only works correctly with REAL timestamps.

        The old code used one fake segment spanning 0–9999s for the entire
        transcript. Every pyannote segment overlapped it, so all text was
        assigned to the first speaker. This is now fixed: the endpoint calls
        transcribe_audio_with_timestamps() before calling run_diarization().

    Args:
        whisper_segments:     list of {"start", "end", "text"} from Whisper
        diarization_segments: list of SpeakerSegment from pyannote

    Returns:
        list of SpeakerSegment with text filled in, merged for readability
    """
    if not diarization_segments:
        # No diarization data — bundle everything under one speaker
        full_text = " ".join(s.get("text", "") for s in whisper_segments)
        return [SpeakerSegment(
            start=0, end=0,
            speaker="SPEAKER_00", speaker_label="Speaker 1",
            text=full_text.strip(),
        )]

    # Build speaker → label mapping once
    unique_speakers = sorted(set(ds.speaker for ds in diarization_segments))
    speaker_label   = {sp: f"Speaker {i+1}" for i, sp in enumerate(unique_speakers)}

    result = []
    for ws in whisper_segments:
        ws_start = ws.get("start", 0.0)
        ws_end   = ws.get("end", ws_start + 1.0)
        ws_text  = ws.get("text", "").strip()
        if not ws_text:
            continue

        # Find the diarization segment with the most time overlap with this whisper segment
        best_speaker = unique_speakers[0] if unique_speakers else "SPEAKER_00"
        best_overlap = 0.0

        for ds in diarization_segments:
            # overlap = intersection of [ws_start, ws_end] and [ds.start, ds.end]
            overlap = max(0.0, min(ws_end, ds.end) - max(ws_start, ds.start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = ds.speaker

        result.append(SpeakerSegment(
            start=ws_start,
            end=ws_end,
            speaker=best_speaker,
            speaker_label=speaker_label.get(best_speaker, best_speaker),
            text=ws_text,
        ))

    merged = _merge_consecutive(result, speaker_label)
    logger.debug("Merged into %d speaker blocks", len(merged))
    return merged


def _merge_consecutive(
    segments:      list[SpeakerSegment],
    speaker_label: dict,
) -> list[SpeakerSegment]:
    """
    Merge back-to-back segments from the same speaker into one block.

    Before: SPEAKER_00 [0:00]: "let's"  |  SPEAKER_00 [0:01]: "ship it."
    After:  SPEAKER_00 [0:00]: "let's ship it."

    This reduces noise — fewer, longer segments are easier to read.
    """
    if not segments:
        return []
    merged = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        if seg.speaker == prev.speaker:
            merged[-1] = SpeakerSegment(
                start=prev.start,
                end=seg.end,
                speaker=prev.speaker,
                speaker_label=speaker_label.get(prev.speaker, prev.speaker),
                text=prev.text.strip() + " " + seg.text.strip(),
            )
        else:
            merged.append(seg)
    return merged


# ── Formatting ────────────────────────────────────────────────────────────────

def format_transcript(segments: list[SpeakerSegment]) -> str:
    """
    Build a readable labeled transcript string for storage and LLM input.

    Output:
        Speaker 1 [0:00]: let's ship it this week.
        Speaker 2 [0:14]: I'm worried we haven't tested edge cases.
        Speaker 1 [0:22]: Fair point. Let's add two days for QA.

    Using human labels (Speaker 1) instead of raw IDs (SPEAKER_00)
    makes LLM-generated action items read naturally:
        "Speaker 2 will add edge case testing to the backlog"
    instead of:
        "SPEAKER_01 will add edge case testing to the backlog"
    """
    lines = []
    for seg in segments:
        m = int(seg.start // 60)
        s = int(seg.start % 60)
        label = seg.speaker_label or seg.speaker
        lines.append(f"{label} [{m}:{s:02d}]: {seg.text.strip()}")
    return "\n".join(lines)


# ── Talk time calculation ─────────────────────────────────────────────────────

def compute_talk_time(segments: list[SpeakerSegment]) -> dict:
    """
    Calculate how long each speaker talked.

    Returns dict keyed by speaker ID (not label) for consistency with DB storage:
        {
            "SPEAKER_00": {"seconds": 142.3, "percentage": 58.2, "segments": 14,
                           "label": "Speaker 1"},
            "SPEAKER_01": {"seconds": 102.1, "percentage": 41.8, "segments": 11,
                           "label": "Speaker 2"},
        }
    Sorted most-to-least talkative.
    """
    talk_time:  dict[str, float] = {}
    seg_count:  dict[str, int]   = {}
    labels:     dict[str, str]   = {}

    for seg in segments:
        dur = max(0.0, seg.end - seg.start)
        talk_time[seg.speaker] = talk_time.get(seg.speaker, 0.0) + dur
        seg_count[seg.speaker] = seg_count.get(seg.speaker, 0)   + 1
        labels[seg.speaker]    = seg.speaker_label or seg.speaker

    total = sum(talk_time.values()) or 1.0

    return {
        sp: {
            "seconds":    round(secs, 1),
            "percentage": round(secs / total * 100, 1),
            "segments":   seg_count[sp],
            "label":      labels[sp],
        }
        for sp, secs in sorted(talk_time.items(), key=lambda x: -x[1])
    }


# ── Response builder ──────────────────────────────────────────────────────────
# FIX: builds the exact shape the frontend SpeakersTab expects.
#
# Frontend expects:
#   {
#     speakers: [{ id, label, total_time, percentage, segments_count }],
#     segments: [{ speaker, speaker_label, start, end, text }],
#     total_duration: float,
#     num_speakers: int,
#     transcript: str,         ← labeled transcript string for LLM/storage
#     talk_time: dict,         ← raw dict for DB storage + sentiment analysis
#   }

def build_response(segments: list[SpeakerSegment]) -> dict:
    """Build the complete diarization response dict matching the frontend shape."""
    talk_time = compute_talk_time(segments)
    transcript = format_transcript(segments)
    total_dur  = max((s.end for s in segments), default=0.0)

    # speakers list — sorted most to least talkative
    speakers_list = [
        {
            "id":             sp_id,
            "label":          data["label"],
            "total_time":     data["seconds"],
            "percentage":     data["percentage"],
            "segments_count": data["segments"],
        }
        for sp_id, data in talk_time.items()
    ]

    # segments list — each individual speaker block with text
    segments_list = [
        {
            "speaker":       seg.speaker,
            "speaker_label": seg.speaker_label,
            "start":         seg.start,
            "end":           seg.end,
            "text":          seg.text,
        }
        for seg in segments
    ]

    return {
        "speakers":       speakers_list,
        "segments":       segments_list,
        "total_duration": round(total_dur, 1),
        "num_speakers":   len(speakers_list),
        "transcript":     transcript,
        "talk_time":      talk_time,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def run_diarization(audio_path: str, whisper_segments: list[dict]) -> dict:
    """
    Full diarization pipeline: pyannote + merge + response build.

    IMPORTANT: whisper_segments must be REAL per-sentence timestamps from
    transcribe_audio_with_timestamps(), NOT a fake single-segment list.
    Passing fake segments is what caused the original bug where all text
    was attributed to SPEAKER_00.

    Args:
        audio_path:       path to the WAV file
        whisper_segments: list of {"start": float, "end": float, "text": str}
                          from transcribe_audio_with_timestamps()

    Returns:
        Full response dict from build_response() — matches frontend shape.
    """
    if not whisper_segments:
        raise ValueError(
            "whisper_segments is empty. "
            "Call transcribe_audio_with_timestamps() first and pass the result here."
        )

    # Check if any fake segments snuck through
    if len(whisper_segments) == 1 and whisper_segments[0].get("end", 0) > 1000:
        logger.warning(
            "Detected fake single-segment input (end=%.0f). "
            "This will produce incorrect results. "
            "Pass real timestamps from transcribe_audio_with_timestamps().",
            whisper_segments[0].get("end", 0),
        )

    diarization_segs = diarize_audio(audio_path)
    merged           = merge_with_transcript(whisper_segments, diarization_segs)
    return build_response(merged)