# core/transcription/audio_extractor.py
#
# FIX: WAV output now uses a system temp file instead of a permanent uploads/audio/ directory.
#
# OLD: FFmpeg wrote to server/uploads/audio/<stem>.wav — stayed on disk forever.
#      After 100 uploads: 100 WAV files sitting on the server eating disk.
#      Two uploads of "standup.wav" would silently overwrite each other.
#
# NEW: FFmpeg writes to /tmp/summly_<uuid>.wav — caller is responsible for
#      deleting it when done (same pattern as main.py's /upload endpoint
#      which already does this correctly with try/finally).
#
# CALLER CONTRACT:
#   wav_path = extract_audio(input_path)
#   try:
#       transcript = transcribe_audio(wav_path)
#   finally:
#       Path(wav_path).unlink(missing_ok=True)  # always clean up

import subprocess
import logging
import tempfile
import uuid
from pathlib import Path

from server.core.transcription.audio_cleaner import AudioCleaner

logger = logging.getLogger(__name__)


def extract_audio(
    input_path: str,
    enable_cleaning: bool = True,
) -> str:
    """
    Extract and convert audio from a video or audio file to 16kHz mono WAV.
    Returns the path to a temp WAV file.

    IMPORTANT: The caller MUST delete this file when done:
        wav = extract_audio(src)
        try:
            transcript = transcribe_audio(wav)
        finally:
            Path(wav).unlink(missing_ok=True)

    Args:
        input_path      : path to source video or audio file
        enable_cleaning : run noise reduction + compression (default True)

    Returns:
        Path to a temp WAV file (in the system temp directory)

    Raises:
        FileNotFoundError        : if input_path doesn't exist
        subprocess.CalledProcessError : if FFmpeg fails
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    # FIX: Write to a unique temp file instead of a permanent uploads/ path.
    # NamedTemporaryFile(delete=False) creates the file but doesn't auto-delete —
    # we close it immediately so FFmpeg can open it (Windows requires this).
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".wav",
        prefix=f"summly_wav_{uuid.uuid4().hex[:8]}_",
    )
    output_path = Path(tmp.name)
    tmp.close()

    command = [
        "ffmpeg",
        "-i",  str(input_file),
        "-ar", "16000",    # 16kHz — required by Whisper
        "-ac", "1",        # mono
        "-vn",             # drop video stream
        "-y",              # overwrite without asking
        str(output_path),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Audio extracted to temp: %s", output_path)
    except subprocess.CalledProcessError as e:
        # Clean up the empty temp file on FFmpeg failure
        output_path.unlink(missing_ok=True)
        logger.error("FFmpeg failed: %s", e.stderr)
        raise

    # Optional noise reduction + dynamic range compression
    if enable_cleaning:
        try:
            logger.info("Cleaning audio...")
            cleaner = AudioCleaner(sr=16000)
            result  = cleaner.clean_audio(
                str(output_path),
                output_path=str(output_path),   # overwrite in place
                enable_noise_reduction=True,
                enable_compression=True,
            )
            logger.info(
                "Audio cleaned | SNR improvement: +%.1f dB",
                result.get("snr_improvement_db", 0),
            )
            warnings = result.get("quality_after", {}).get("warnings", [])
            if warnings:
                logger.warning("Audio quality warnings: %s", warnings)
        except Exception as e:
            # Non-fatal — proceed with uncleaned audio
            logger.warning("Audio cleaning failed (non-fatal): %s", e)

    return str(output_path)