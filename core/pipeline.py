from pathlib import Path

from core.audio_extractor import extract_audio
from core.transcribe import transcribe_audio
from core.youtube_downloader import download_youtube
from core.database import (
    init_db,
    save_transcript_and_get_id,
    save_meeting_intelligence,
)
from core.intelligence.workflow import analyze_transcript


# ─── Phase 2 internal helper ──────────────────────────────────────────────────

def _run_intelligence(meeting_id: int, transcript: str) -> None:
    """
    Runs the intelligence engine and saves results.
    Called after every successful transcription.
    Failures are caught and logged — they never crash the pipeline.
    """
    try:
        print("Step 3: Running meeting intelligence engine...")
        intelligence = analyze_transcript(transcript)
        save_meeting_intelligence(meeting_id, intelligence)
        print(
            f"  ✓ Intelligence saved: "
            f"{len(intelligence.action_items)} action items, "
            f"{len(intelligence.decisions)} decisions, "
            f"{len(intelligence.topics)} topics"
        )
    except Exception as e:
        print(f"  ⚠ Intelligence analysis failed (transcript still saved): {e}")


# ─── Phase 1 functions — extended but interface unchanged ─────────────────────

def process_video(video_file: str) -> str:
    """
    Process a local video file.
    Returns the transcript text (same as Phase 1).
    Now also runs intelligence and saves to database.
    """
    print("Step 1: Extracting audio...")
    wav_file = extract_audio(video_file)

    print("Step 2: Transcribing audio...")
    transcript = transcribe_audio(wav_file)

    meeting_id = save_transcript_and_get_id(
        filename=Path(video_file).stem,
        transcript=transcript,
    )

    _run_intelligence(meeting_id, transcript)

    return transcript


def process_youtube(url: str) -> str:
    """
    Process a YouTube URL.
    Returns the transcript text (same as Phase 1).
    Now also runs intelligence and saves to database.
    """
    print("Step 1: Downloading YouTube audio...")
    youtube_data = download_youtube(url)
    print(f"  Title: {youtube_data['title']}")

    mp3_file = youtube_data["audio_file"]

    print("Step 2: Converting to WAV...")
    wav_file = extract_audio(mp3_file)

    print("Step 3: Transcribing audio...")
    transcript = transcribe_audio(wav_file)

    meeting_id = save_transcript_and_get_id(
        filename=youtube_data["title"],
        transcript=transcript,
    )

    _run_intelligence(meeting_id, transcript)

    return transcript


# ─── CLI runner — unchanged ───────────────────────────────────────────────────

if __name__ == "__main__":

    init_db()

    choice = input(
        "Choose input type:\n"
        "1. Local Video\n"
        "2. YouTube URL\n\n"
        "Enter choice: "
    )

    if choice == "1":
        video_file = input("Enter video path: ")
        result = process_video(video_file)

    elif choice == "2":
        url = input("Enter YouTube URL: ")
        result = process_youtube(url)

    else:
        print("Invalid choice.")
        exit()

    print("\n=== FINAL TRANSCRIPT ===\n")
    print(result)