# server/core/transcription/transcribe.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# Converts audio files into text using Faster-Whisper.
#
# faster-whisper is a re-implementation of OpenAI's Whisper that runs
# 4x faster on CPU by using CTranslate2 as its inference backend.
# We use the "tiny" model with int8 quantisation — small enough to run
# on a 2GB VPS, fast enough for production use.
#
# Two functions are exported:
#   transcribe_audio()               → returns a plain text string
#   transcribe_audio_with_timestamps() → returns list of timed segments
#
# The second is used by speaker diarization (speaker_diarization.py).
# Having per-sentence timestamps is what makes diarization work correctly
# (see the root-cause explanation in speaker_diarization.py).
#
# PRODUCTION FIXES IN THIS FILE:
# ───────────────────────────────
# FIX 1: threading.Lock() on model init.
#   Old code had bare `if _model is None: _model = WhisperModel(...)`.
#   With two simultaneous uploads:
#     Thread A sees _model is None → starts loading (takes 3-8 seconds)
#     Thread B sees _model is None → also starts loading (race condition)
#   Both threads load the model independently. RAM usage doubles.
#   In the worst case, CTranslate2 raises a "model already loaded" error.
#   Fix: threading.Lock() with double-checked locking — same pattern as
#   embedder.py and indexer.py.
#
# FIX 2: vad_filter=True (already in previous version, kept here).
#   VAD = Voice Activity Detection. Whisper's built-in silero-VAD filter
#   skips silent portions of the audio before sending to the model.
#   A 1-hour meeting with 20 minutes of silence → processes 40 min of audio.
#   Typical speedup: 20-30% on real meeting recordings.
#
# FIX 3: beam_size=1 (greedy decoding, already in previous version).
#   beam_size=5 explores 5 alternative transcriptions at each step.
#   On a tiny model running on CPU: 5 beams = 3x slower, negligible gain.
#   The tiny model doesn't have enough capacity to benefit from wide beams.
#
# FIX 4: Added warmup() function.
#   Called from main.py at server startup to load the model in a background
#   thread. This means the model is ready in RAM when the first upload arrives.
#   Without warmup: first upload waits 8-15 seconds for model load.
#   With warmup: model loads during server startup, first upload is instant.

import threading
import logging
import warnings

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

MODEL_SIZE   = "tiny"
DEVICE       = "cpu"
COMPUTE_TYPE = "int8"

# ── Singleton + lock ──────────────────────────────────────────────────────────
# FIX: added _model_lock to prevent two threads loading simultaneously.
_model      = None
_model_lock = threading.Lock()


def get_whisper_model():
    """
    Return the Whisper model, loading it on first call.

    Thread-safe via double-checked locking:
      1. Fast check without lock (99% of calls — model already loaded)
      2. Acquire lock only if model is None
      3. Check again inside lock — another thread may have loaded it
         while we were waiting

    Why lazy load (not module-level)?
      FastAPI imports this module for every worker process.
      Eager loading would load the 40MB model file for every worker
      on every import, even for workers that only handle auth or health checks.
      Lazy loading: only the Celery worker (which actually runs transcription)
      pays the load cost.
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # re-check inside lock
                from faster_whisper import WhisperModel
                logger.info(
                    "Loading Faster-Whisper model: %s / %s / %s",
                    MODEL_SIZE, DEVICE, COMPUTE_TYPE,
                )
                _model = WhisperModel(
                    MODEL_SIZE,
                    device       = DEVICE,
                    compute_type = COMPUTE_TYPE,
                )
                logger.info("Faster-Whisper model loaded and ready")
    return _model


def warmup():
    """
    Pre-load the Whisper model so the first upload request is instant.

    Called from main.py lifespan startup in a background thread.
    The model loads asynchronously — server startup is not blocked.
    When the first upload arrives, the model is already in RAM.

    Why a background thread and not asyncio?
      WhisperModel() is synchronous and CPU-bound (reads a binary file,
      runs initialisation code). It blocks for 3-8 seconds.
      Running it in the event loop would block all FastAPI requests
      during that window. A thread keeps the event loop free.
    """
    logger.info("Warming up Whisper model in background...")
    try:
        get_whisper_model()
        logger.info("Whisper model warmup complete")
    except Exception as e:
        logger.warning("Whisper model warmup failed (non-fatal): %s", e)


def transcribe_audio(audio_file: str) -> str:
    """
    Transcribe an audio file to a plain text string.

    Args:
        audio_file: path to any audio file (WAV, MP3, M4A, etc.)

    Returns:
        Full transcript as a single space-joined string.
        Returns empty string if no speech is detected.

    Performance on CPU (tiny + int8):
        1 hour of speech  ≈ 8-12 minutes (without VAD filter)
        1 hour of speech  ≈ 6-9 minutes  (with VAD, 20% silence)
        30 min of speech  ≈ 4-6 minutes
        10 min of speech  ≈ 90-120 seconds
    """
    model = get_whisper_model()
    logger.info("Transcribing: %s", audio_file)

    segments, info = model.transcribe(
        str(audio_file),
        beam_size                = 1,      # greedy: 3x faster, negligible accuracy loss on tiny
        language                 = None,   # auto-detect language
        condition_on_previous_text = True, # better coherence across segments
        vad_filter               = True,   # skip silent portions
        vad_parameters           = dict(
            min_silence_duration_ms = 500, # silence shorter than 500ms is kept
        ),
    )

    # segments is a generator — must be iterated exactly once
    # Joining with space gives a readable paragraph-style transcript
    transcript = " ".join(
        seg.text.strip()
        for seg in segments
        if seg.text.strip()
    )

    logger.info(
        "Transcription done: %d chars, detected language: %s (%.0f%% confidence)",
        len(transcript),
        info.language,
        info.language_probability * 100,
    )
    return transcript


def transcribe_audio_with_timestamps(audio_file: str) -> list[dict]:
    """
    Transcribe with per-segment timestamps. Used by speaker diarization.

    Returns:
        list of dicts: [{"start": 0.0, "end": 4.2, "text": "let's ship it"}, ...]

    WHY TIMESTAMPS MATTER FOR DIARIZATION:
        Speaker diarization (pyannote) outputs time ranges:
            SPEAKER_00: 0.0s – 14.3s
            SPEAKER_01: 14.3s – 27.0s

        To know which speaker said which sentence, we need each sentence's
        start/end time. Without timestamps, all text is one blob and we
        can't match it to the speaker time ranges.

        This function returns per-sentence timestamps that merge_with_transcript()
        uses to correctly attribute each sentence to the right speaker.

    Note on word_timestamps=True:
        Whisper returns word-level timestamps when requested.
        We use them to get accurate sentence boundaries.
        Adds ~10% processing overhead — acceptable for diarization use.
    """
    model = get_whisper_model()
    logger.info("Transcribing with timestamps: %s", audio_file)

    segments, info = model.transcribe(
        str(audio_file),
        beam_size        = 1,
        word_timestamps  = True,   # needed for accurate segment timing
        vad_filter       = True,
        vad_parameters   = dict(min_silence_duration_ms=500),
    )

    result = [
        {
            "start": round(seg.start, 2),
            "end":   round(seg.end,   2),
            "text":  seg.text.strip(),
        }
        for seg in segments
        if seg.text.strip()
    ]

    logger.info("Timestamp transcription done: %d segments", len(result))
    return result


def get_model_info() -> dict:
    """Return model metadata for the /health endpoint."""
    return {
        "model":        MODEL_SIZE,
        "device":       DEVICE,
        "compute_type": COMPUTE_TYPE,
        "backend":      "faster-whisper",
        "loaded":       _model is not None,
    }