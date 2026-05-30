from pathlib import Path

from app.audio_utils import extract_audio
from app.transcriber import transcribe_audio
from app.youtube_downloader import download_youtube
from app.database import save_transcript, init_db

def process_video(video_file: str):

    print("Step 1: Extracting audio...")

    wav_file = extract_audio(video_file)

    print("Step 2: Transcribing audio...")

    transcript = transcribe_audio(wav_file)

    save_transcript(
        filename=Path(video_file).stem,
        transcript=transcript
    )

    return transcript


def process_youtube(url: str):

    print("Step 1: Downloading YouTube audio...")

    youtube_data = download_youtube(url)

    print(f"Title: {youtube_data['title']}")

    mp3_file = youtube_data["audio_file"]

    print("Step 2: Converting to WAV...")

    wav_file = extract_audio(mp3_file)

    print("Step 3: Transcribing audio...")

    transcript = transcribe_audio(wav_file)

    save_transcript(
        filename=youtube_data["title"],
        transcript=transcript
    )

    return transcript


if __name__ == "__main__":

    # Create database/table if not exists
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