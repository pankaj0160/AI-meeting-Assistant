# audio_extractor.py
import subprocess
import logging
from pathlib import Path

from server.core.transcription.audio_cleaner import AudioCleaner

logger = logging.getLogger(__name__)

# ── Resolve paths relative to THIS file, not CWD ─────────────────────────────
# This file lives at: server/core/transcription/audio_extractor.py
# uploads/audio should be at: server/uploads/audio  (or project root/uploads/audio)
# Adjust BASE_DIR to match your actual intended uploads location.

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # → server/
OUTPUT_AUDIO_DIR = BASE_DIR / "uploads" / "audio"


def extract_audio(
    input_path: str,
    enable_cleaning: bool = True
) -> str:
    """
    Extract audio from video/audio and optionally clean it.
    Returns path to WAV file.
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    # ── Ensure output directory exists ────────────────────────────────────────
    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_AUDIO_DIR / f"{input_file.stem}.wav"

    # Convert to 16kHz mono WAV
    command = [
        "ffmpeg",
        "-i", str(input_file),
        "-ar", "16000",
        "-ac", "1",
        "-vn",
        "-y",
        str(output_file)
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✓ Audio extracted: {output_file}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg Error: {e.stderr}")
        raise

    # Optional cleaning
    if enable_cleaning:
        try:
            logger.info("Cleaning audio...")
            cleaner = AudioCleaner(sr=16000)
            result = cleaner.clean_audio(
                str(output_file),
                output_path=str(output_file),  # overwrite in place
                enable_noise_reduction=True,
                enable_compression=True
            )
            logger.info(
                f"✓ Audio cleaned | SNR improvement: +{result['snr_improvement_db']:.1f} dB"
            )
            warnings = result.get("quality_after", {}).get("warnings", [])
            if warnings:
                logger.warning(f"Audio quality warnings: {warnings}")

        except Exception as e:
            # Non-fatal — proceed with uncleaned audio
            logger.warning(f"Audio cleaning failed (non-fatal): {e}")

    return str(output_file)


if __name__ == "__main__":
    wav_file = extract_audio("test.mp4", enable_cleaning=True)
    print(f"Generated file: {wav_file}")