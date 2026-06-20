# server/core/storage.py
#
# New file. Create it at exactly that path.
# This module handles all file uploads to Supabase Storage.
# The rest of your code never talks to Supabase directly — it calls
# functions from this file only.
#
# WHY ISOLATE IT HERE?
#   If you ever want to switch from Supabase to AWS S3 or Cloudflare R2,
#   you only change this one file. Nothing in main.py changes.

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Supabase bucket name — matches what you created in the dashboard
BUCKET = os.getenv("SUPABASE_BUCKET", "meeting-files")

# We create the client lazily (on first use) because importing supabase
# at module load time would crash the server if credentials aren't set yet
_client = None


def _get_client():
    """
    Returns the Supabase client, creating it on first call.

    WHY LAZY INITIALIZATION?
        If we created the client at import time (module level), the server
        would crash at startup whenever SUPABASE_URL isn't set — like
        during tests, or a developer's first run before they've set up .env.
        Lazy init means the error only happens when you actually try to
        upload something.
    """
    global _client
    if _client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise RuntimeError(
                "Supabase credentials not set.\n"
                "Add these to your .env file:\n"
                "  SUPABASE_URL=https://your-project.supabase.co\n"
                "  SUPABASE_SERVICE_KEY=eyJ...\n"
                "  SUPABASE_BUCKET=meeting-files\n"
                "Get them from: Supabase dashboard → Settings → API"
            )

        _client = create_client(url, key)
        logger.info(f"Supabase client initialized (bucket: {BUCKET})")

    return _client


def upload_file(local_path: str, filename: str) -> str:
    """
    Upload a file from your server's disk to Supabase Storage.
    Returns the public URL of the uploaded file.

    HOW IT WORKS:
        1. Read the file from local_path into memory as bytes
        2. Send those bytes to Supabase via their Storage API
        3. Return the public URL so you can save it to the database

    Args:
        local_path : path to the file on disk, e.g. "uploads/audio/standup.wav"
        filename   : what to name it in Supabase, e.g. "user_5/standup.wav"
                     (including a user subfolder keeps things organised)

    Returns:
        Public URL string like:
        "https://abcdef.supabase.co/storage/v1/object/public/meeting-files/user_5/standup.wav"
    """
    client = _get_client()

    with open(local_path, "rb") as f:
        file_bytes = f.read()

    # Guess the MIME type from the file extension
    # Supabase uses this to serve the file with the right Content-Type header
    ext = Path(filename).suffix.lower()
    content_type_map = {
        ".wav":  "audio/wav",
        ".mp3":  "audio/mpeg",
        ".m4a":  "audio/mp4",
        ".mp4":  "video/mp4",
        ".mov":  "video/quicktime",
        ".avi":  "video/x-msvideo",
        ".webm": "video/webm",
    }
    content_type = content_type_map.get(ext, "application/octet-stream")

    logger.info(f"Uploading {filename} to Supabase bucket '{BUCKET}'...")

    # upsert=True means: overwrite if a file with this name already exists
    # Without upsert, re-uploading the same filename raises an error
    client.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    # Build the public URL
    # Supabase public bucket URLs follow this exact pattern
    url = os.getenv("SUPABASE_URL").rstrip("/")
    public_url = f"{url}/storage/v1/object/public/{BUCKET}/{filename}"

    logger.info(f"Uploaded successfully: {public_url}")
    return public_url


def upload_bytes(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Upload raw bytes directly to Supabase (no local file needed).
    Use this when you have the file in memory and don't want to write it to disk first.

    Args:
        file_bytes   : the file content as bytes
        filename     : destination path in the bucket, e.g. "user_5/standup.wav"
        content_type : MIME type, e.g. "audio/wav"

    Returns:
        Public URL string
    """
    client = _get_client()

    client.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    url = os.getenv("SUPABASE_URL").rstrip("/")
    return f"{url}/storage/v1/object/public/{BUCKET}/{filename}"


def delete_file(filename: str) -> None:
    """
    Delete a file from Supabase Storage.
    Use this when a user deletes their meeting — clean up the file too.

    Does NOT raise an error if the file doesn't exist (idempotent).
    """
    try:
        client = _get_client()
        client.storage.from_(BUCKET).remove([filename])
        logger.info(f"Deleted from Supabase: {filename}")
    except Exception as e:
        # Log but don't crash — a missing file isn't fatal
        logger.warning(f"Could not delete {filename} from Supabase: {e}")


def get_public_url(filename: str) -> str:
    """
    Get the public URL for an already-uploaded file.
    No network call — just builds the URL from the filename.

    Use this when you have the filename stored in the database
    and need to give the user a download link.
    """
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    return f"{url}/storage/v1/object/public/{BUCKET}/{filename}"