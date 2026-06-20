# ─────────────────────────────────────────────────────────────────────────────
# server/core/transcription/speaker_diarization.py
#
# New file — create it at that path. Nothing existing is modified.
# ─────────────────────────────────────────────────────────────────────────────

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """
    One block of speech by one speaker.

    start   : seconds from the start of the audio (e.g. 14.3)
    end     : seconds from the start of the audio (e.g. 27.8)
    speaker : label assigned by pyannote (e.g. "SPEAKER_00", "SPEAKER_01")
    text    : the words spoken — filled in after the merge step, empty before
    """
    start:   float
    end:     float
    speaker: str
    text:    str = ""


def diarize_audio(audio_path: str) -> list[SpeakerSegment]:
    """
    Run pyannote speaker diarization on a .wav file.
    Returns a list of SpeakerSegments with start/end/speaker filled in.
    The text field is still empty at this point — filled by merge_with_transcript().

    First call: downloads the pyannote model (~1.5GB) from HuggingFace.
    Every call after that: loads from local cache in ~/.cache/huggingface/
    On CPU a 1-hour meeting takes ~4 minutes.
    On GPU (CUDA) it takes ~12 seconds.
    """
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN is not set in your .env file.\n"
            "You need it to download the pyannote model from HuggingFace.\n"
            "Also make sure you've accepted the terms at:\n"
            "  https://huggingface.co/pyannote/speaker-diarization-3.1\n"
            "  https://huggingface.co/pyannote/segmentation-3.0"
        )

    # Lazy imports — pyannote is heavy, don't load it at server startup
    try:
        from pyannote.audio import Pipeline
        import torch
    except ImportError:
        raise ImportError(
            "pyannote.audio is not installed.\n"
            "Run:  pip install pyannote.audio"
        )

    # Use GPU if available, otherwise CPU
    # torch.cuda.is_available() returns True only if you have an NVIDIA GPU
    # with CUDA drivers installed. On most laptops this will be False → CPU.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"[Diarization] Loading pyannote pipeline on {device}...")

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    pipeline.to(torch.device(device))

    logger.info(f"[Diarization] Running on: {audio_path}")
    diarization = pipeline(audio_path)

    segments = [
        SpeakerSegment(
            start=round(turn.start, 3),
            end=round(turn.end, 3),
            speaker=speaker,
        )
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]

    logger.info(
        f"[Diarization] Done — {len(segments)} segments, "
        f"{len(set(s.speaker for s in segments))} speakers"
    )

    return sorted(segments, key=lambda s: s.start)


def merge_with_transcript(
    whisper_segments: list[dict],
    diarization_segments: list[SpeakerSegment],
) -> list[SpeakerSegment]:
    """
    Combine Whisper text segments with pyannote speaker labels.

    whisper_segments looks like:
        [{"start": 0.0, "end": 4.2, "text": "let's ship it"}, ...]
        (this is what faster-whisper returns when you ask for segments)

    For each Whisper segment we find the diarization segment that overlaps
    the most with its time window — that speaker "wins" that text.

    After assigning speakers to every segment, we merge consecutive segments
    from the same speaker into one block (so you don't get 40 tiny segments
    from SPEAKER_00 one after the other).
    """
    if not diarization_segments:
        full_text = " ".join(s.get("text", "") for s in whisper_segments)
        return [SpeakerSegment(start=0, end=0, speaker="SPEAKER_00", text=full_text.strip())]

    result = []

    for ws in whisper_segments:
        ws_start = ws.get("start", 0.0)
        ws_end   = ws.get("end",   ws_start + 1.0)
        ws_text  = ws.get("text",  "").strip()

        if not ws_text:
            continue

        # Find the diarization segment with the most time overlap
        best_speaker = "SPEAKER_00"
        best_overlap = 0.0

        for ds in diarization_segments:
            overlap = max(0.0, min(ws_end, ds.end) - max(ws_start, ds.start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = ds.speaker

        result.append(SpeakerSegment(
            start=ws_start,
            end=ws_end,
            speaker=best_speaker,
            text=ws_text,
        ))

    return _merge_consecutive(result)


def _merge_consecutive(segments: list[SpeakerSegment]) -> list[SpeakerSegment]:
    """
    Merge back-to-back segments from the same speaker into one block.

    Before:
        SPEAKER_00 [0:00]: let's
        SPEAKER_00 [0:01]: ship it.
    After:
        SPEAKER_00 [0:00]: let's ship it.
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
                text=prev.text + " " + seg.text,
            )
        else:
            merged.append(seg)
    return merged


def format_transcript(segments: list[SpeakerSegment]) -> str:
    """
    Turn a list of SpeakerSegments into a readable transcript string.

    Output:
        SPEAKER_00 [0:00]: let's ship it.
        SPEAKER_01 [0:08]: i agree. what about testing though.
        SPEAKER_00 [0:22]: good point. let's add that to the backlog.

    This string replaces the plain transcript in SQLite and ChromaDB.
    The LLM agents now see speaker labels, so action items become:
        "SPEAKER_01 will add testing to the backlog"
    instead of:
        "someone will add testing to the backlog"
    """
    lines = []
    for seg in segments:
        minutes = int(seg.start // 60)
        seconds = int(seg.start % 60)
        lines.append(f"{seg.speaker} [{minutes}:{seconds:02d}]: {seg.text}")
    return "\n".join(lines)


def compute_talk_time(segments: list[SpeakerSegment]) -> dict:
    """
    Calculate how long each speaker talked and their share of total talk time.

    Returns:
        {
            "SPEAKER_00": {"seconds": 142.3, "percentage": 58.2, "segments": 14},
            "SPEAKER_01": {"seconds": 102.1, "percentage": 41.8, "segments": 11},
        }

    Sorted by most-to-least talkative.
    Used for the participation score in the meeting health analysis.
    """
    talk_time: dict[str, float] = {}
    seg_count: dict[str, int]   = {}

    for seg in segments:
        dur = max(0.0, seg.end - seg.start)
        talk_time[seg.speaker] = talk_time.get(seg.speaker, 0.0) + dur
        seg_count[seg.speaker] = seg_count.get(seg.speaker, 0)   + 1

    total = sum(talk_time.values()) or 1.0   # avoid division by zero

    return {
        speaker: {
            "seconds":    round(secs, 1),
            "percentage": round(secs / total * 100, 1),
            "segments":   seg_count[speaker],
        }
        for speaker, secs in sorted(talk_time.items(), key=lambda x: -x[1])
    }


def run_diarization(audio_path: str, whisper_segments: list[dict]) -> dict:
    """
    Single entry point for the full diarization pipeline.
    Call this from main.py — it handles everything internally.

    Args:
        audio_path       : path to the .wav file (same one passed to transcribe_audio)
        whisper_segments : list of dicts from faster-whisper, each with start/end/text

    Returns:
        {
            "transcript":   str,   # formatted SPEAKER_XX [m:ss]: text transcript
            "talk_time":    dict,  # per-speaker seconds + percentage
            "num_speakers": int,   # how many distinct speakers detected
        }
    """
    diarization_segs = diarize_audio(audio_path)
    merged           = merge_with_transcript(whisper_segments, diarization_segs)
    transcript       = format_transcript(merged)
    talk_time        = compute_talk_time(merged)

    return {
        "transcript":   transcript,
        "talk_time":    talk_time,
        "num_speakers": len(set(s.speaker for s in merged)),
    }