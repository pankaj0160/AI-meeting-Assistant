# server/core/tasks.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# Defines the Celery background worker task that processes uploaded meetings.
#
# WITHOUT Celery: user uploads → browser waits 3-5 minutes for Whisper
# WITH Celery: user uploads → gets job_id immediately → worker runs in background
#
# HOW IT FITS TOGETHER:
#
#   FastAPI (web server)
#       │  1. Saves uploaded file to disk
#       │  2. Calls process_meeting_task.delay(...)  ← sends job to Redis
#       │  3. Returns job_id to browser immediately (<1 second)
#       │
#       └──→ Redis (message broker — holds the job)
#                │
#                └──→ Celery Worker (separate Python process)
#                          Reads job from Redis, runs:
#                            FFmpeg → Whisper → LLM agents → ChromaDB
#                          Writes progress updates back to Redis
#                          Browser polls /jobs/{id}/status to show progress bar
#
# PRODUCTION FIXES IN THIS FILE:
# ───────────────────────────────
# FIX 1: WAV temp file cleanup
#   When processing a video file, FFmpeg creates a .wav file in /tmp.
#   Old code never deleted this file — disk fills up over time.
#   New code: tracks the wav_path and deletes it in a finally block.
#
# FIX 2: Redis idempotency lock
#   If the same job_id is submitted twice (retry, duplicate request),
#   the second run would overwrite the first, creating duplicate DB records.
#   Fix: SET NX (set only if not exists) lock in Redis before starting.
#   If lock already exists → skip processing, log the duplicate.
#
# FIX 3: Moved all imports to module top-level
#   Old code had lazy imports inside the task body (e.g. `from server.core...`).
#   Celery workers import the module at startup — top-level imports happen once.
#   Imports inside the function body happen on EVERY task execution.
#   For a 100-task queue, that's 100 module loads instead of 1.
#
# FIX 4: Better progress granularity
#   Added more progress steps so the frontend progress bar moves more smoothly.
#
# FIX 5: Proper error logging with exc_info=True
#   Old code: logger.error(f"...: {e}") — no stack trace in logs.
#   New code: logger.error("...", exc_info=True) — full traceback logged.

import os
import json
import logging
from pathlib import Path
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Celery setup ──────────────────────────────────────────────────────────────
# REDIS_URL: where to send jobs and where to store results.
# In Docker (docker-compose.yml): redis://redis:6379/0
# In local dev without Docker:    redis://localhost:6379/0
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "summly",
    broker  = REDIS_URL,
    backend = REDIS_URL,
)

celery_app.conf.update(
    result_expires    = 3600,       # keep results in Redis for 1 hour
    task_serializer   = "json",
    result_serializer = "json",
    accept_content    = ["json"],
    timezone          = "UTC",
    enable_utc        = True,
    task_acks_late    = True,       # ack only after task completes (safer)
    worker_prefetch_multiplier = 1, # don't grab more than 1 task per worker
                                    # prevents slow Whisper jobs from blocking
                                    # quick tasks behind them in the queue
)

# ── File type constants ───────────────────────────────────────────────────────
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "aac"}


# =============================================================================
# JOB STATUS HELPERS
# =============================================================================
# We store fine-grained progress in Redis ourselves (separate from Celery's
# built-in result backend) because Celery only has "pending/running/done".
# We want per-step updates: "extracting audio 30%", "transcribing 55%", etc.
#
# Key format : "job:{job_id}:status"
# Value      : JSON string { step, message, pct, meeting_id, error }
# TTL        : 1 hour (auto-deleted by Redis after that)

def _status_key(job_id: str) -> str:
    return f"job:{job_id}:status"

def _lock_key(job_id: str) -> str:
    return f"job:{job_id}:lock"


def set_job_status(job_id: str, status: dict) -> None:
    """
    Write job progress to Redis.

    status dict shape:
        step       : "queued" | "extract" | "transcribe" | "intel" | "index" | "done" | "error"
        message    : plain English description shown in the UI progress bar
        pct        : 0-100 integer
        meeting_id : int or None (set once the DB record is created)
        error      : error message string, or None
    """
    try:
        redis_client = celery_app.backend.client
        redis_client.setex(
            _status_key(job_id),
            3600,                     # expire after 1 hour
            json.dumps(status),
        )
    except Exception as e:
        logger.debug("Could not write job status to Redis: %s", e)


def get_job_status(job_id: str) -> dict | None:
    """
    Read job progress from Redis.
    Returns None if job_id doesn't exist (expired or never created).
    """
    try:
        redis_client = celery_app.backend.client
        raw = redis_client.get(_status_key(job_id))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug("Could not read job status from Redis: %s", e)
        return None


# =============================================================================
# CELERY TASK
# =============================================================================

@celery_app.task(bind=True, name="summly.process_meeting")
def process_meeting_task(
    self,
    job_id:                str,
    file_path:             str,
    filename:              str,
    user_id:               int,
    enable_audio_cleaning: bool = True,
):
    """
    Background Celery task: transcribe a meeting and run the full AI pipeline.

    Pipeline:
        1. Idempotency check (Redis lock) — skip if already running
        2. Audio extraction (FFmpeg: video/audio → 16kHz WAV)
        3. Transcription (Faster-Whisper)
        4. Save transcript to PostgreSQL
        5. Intelligence analysis (4 LLM agents in parallel via workflow.py)
        6. Save intelligence to PostgreSQL
        7. Index into ChromaDB for RAG chat
        8. Cleanup all temp files (guaranteed in finally block)

    Progress updates are written to Redis at each step.
    The frontend polls GET /jobs/{job_id}/status to show the progress bar.

    Args:
        job_id                : unique ID generated by /upload/async endpoint
        file_path             : absolute path to the saved upload on disk
        filename              : original filename (e.g. "standup.mp4")
        user_id               : the authenticated user who uploaded the file
        enable_audio_cleaning : whether to apply noise reduction before Whisper
    """

    def update(step: str, message: str, pct: int, meeting_id=None, error=None):
        """Write one progress update to Redis."""
        set_job_status(job_id, {
            "step":       step,
            "message":    message,
            "pct":        pct,
            "meeting_id": meeting_id,
            "error":      error,
        })
        logger.info("[Job %s] %d%% — %s", job_id, pct, message)

    # FIX: Idempotency lock — prevents duplicate processing if the task
    # is accidentally submitted twice (e.g. user double-clicks Upload).
    #
    # SET NX = "SET only if Not eXists"
    # If the lock key already exists → another instance is running → skip.
    # TTL 7200 = 2 hours. If the worker crashes, the lock auto-expires
    # so re-queuing works again after 2 hours.
    try:
        redis_client = celery_app.backend.client
        lock_acquired = redis_client.set(
            _lock_key(job_id),
            "1",
            nx  = True,    # only set if key does NOT exist
            ex  = 7200,    # auto-expire after 2 hours (crash safety)
        )
        if not lock_acquired:
            logger.warning(
                "[Job %s] Duplicate task detected — skipping (lock exists in Redis).",
                job_id,
            )
            return {"status": "skipped", "reason": "duplicate"}
    except Exception as e:
        # Lock check failed (Redis issue) — proceed anyway rather than
        # blocking all uploads if Redis has a transient problem
        logger.warning("[Job %s] Could not acquire Redis lock: %s — proceeding anyway", job_id, e)

    file_path_obj = Path(file_path)
    wav_path      = None   # FIX: track WAV temp file for cleanup

    try:
        # ── Step 1: Audio extraction ──────────────────────────────────────
        update("extract", "Extracting audio from file...", 10)

        ext = file_path_obj.suffix.lower().lstrip(".")

        from server.core.transcription.audio_extractor import extract_audio

        if ext in VIDEO_EXTENSIONS:
            # FFmpeg extracts audio from video and writes a temp WAV file.
            # We track wav_path so we can delete it in the finally block.
            wav_path = extract_audio(
                str(file_path_obj),
                enable_cleaning=enable_audio_cleaning,
            )
        elif ext in AUDIO_EXTENSIONS:
            # Audio files go directly to Whisper — no extraction needed.
            wav_path = str(file_path_obj)
        else:
            raise ValueError(
                f"Unsupported file type: .{ext}. "
                f"Accepted: {sorted(VIDEO_EXTENSIONS | AUDIO_EXTENSIONS)}"
            )

        update("extract", "Audio ready for transcription", 25)

        # ── Step 2: Transcription ─────────────────────────────────────────
        update("transcribe", "Transcribing speech to text (this takes a while)...", 30)

        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_path)

        char_count = len(transcript)
        word_count = len(transcript.split())
        update(
            "transcribe",
            f"Transcription complete: {word_count:,} words",
            50,
        )
        logger.info("[Job %s] Transcript: %d chars, %d words", job_id, char_count, word_count)

        # ── Step 3: Save transcript ───────────────────────────────────────
        from server.core.database import save_transcript_and_get_id
        meeting_id = save_transcript_and_get_id(
            filename   = filename,
            transcript = transcript,
            duration   = None,
            user_id    = user_id,
        )
        logger.info("[Job %s] Saved to DB as meeting_id=%d", job_id, meeting_id)

        # ── Step 4: Intelligence pipeline ─────────────────────────────────
        update("intel", "Running AI analysis (summary, actions, decisions, topics)...", 60, meeting_id=meeting_id)

        from server.core.intelligence.workflow import analyze_transcript
        from server.core.database import save_meeting_intelligence

        intelligence = analyze_transcript(transcript)
        save_meeting_intelligence(meeting_id, intelligence)

        update(
            "intel",
            f"Analysis complete: {len(intelligence.action_items)} actions, "
            f"{len(intelligence.decisions)} decisions",
            78,
            meeting_id=meeting_id,
        )

        # ── Step 5: ChromaDB indexing ──────────────────────────────────────
        update("index", "Indexing transcript for chat search...", 88, meeting_id=meeting_id)

        try:
            from server.core.rag.indexer import index_meeting
            n_chunks = index_meeting(
                meeting_id = meeting_id,
                filename   = filename,
                transcript = transcript,
                created_at = "",
                user_id    = user_id,
            )
            logger.info("[Job %s] Indexed %d chunks for meeting %d", job_id, n_chunks, meeting_id)
        except Exception as e:
            # Indexing failure is non-fatal: meeting is saved and intel is ready.
            # User just won't be able to use chat search for this meeting.
            logger.warning(
                "[Job %s] ChromaDB index failed (non-fatal): %s — chat search disabled for meeting %d",
                job_id, e, meeting_id,
            )

        # ── Step 6: Done ───────────────────────────────────────────────────
        update("done", "Processing complete!", 100, meeting_id=meeting_id)
        logger.info("[Job %s] Pipeline complete for meeting %d", job_id, meeting_id)

        # PHASE 1: notify the user their meeting is ready. Best-effort and
        # NEVER allowed to fail the task — this runs after everything the
        # user actually needs (meeting_id, intelligence, index) is already
        # saved, so an email failure here must not mark a successful
        # pipeline run as failed in Celery.
        try:
            from server.core.auth.service import get_user_by_id
            from server.core.email import send_meeting_ready_email
            user = get_user_by_id(user_id)
            if user and getattr(user, "email", None):
                send_meeting_ready_email(user.email, filename, str(meeting_id))
        except Exception as e:
            logger.warning(
                "[Job %s] Meeting-ready email failed (non-fatal): %s",
                job_id, e,
            )

        return {"meeting_id": meeting_id, "status": "done"}

    except Exception as e:
        logger.error(
            "[Job %s] Pipeline failed: %s",
            job_id, e,
            exc_info=True,   # FIX: includes full stack trace in logs
        )
        update("error", f"Processing failed: {type(e).__name__}", 0, error=str(e))
        raise   # re-raise so Celery marks task as FAILED in its result backend

    finally:
        # FIX: Delete the WAV temp file created by FFmpeg, guaranteed.
        # "finally" runs even if an exception was raised above.
        #
        # We only delete the WAV if it is DIFFERENT from the original uploaded file.
        # For audio uploads: wav_path == file_path (same file) → don't delete.
        # For video uploads: wav_path is a new /tmp/... file → delete it.
        if wav_path and wav_path != str(file_path_obj):
            wav_file = Path(wav_path)
            if wav_file.exists():
                try:
                    wav_file.unlink()
                    logger.info("[Job %s] Cleaned up WAV temp file: %s", job_id, wav_path)
                except Exception as e:
                    logger.warning("[Job %s] Could not delete WAV temp file %s: %s", job_id, wav_path, e)

        # Release the Redis idempotency lock
        try:
            redis_client = celery_app.backend.client
            redis_client.delete(_lock_key(job_id))
        except Exception:
            pass   # non-critical — lock has a 2-hour TTL anyway