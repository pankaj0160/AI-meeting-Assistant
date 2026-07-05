# server/core/storage.py
#
# Handles all file uploads/downloads/deletes to Supabase Storage.
# The rest of your code never talks to Supabase directly — it calls
# functions from this file only.

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BUCKET = os.getenv("SUPABASE_BUCKET", "meeting-files")

_client = None


class StorageError(Exception):
    """Raised when a Supabase Storage operation fails."""
    pass


def _get_client():
    """
    Returns the Supabase client, creating it on first call (lazy init).
    Raises RuntimeError clearly if credentials are missing.
    """
    global _client
    if _client is None:
        try:
            from supabase import create_client
        except ImportError:
            raise RuntimeError(
                "supabase-py is not installed. Run: pip install supabase"
            )

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
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

        if not url.startswith("https://"):
            raise RuntimeError(
                f"SUPABASE_URL looks wrong: '{url}'\n"
                "It must start with https://"
            )

        _client = create_client(url, key)
        logger.info(f"Supabase client initialized (bucket: {BUCKET})")

    return _client


def _check_response(response, operation: str, filename: str) -> None:
    """
    Inspect a Supabase storage response and raise StorageError on failure.

    The supabase-py SDK (v1 and v2) returns different shapes:
      - v1: a dict like {"data": {...}} or {"error": {"message": "..."}}
      - v2: raises an exception directly on failure

    This handles both.
    """
    if response is None:
        raise StorageError(f"{operation} returned None for '{filename}'")

    # v1 SDK: response is a dict
    if isinstance(response, dict):
        error = response.get("error")
        if error:
            # error can be a dict {"message": "..."} or a string
            msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            raise StorageError(f"{operation} failed for '{filename}': {msg}")


def _guess_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".wav":  "audio/wav",
        ".mp3":  "audio/mpeg",
        ".m4a":  "audio/mp4",
        ".mp4":  "video/mp4",
        ".mov":  "video/quicktime",
        ".avi":  "video/x-msvideo",
        ".webm": "video/webm",
        ".pdf":  "application/pdf",
        ".txt":  "text/plain",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")


def _build_public_url(filename: str) -> str:
    """Construct the public URL without any extra slashes."""
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    # filename may already have a leading slash — strip it to be safe
    clean = filename.lstrip("/")
    return f"{base}/storage/v1/object/public/{BUCKET}/{clean}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_file(local_path: str, filename: str) -> str:
    """
    Upload a file from disk to Supabase Storage.

    Args:
        local_path : path on disk, e.g. "uploads/audio/standup.wav"
        filename   : destination in bucket, e.g. "user_5/standup.wav"

    Returns:
        Public URL string.

    Raises:
        FileNotFoundError : if local_path doesn't exist
        StorageError      : if the upload fails
    """
    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {local_path}")

    file_bytes = path.read_bytes()
    content_type = _guess_content_type(filename)

    logger.info(f"Uploading '{filename}' ({len(file_bytes):,} bytes) to bucket '{BUCKET}'...")

    try:
        client = _get_client()
        response = client.storage.from_(BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        _check_response(response, "upload_file", filename)
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"upload_file failed for '{filename}': {e}") from e

    public_url = _build_public_url(filename)
    logger.info(f"Upload successful: {public_url}")
    return public_url


def upload_bytes(file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> str:
    """
    Upload raw bytes to Supabase (no local file needed).

    Args:
        file_bytes   : file content as bytes
        filename     : destination path in bucket, e.g. "user_5/standup.wav"
        content_type : MIME type; auto-detected from filename if omitted

    Returns:
        Public URL string.

    Raises:
        StorageError : if the upload fails
    """
    if not file_bytes:
        raise ValueError("file_bytes must not be empty")

    ct = content_type or _guess_content_type(filename)

    logger.info(f"Uploading bytes '{filename}' ({len(file_bytes):,} bytes) to bucket '{BUCKET}'...")

    try:
        client = _get_client()
        response = client.storage.from_(BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": ct, "upsert": "true"},
        )
        _check_response(response, "upload_bytes", filename)
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"upload_bytes failed for '{filename}': {e}") from e

    public_url = _build_public_url(filename)
    logger.info(f"Upload successful: {public_url}")
    return public_url


def delete_file(filename: str) -> None:
    """
    Delete a file from Supabase Storage.
    Idempotent — does not raise if the file doesn't exist.

    Raises:
        StorageError : if deletion fails for a reason other than "not found"
    """
    try:
        client = _get_client()
        response = client.storage.from_(BUCKET).remove([filename])
        _check_response(response, "delete_file", filename)
        logger.info(f"Deleted from Supabase: '{filename}'")
    except StorageError as e:
        msg = str(e).lower()
        if "not found" in msg or "does not exist" in msg:
            logger.warning(f"File already gone (skipping): '{filename}'")
        else:
            raise
    except Exception as e:
        # Log but don't crash — a failed delete shouldn't break the caller
        logger.warning(f"Could not delete '{filename}' from Supabase: {e}")


def get_public_url(filename: str) -> str:
    """
    Build the public URL for an already-uploaded file.
    Pure string construction — no network call.
    """
    return _build_public_url(filename)


def bucket_exists() -> bool:
    """
    Health-check helper: returns True if the bucket is reachable.
    Call this from your /health endpoint to surface misconfigurations early.
    """
    try:
        client = _get_client()
        client.storage.from_(BUCKET).list()
        return True
    except Exception as e:
        logger.error(f"Bucket '{BUCKET}' health check failed: {e}")
        return False