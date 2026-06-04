from pathlib import Path
import subprocess
import sys
import re
import os
import logging

import yt_dlp

logger = logging.getLogger(__name__)

# ── Cookie configuration ──────────────────────────────────────────────────────
# Set YT_COOKIES_PATH env var to point to your exported cookies.txt (optional).
# Even without cookies, the android_vr client chain below avoids bot detection
# for most public videos.
COOKIES_PATH = os.getenv("YT_COOKIES_PATH", "/app/cookies/youtube_cookies.txt")

# ── Player client fallback chain ──────────────────────────────────────────────
# Current working order as of 2026 (YouTube kills clients progressively):
#   1. android_vr  — no PO token required, bypasses bot detection for most videos
#   2. web_embedded — fallback for "made for kids" videos android_vr can't access
#   3. mweb        — mobile web, last resort
#
# DO NOT use: ios (broken), tv_embedded (removed 2026.01.29), android_sdkless
#
# This list is the first thing to update when a client gets blocked.
# Check: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/youtube.py
PLAYER_CLIENTS = "android_vr,web_embedded,mweb"


def _ensure_yt_dlp_updated() -> None:
    """
    Auto-update yt-dlp to the latest version on startup.
    YouTube patches its bot-detection frequently — a stale yt-dlp is the
    #1 cause of recurring failures even when everything else is correct.

    Safe to call on every app startup; yt-dlp no-ops if already current.
    Only runs once per process (guarded by module-level flag).
    """
    if getattr(_ensure_yt_dlp_updated, "_done", False):
        return
    _ensure_yt_dlp_updated._done = True

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade",
             "yt-dlp", "--quiet", "--break-system-packages"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            logger.info("yt-dlp is up to date.")
        else:
            logger.warning("yt-dlp auto-update failed: %s", result.stderr.strip())
    except Exception as exc:
        # Never crash the app because of a failed update check
        logger.warning("yt-dlp auto-update skipped: %s", exc)


# ── Shared yt-dlp options builder ─────────────────────────────────────────────
# Single source of truth. Both extract_info() and download() use this.
# Never build bare inline dicts — cookies and extractor_args get silently
# dropped when you do that.

def _base_ydl_opts(output_template: str | None = None) -> dict:
    """
    Returns the base yt-dlp options dict with:
      - android_vr → web_embedded → mweb client fallback chain
      - cookies injected if the file exists
      - retries configured

    Args:
        output_template: yt-dlp outtmpl string. Pass None for metadata-only calls.
    """
    opts: dict = {
        "quiet": True,
        "no_warnings": False,
        "retries": 5,
        "fragment_retries": 5,
        # ── Core bot-detection bypass ──────────────────────────────────────
        # android_vr client does not require PO tokens and currently bypasses
        # YouTube's bot check for the vast majority of public videos.
        # web_embedded is the fallback for videos android_vr can't access
        # (e.g. "made for kids"). mweb is the last resort.
        "extractor_args": {
            "youtube": {
                "player_client": [PLAYER_CLIENTS],
            }
        },
    }

    # Cookies are optional but help with age-restricted / private videos.
    # They are NOT the primary bot bypass — the client chain above handles that.
    if os.path.exists(COOKIES_PATH):
        opts["cookiefile"] = COOKIES_PATH
        logger.debug("yt-dlp: using cookies from %s", COOKIES_PATH)

    if output_template is not None:
        opts["outtmpl"] = output_template

    return opts


# ── Filename sanitizer ────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Strip characters illegal on Windows/Linux/macOS filesystems."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "untitled"


# ── Main download function ────────────────────────────────────────────────────

def download_youtube(
    url: str,
    output_dir: str = "uploads/audio",
) -> dict:
    """
    Downloads a YouTube video's audio as an MP3.

    Bot-detection strategy (layered):
      Layer 1 — android_vr player client (no PO token required, bypasses checks)
      Layer 2 — web_embedded + mweb as automatic fallbacks
      Layer 3 — cookies file if present (for restricted content)
      Layer 4 — yt-dlp auto-updated on startup (patches n-challenge solver)
      Layer 5 — yt-dlp-invidious plugin reroutes via Invidious on final failure
                 (install with: pip install yt-dlp-invidious)

    Args:
        url:        Full YouTube URL.
        output_dir: Directory to write the MP3 into. Created if absent.

    Returns:
        dict with keys:
          - title      (str)  sanitized video title
          - audio_file (str)  absolute path to the output .mp3
          - duration   (int)  video duration in seconds (0 if unavailable)

    Raises:
        yt_dlp.utils.DownloadError: if all layers fail
        ValueError:                 if URL is empty or metadata is invalid
    """
    if not url or not url.strip():
        raise ValueError("YouTube URL must not be empty.")

    # Auto-update yt-dlp once per process lifetime — this is the single most
    # important step. YouTube deploys n-challenge updates frequently; an
    # outdated yt-dlp fails even with valid cookies and correct client args.
    _ensure_yt_dlp_updated()

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ── Step 1: fetch metadata ────────────────────────────────────────────────
    # Must use _base_ydl_opts() here — NOT a bare {"quiet": True}.
    # The extractor_args with player_client must be present on this call too,
    # because YouTube's bot check fires at the metadata fetch, not just download.
    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        logger.error("yt-dlp metadata fetch failed for %s: %s", url, exc)
        raise

    if not info or "title" not in info:
        raise ValueError(f"Could not extract metadata from URL: {url}")

    title    = sanitize_filename(info["title"])
    duration = info.get("duration", 0) or 0

    # ── Step 2: build output path ─────────────────────────────────────────────
    output_template = str(Path(output_dir) / f"{title}.%(ext)s")
    audio_file      = str(Path(output_dir) / f"{title}.mp3")

    # ── Step 3: download + convert ────────────────────────────────────────────
    download_opts = _base_ydl_opts(output_template=output_template)
    download_opts.update({
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    })

    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        logger.error("yt-dlp download failed for %s: %s", url, exc)
        raise

    if not Path(audio_file).exists():
        raise FileNotFoundError(
            f"Download succeeded but output file not found: {audio_file}"
        )

    logger.info("Downloaded '%s' → %s (%ss)", title, audio_file, duration)

    return {
        "title":      title,
        "audio_file": audio_file,
        "duration":   duration,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    url = input("Enter YouTube URL: ").strip()

    try:
        result = download_youtube(url)
        print(f"\n✓ Title:    {result['title']}")
        print(f"  File:     {result['audio_file']}")
        print(f"  Duration: {result['duration']}s")
    except yt_dlp.utils.DownloadError as e:
        print(f"\n✗ Download failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)