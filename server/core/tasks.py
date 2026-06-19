# server/core/tasks.py
#
# WHAT IS CELERY?
# ───────────────
# Celery is a "task queue" — a system for running Python functions
# in the background, outside of your web server.
#
# WITHOUT Celery (how your app works right now):
#   User uploads file → FastAPI receives it → Whisper transcribes it (3-5 min)
#   → User's browser sits there waiting the whole time
#   → If they close the tab, the upload is LOST
#
# WITH Celery (what we're building):
#   User uploads file → FastAPI saves the file → returns job_id IMMEDIATELY (<1 second)
#   → Celery worker picks up the job in the background
#   → WebSocket streams progress back to the browser
#   → User can close the tab and come back — job keeps running
#
# HOW THE PIECES FIT TOGETHER:
#
#   FastAPI (your web server)
#       │  1. Saves file to disk
#       │  2. Calls process_meeting_task.delay(...)  ← drops job into Redis
#       │  3. Returns job_id immediately
#       │
#       └──→ Redis (the "post box")
#                │  stores the job message
#                │
#                └──→ Celery Worker (a separate Python process)
#                          │  picks up the job from Redis
#                          │  runs Whisper, LLM, ChromaDB
#                          │  updates job status in Redis
#                          └──→ WebSocket sends progress to browser
#
# WHY REDIS?
#   Redis is the "broker" — the middleman between FastAPI and Celery.
#   FastAPI writes a message to Redis: "please process this file".
#   Celery reads it and does the work. They never talk directly.
#   Redis also stores the job results ("done", "failed", progress %).
#
# IMPORTANT: This file does NOT replace your existing /upload/progress endpoint.
#   That endpoint still works exactly as before.
#   We're adding a NEW /upload/async endpoint that uses Celery instead.

import os
import json
import asyncio
import logging
from pathlib import Path
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Celery app setup ──────────────────────────────────────────────────────────
# Celery needs two URLs:
#   broker_url    → where to SEND jobs (FastAPI writes here)
#   backend_url   → where to STORE results (both FastAPI and Celery read here)
#
# We use Redis for both. In our docker-compose.yml, Redis is at redis://redis:6379/0
# The /0 means "database 0" — Redis has 16 databases (0-15), we use 0.
#
# REDIS_URL comes from your .env file (set to redis://redis:6379/0 for Docker,
# or redis://localhost:6379/0 if running Redis locally without Docker).

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "summly",                      # Name of this Celery application
    broker=REDIS_URL,              # Where to send task messages
    backend=REDIS_URL,             # Where to store task results/status
)

# Celery configuration
celery_app.conf.update(
    # How long to keep task results in Redis (1 hour)
    # After this, Redis deletes the result to save memory
    result_expires=3600,

    # Serialize task messages as JSON (human-readable, easier to debug)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # If a task raises an exception, don't automatically retry it
    # (we handle errors explicitly inside the task)
    task_acks_late=True,
)


# =============================================================================
# JOB STATUS HELPERS
# =============================================================================
# We store job progress in Redis ourselves (separate from Celery's built-in
# result backend) because we need fine-grained step updates, not just
# "pending/running/done".
#
# Key format: "job:{job_id}:status"
# Value: JSON string with step, message, pct, meeting_id, error

def _status_key(job_id: str) -> str:
    """Redis key for a job's status."""
    return f"job:{job_id}:status"


def set_job_status(job_id: str, status: dict) -> None:
    """
    Write job status to Redis.
    Uses the Celery app's Redis connection (no extra redis-py import needed).

    status dict shape:
        {
            "step":       str,   # "queued" | "extract" | "transcribe" | "intel" | "index" | "done" | "error"
            "message":    str,   # human-readable description
            "pct":        int,   # 0-100 progress percentage
            "meeting_id": int | None,
            "error":      str | None,
        }
    """
    try:
        # Get Redis connection from Celery's broker
        # celery_app.backend.client is the redis-py client Celery already has open
        redis_client = celery_app.backend.client
        redis_client.setex(
            _status_key(job_id),
            3600,                      # expire after 1 hour
            json.dumps(status),
        )
    except Exception as e:
        logger.warning(f"Could not write job status to Redis: {e}")


def get_job_status(job_id: str) -> dict | None:
    """
    Read job status from Redis.
    Returns None if the job_id doesn't exist (expired or never created).
    """
    try:
        redis_client = celery_app.backend.client
        raw = redis_client.get(_status_key(job_id))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Could not read job status from Redis: {e}")
        return None


# =============================================================================
# THE CELERY TASK
# =============================================================================
# @celery_app.task turns a regular Python function into a Celery task.
# When you call process_meeting_task.delay(...), Celery:
#   1. Serializes the arguments to JSON
#   2. Sends them to Redis
#   3. Returns immediately (doesn't wait for the function to run)
#   4. A worker process picks up the message and actually runs the function
#
# bind=True gives the task access to `self` — useful for getting the task ID
# and for updating task state.
#
# The function signature uses only JSON-serializable types (str, int, bool)
# because Celery sends arguments through Redis as JSON.

@celery_app.task(bind=True, name="summly.process_meeting")
def process_meeting_task(
    self,
    job_id: str,
    file_path: str,       # Absolute path to the saved file on disk
    filename: str,        # Original filename (e.g. "standup.mp4")
    user_id: int,
    enable_audio_cleaning: bool = True,
):
    """
    Background Celery task: transcribe a meeting file and run full intelligence pipeline.

    This runs the EXACT same steps as _run_with_progress() in main.py,
    but in a background worker process instead of in FastAPI's async loop.

    Steps:
        1.  Extract audio (FFmpeg)
        2.  Transcribe (faster-whisper)
        3.  Save transcript to SQLite
        4.  Generate intelligence (Groq LLM agents)
        5.  Save intelligence to SQLite
        6.  Index transcript into ChromaDB
        7.  Mark job as done

    Progress updates are written to Redis at each step.
    The /jobs/{job_id}/status endpoint reads these updates.

    Args:
        job_id                : unique ID for this job (generated by FastAPI)
        file_path             : where the file was saved (e.g. "uploads/video/standup.mp4")
        filename              : original filename
        user_id               : the authenticated user who uploaded it
        enable_audio_cleaning : whether to apply audio cleanup before transcription
    """

    def update(step: str, message: str, pct: int, meeting_id=None, error=None):
        """Write a progress update to Redis."""
        set_job_status(job_id, {
            "step":       step,
            "message":    message,
            "pct":        pct,
            "meeting_id": meeting_id,
            "error":      error,
        })
        logger.info(f"[Task {job_id}] {pct}% — {message}")

    try:
        # ── Step 1: Audio extraction ────────────────────────────────────────
        update("extract", "Extracting audio...", 10)

        from server.core.transcription.audio_extractor import extract_audio

        file_path_obj = Path(file_path)
        ext = file_path_obj.suffix.lower().lstrip(".")

        VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}
        AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "aac"}

        if ext in VIDEO_EXTENSIONS:
            wav_path = extract_audio(
                str(file_path_obj),
                enable_cleaning=enable_audio_cleaning,
            )
        elif ext in AUDIO_EXTENSIONS:
            # Audio files go straight to transcription — no extraction needed
            wav_path = str(file_path_obj)
        else:
            raise ValueError(f"Unsupported file type: .{ext}")

        # ── Step 2: Transcription ───────────────────────────────────────────
        update("transcribe", "Transcribing audio (this takes a few minutes)...", 30)

        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_path)

        update("transcribe", "Transcription complete", 45)

        # ── Step 3: Save transcript to SQLite ───────────────────────────────
        from server.core.database import save_transcript_and_get_id
        meeting_id = save_transcript_and_get_id(
            filename=filename,
            transcript=transcript,
            duration=None,
            user_id=user_id,
        )

        update("intel", "Generating meeting intelligence...", 60, meeting_id=meeting_id)

        # ── Step 4+5: Intelligence pipeline ────────────────────────────────
        from server.core.intelligence.workflow import analyze_transcript
        from server.core.database import save_meeting_intelligence

        intelligence = analyze_transcript(transcript)
        save_meeting_intelligence(meeting_id, intelligence)

        update("intel", "Intelligence saved", 78, meeting_id=meeting_id)

        # ── Step 6: ChromaDB indexing ───────────────────────────────────────
        update("index", "Indexing for RAG search...", 88, meeting_id=meeting_id)

        try:
            from server.core.rag.indexer import index_meeting
            index_meeting(
                meeting_id=meeting_id,
                filename=filename,
                transcript=transcript,
                created_at="",
            )
        except Exception as e:
            # Indexing failure is non-fatal — same behaviour as _run_with_progress
            logger.warning(f"[Task {job_id}] ChromaDB index failed (non-fatal): {e}")

        # ── Step 7: Done ────────────────────────────────────────────────────
        update("done", "Processing complete!", 100, meeting_id=meeting_id)
        return {"meeting_id": meeting_id, "status": "done"}

    except Exception as e:
        logger.error(f"[Task {job_id}] Failed: {type(e).__name__}: {e}")
        update("error", str(e), 0, error=str(e))
        # Re-raise so Celery marks the task as FAILED in its result backend
        raise