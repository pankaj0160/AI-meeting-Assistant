import subprocess
from pathlib import Path


def extract_audio(input_path: str) -> str:
    """
    Extract audio from a video file and convert it to:
    - WAV format
    - 16kHz sample rate
    - Mono channel

    Returns:
        Path to generated WAV file
    """

    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    OUTPUT_AUDIO_DIR = Path("uploads/audio")
    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_AUDIO_DIR / f"{input_file.stem}.wav"

    command = [
        "ffmpeg",
        "-i", str(input_file),
        "-ar", "16000",
        "-ac", "1",
        "-vn",              # remove video stream
        "-y",               # overwrite existing file
        str(output_file)
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        print(f"✓ Audio extracted: {output_file}")

        return str(output_file)

    except subprocess.CalledProcessError as e:
        print("FFmpeg Error:")
        print(e.stderr)
        raise


if __name__ == "__main__":
    wav_file = extract_audio("test.mp4")
    print(f"Generated file: {wav_file}")