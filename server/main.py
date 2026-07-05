"""
Summly FastAPI Backend
Phase 2 Complete with Meeting Intelligence Engine
"""

# ── Structured logging — must be first ────────────────────────────────────────
from server.core.logging_config import setup_logging
setup_logging()

try:
    import structlog
    mlog = structlog.get_logger("server.main")
except ImportError:
    # structlog not installed — use standard logging as fallback
    import logging as _std_logging
    mlog = _std_logging.getLogger("server.main")

# slog is an alias used in some older parts of the codebase
slog = mlog

# ── Standard library ──────────────────────────────────────────────────────────
import uuid
import time
import os
import datetime
import asyncio
import io
import logging
import traceback

# ── Third-party ───────────────────────────────────────────────────────────────
import shutil
from pathlib import Path
from typing import Optional

from fastapi import (
    Depends, FastAPI, Request, UploadFile, File,
    HTTPException, WebSocket, WebSocketDisconnect, Query,
)
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException as FastAPIHTTPException
from pydantic import BaseModel, HttpUrl
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _SLOWAPI = True
except ImportError:
    # slowapi not installed — rate limiting disabled, server still works
    _SLOWAPI = False
    class RateLimitExceeded(Exception): pass
    def get_remote_address(request): return "0.0.0.0"
    def _rate_limit_exceeded_handler(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "rate_limited"}, status_code=429)
    class Limiter:
        def __init__(self, **kw): pass
        def limit(self, *a, **kw):
            def decorator(fn): return fn
            return decorator

# ── Internal ──────────────────────────────────────────────────────────────────
from server.core.auth.dependencies import get_current_user, get_optional_user
from server.core.auth.models import User
from server.core.auth.router import router as auth_router
from server.core.storage import upload_file as upload_to_supabase

# FIX: import celery_app at top level — it was used in reindex/status endpoints
# but never imported, causing NameError: name 'celery_app' is not defined
try:
    from server.core.tasks import celery_app, set_job_status, get_job_status
except ImportError:
    celery_app = None

# Direct Redis client helper — works even if celery_app fails to import
def _get_redis():
    """
    Return a connected Redis client, or None if Redis is not reachable.

    FIX: redis.from_url() only creates a client object — it does NOT connect.
    The connection happens on the first actual command (.ping()).
    Old code: always returned a client even when Redis was offline,
    causing every subsequent .get()/.setex() call to fail with a
    ConnectionError that propagated as HTTP 500.
    New code: tests the connection with .ping() — returns None if Redis
    is not running so callers can degrade gracefully.
    """
    try:
        import redis as _redis
        url    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = _redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
        client.ping()   # actually test the connection — raises if Redis is down
        return client
    except Exception:
        return None   # Redis not available — callers handle this gracefully


# ── In-memory job store (Redis fallback) ──────────────────────────────────────
# When Redis is not running (local dev on Windows without Redis),
# job progress is stored in this plain Python dict.
# Works perfectly for single-process Uvicorn dev mode.
# In production with multiple workers, use Redis via REDIS_URL env var.
_mem_jobs: dict[str, dict] = {}

def _write_job_status(job_id: str, status: dict) -> None:
    """Write progress to Redis if available, else to in-memory dict."""
    import json as _json
    rc = _get_redis()
    if rc:
        try:
            rc.setex(f"job:{job_id}:status", 3600, _json.dumps(status))
            return
        except Exception:
            pass
    # Redis unavailable — fall back to in-memory
    _mem_jobs[job_id] = status

def _read_job_status(job_id: str) -> dict | None:
    """Read progress from Redis if available, else from in-memory dict."""
    import json as _json
    rc = _get_redis()
    if rc:
        try:
            raw = rc.get(f"job:{job_id}:status")
            if raw:
                return _json.loads(raw)
        except Exception:
            pass
    # Redis unavailable — fall back to in-memory
    return _mem_jobs.get(job_id)


from server.core.database import (
    init_db,
    get_all_transcripts,
    get_user_stats,           # FIX: replaces N+1 stats loop
    get_meetings_page,         # FIX: paginated meetings list
    get_tasks_page,            # FIX: paginated tasks list
    get_analytics_data,        # Analytics page — single query
    save_transcript_and_get_id,
    save_meeting_intelligence,
    get_meeting_intelligence,
    get_meeting_by_id,
    get_all_action_items,
    get_action_items_by_meeting,
    update_action_item_fields,
    delete_action_item,
    get_action_item_stats,
    save_diarization,
    get_diarization,
    save_meeting_health,
    get_meeting_health,
    save_meeting_quotes,
    get_meeting_quotes,
    save_meeting_title,
    get_meeting_title,
    update_action_item_status,
    get_all_meetings_for_indexing,
    delete_meeting,           # FIX: was missing entirely — no way to delete a meeting existed
    get_meeting_owner_map,    # FIX: used to backfill + vacuum ChromaDB ownership (vacuum endpoint)
    # ── Week 5: Workspaces ──────────────────────────────
    create_workspace,
    get_workspaces_for_user,
    get_workspace_by_id,
    update_workspace,
    delete_workspace,
    add_meeting_to_workspace,
    remove_meeting_from_workspace,
    get_meetings_in_workspace,
    get_workspace_for_meeting,
    # ── Week 6 ──────────────────────────────────────
    get_workspace_members,
    invite_member_to_workspace,
    remove_member_from_workspace,
    create_webhook,
    get_webhooks_for_user,
    delete_webhook,
    get_webhook_events,
    write_audit_log,
    get_audit_logs,
    export_user_data,
    delete_user_data,
    # FIX: get_sentiment_analysis was defined in core/database.py but never
    # imported here — every call to GET /meetings/{id}/sentiment raised
    # NameError: name 'get_sentiment_analysis' is not defined and returned
    # a 500. (save_sentiment_analysis doesn't need importing here — it's
    # only called from within core/intelligence/sentiment.py itself.)
    get_sentiment_analysis,
)

from server.core.intelligence.health   import analyze_meeting_health
from server.core.intelligence.quotes   import extract_key_quotes
from server.core.intelligence.titles   import generate_meeting_title
from server.core.intelligence.followup import generate_followup_email

# ── Lazy-loaded at first use (heavy AI / ML deps) ─────────────────────────────
# from server.core.transcription.audio_extractor import extract_audio
# from server.core.transcription.transcribe import transcribe_audio
# from server.core.transcription.youtube_downloader import download_youtube
# from server.core.intelligence.workflow import analyze_transcript
# from server.core.rag.indexer import index_meeting
# from server.core.rag.chat import chat_with_meeting, chat_across_meetings
# ─────────────────────────────────────────────────────────────────────────────


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)


# =====================================================
# APP SETUP
# =====================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app_instance):
    """
    Server startup / shutdown lifecycle.

    STARTUP — runs once when uvicorn starts:
      Warms Whisper and the embedding model in background threads.
      Both are large models that take 5-15 seconds to load from disk.
      Loading them NOW means the first upload request is instant instead
      of making the first user wait 15+ seconds.

      Why threads (not asyncio)?
        Both model loads are synchronous C extensions.
        Running them in the event loop would block all other requests
        during the load window. Threads keep the event loop free.

      Why background (not blocking startup)?
        Server becomes ready to accept health-check requests immediately.
        Warmup happens in parallel with the first requests.
        If warmup fails (missing HF_TOKEN, disk issue), the server still
        starts — diarization just won't work until the issue is fixed.
    """
    import threading

    def _warm_whisper():
        try:
            from server.core.transcription.transcribe import warmup as whisper_warmup
            whisper_warmup()
        except Exception as e:
            logger.warning("Whisper warmup failed (non-fatal): %s", e)

    def _warm_embedder():
        try:
            from server.core.rag.embedder import get_embedding_model
            get_embedding_model()
            logger.info("Embedding model warmup complete")
        except Exception as e:
            logger.warning("Embedding model warmup failed (non-fatal): %s", e)

    # Start both warmups in parallel — they are independent
    t1 = threading.Thread(target=_warm_whisper,  daemon=True, name="warmup-whisper")
    t2 = threading.Thread(target=_warm_embedder, daemon=True, name="warmup-embedder")
    t1.start()
    t2.start()
    logger.info("Model warmup threads started (whisper + embedder)")

    yield   # server runs here

    # SHUTDOWN — nothing to clean up (models release on process exit)
    logger.info("Summly server shutting down")


app = FastAPI(
    title       = "Summly API",
    version     = "2.0.0",
    description = "AI Meeting Intelligence Platform Backend",
    lifespan    = lifespan,
)


# ── Request logging middleware ────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with timing and a unique request_id.
    The request_id is returned in the X-Request-ID response header.
    """
    async def dispatch(self, request: StarletteRequest, call_next):
        request_id = str(uuid.uuid4())[:8]
        start      = time.perf_counter()

        response    = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        mlog.info(
            "request_complete",
            request_id  = request_id,
            method      = request.method,
            path        = request.url.path,
            status      = response.status_code,
            duration_ms = duration_ms,
            user_agent  = request.headers.get("user-agent", ""),
        )

        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestLoggingMiddleware)


# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── CORS ──────────────────────────────────────────────────────────────────────
#
# FIX: allow_origins=["*"] replaced with explicit allowed origins.
#
# allow_origins=["*"] means ANY website can call your API from a user's browser.
# Combined with allow_credentials=True this is also a browser contradiction —
# browsers refuse to send credentials to a wildcard origin, so some requests
# were already silently failing.
#
# HOW TO CONFIGURE:
#   In your .env file set:
#     ALLOWED_ORIGINS=http://localhost:5173,https://yourapp.com
#
#   Development default (if not set): http://localhost:5173
#   Production: set it to your real frontend domain only.
#
# WHY AN ENVIRONMENT VARIABLE?
#   Your frontend URL is different in development vs production.
#   Environment variables let you change it without touching code.

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"   # safe development default
)

# Split by comma, strip whitespace from each entry
# e.g. "http://localhost:5173, https://summly.app" → two separate origins
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    # FIX: explicit list instead of wildcard "*"
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)


# ── Database + router init ────────────────────────────────────────────────────

init_db()
logger.info("Database initialized")

app.include_router(auth_router)


# =====================================================
# REQUEST / RESPONSE MODELS
# =====================================================

class ContactRequest(BaseModel):
    name:    str
    email:   str
    subject: str
    message: str


class YouTubeRequest(BaseModel):
    url: HttpUrl

    class Config:
        json_schema_extra = {
            "example": {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        }


class ChatRequest(BaseModel):
    query:      str
    meeting_id: int | None = None


class AgentRequest(BaseModel):
    query:      str
    meeting_id: int


class UpdateActionItemRequest(BaseModel):
    owner:    str | None = None
    deadline: str | None = None
    priority: str | None = None   # high | medium | low
    status:   str | None = None   # open | in_progress | done | overdue



class InviteMemberRequest(BaseModel):
    email: str
    role:  str = "member"


class CreateWebhookRequest(BaseModel):
    url:    str
    events: list[str]


class DeleteAccountRequest(BaseModel):
    confirm: str


class AuditLogFilter(BaseModel):
    resource_type: str | None = None
    resource_id:   int | None = None
    limit:         int        = 100


class CreateWorkspaceRequest(BaseModel):
    name:        str
    description: str = ""
    type:        str = "individual"   # "individual" or "project"
    color:       str = "#10b981"      # FIX: was indigo, now matches frontend default


class UpdateWorkspaceRequest(BaseModel):
    name:        str | None = None
    description: str | None = None
    color:       str | None = None


class IntelligenceResponse(BaseModel):
    summary:      str
    action_items: list = []
    decisions:    list = []
    topics:       list = []
    generated_at: str


class MeetingBasic(BaseModel):
    id:               int
    filename:         str
    created_at:       str
    duration_seconds: float | None = None


class TranscriptResponse(BaseModel):
    meeting_id:      int
    filename:        str
    transcript_file: str
    transcript:      str
    intelligence:    IntelligenceResponse | None = None
    processing_time: float
    file_size_mb:    float


class YouTubeResponse(BaseModel):
    meeting_id:      int
    title:           str
    transcript_file: str
    transcript:      str
    intelligence:    IntelligenceResponse | None = None
    processing_time: float


class MeetingDetail(BaseModel):
    id:               int
    filename:         str
    transcript:       str
    created_at:       str
    duration_seconds: float | None = None
    intelligence:     IntelligenceResponse | None = None


class ProgressRequest(BaseModel):
    job_id: str


# =====================================================
# CONFIGURATION
# =====================================================

VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "webm", "m4v"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac", "flac", "ogg"}
MAX_FILE_SIZE    = 500 * 1024 * 1024   # 500 MB

AUDIO_DIR      = Path("uploads/audio")
VIDEO_DIR      = Path("uploads/video")
TRANSCRIPT_DIR = Path("uploads/transcripts")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Upload directories ready: {AUDIO_DIR}, {VIDEO_DIR}, {TRANSCRIPT_DIR}")


# =====================================================
# HELPERS
# =====================================================

def get_intelligence_for_response(meeting_id: int) -> IntelligenceResponse | None:
    """Fetch intelligence from DB and wrap in the response model."""
    try:
        intel = get_meeting_intelligence(meeting_id)
        if intel:
            return IntelligenceResponse(
                summary      = intel.get("summary", ""),
                action_items = intel.get("action_items", []),
                decisions    = intel.get("decisions", []),
                topics       = intel.get("topics", []),
                generated_at = intel.get("generated_at", ""),
            )
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch intelligence for meeting {meeting_id}: {e}")
        return None


# =====================================================
# SYSTEM ENDPOINTS
# =====================================================

@app.get("/", tags=["System"])
def root():
    return {
        "service":  "Summly Backend",
        "version":  "2.0.0",
        "status":   "running",
        "features": ["Audio Upload", "YouTube Download", "Speech-to-Text", "Meeting Intelligence"],
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/stats", tags=["System"])
def get_stats(current_user: User = Depends(get_current_user)):
    """
    Aggregate stats across all meetings for the logged-in user.

    FIX: N+1 query problem removed.

    Old code: fetched all meetings, then looped calling get_meeting_intelligence()
    for every single meeting — 1 DB query + N queries (one per meeting).
    With 50 meetings = 51 queries on every dashboard load.

    New code: calls get_user_stats() which runs ONE SQL query using JOINs
    and COUNT() to get all four numbers at once. Always 1 query, any scale.
    """
    try:
        return get_user_stats(user_id=current_user.id)
    except Exception as e:
        logger.error(f"Stats failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


# =====================================================
# ACTION ITEM ENDPOINTS
# =====================================================

@app.get("/tasks", tags=["Action Items"])
def get_all_tasks(
    current_user: User       = Depends(get_current_user),
    limit:        int        = Query(default=20, ge=1, le=100),
    cursor:       int | None = Query(default=None),
    status:       str | None = Query(default=None),
    priority:     str | None = Query(default=None),
    owner:        str | None = Query(default=None),
):
    """
    FIX: Paginated tasks list — returns one page at a time.

    Old: loaded ALL tasks for a user at once. With 500 tasks across
    50 meetings, this was 500 rows in one response every time the
    Tasks page opened.

    New: same cursor-based pagination as /meetings.
    Filters (status, priority, owner) still work — applied in SQL,
    not in Python after loading everything.

    Response shape:
      {
        "items":       [...],   task objects with meeting_filename included
        "has_more":    true,
        "next_cursor": 38,
        "count":       20
      }
    """
    try:
        return get_tasks_page(
            user_id=current_user.id,
            limit=limit,
            cursor=cursor,
            status=status,
            priority=priority,
            owner=owner,
        )
    except Exception as e:
        logger.error(f"Failed to fetch tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


@app.get("/analytics", tags=["Analytics"])
def get_analytics(current_user: User = Depends(get_current_user)):
    """
    All analytics data in one request.
    Replaces the old N+1 getMeetings + getMeetingIntelligence loop.
    """
    try:
        return get_analytics_data(user_id=current_user.id)
    except Exception as e:
        logger.error(f"Analytics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load analytics")


@app.get("/tasks/stats", tags=["Action Items"])
def get_task_stats(current_user: User = Depends(get_current_user)):
    return get_action_item_stats(user_id=current_user.id)


@app.patch("/tasks/{item_id}", tags=["Action Items"])
def patch_action_item(
    item_id:      int,
    body:         UpdateActionItemRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        updated = update_action_item_fields(
            item_id  = item_id,
            user_id  = current_user.id,
            owner    = body.owner,
            deadline = body.deadline,
            priority = body.priority,
            status   = body.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Action item not found or access denied")

    return {"message": "Updated", "item_id": item_id}


@app.put("/tasks/{item_id}/status", tags=["Action Items"])
def update_task_status(
    item_id:      int,
    body:         dict,
    current_user: User = Depends(get_current_user),
):
    status = body.get("status", "").lower()
    valid  = {"open", "in_progress", "done", "overdue"}

    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")

    updated = update_action_item_status(item_id, status, current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Action item not found or access denied")

    return {"message": "Status updated", "status": status}


@app.delete("/tasks/{item_id}", tags=["Action Items"])
def remove_action_item(
    item_id:      int,
    current_user: User = Depends(get_current_user),
):
    deleted = delete_action_item(item_id=item_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Action item not found or access denied")
    
    write_audit_log(user_id=current_user.id, resource_type="task", resource_id=item_id, action="deleted")

    return {"message": "Deleted", "item_id": item_id}




# =====================================================
# WORKSPACE ENDPOINTS
# =====================================================

@app.post("/workspaces", tags=["Workspaces"])
def create_workspace_endpoint(
    body:         CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
):
    if body.type not in {"individual", "project"}:
        raise HTTPException(status_code=400, detail="type must be 'individual' or 'project'")

    return create_workspace(
        owner_id    = current_user.id,
        name        = body.name,
        description = body.description,
        type        = body.type,
        color       = body.color,
    )


@app.get("/workspaces", tags=["Workspaces"])
def list_workspaces(current_user: User = Depends(get_current_user)):
    return get_workspaces_for_user(user_id=current_user.id)


@app.get("/workspaces/{workspace_id}", tags=["Workspaces"])
def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_by_id(workspace_id, user_id=current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@app.patch("/workspaces/{workspace_id}", tags=["Workspaces"])
def patch_workspace(
    workspace_id: int,
    body:         UpdateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
):
    updated = update_workspace(
        workspace_id = workspace_id,
        owner_id     = current_user.id,
        name         = body.name,
        description  = body.description,
        color        = body.color,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    return {"message": "Workspace updated"}


@app.delete("/workspaces/{workspace_id}", tags=["Workspaces"])
def delete_workspace_endpoint(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
):
    deleted = delete_workspace(workspace_id=workspace_id, owner_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    return {"message": "Workspace deleted"}


@app.get("/workspaces/{workspace_id}/meetings", tags=["Workspaces"])
def list_workspace_meetings(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_by_id(workspace_id, user_id=current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    meetings = get_meetings_in_workspace(workspace_id=workspace_id, user_id=current_user.id)
    return {
        "workspace_id":   workspace_id,
        "workspace_name": workspace["name"],
        "total":          len(meetings),
        "meetings":       meetings,
    }


@app.post("/workspaces/{workspace_id}/meetings/{meeting_id}", tags=["Workspaces"])
def add_meeting_to_workspace_endpoint(
    workspace_id: int,
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    added = add_meeting_to_workspace(
        workspace_id = workspace_id,
        meeting_id   = meeting_id,
        user_id      = current_user.id,
    )
    if not added:
        raise HTTPException(status_code=404, detail="Workspace or meeting not found, or access denied")
    return {"message": "Meeting added to workspace", "workspace_id": workspace_id, "meeting_id": meeting_id}


@app.delete("/workspaces/{workspace_id}/meetings/{meeting_id}", tags=["Workspaces"])
def remove_meeting_from_workspace_endpoint(
    workspace_id: int,
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    removed = remove_meeting_from_workspace(
        workspace_id = workspace_id,
        meeting_id   = meeting_id,
        user_id      = current_user.id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    return {"message": "Meeting removed from workspace"}


# FIX: This endpoint didn't exist — get_workspace_for_meeting() was imported
# above but never wired to a route, so the frontend had no way to find out
# which workspace (if any) a given meeting already belongs to. Without this,
# the MeetingDetail page can't show a meeting's current workspace or offer
# a "move to workspace" action without guessing.
#
# Ownership check: we verify the meeting belongs to current_user via
# get_meeting_by_id() BEFORE looking up its workspace, since
# get_workspace_for_meeting() itself does not check ownership.
@app.get("/meetings/{meeting_id}/workspace", tags=["Workspaces"])
async def get_meeting_workspace_endpoint(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = await asyncio.to_thread(get_meeting_by_id, meeting_id, current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    workspace = await asyncio.to_thread(get_workspace_for_meeting, meeting_id)
    return {"workspace": workspace}




# =====================================================
# WORKSPACE INTELLIGENCE ENDPOINTS
# =====================================================

@app.get("/workspaces/{workspace_id}/intelligence", tags=["Workspaces"])
async def workspace_intelligence(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
):
    from server.core.intelligence.workspace_intel import get_workspace_summary

    result = await asyncio.to_thread(
        get_workspace_summary,
        workspace_id = workspace_id,
        user_id      = current_user.id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    return result


@app.get("/workspaces/{workspace_id}/tasks", tags=["Workspaces"])
def workspace_tasks(
    workspace_id: int,
    status:       str | None = Query(default=None, description="Filter: open / in_progress / done / overdue"),
    current_user: User = Depends(get_current_user),
):
    from server.core.intelligence.workspace_intel import get_workspace_action_items

    result = get_workspace_action_items(workspace_id=workspace_id, user_id=current_user.id)

    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    if status:
        result["items"] = [i for i in result["items"] if i.get("status") == status.lower()]
        result["total"] = len(result["items"])

    return result


@app.post("/workspaces/{workspace_id}/chat", tags=["Workspaces"])
async def workspace_chat(
    workspace_id: int,
    body:         ChatRequest,
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_by_id(workspace_id, user_id=current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    meetings = get_meetings_in_workspace(workspace_id=workspace_id, user_id=current_user.id)

    if not meetings:
        return {
            "answer":         "This workspace has no meetings yet. Add meetings to this workspace first.",
            "sources":        [],
            "meeting_count":  0,
            "workspace_id":   workspace_id,
        }

    meeting_ids = [m["id"] for m in meetings]

    from server.core.rag.hybrid_search import hybrid_search
    from server.core.rag.chat import get_groq_client, MODEL

    all_chunks = []
    for mid in meeting_ids:
        chunks = hybrid_search(query=body.query, meeting_id=mid, top_k=3)
        all_chunks.extend(chunks)

    all_chunks.sort(key=lambda c: c.get("score", 0), reverse=True)
    top_chunks = all_chunks[:8]

    if not top_chunks:
        return {
            "answer":        "I could not find relevant information across this workspace's meetings.",
            "sources":       [],
            "meeting_count": len(meeting_ids),
            "workspace_id":  workspace_id,
        }

    context_parts = []
    for i, chunk in enumerate(top_chunks, 1):
        mtg_name = next(
            (m.get("ai_title") or m["filename"] for m in meetings if m["id"] == chunk.get("meeting_id")),
            f"Meeting {chunk.get('meeting_id')}",
        )
        context_parts.append(f"[{i}] From '{mtg_name}':\n{chunk['text']}")

    context = "\n\n".join(context_parts)

    system = f"""You are an expert assistant for the project workspace "{workspace["name"]}".
You answer questions using ONLY the meeting transcript context provided.
Always mention which meeting the information came from.
If the answer is not in the context, say so clearly."""

    client   = get_groq_client()
    response = client.chat.completions.create(
        model       = MODEL,
        messages    = [
            {"role": "system", "content": system},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {body.query}"},
        ],
        temperature = 0.1,
        max_tokens  = 1024,
    )

    return {
        "answer":         response.choices[0].message.content.strip(),
        "sources":        top_chunks,
        "meeting_count":  len(meeting_ids),
        "workspace_id":   workspace_id,
        "workspace_name": workspace["name"],
    }



@app.get("/workspaces/{workspace_id}/agenda", tags=["Workspaces"])
async def workspace_smart_agenda(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_by_id(workspace_id, user_id=current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    from server.core.intelligence.personalized import generate_smart_agenda

    result = await asyncio.to_thread(
        generate_smart_agenda,
        workspace_id = workspace_id,
        user_id      = current_user.id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    return result


@app.get("/workspaces/{workspace_id}/meetings/{meeting_id}/carry-forward", tags=["Workspaces"])
def get_carry_forward(
    workspace_id: int,
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_by_id(workspace_id, user_id=current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    from server.core.intelligence.personalized import get_carry_forward_items

    result = get_carry_forward_items(
        workspace_id = workspace_id,
        meeting_id   = meeting_id,
        user_id      = current_user.id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    return result


@app.get("/workspaces/{workspace_id}/meetings/{meeting_id}/compare", tags=["Workspaces"])
def compare_meeting_to_workspace(
    workspace_id: int,
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_by_id(workspace_id, user_id=current_user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    from server.core.intelligence.personalized import compare_meeting_health

    result = compare_meeting_health(
        workspace_id = workspace_id,
        meeting_id   = meeting_id,
        user_id      = current_user.id,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    return result




# ─────────────────────────────────────────────────────────────────────────────
# WORKSPACE MEMBER MANAGEMENT (RBAC)
# ─────────────────────────────────────────────────────────────────────────────
 
@app.get("/workspaces/{workspace_id}/members", tags=["Workspaces"])
def list_workspace_members(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    List all members of a workspace and their roles.
 
    Roles:
        owner  → created the workspace, can invite/remove members, delete workspace
        member → can view all meetings and add meetings to the workspace
        viewer → read-only access, cannot add meetings or invite others
 
    Returns 404 if you're not a member of this workspace.
    """
    members = get_workspace_members(workspace_id=workspace_id, user_id=current_user.id)
    if members is None:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
 
    return {
        "workspace_id": workspace_id,
        "total":        len(members),
        "members":      members,
    }
 
 
@app.post("/workspaces/{workspace_id}/members", tags=["Workspaces"])
async def invite_member(
    workspace_id: int,
    body:         InviteMemberRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Invite a user to a workspace by their email address.
 
    Rules:
        - Only workspace owners can invite
        - The invitee must already have a Summly account
        - Valid roles: 'member' or 'viewer' (cannot invite as 'owner')
        - You cannot invite someone who is already a member
 
    After a successful invite:
        - The invited user immediately gains access (no email confirmation needed)
        - They will see the workspace in their GET /workspaces list
        - A webhook event "member.invited" fires if configured
 
    Returns 400 with a clear reason message if the invite fails.
    """
    result = invite_member_to_workspace(
        workspace_id=workspace_id,
        inviter_id=current_user.id,
        invitee_email=body.email,
        role=body.role,
    )
 
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["reason"])
 
    # Write audit log
    write_audit_log(
        user_id=current_user.id,
        resource_type="workspace",
        resource_id=workspace_id,
        action="member_invited",
        metadata={"invitee_email": body.email, "role": body.role},
    )
 
    # Fire webhook event
    from server.core.webhooks import fire_event
    await fire_event(
        user_id=current_user.id,
        event_type="member.invited",
        payload={
            "workspace_id": workspace_id,
            "invitee_email": body.email,
            "invitee_name":  result.get("full_name"),
            "role":          body.role,
        },
    )
 
    return {
        "message":  f"Successfully added {result['full_name']} as {body.role}",
        "user_id":  result["user_id"],
        "email":    result["email"],
        "role":     body.role,
    }
 
 
@app.delete("/workspaces/{workspace_id}/members/{target_user_id}", tags=["Workspaces"])
async def remove_member(
    workspace_id:    int,
    target_user_id:  int,
    current_user:    User = Depends(get_current_user),
):
    """
    Remove a member from a workspace.
 
    Only the workspace owner can do this.
    The owner cannot remove themselves — use DELETE /workspaces/{id} instead.
    The removed user immediately loses access to the workspace.
    Their meetings are not deleted — they just lose access to this workspace.
    """
    removed = remove_member_from_workspace(
        workspace_id=workspace_id,
        owner_id=current_user.id,
        target_user_id=target_user_id,
    )
    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found, you are not the owner, or cannot remove yourself"
        )
 
    write_audit_log(
        user_id=current_user.id,
        resource_type="workspace",
        resource_id=workspace_id,
        action="member_removed",
        metadata={"removed_user_id": target_user_id},
    )
 
    from server.core.webhooks import fire_event
    await fire_event(
        user_id=current_user.id,
        event_type="member.removed",
        payload={"workspace_id": workspace_id, "removed_user_id": target_user_id},
    )
 
    return {"message": "Member removed from workspace"}
 
 
# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOKS
# ─────────────────────────────────────────────────────────────────────────────
 
@app.post("/webhooks", tags=["Webhooks"])
def create_webhook_endpoint(
    body:         CreateWebhookRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Register a new webhook URL to receive event notifications.
 
    When events happen in Summly, we will POST a JSON payload to your URL.
 
    The response includes a 'secret' field — save this immediately.
    We never show it again. Use it to verify incoming requests:
 
        import hmac, hashlib
        def verify(secret, body_bytes, signature_header):
            expected = "sha256=" + hmac.new(
                secret.encode(), body_bytes, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header)
 
    Valid event types to subscribe to:
        meeting.processed   → fires when a meeting finishes processing
        task.updated        → fires when an action item changes
        task.deleted        → fires when an action item is deleted
        member.invited      → fires when someone joins a workspace
        member.removed      → fires when someone is removed from a workspace
        workspace.created   → fires when a workspace is created
        workspace.deleted   → fires when a workspace is deleted
 
    Returns the new webhook with its secret (shown once only).
    """
    valid_events = {
        "meeting.processed", "task.updated", "task.deleted",
        "member.invited", "member.removed",
        "workspace.created", "workspace.deleted",
    }
 
    invalid = [e for e in body.events if e not in valid_events]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event types: {invalid}. Valid: {sorted(valid_events)}"
        )
 
    webhook = create_webhook(
        user_id=current_user.id,
        url=body.url,
        events=body.events,
    )
 
    write_audit_log(
        user_id=current_user.id,
        resource_type="webhook",
        resource_id=webhook["id"],
        action="created",
        metadata={"url": body.url, "events": body.events},
    )
 
    return webhook
 
 
@app.get("/webhooks", tags=["Webhooks"])
def list_webhooks(current_user: User = Depends(get_current_user)):
    """
    List all webhook endpoints you have registered.
    Secrets are not returned here for security.
    Use GET /webhooks/{id}/events to see delivery history.
    """
    return get_webhooks_for_user(user_id=current_user.id)
 
 
@app.delete("/webhooks/{webhook_id}", tags=["Webhooks"])
def remove_webhook(
    webhook_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a webhook endpoint.
    All delivery history for this webhook is also deleted.
    """
    deleted = delete_webhook(webhook_id=webhook_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
 
    write_audit_log(
        user_id=current_user.id,
        resource_type="webhook",
        resource_id=webhook_id,
        action="deleted",
    )
 
    return {"message": "Webhook deleted"}
 
 
@app.get("/webhooks/{webhook_id}/events", tags=["Webhooks"])
def list_webhook_events(
    webhook_id:   int,
    limit:        int  = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
):
    """
    Get delivery history for a webhook endpoint.
 
    Shows the last N attempts (default 50, max 200), most recent first.
    Each entry shows: event_type, status_code, success, error_message, delivered_at.
 
    Use this to debug failed webhooks — you can see exactly what went wrong.
    """
    events = get_webhook_events(
        webhook_id=webhook_id,
        user_id=current_user.id,
        limit=limit,
    )
    return {"webhook_id": webhook_id, "total": len(events), "events": events}
 
 
# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOGS
# ─────────────────────────────────────────────────────────────────────────────
 
@app.get("/audit-logs", tags=["Audit"])
def get_my_audit_logs(
    resource_type: str | None = Query(default=None),
    resource_id:   int | None = Query(default=None),
    limit:         int        = Query(default=100, le=500),
    current_user:  User       = Depends(get_current_user),
):
    """
    View your own audit log — a complete history of everything you've done.
 
    Optional filters:
        ?resource_type=meeting     → only meeting events
        ?resource_type=workspace   → only workspace events
        ?resource_id=5             → only events for resource with id=5
        ?resource_type=meeting&resource_id=5  → history of meeting 5
 
    Each entry shows:
        resource_type, resource_id, action, metadata, created_at
 
    This log is append-only — entries are never edited or deleted.
    """
    logs = get_audit_logs(
        user_id=current_user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )
    return {"total": len(logs), "logs": logs}
 
 
# ─────────────────────────────────────────────────────────────────────────────
# GDPR — DATA EXPORT AND ACCOUNT DELETION
# ─────────────────────────────────────────────────────────────────────────────
 
@app.get("/me/export", tags=["GDPR"])
def export_my_data(current_user: User = Depends(get_current_user)):
    """
    Export all your data as a JSON file.
 
    Required by GDPR Article 20 (Right to data portability).
 
    Returns a JSON object containing:
        user         → your profile
        meetings     → all meeting metadata (not full transcripts — too large)
        action_items → all tasks across all meetings
        workspaces   → workspaces you own
        audit_history → everything you've done in Summly
 
    The response is sent as a downloadable file (Content-Disposition: attachment).
    """
    data = export_user_data(user_id=current_user.id)
 
    write_audit_log(
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        action="data_exported",
    )
 
    # Return as a downloadable JSON file
    import json as _json
    content = _json.dumps(data, indent=2, default=str)
 
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=summly_export_{current_user.id}.json"
        },
    )
 
 
@app.delete("/me/account", tags=["GDPR"])
def delete_my_account(
    body:         DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete your account and all associated data.
 
    Required by GDPR Article 17 (Right to erasure).
 
    IMPORTANT: This is irreversible. Everything is deleted:
        - Your profile
        - All meetings, transcripts, and intelligence
        - All action items, decisions, topics
        - All workspaces you own
        - All audit logs
 
    To confirm, you must send:
        {"confirm": "DELETE MY ACCOUNT"}
 
    After deletion your JWT token will no longer work.
    """
    if body.confirm != "DELETE MY ACCOUNT":
        raise HTTPException(
            status_code=400,
            detail='To confirm account deletion, send {"confirm": "DELETE MY ACCOUNT"}'
        )
 
    deleted = delete_user_data(user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
 
    return {"message": "Your account and all data have been permanently deleted."}
 


# =====================================================
# MEETING ENDPOINTS
# =====================================================

@app.get("/meetings", tags=["Meetings"])
async def list_meetings(
    current_user: User       = Depends(get_current_user),
    limit:        int        = Query(default=20, ge=1, le=100),
    cursor:       int | None = Query(default=None),
):
    """
    FIX: Paginated meetings list — returns one page at a time.

    Old: returned ALL meetings at once — 200 meetings = 200 rows in one response.
    Browser had to render all 200 cards → laggy, freezes on low-end devices.

    New: returns 20 at a time (configurable via ?limit=20).
    Frontend sends ?cursor=<last_id> to get the next page.

    Response shape:
      {
        "items":       [...],   20 meeting objects
        "has_more":    true,    false when this is the last page
        "next_cursor": 42,      pass as ?cursor=42 for next page
        "count":       20       items in this response
      }

    Query params:
      limit  = how many per page (1-100, default 20)
      cursor = id of last item from previous page (omit for first page)
    """
    try:
        # FIX: DB reads are synchronous (psycopg2). Running them directly inside
        # async def blocks the entire FastAPI event loop — all other requests wait.
        # asyncio.to_thread() runs the blocking call in a thread pool worker.
        # The event loop stays free to handle other concurrent requests.
        return await asyncio.to_thread(
            get_meetings_page,
            user_id=current_user.id,
            limit=limit,
            cursor=cursor,
        )
    except Exception as e:
        logger.error("Failed to fetch meetings: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch meetings")


@app.delete("/meetings/{meeting_id}", tags=["Meetings"])
async def delete_meeting_endpoint(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete a meeting: the Postgres row, every derived
    intelligence table (summaries, action items, decisions, topics,
    health score, quotes, title, diarization), and its ChromaDB vectors.

    FIX: this endpoint did not exist at all before. The only way to
    remove a meeting was deleting it directly in Supabase — which leaves
    its ChromaDB vectors behind (Chroma is a separate datastore, nothing
    about a Postgres-side delete touches it). Those orphaned vectors keep
    matching chat queries scoped to that meeting_id forever, and if
    Postgres's id sequence ever gets reused (e.g. after a table
    truncation), a brand-new meeting can inherit a deleted one's stale,
    unrelated content in chat. This endpoint keeps both stores in sync
    going forward. If you have existing orphaned vectors from before this
    endpoint existed, run POST /rag/vacuum-orphaned once to clean them up.
    """
    deleted = await asyncio.to_thread(delete_meeting, meeting_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        from server.core.rag.indexer import delete_meeting_index
        from server.core.rag.hybrid_search import invalidate_meeting_cache
        await asyncio.to_thread(delete_meeting_index, meeting_id)
        invalidate_meeting_cache(meeting_id)
    except Exception as e:
        # The Postgres row is already gone — that's the part the user
        # asked for and can't be safely rolled back at this point. Log
        # loudly so this doesn't fail silently; POST /rag/vacuum-orphaned
        # will catch and clean up any vectors left behind by this failure.
        logger.error(
            f"Meeting {meeting_id} deleted from Postgres, but ChromaDB "
            f"cleanup failed — will need /rag/vacuum-orphaned: {e}"
        )

    return {"message": "Meeting deleted", "meeting_id": meeting_id}


@app.get("/meetings/{meeting_id}", response_model=MeetingDetail, tags=["Meetings"])
async def get_meeting(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    try:
        # FIX: async + to_thread — DB read was blocking the event loop
        meeting = await asyncio.to_thread(
            get_meeting_by_id, meeting_id, current_user.id
        )
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        intel = await asyncio.to_thread(get_intelligence_for_response, meeting_id)

        return MeetingDetail(
            id               = meeting["id"],
            filename         = meeting["filename"],
            transcript       = meeting["transcript"],
            created_at       = str(meeting["created_at"]),
            duration_seconds = meeting["duration_seconds"],
            intelligence     = intel,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch meeting {meeting_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch meeting")


@app.get("/meetings/{meeting_id}/intelligence", response_model=IntelligenceResponse, tags=["Meetings"])
def meeting_intelligence(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    try:
        meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        intel = get_meeting_intelligence(meeting_id)
        if intel is None:
            raise HTTPException(status_code=404, detail="No intelligence found for this meeting")

        return IntelligenceResponse(
            summary      = intel.get("summary", ""),
            action_items = intel.get("action_items", []),
            decisions    = intel.get("decisions", []),
            topics       = intel.get("topics", []),
            generated_at = intel.get("generated_at", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch intelligence for meeting {meeting_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch intelligence")


@app.get("/meetings/{meeting_id}/tasks", tags=["Meetings"])
def get_meeting_tasks(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    items = get_action_items_by_meeting(meeting_id=meeting_id)
    return {
        "meeting_id": meeting_id,
        "filename":   meeting["filename"],
        "total":      len(items),
        "items":      items,
    }


# =====================================================
# INTELLIGENCE ENDPOINTS
# =====================================================

@app.get("/meetings/{meeting_id}/health", tags=["Intelligence"])
def get_health_score(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    cached = get_meeting_health(meeting_id)
    if cached:
        return cached

    intel = get_meeting_intelligence(meeting_id)
    if not intel:
        raise HTTPException(status_code=404, detail="No intelligence data found. Process meeting first.")

    health = analyze_meeting_health(transcript=meeting["transcript"], intelligence=intel)
    save_meeting_health(meeting_id, health)
    return health


@app.get("/meetings/{meeting_id}/quotes", tags=["Intelligence"])
def get_quotes(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    cached = get_meeting_quotes(meeting_id)
    if cached:
        return {"quotes": cached}

    quotes = extract_key_quotes(meeting["transcript"])
    save_meeting_quotes(meeting_id, quotes)
    return {"quotes": quotes}


@app.get("/meetings/{meeting_id}/title", tags=["Intelligence"])
def get_ai_title(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    cached = get_meeting_title(meeting_id)
    if cached:
        return {"title": cached}

    intel   = get_meeting_intelligence(meeting_id)
    summary = intel.get("summary", "") if intel else ""

    title = generate_meeting_title(transcript=meeting["transcript"], summary=summary)
    save_meeting_title(meeting_id, title)
    return {"title": title}


# =====================================================
# EXPORT ENDPOINTS
# =====================================================

@app.get("/meetings/{meeting_id}/followup-email", tags=["Export"])
def get_followup_email(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    intel = get_meeting_intelligence(meeting_id)
    if not intel:
        raise HTTPException(status_code=404, detail="No intelligence data found.")

    ai_title = get_meeting_title(meeting_id)
    title    = ai_title or meeting.get("filename", "Our Meeting")

    email = generate_followup_email(meeting_title=title, intelligence=intel)
    return {"email": email, "title": title}


@app.get("/meetings/{meeting_id}/export/pdf", tags=["Export"])
def export_pdf(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units     import cm
    from reportlab.lib           import colors
    from reportlab.platypus      import (
        SimpleDocTemplate, Paragraph, Spacer,
        HRFlowable, Table, TableStyle,
    )
    from reportlab.lib.enums import TA_LEFT

    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    write_audit_log(user_id=current_user.id, resource_type="meeting", resource_id=meeting_id, action="exported")

    intel    = get_meeting_intelligence(meeting_id)
    health   = get_meeting_health(meeting_id)
    quotes   = get_meeting_quotes(meeting_id)
    ai_title = get_meeting_title(meeting_id)
    title    = ai_title or meeting.get("filename", "Meeting Report")

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    W      = A4[0] - 4*cm

    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    S_title   = style("T",  fontSize=22, fontName="Helvetica-Bold",
                      textColor=colors.HexColor("#0e1117"), spaceAfter=4, alignment=TA_LEFT)
    S_meta    = style("M",  fontSize=10, textColor=colors.HexColor("#6b748f"), spaceAfter=4)
    # FIX: section headers/quotes were #4f46e5 (indigo) with a #f5f7ff
    # (lavender-tinted) table background — this is a real client-facing PDF
    # export, so the brand mismatch actually reached users, not just the
    # app UI. Now emerald throughout, consistent with everything else.
    S_section = style("S",  fontSize=13, fontName="Helvetica-Bold",
                      textColor=colors.HexColor("#059669"), spaceBefore=24, spaceAfter=10)
    S_body    = style("B",  fontSize=10, leading=16,
                      textColor=colors.HexColor("#2e3650"), spaceAfter=4)
    S_bullet  = style("BL", fontSize=10, leading=15,
                      textColor=colors.HexColor("#2e3650"), leftIndent=14, spaceAfter=3)
    S_quote   = style("Q",  fontSize=10, leading=15, textColor=colors.HexColor("#059669"),
                      leftIndent=14, fontName="Helvetica-Oblique", spaceAfter=4)
    S_label   = style("L",  fontSize=9,  fontName="Helvetica-Bold",
                      textColor=colors.HexColor("#9aa3bc"), spaceAfter=2)

    gray = colors.HexColor("#e2e8f0")

    def hr():
        return HRFlowable(width="100%", thickness=1, color=gray, spaceAfter=10, spaceBefore=10)

    story = []

    story.append(Table(
        [[Paragraph(title, S_title)]],
        colWidths=[W],
        style=TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#ecfdf5")),
            ("TOPPADDING",    (0,0), (-1,-1), 14),
            ("BOTTOMPADDING", (0,0), (-1,-1), 14),
            ("LEFTPADDING",   (0,0), (-1,-1), 16),
            ("RIGHTPADDING",  (0,0), (-1,-1), 16),
            ("BOX",           (0,0), (-1,-1), 1, colors.HexColor("#dde3f0")),
        ]),
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"{str(meeting.get('created_at', ''))[:10]}   |   "
        f"{meeting.get('filename', '')}   |   AI Generated Report",
        S_meta,
    ))

    if health:
        score       = health.get("overall_score", 0)
        score_color = "#10b981" if score >= 75 else "#f59e0b" if score >= 50 else "#ef4444"
        story.append(Paragraph(
            f"Meeting Health Score: <font color='{score_color}'><b>{score}/100</b></font>",
            S_meta,
        ))

    story.append(Spacer(1, 6))
    story.append(hr())

    if intel and intel.get("summary"):
        story.append(Paragraph("Executive Summary", S_section))
        story.append(Paragraph(intel["summary"], S_body))
        story.append(hr())

    if intel and intel.get("topics"):
        story.append(Paragraph("Topics Discussed", S_section))
        story.append(Paragraph("   |   ".join(t["title"] for t in intel["topics"]), S_body))
        story.append(hr())

    if intel and intel.get("decisions"):
        story.append(Paragraph("Decisions Made", S_section))
        for d in intel["decisions"]:
            story.append(Paragraph(f"- {d['decision']}", S_bullet))
            if d.get("rationale"):
                story.append(Paragraph(f"  {d['rationale']}", S_label))
        story.append(hr())

    if intel and intel.get("action_items"):
        story.append(Paragraph("Action Items", S_section))
        data = [["Task", "Owner", "Deadline", "Priority"]]
        for item in intel["action_items"]:
            data.append([
                item.get("task",     "-"),
                item.get("owner",    "-") or "-",
                item.get("deadline", "-") or "-",
                (item.get("priority") or "medium").title(),
            ])
        col_w = [W*0.45, W*0.2, W*0.2, W*0.15]
        t = Table(data, colWidths=col_w)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0),  colors.HexColor("#ecfdf5")),
            ("TEXTCOLOR",      (0,0), (-1,0),  colors.HexColor("#059669")),
            ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f6fdf9")]),
            ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING",     (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 7),
            ("LEFTPADDING",    (0,0), (-1,-1), 8),
            ("RIGHTPADDING",   (0,0), (-1,-1), 8),
            ("ALIGN",          (0,0), (-1,-1), "LEFT"),
            ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(t)
        story.append(hr())

    if quotes:
        story.append(Paragraph("Key Quotes", S_section))
        for q in quotes:
            story.append(Paragraph(f'"{q["quote"]}"', S_quote))
            if q.get("speaker"):
                story.append(Paragraph(
                    f"- {q['speaker']}" + (f"  |  {q['context']}" if q.get("context") else ""),
                    S_label,
                ))
            story.append(Spacer(1, 4))
        story.append(hr())

    if health:
        story.append(Paragraph("Meeting Health Analysis", S_section))
        health_data = [
            ["Metric",           "Score"],
            ["Participation",    f"{health['participation']}/100"],
            ["Decision Quality", f"{health['decision_quality']}/100"],
            ["Action Clarity",   f"{health['action_clarity']}/100"],
            ["Follow-up Risk",   f"{health['followup_risk']}/100"],
            ["Overall Score",    f"{health['overall_score']}/100"],
        ]
        ht = Table(health_data, colWidths=[W*0.6, W*0.4])
        ht.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),  (-1,0),  colors.HexColor("#ecfdf5")),
            ("TEXTCOLOR",      (0,0),  (-1,0),  colors.HexColor("#059669")),
            ("FONTNAME",       (0,0),  (-1,0),  "Helvetica-Bold"),
            ("FONTNAME",       (0,-1), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),  (-1,-1), 9),
            ("GRID",           (0,0),  (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0,1),  (-1,-2), [colors.white, colors.HexColor("#f6fdf9")]),
            ("TOPPADDING",     (0,0),  (-1,-1), 7),
            ("BOTTOMPADDING",  (0,0),  (-1,-1), 7),
            ("LEFTPADDING",    (0,0),  (-1,-1), 8),
            ("RIGHTPADDING",   (0,0),  (-1,-1), 8),
        ]))
        story.append(ht)

        if health.get("highlights"):
            story.append(Spacer(1, 8))
            story.append(Paragraph("Highlights", S_label))
            story.append(Paragraph(health["highlights"], S_body))
        if health.get("concerns"):
            story.append(Spacer(1, 4))
            story.append(Paragraph("To Improve", S_label))
            story.append(Paragraph(health["concerns"], S_body))

        story.append(hr())

    transcript_text = meeting.get("transcript", "")
    if transcript_text:
        story.append(Paragraph("Transcript", S_section))
        for para in transcript_text.split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, S_body))

    story.append(Spacer(1, 16))
    story.append(hr())
    story.append(Paragraph(
        "Generated by Summly  |  AI Meeting Intelligence Platform  |  summly.ai",
        S_meta,
    ))

    doc.build(story)
    buffer.seek(0)

    safe_name = (title or "meeting").replace(" ", "_")[:40]
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_report.pdf"'},
    )


# =====================================================
# UPLOAD ENDPOINT
# =====================================================

@app.post("/upload", response_model=TranscriptResponse, tags=["Processing"])
@limiter.limit("10/minute")
async def upload_file(
    request:               Request,
    file:                  UploadFile = File(...),
    current_user:          User       = Depends(get_current_user),
    enable_audio_cleaning: bool       = Query(default=True),
):
    """
    Upload an audio/video file for transcription and AI analysis.

    Flow:
      1. Validate file type and stream into a temp file (size checked during streaming)
      2. Upload original to Supabase Storage (permanent cloud copy)
      3. Run FFmpeg + Whisper on the temp file
      4. Run 6 AI agents on the transcript
      5. Save everything to PostgreSQL
      6. Delete temp file — guaranteed in finally block

    No permanent local storage — temp file is the only local file,
    and it is always deleted when the request finishes.
    """
    import uuid
    import tempfile

    start_time = time.time()
    ext        = file.filename.split(".")[-1].lower()

    if ext not in VIDEO_EXTENSIONS and ext not in AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: .{ext}. "
                f"Supported formats: mp3, wav, mp4, m4a, aac, flac, ogg, mkv, avi, mov, webm, m4v"
            ),
        )

    # Sanitise the original filename for use in paths + DB storage
    # Strips dangerous characters like "../" that could escape the upload folder
    safe_stem   = "".join(c for c in Path(file.filename).stem if c.isalnum() or c in "-_ ")[:50]
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_stem}.{ext}"

    # FIX: Use a system temp file instead of a permanent uploads/ directory.
    #
    # Old code wrote to: uploads/audio/user_42/filename.mp3 — stayed on disk forever.
    # New code writes to: /tmp/summly_abc123.mp3 — deleted in the finally block below.
    #
    # tempfile.NamedTemporaryFile(delete=False) creates a file like /tmp/summly_xxxxx.ext
    # We set delete=False because we close the file before Whisper/FFmpeg open it —
    # if delete=True Python would delete it the moment we call .close(), before
    # transcription can read it. We handle deletion ourselves in the finally block.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{ext}",
            prefix="summly_"
        ) as tmp:
            tmp_path = Path(tmp.name)

            # FIX: Stream file in 1MB chunks, reject immediately if too large.
            # Old code: write entire file first, check size after — fills disk on large uploads.
            # New code: count bytes while writing — stop and delete the moment limit is hit.
            CHUNK_SIZE  = 1024 * 1024   # 1 MB
            total_bytes = 0

            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail="File is too large. Maximum allowed size is 500 MB.",
                    )
                tmp.write(chunk)

        slog.info("temp_file_written",
                  original_name=file.filename,
                  size_mb=round(total_bytes / 1024 / 1024, 2),
                  user_id=current_user.id)

        # ── Step 1: Upload original to Supabase (permanent cloud copy) ─────
        # This is done BEFORE transcription so that even if AI processing
        # fails, the user's original file is already safely in the cloud.
        ext_to_mime = {
            "wav": "audio/wav",   "mp3": "audio/mpeg",  "m4a": "audio/mp4",
            "aac": "audio/aac",   "flac": "audio/flac", "ogg": "audio/ogg",
            "mp4": "video/mp4",   "mkv": "video/x-matroska",
            "avi": "video/x-msvideo", "mov": "video/quicktime", "webm": "video/webm",
        }
        supabase_path = f"user_{current_user.id}/{unique_name}"
        file_url = upload_to_supabase(
            local_path=str(tmp_path),
            filename=supabase_path,
        )
        slog.info("uploaded_to_supabase",
                  path=supabase_path,
                  url=file_url,
                  user_id=current_user.id)

        # ── Step 2: Transcription (FFmpeg + Whisper) ───────────────────────
        # FFmpeg and Whisper are C++ programs — they need a file path on disk.
        # We pass them tmp_path which still exists at this point.
        from server.core.transcription.audio_extractor import extract_audio

        if ext in VIDEO_EXTENSIONS:
            # extract_audio runs FFmpeg: video → WAV
            # It creates another temp file internally and returns its path
            wav_file = extract_audio(str(tmp_path), enable_cleaning=enable_audio_cleaning)
        else:
            wav_file = str(tmp_path)
            if enable_audio_cleaning:
                try:
                    from server.core.transcription.audio_cleaner import AudioCleaner
                    cleaner = AudioCleaner(sr=16000)
                    cleaner.clean_audio(
                        wav_file, output_path=wav_file,
                        enable_noise_reduction=True,
                        enable_compression=True,
                        save_output=True,
                    )
                except Exception as e:
                    logger.warning(f"Audio cleaning failed (non-fatal): {e}")

        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_file)
        logger.info(f"Transcription complete: {len(transcript)} characters")

        # ── Step 3: Save transcript to PostgreSQL ──────────────────────────
        # FIX: Removed file_url= parameter — save_transcript_and_get_id does not
        # accept it. The Supabase URL is stored in the audit log metadata below.
        meeting_id = save_transcript_and_get_id(
            filename=file.filename,
            transcript=transcript,
            user_id=current_user.id,
        )

        # ── Step 4: Run AI agents ──────────────────────────────────────────
        from server.core.intelligence.workflow import analyze_transcript
        intelligence = analyze_transcript(transcript)
        save_meeting_intelligence(meeting_id, intelligence)

        write_audit_log(
            user_id=current_user.id,
            resource_type="meeting",
            resource_id=meeting_id,
            action="created",
            metadata={"filename": file.filename, "file_url": file_url},
        )

        slog.info("intelligence_saved",
                  meeting_id=meeting_id,
                  actions=len(intelligence.action_items),
                  decisions=len(intelligence.decisions),
                  topics=len(intelligence.topics))

        # ── Step 5: Index for RAG chat ─────────────────────────────────────
        try:
            from server.core.rag.indexer import index_meeting
            index_meeting(
                meeting_id=meeting_id,
                filename=file.filename,
                transcript=transcript,
                created_at="",
                user_id=current_user.id,  # FIX: was never passed — every chunk from this path was tagged user_id=0
            )
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        processing_time = round(time.time() - start_time, 2)
        slog.info("upload_complete",
                  filename=file.filename,
                  meeting_id=meeting_id,
                  processing_time=processing_time,
                  user_id=current_user.id)

        return TranscriptResponse(
            meeting_id      = meeting_id,
            filename        = file.filename,
            transcript_file = supabase_path,   # Supabase path, not local path
            transcript      = transcript,
            intelligence    = get_intelligence_for_response(meeting_id),
            processing_time = processing_time,
            file_size_mb    = round(total_bytes / 1024 / 1024, 2),
        )

    except HTTPException:
        raise   # pass our clean 400/403 errors through unchanged

    except Exception as e:
        logger.error(f"Upload processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Processing failed. Please try again.",
        )

    finally:
        # FIX: Always delete the temp file — whether processing succeeded or failed.
        # "finally" runs no matter what: success, exception, even HTTPException.
        # This is the key guarantee: temp file NEVER stays on disk after this request.
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
            slog.info("temp_file_deleted", path=str(tmp_path), user_id=current_user.id)


@app.post("/youtube", response_model=YouTubeResponse, tags=["Processing"])
async def process_youtube(
    request:               YouTubeRequest,
    current_user:          User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True),
):
    start_time = time.time()

    try:
        from server.core.transcription.youtube_downloader import download_youtube
        youtube_data = download_youtube(str(request.url))
        mp3_file     = youtube_data["audio_file"]
        title        = youtube_data["title"]
        logger.info(f"Downloaded: {title}")

        from server.core.transcription.audio_extractor import extract_audio
        wav_file = extract_audio(mp3_file, enable_cleaning=enable_audio_cleaning)

        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_file)

        meeting_id = save_transcript_and_get_id(
            filename=title, transcript=transcript, user_id=current_user.id,
        )

        from server.core.intelligence.workflow import analyze_transcript
        intelligence = analyze_transcript(transcript)
        save_meeting_intelligence(meeting_id, intelligence)

        try:
            from server.core.rag.indexer import index_meeting
            index_meeting(meeting_id=meeting_id, filename=title,
                          transcript=transcript, created_at="",
                          user_id=current_user.id)  # FIX: was never passed — tagged user_id=0
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        transcript_file = TRANSCRIPT_DIR / f"{title}.txt"
        transcript_file.write_text(transcript, encoding="utf-8")

        processing_time = round(time.time() - start_time, 2)

        return YouTubeResponse(
            meeting_id      = meeting_id,
            title           = title,
            transcript_file = str(transcript_file),
            transcript      = transcript,
            intelligence    = get_intelligence_for_response(meeting_id),
            processing_time = processing_time,
        )

    except Exception as e:
        logger.error(f"YouTube processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# =====================================================
# CHAT ENDPOINTS
# =====================================================

@app.post("/chat/meeting", tags=["Chat"])
@limiter.limit("30/minute")
async def chat_with_meeting_endpoint(
    request:      Request,
    body:         ChatRequest,
    current_user: User = Depends(get_current_user),
):
    if not body.meeting_id:
        raise HTTPException(status_code=400, detail="meeting_id is required for single meeting chat")

    try:
        meeting = get_meeting_by_id(body.meeting_id, user_id=current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        from server.core.rag.chat import chat_with_meeting
        result = chat_with_meeting(query=body.query, meeting_id=body.meeting_id, user_id=current_user.id)
        return {
            "answer":     result["answer"],
            "sources":    result["sources"],
            "meeting_id": body.meeting_id,
            "mode":       "single",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed for meeting {body.meeting_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/chat/search", tags=["Chat"])
def chat_search(
    request:      ChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        from server.core.rag.chat import chat_across_meetings
        # FIX: previously called with no user_id at all, which meant this
        # endpoint searched every user's meetings, not just yours — see
        # the FIX note on chat_across_meetings() in core/rag/chat.py for
        # the full explanation of this bug.
        result = chat_across_meetings(query=request.query, user_id=current_user.id)
        return {"answer": result["answer"], "sources": result["sources"], "mode": "cross"}
    except Exception as e:
        logger.error(f"Cross-meeting chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/chat/meeting/stream", tags=["Chat"])
async def stream_chat_meeting(
    query:        str  = Query(...),
    meeting_id:   int  = Query(...),
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    from server.core.rag.chat import stream_chat_with_meeting
    return StreamingResponse(
        stream_chat_with_meeting(query=query, meeting_id=meeting_id, user_id=current_user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/chat/search/stream", tags=["Chat"])
async def stream_chat_search(
    query:        str  = Query(...),
    current_user: User = Depends(get_current_user),
):
    from server.core.rag.chat import stream_chat_across_meetings
    # FIX: same unscoped cross-user bug as /chat/search — see the FIX note
    # on stream_chat_across_meetings() in core/rag/chat.py.
    return StreamingResponse(
        stream_chat_across_meetings(query=query, user_id=current_user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# =====================================================
# AGENT ENDPOINT
# =====================================================

@app.post("/agent/chat", tags=["Agent"])
async def agent_chat(
    request:      AgentRequest,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(request.meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        from server.core.agent.meeting_agent import run_agent
        result = run_agent(query=request.query, meeting_id=request.meeting_id)
        return {
            "answer":     result["answer"],
            "tools_used": result["tools_used"],
            "iterations": result["iterations"],
            "meeting_id": request.meeting_id,
        }
    except Exception as e:
        logger.error(f"Agent failed for meeting {request.meeting_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")


# =====================================================
# RAG REINDEX
# =====================================================

@app.post("/rag/reindex", tags=["RAG"])
async def reindex_all(current_user: User = Depends(get_current_user)):
    """
    Re-index all meetings into ChromaDB.

    ROOT CAUSE OF SLOWNESS (now fixed):
    ─────────────────────────────────────
    SentenceTransformer (~400MB) is a module-level singleton in embedder.py.
    The singleton is cached per PROCESS.

    In Docker: Celery runs in one process, FastAPI in another.
    When FastAPI's asyncio.to_thread() runs _do_reindex(), it runs in
    FastAPI's thread pool — same process. The model IS cached there after
    the first call. BUT on a cold start (first reindex ever), it loads from disk.

    The real bottleneck is NOT the model — it's:
    1. ChromaDB upsert is slow for large transcripts (10,000+ word meetings)
    2. The SentenceTransformer encodes all chunks sequentially
    3. Each meeting takes 2-8 seconds depending on transcript length

    FIXES:
    ─────
    1. Pre-warm the embedding model before the loop.
       This surfaces the model-loading time clearly in logs instead of
       hiding it inside the first meeting's processing time.

    2. Return immediately with a job_id and run reindex as a background task.
       The frontend no longer spins indefinitely — it gets a response in <1s
       and can poll GET /rag/reindex/{job_id}/status for progress.

    3. Store per-meeting progress in Redis so the frontend can show
       "Indexing meeting 2 of 5..." instead of a blank spinner.
    """
    import uuid, json

    job_id = str(uuid.uuid4())[:8]
    rc     = _get_redis()   # None if Redis not running (ping() tested inside)

    # ── No Redis: run synchronously, return result directly ───────────────────
    # When Redis is not available (Windows dev without Redis installed),
    # we cannot store progress or background the job.
    # Instead: run reindex in a thread right now and return the final result.
    # The frontend receives { done: true, indexed: N } immediately — no polling needed.
    if rc is None:
        logger.info("Redis not available — running reindex synchronously for job %s", job_id)

        def _do_reindex_sync():
            from server.core.rag.embedder import get_embedding_model
            from server.core.rag.indexer  import index_meeting
            get_embedding_model()
            meetings = get_all_meetings_for_indexing(user_id=current_user.id)
            indexed, failed = 0, []
            for m in meetings:
                try:
                    index_meeting(
                        meeting_id = m["id"],
                        filename   = m["filename"],
                        transcript = m["transcript"],
                        created_at = str(m.get("created_at", "")),
                        user_id    = m.get("user_id"),
                    )
                    indexed += 1
                except Exception as e:
                    failed.append({"id": m["id"], "filename": m["filename"], "error": str(e)})
            return {"indexed": indexed, "total": len(meetings), "failed": failed}

        try:
            result = await asyncio.to_thread(_do_reindex_sync)
            return {
                "job_id":  job_id,
                "status":  "done",
                "step":    f"Complete — {result['indexed']} of {result['total']} meetings indexed.",
                "indexed": result["indexed"],
                "total":   result["total"],
                "failed":  result["failed"],
                "done":    True,
            }
        except Exception as e:
            logger.error("Synchronous reindex failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")

    # ── Redis available: background job with polling ───────────────────────────
    # Store initial status immediately — frontend gets this within <100ms
    try:
        rc.setex(
            f"reindex:{job_id}",
            3600,
            json.dumps({"status": "running", "indexed": 0, "total": 0, "failed": [], "done": False}),
        )
    except Exception:
        pass   # Redis write failed — non-fatal

    async def _run_background():
        """Run reindex in background, updating Redis progress as we go."""
        def _update(data: dict):
            try:
                rc = _get_redis()
                if rc:
                    rc.setex(f"reindex:{job_id}", 3600, json.dumps(data))
            except Exception:
                pass

        def _do_reindex():
            from server.core.rag.embedder import get_embedding_model
            from server.core.rag.indexer  import index_meeting

            logger.info("Reindex job %s: warming embedding model...", job_id)
            _update({"status": "running", "step": "Loading AI model...", "indexed": 0, "total": 0, "failed": [], "done": False})
            get_embedding_model()

            meetings = get_all_meetings_for_indexing(user_id=current_user.id)
            total    = len(meetings)
            indexed  = 0
            failed   = []

            logger.info("Reindex job %s: %d meetings to index", job_id, total)
            _update({"status": "running", "step": f"Indexing 0 of {total} meetings...", "indexed": 0, "total": total, "failed": [], "done": False})

            for i, m in enumerate(meetings):
                try:
                    n_chunks = index_meeting(
                        meeting_id = m["id"],
                        filename   = m["filename"],
                        transcript = m["transcript"],
                        created_at = str(m.get("created_at", "")),
                        user_id    = m.get("user_id"),
                    )
                    indexed += 1
                    logger.info("Reindex %s: meeting %d → %d chunks (%d/%d)", job_id, m["id"], n_chunks, indexed, total)
                except Exception as e:
                    failed.append({"id": m["id"], "filename": m["filename"], "error": str(e)})
                    logger.warning("Reindex %s: meeting %d failed: %s", job_id, m["id"], e)

                _update({
                    "status":  "running",
                    "step":    f"Indexed {indexed} of {total} meetings...",
                    "indexed": indexed,
                    "total":   total,
                    "failed":  failed,
                    "done":    False,
                })

            _update({
                "status":  "done",
                "step":    f"Complete — {indexed} of {total} meetings indexed.",
                "indexed": indexed,
                "total":   total,
                "failed":  failed,
                "done":    True,
            })
            return {"indexed": indexed, "total": total, "failed": failed}

        try:
            await asyncio.to_thread(_do_reindex)
        except Exception as e:
            logger.error("Reindex job %s failed: %s", job_id, e, exc_info=True)
            try:
                rc = _get_redis()
                if rc:
                    rc.setex(f"reindex:{job_id}", 3600, json.dumps({
                        "status": "error", "step": str(e), "indexed": 0, "total": 0, "failed": [], "done": True,
                    }))
            except Exception:
                pass

    # Fire and forget — don't await, return job_id immediately
    asyncio.create_task(_run_background())

    return {
        "job_id":  job_id,
        "status":  "started",
        "message": "Reindex started in background. Poll /rag/reindex/status?job_id={job_id} for progress.",
    }


@app.get("/rag/reindex/status", tags=["RAG"])
async def get_reindex_status(
    job_id:       str,
    current_user: User = Depends(get_current_user),
):
    """
    Poll reindex background job progress.

    FIX: was using celery_app.backend.client which requires Celery to be
    fully configured and Redis reachable via Celery's broker URL.
    On Windows dev without Redis running, this raised:
      NameError: name 'celery_app' is not defined
    Now uses a direct Redis client via _get_redis() which is more robust.
    Falls back to a clear error message if Redis is not running.
    """
    import json

    rc = _get_redis()
    if rc is None:
        raise HTTPException(
            status_code=503,
            detail="Redis is not available. Reindex status cannot be retrieved. "
                   "Start Redis or run: redis-server",
        )

    try:
        raw = rc.get(f"reindex:{job_id}")
        if not raw:
            raise HTTPException(
                status_code=404,
                detail=f"Reindex job '{job_id}' not found or expired (TTL 1 hour).",
            )
        return json.loads(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to read reindex status for job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Status check failed: {e}")


@app.post("/rag/vacuum-orphaned", tags=["RAG"])
async def vacuum_orphaned_chunks_endpoint(
    current_user: User = Depends(get_current_user),
):
    """
    Repairs ChromaDB data drift against Postgres, in two passes:

    1. Backfill ownership: chunks tagged `user_id: 0` ("unknown owner",
       from indexing call sites that historically never passed user_id —
       now fixed, but existing data needs a one-time repair) get corrected
       to their real owner by looking up meeting_id in Postgres.
    2. Vacuum orphans: chunks whose meeting_id no longer exists in
       Postgres at all (e.g. deleted directly in Supabase before
       DELETE /meetings/{id} existed) are removed entirely.

    Meeting ids and ownership are a single global sequence in Postgres
    (not per-user), so this comparison is the same regardless of which
    user runs it — it can only ever correct/remove data that has no
    legitimate current owner, never something you or anyone else can
    still access. Safe to run repeatedly; it's a no-op once caught up.
    """
    from server.core.rag.indexer import vacuum_orphaned_chunks, backfill_chunk_ownership

    owner_map = await asyncio.to_thread(get_meeting_owner_map)
    backfill_result = await asyncio.to_thread(backfill_chunk_ownership, owner_map)

    valid_ids = set(owner_map.keys())
    vacuum_result = await asyncio.to_thread(vacuum_orphaned_chunks, valid_ids)

    if vacuum_result["orphaned_meeting_ids"] or backfill_result["chunks_fixed"]:
        logger.warning(
            "Repair run by user %d: backfilled %d chunks' ownership, "
            "removed %d orphaned chunks from meeting_ids %s",
            current_user.id, backfill_result["chunks_fixed"],
            vacuum_result["chunks_deleted"], vacuum_result["orphaned_meeting_ids"],
        )

    return {**vacuum_result, **backfill_result}


# =====================================================
# WEBSOCKET + PROGRESS PIPELINE
# =====================================================

class ProgressManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, job_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[job_id] = ws

    def disconnect(self, job_id: str):
        self.connections.pop(job_id, None)

    async def send(self, job_id: str, data: dict):
        ws = self.connections.get(job_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(job_id)


progress = ProgressManager()


@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await progress.connect(job_id, websocket)
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        progress.disconnect(job_id)


async def _run_with_progress(job_id: str, filename: str, transcript_fn, user_id: int = None):
    # Write initial status immediately so first poll returns something
    _write_job_status(job_id, {"step": "extract", "message": "Starting...", "pct": 5, "meeting_id": None})

    async def step(name: str, message: str, pct: int, meeting_id=None):
        payload = {
            "step":       name,
            "message":    message,
            "pct":        pct,
            "meeting_id": meeting_id,
            "ts":         datetime.datetime.now().isoformat(),
        }
        # Write to job store so HTTP polling (/jobs/{id}/status) works
        _write_job_status(job_id, payload)
        # Also push via WebSocket if connected
        await progress.send(job_id, payload)

    try:
        await step("extract",    "Extracting audio...",                10)
        transcript = await asyncio.to_thread(transcript_fn)

        await step("transcribe", "Transcription complete",             40)
        meeting_id = await asyncio.to_thread(
            save_transcript_and_get_id, filename, transcript, None, user_id
        )

        await step("intel",      "Generating meeting intelligence...", 60, meeting_id)
        from server.core.intelligence.workflow import analyze_transcript
        intelligence = await asyncio.to_thread(analyze_transcript, transcript)

        await step("intel",      "Saving intelligence...",             75, meeting_id)
        await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

        await step("index",      "Indexing for RAG search...",         88, meeting_id)
        try:
            from server.core.rag.indexer import index_meeting
            await asyncio.to_thread(index_meeting, meeting_id, filename, transcript, "")
        except Exception as e:
            logger.warning(f"Index failed (non-fatal): {e}")

        await step("done",       "Processing complete!",               100, meeting_id)
        return meeting_id, transcript, intelligence

    except Exception as e:
        err_payload = {"step": "error", "message": str(e), "pct": 0, "meeting_id": None}
        _write_job_status(job_id, err_payload)
        await progress.send(job_id, err_payload)
        raise


@app.post("/upload/progress", tags=["Processing"])
@limiter.limit("10/minute")
async def upload_file_with_progress(
    request:               Request,
    file:                  UploadFile = File(...),
    job_id:                str        = Query(default=None),
    current_user:          User       = Depends(get_current_user),
    enable_audio_cleaning: bool       = Query(default=True),
):
    start_time = time.time()
    ext        = file.filename.split(".")[-1].lower()

    if ext in VIDEO_EXTENSIONS:
        file_path = VIDEO_DIR / file.filename
    elif ext in AUDIO_EXTENSIONS:
        file_path = AUDIO_DIR / file.filename
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"File save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file to disk")

    # Supabase upload is optional — if not configured or fails, processing continues
    try:
        supabase_filename = f"user_{current_user.id}/{file.filename}"
        upload_to_supabase(local_path=str(file_path), filename=supabase_filename)
    except Exception as e:
        logger.warning(f"Supabase upload skipped (non-fatal): {e}")

    file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)

    def do_transcribe():
        from server.core.transcription.audio_extractor import extract_audio
        from server.core.transcription.transcribe import transcribe_audio
        wav = extract_audio(str(file_path), enable_cleaning=enable_audio_cleaning) \
              if ext in VIDEO_EXTENSIONS else str(file_path)
        return transcribe_audio(wav)

    meeting_id, transcript, intelligence = await _run_with_progress(
        job_id        = job_id or "noop",
        filename      = file.filename,
        transcript_fn = do_transcribe,
        user_id       = current_user.id,
    )

    return TranscriptResponse(
        meeting_id      = meeting_id,
        filename        = file.filename,
        transcript_file = "",
        transcript      = transcript,
        intelligence    = get_intelligence_for_response(meeting_id),
        processing_time = round(time.time() - start_time, 2),
        file_size_mb    = file_size_mb,
    )


@app.post("/youtube/progress", tags=["Processing"])
async def youtube_with_progress(
    request:               dict,
    job_id:                str  = None,
    current_user:          User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True),
):
    url        = request.get("url", "")
    job_id     = request.get("job_id") or job_id or "noop"
    start_time = time.time()

    def _yt_step(name, message, pct, meeting_id=None):
        """Sync helper to write job status from inside a thread."""
        _write_job_status(job_id, {"step": name, "message": message, "pct": pct, "meeting_id": meeting_id})

    def do_transcribe():
        from server.core.transcription.youtube_downloader import download_youtube
        from server.core.transcription.audio_extractor import extract_audio
        from server.core.transcription.transcribe import transcribe_audio
        yt_data = download_youtube(str(url))
        wav     = extract_audio(yt_data["audio_file"], enable_cleaning=enable_audio_cleaning)
        return transcribe_audio(wav), yt_data["title"]

    # Write initial status immediately so first poll does not 404
    _write_job_status(job_id, {"step": "download", "message": "Downloading YouTube audio...", "pct": 8, "meeting_id": None})
    await progress.send(job_id, {"step": "download", "message": "Downloading YouTube audio...", "pct": 8})

    try:
        transcript, title = await asyncio.to_thread(do_transcribe)
    except Exception as e:
        err = {"step": "error", "message": str(e), "pct": 0, "meeting_id": None}
        _write_job_status(job_id, err)
        await progress.send(job_id, err)
        raise HTTPException(status_code=500, detail=str(e))

    _write_job_status(job_id, {"step": "transcribe", "message": "Transcription complete", "pct": 40, "meeting_id": None})
    await progress.send(job_id, {"step": "transcribe", "message": "Transcription complete", "pct": 40})

    meeting_id = await asyncio.to_thread(
        save_transcript_and_get_id, title, transcript, None, current_user.id
    )

    _write_job_status(job_id, {"step": "intel", "message": "Generating intelligence...", "pct": 60, "meeting_id": meeting_id})
    await progress.send(job_id, {"step": "intel", "message": "Generating intelligence...", "pct": 60})
    from server.core.intelligence.workflow import analyze_transcript
    intelligence = await asyncio.to_thread(analyze_transcript, transcript)
    await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

    _write_job_status(job_id, {"step": "index", "message": "Indexing for RAG...", "pct": 88, "meeting_id": meeting_id})
    await progress.send(job_id, {"step": "index", "message": "Indexing for RAG...", "pct": 88})
    try:
        from server.core.rag.indexer import index_meeting
        await asyncio.to_thread(index_meeting, meeting_id, title, transcript, "")
    except Exception as e:
        logger.warning(f"Index failed: {e}")

    _write_job_status(job_id, {"step": "done", "message": "Processing complete!", "pct": 100, "meeting_id": meeting_id})
    await progress.send(job_id, {"step": "done", "message": "Processing complete!", "pct": 100})

    return YouTubeResponse(
        meeting_id      = meeting_id,
        title           = title,
        transcript_file = "",
        transcript      = transcript,
        intelligence    = get_intelligence_for_response(meeting_id),
        processing_time = round(time.time() - start_time, 2),
    )


# =====================================================
# DIARIZATION ENDPOINTS
# =====================================================

@app.post("/meetings/{meeting_id}/diarize", tags=["Transcription"])
async def diarize_meeting(
    meeting_id:   int,
    force:        bool = False,   # ?force=true skips cache and re-runs
    current_user: User = Depends(get_current_user),
):
    """
    Run speaker diarization on a meeting.

    FIX 1 — Root cause of blank speaker results:
        Old code passed a FAKE single segment spanning 0–9999s as "whisper segments".
        This caused every word to be attributed to SPEAKER_00 because that one fake
        segment overlapped with every pyannote time range.
        Fix: call transcribe_audio_with_timestamps() to get REAL per-sentence timestamps
        BEFORE running diarization. Each sentence now maps to its actual speaker.

    FIX 2 — Response shape:
        Old response: { transcript, talk_time, num_speakers }
        New response: { speakers, segments, total_duration, num_speakers, ... }
        The frontend SpeakersTab now receives exactly the shape it expects.

    FIX 3 — Cached response also returns full shape:
        Old cached response returned a truncated dict. Now returns the same
        complete shape as a fresh run, rebuilt from DB storage.
    """
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.get("transcript"):
        raise HTTPException(
            status_code=400,
            detail="No transcript yet. Upload and process the meeting first."
        )

    # Return cached result unless force=true
    if not force:
        cached = get_diarization(meeting_id)
        if cached:
            # FIX: rebuild full frontend shape from cached DB data.
            # The DB stores talk_time (dict) and transcript (labeled string).
            # We rebuild speakers list and segments list from transcript parsing.
            talk_time  = cached["talk_time"]
            transcript = cached["transcript"]

            speakers_list = [
                {
                    "id":             sp_id,
                    "label":          data.get("label", sp_id),
                    "total_time":     data.get("seconds", 0),
                    "percentage":     data.get("percentage", 0),
                    "segments_count": data.get("segments", 0),
                }
                for sp_id, data in talk_time.items()
            ]

            # Parse the stored labeled transcript into segment dicts
            segments_list = _parse_labeled_transcript(transcript)

            return {
                "meeting_id":     meeting_id,
                "speakers":       speakers_list,
                "segments":       segments_list,
                "total_duration": segments_list[-1]["end"] if segments_list else 0,
                "num_speakers":   cached["num_speakers"],
                "transcript":     transcript,
                "talk_time":      talk_time,
                "cached":         True,
            }

    # Find the audio file on disk
    filename = meeting["filename"]
    stem     = Path(filename).stem   # "Weekly Meeting Example" (no extension)

    AUDIO_EXTENSIONS_LIST = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".mp4", ".mov", ".webm"]

    candidates = []
    # 1. Try stem + every audio extension in both audio and video dirs
    for ext in AUDIO_EXTENSIONS_LIST:
        candidates.append(AUDIO_DIR / f"{stem}{ext}")
        candidates.append(VIDEO_DIR / f"{stem}{ext}")
    # 2. Try exact filename as stored in DB
    candidates.append(AUDIO_DIR / filename)
    candidates.append(VIDEO_DIR / filename)
    # 3. Glob search — use as_posix() to avoid Windows backslash bug in glob
    import glob as _glob
    for pattern in [
        (AUDIO_DIR / f"{stem}.*").as_posix(),
        (VIDEO_DIR / f"{stem}.*").as_posix(),
    ]:
        for found in _glob.glob(pattern):
            candidates.append(Path(found))
    # 4. os.walk fallback — scans entire uploads folder, catches anything glob missed
    for search_dir in [AUDIO_DIR, VIDEO_DIR]:
        if search_dir.exists():
            for root, _, files in os.walk(str(search_dir)):
                for fname in files:
                    fpath = Path(root) / fname
                    if fpath.stem.lower() == stem.lower():
                        candidates.append(fpath)

    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for p in candidates:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique_candidates.append(p)

    audio_path = next((str(p) for p in unique_candidates if p.exists()), None)

    if not audio_path:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Audio file not found on disk for '{filename}'. "
                f"Diarization needs the original recording. "
                f"Searched {len(unique_candidates)} locations including: "
                f"{[str(p) for p in unique_candidates[:6]]}"
            ),
        )

    try:
        # FIX: Get REAL per-sentence timestamps from Whisper before running diarization.
        # This is the critical fix — we must NOT use fake pseudo_segments.
        # transcribe_audio_with_timestamps() returns hundreds of small segments,
        # each with accurate start/end times. merge_with_transcript() uses these
        # to correctly assign each sentence to the speaker who said it.
        from server.core.transcription.transcribe          import transcribe_audio_with_timestamps
        from server.core.transcription.speaker_diarization import run_diarization

        logger.info(
            "Diarization for meeting %d: transcribing with timestamps first...",
            meeting_id,
        )

        # Run both Whisper (with timestamps) and pyannote in a thread
        # — both are CPU-bound blocking operations, must not run on the event loop
        whisper_segments = await asyncio.to_thread(
            transcribe_audio_with_timestamps, audio_path
        )

        logger.info(
            "Got %d whisper segments for meeting %d. Running pyannote...",
            len(whisper_segments), meeting_id,
        )

        result = await asyncio.to_thread(
            run_diarization,
            audio_path       = audio_path,
            whisper_segments = whisper_segments,
        )

        # Save to DB (talk_time and transcript for later cache + sentiment use)
        save_diarization(
            meeting_id   = meeting_id,
            transcript   = result["transcript"],
            talk_time    = result["talk_time"],
            num_speakers = result["num_speakers"],
        )

        return {
            "meeting_id":     meeting_id,
            "speakers":       result["speakers"],
            "segments":       result["segments"],
            "total_duration": result["total_duration"],
            "num_speakers":   result["num_speakers"],
            "transcript":     result["transcript"],
            "talk_time":      result["talk_time"],
            "cached":         False,
        }

    except RuntimeError as e:
        # RuntimeError = missing HF_TOKEN or pyannote not installed
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Diarization failed for meeting %d: %s", meeting_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Diarization failed: {type(e).__name__}: {str(e)[:200]}",
        )


def _parse_labeled_transcript(transcript: str) -> list[dict]:
    """
    Parse a labeled transcript string back into a list of segment dicts.

    Input line format:  "Speaker 1 [0:14]: I agree with that plan."
    Output:             {"speaker": "SPEAKER_01", "speaker_label": "Speaker 1",
                         "start": 14.0, "end": 14.0, "text": "I agree with that plan."}

    This allows us to rebuild the segments list from DB storage
    without re-running diarization.
    """
    import re
    segments = []
    pattern = re.compile(r'^(.*?)\s*\[(\d+):(\d{2})\]:\s*(.*)$')

    for i, line in enumerate(transcript.strip().split('\n')):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if not m:
            continue
        label   = m.group(1).strip()
        minutes = int(m.group(2))
        seconds = int(m.group(3))
        text    = m.group(4).strip()
        start   = float(minutes * 60 + seconds)

        # Try to infer speaker ID from label (Speaker 1 → SPEAKER_00)
        num_match = re.search(r'\d+', label)
        if num_match:
            sp_num = int(num_match.group()) - 1
            speaker_id = f"SPEAKER_{sp_num:02d}"
        else:
            speaker_id = f"SPEAKER_{i:02d}"

        segments.append({
            "speaker":       speaker_id,
            "speaker_label": label,
            "start":         start,
            "end":           start,   # end not stored in transcript string
            "text":          text,
        })

    return segments


@app.get("/meetings/{meeting_id}/diarization", tags=["Transcription"])
def get_diarization_result(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch stored diarization result. Returns 404 if not yet run.
    Returns the same full shape as POST /diarize for consistent frontend handling.
    """
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = get_diarization(meeting_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Speaker detection not run yet. Click 'Run Speaker Detection' to start."
        )

    talk_time  = result["talk_time"]
    transcript = result["transcript"]

    speakers_list = [
        {
            "id":             sp_id,
            "label":          data.get("label", sp_id),
            "total_time":     data.get("seconds", 0),
            "percentage":     data.get("percentage", 0),
            "segments_count": data.get("segments", 0),
        }
        for sp_id, data in talk_time.items()
    ]

    segments_list = _parse_labeled_transcript(transcript)

    return {
        "meeting_id":     meeting_id,
        "speakers":       speakers_list,
        "segments":       segments_list,
        "total_duration": segments_list[-1]["end"] if segments_list else 0,
        "num_speakers":   result["num_speakers"],
        "transcript":     transcript,
        "talk_time":      talk_time,
    }




@app.post("/meetings/{meeting_id}/sentiment", tags=["Analysis"])
async def analyze_meeting_sentiment(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Run sentiment + talk-time analysis on a meeting.
 
    PREREQUISITE:
        Diarization must be run first.
        Call POST /meetings/{id}/diarize before this endpoint.
        Without speaker labels, per-speaker sentiment is impossible.
 
    WHAT THIS DOES:
        1. Reads the diarized transcript from the database
        2. Runs Instructor-based sentiment extraction — one entry per speaker
        3. Analyses overall meeting tone, energy level, and tension
        4. Adds participation labels (dominant / balanced / quiet) to talk-time data
        5. Calculates a balance score (0-100, higher = more equal participation)
        6. Saves everything to the database
 
    FIRST CALL: runs the full analysis (~10-20 seconds, makes 2 LLM calls)
    REPEAT CALLS: returns the cached result instantly (no LLM call)
 
    To force a fresh analysis, call DELETE /meetings/{id}/sentiment first
    (not implemented yet — re-run diarization to invalidate).
 
    Returns:
        meeting_id         : the meeting
        num_speakers       : how many speakers were detected
        overall_sentiment  : "positive" / "neutral" / "negative"
        meeting_energy     : "high" / "medium" / "low"
        tension_detected   : true if conflict or frustration was detected
        sentiment_shift    : string describing mood change, or null
        speaker_sentiments : list of per-speaker sentiment objects
        talk_time          : talk-time breakdown with participation labels
    """
    # Verify meeting ownership
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
 
    # Return cached result if it exists
    cached = get_sentiment_analysis(meeting_id)
    if cached:
        return {**cached, "cached": True}
 
    # Run the full analysis in a thread (LLM calls are blocking)
    from server.core.intelligence.sentiment import run_full_analysis
 
    result = await asyncio.to_thread(run_full_analysis, meeting_id=meeting_id)
 
    if result is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Diarization has not been run for this meeting yet. "
                "Call POST /meetings/{id}/diarize first, then retry."
            ),
        )
 
    return {**result, "cached": False}
 
 
@app.get("/meetings/{meeting_id}/sentiment", tags=["Analysis"])
def get_meeting_sentiment(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch stored sentiment analysis for a meeting.
 
    Returns 404 if analysis hasn't been run yet.
    Call POST /meetings/{id}/sentiment first.
 
    This is a plain GET — no LLM calls, just a database read.
    Use this to display the results after the POST has completed.
    """
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
 
    result = get_sentiment_analysis(meeting_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No sentiment analysis found. Run POST /meetings/{id}/sentiment first.",
        )
 
    return result
 



@app.get("/meetings/{meeting_id}/agenda", tags=["Analysis"])
async def generate_meeting_agenda(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a smart agenda for the NEXT meeting after this one.
 
    Works in two modes — detected automatically:
 
    WORKSPACE MODE (if this meeting is in a project workspace):
        Pulls open action items and recurring topics from ALL meetings
        in the workspace. Gives the richest, most contextual agenda.
        Example: "You have 8 open items across 4 meetings — here are
                  the 5 most important things for next time."
 
    STANDALONE MODE (if this meeting has no workspace):
        Uses only this meeting's own open action items and topics.
        Still useful — just based on less history.
        Example: "You have 3 open items from this meeting — here's
                  a suggested agenda to follow up on them."
 
    REQUIRES:
        The meeting must have intelligence generated.
        Call GET /meetings/{id}/intelligence first if you haven't.
 
    This endpoint makes ONE Groq LLM call (~3-5 seconds).
    Results are NOT cached — each call generates a fresh agenda.
    (Agendas are time-sensitive — cached ones go stale fast.)
 
    Returns:
        meeting_id      : the meeting this agenda is based on
        mode            : "workspace" or "standalone"
        workspace_name  : name of the workspace (if mode is "workspace"), else null
        agenda_items    : list of 4-6 items, each with title, reason, priority
        context_source  : description of what data was used to generate this
        open_items_used : how many open action items were fed into the prompt
        topics_used     : how many unique topics were fed into the prompt
 
    Example agenda_items:
        [
            {
                "title":    "Q4 pricing decision",
                "reason":   "Discussed in 2 meetings, no final number confirmed",
                "priority": "high"
            },
            {
                "title":    "Deploy status update — Alice",
                "reason":   "Open action item, deadline was last Friday",
                "priority": "high"
            },
            {
                "title":    "Retrospective on sprint 14",
                "reason":   "Recurring topic across past 3 meetings",
                "priority": "medium"
            }
        ]
    """
    # Verify the meeting belongs to this user
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
 
    from server.core.intelligence.agenda import generate_agenda_for_meeting
 
    result = await asyncio.to_thread(
        generate_agenda_for_meeting,
        meeting_id=meeting_id,
        user_id=current_user.id,
    )
 
    if result is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
 
    return result

# =====================================================
# ASYNC CELERY UPLOAD
# =====================================================

@app.post("/upload/async", tags=["Processing"])
async def upload_file_async(
    file:                  UploadFile = File(...),
    current_user:          User       = Depends(get_current_user),
    enable_audio_cleaning: bool       = Query(default=True),
):
    ext = file.filename.split(".")[-1].lower()

    if ext in VIDEO_EXTENSIONS:
        file_path = VIDEO_DIR / file.filename
    elif ext in AUDIO_EXTENSIONS:
        file_path = AUDIO_DIR / file.filename
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    job_id = str(uuid.uuid4())

    from server.core.tasks import set_job_status, process_meeting_task
    set_job_status(job_id, {
        "step": "queued", "message": "Job queued — waiting for worker",
        "pct": 0, "meeting_id": None, "error": None,
    })
    process_meeting_task.delay(
        job_id                = job_id,
        file_path             = str(file_path.resolve()),
        filename              = file.filename,
        user_id               = current_user.id,
        enable_audio_cleaning = enable_audio_cleaning,
    )

    logger.info(f"Queued async job {job_id} for {file.filename} (user {current_user.id})")
    return {
        "job_id":   job_id,
        "status":   "queued",
        "filename": file.filename,
        "message":  "File uploaded. Processing started in background.",
    }


@app.get("/jobs/{job_id}/status", tags=["Processing"])
async def get_job_status(
    job_id:       str,
    current_user: User = Depends(get_current_user),
):
    # Read from our own store (_mem_jobs dict or Redis if available).
    # We do NOT call tasks.get_job_status() here because that uses Celery's
    # Redis backend and logs noisy "Could not read from Redis" warnings on
    # every poll when Redis is not running (local dev without Redis).
    # Our _read_job_status() already handles Redis gracefully via _get_redis().
    status = _read_job_status(job_id)

    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired (jobs kept for 1 hour).",
        )
    return {
        "job_id":     job_id,
        "step":       status.get("step"),
        "message":    status.get("message"),
        "pct":        status.get("pct", 0),
        "meeting_id": status.get("meeting_id"),
        "error":      status.get("error"),
    }


# =====================================================
# CONTACT
# =====================================================

@app.post("/contact", tags=["Support"])
async def contact(request: ContactRequest):
    import json

    try:
        entry = {
            "name":    request.name,
            "email":   request.email,
            "subject": request.subject,
            "message": request.message,
            "sent_at": datetime.datetime.now().isoformat(),
        }
        path        = Path("contact_submissions.json")
        submissions = []
        if path.exists():
            try:
                submissions = json.loads(path.read_text())
            except Exception:
                submissions = []
        submissions.append(entry)
        path.write_text(json.dumps(submissions, indent=2))
        logger.info(f"Contact form: {request.name} <{request.email}> — {request.subject}")
        return {"message": "Message received. We'll get back to you soon."}
    except Exception as e:
        logger.error(f"Contact form failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


# =====================================================
# GLOBAL ERROR HANDLER
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if isinstance(exc, FastAPIHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "status_code": 500},
    )


# =====================================================
# ENTRY POINT
# =====================================================

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Summly Backend on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")