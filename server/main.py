"""
Summly FastAPI Backend
Phase 2 Complete with Meeting Intelligence Engine
"""

# ── Structured logging — must be first ────────────────────────────────────────
from server.core.logging_config import setup_logging
setup_logging()

import structlog
slog = structlog.get_logger()
mlog = structlog.get_logger()

# ── Standard library ──────────────────────────────────────────────────────────
import uuid
import time
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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Internal ──────────────────────────────────────────────────────────────────
from server.core.auth.dependencies import get_current_user, get_optional_user
from server.core.auth.models import User
from server.core.auth.router import router as auth_router
from server.core.storage import upload_file as upload_to_supabase

from server.core.database import (
    init_db,
    get_all_transcripts,
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

app = FastAPI(
    title="Summly API",
    version="2.0.0",
    description="AI Meeting Intelligence Platform Backend",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Aggregate stats across all meetings for the logged-in user."""
    try:
        meetings        = get_all_transcripts(user_id=current_user.id)
        total_meetings  = len(meetings)
        total_decisions = 0
        total_actions   = 0
        total_topics    = 0

        for row in meetings:
            try:
                intel = get_meeting_intelligence(row["id"])
                if intel:
                    total_decisions += len(intel.get("decisions",    []))
                    total_actions   += len(intel.get("action_items", []))
                    total_topics    += len(intel.get("topics",       []))
            except Exception:
                pass

        return {
            "total_meetings":  total_meetings,
            "total_decisions": total_decisions,
            "total_actions":   total_actions,
            "total_topics":    total_topics,
        }
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


# =====================================================
# ACTION ITEM ENDPOINTS
# =====================================================

@app.get("/tasks", tags=["Action Items"])
def get_all_tasks(
    status:       str | None = Query(default=None),
    priority:     str | None = Query(default=None),
    owner:        str | None = Query(default=None),
    current_user: User       = Depends(get_current_user),
):
    items = get_all_action_items(user_id=current_user.id)

    if status:
        items = [i for i in items if i["status"] == status.lower()]
    if priority:
        items = [i for i in items if i["priority"] == priority.lower()]
    if owner:
        items = [i for i in items if i["owner"] and owner.lower() in i["owner"].lower()]

    return {"total": len(items), "items": items}


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

    return {"message": "Deleted", "item_id": item_id}


# =====================================================
# MEETING ENDPOINTS
# =====================================================

@app.get("/meetings", response_model=list[MeetingBasic], tags=["Meetings"])
def list_meetings(current_user: User = Depends(get_current_user)):
    try:
        records = get_all_transcripts(user_id=current_user.id)
        return [
            MeetingBasic(
                id               = row["id"],
                filename         = row["filename"],
                created_at       = str(row["created_at"]),
                duration_seconds = row["duration_seconds"],
            )
            for row in records
        ]
    except Exception as e:
        logger.error(f"Failed to fetch meetings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch meetings")


@app.get("/meetings/{meeting_id}", response_model=MeetingDetail, tags=["Meetings"])
def get_meeting(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    try:
        meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        return MeetingDetail(
            id               = meeting["id"],
            filename         = meeting["filename"],
            transcript       = meeting["transcript"],
            created_at       = str(meeting["created_at"]),
            duration_seconds = meeting["duration_seconds"],
            intelligence     = get_intelligence_for_response(meeting_id),
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
    S_section = style("S",  fontSize=13, fontName="Helvetica-Bold",
                      textColor=colors.HexColor("#4f46e5"), spaceBefore=24, spaceAfter=10)
    S_body    = style("B",  fontSize=10, leading=16,
                      textColor=colors.HexColor("#2e3650"), spaceAfter=4)
    S_bullet  = style("BL", fontSize=10, leading=15,
                      textColor=colors.HexColor("#2e3650"), leftIndent=14, spaceAfter=3)
    S_quote   = style("Q",  fontSize=10, leading=15, textColor=colors.HexColor("#4f46e5"),
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
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f5f7ff")),
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
            ("BACKGROUND",     (0,0), (-1,0),  colors.HexColor("#f5f7ff")),
            ("TEXTCOLOR",      (0,0), (-1,0),  colors.HexColor("#4f46e5")),
            ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f9faff")]),
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
            ("BACKGROUND",     (0,0),  (-1,0),  colors.HexColor("#f5f7ff")),
            ("TEXTCOLOR",      (0,0),  (-1,0),  colors.HexColor("#4f46e5")),
            ("FONTNAME",       (0,0),  (-1,0),  "Helvetica-Bold"),
            ("FONTNAME",       (0,-1), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),  (-1,-1), 9),
            ("GRID",           (0,0),  (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0,1),  (-1,-2), [colors.white, colors.HexColor("#f9faff")]),
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
    start_time = time.time()
    ext        = file.filename.split(".")[-1].lower()

    if ext in VIDEO_EXTENSIONS:
        file_path = VIDEO_DIR / file.filename
    elif ext in AUDIO_EXTENSIONS:
        file_path = AUDIO_DIR / file.filename
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}",
        )

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        slog.info("file_saved", filename=file.filename, path=str(file_path), user_id=current_user.id)

        supabase_filename = f"user_{current_user.id}/{file.filename}"
        file_url = upload_to_supabase(local_path=str(file_path), filename=supabase_filename)
        slog.info("file_uploaded_supabase", filename=file.filename, url=file_url, user_id=current_user.id)

    except Exception as e:
        slog.error("file_save_failed", filename=file.filename, error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to save file")

    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File size exceeds 500 MB limit")

    file_size_mb = round(file_size / (1024 * 1024), 2)

    try:
        from server.core.transcription.audio_extractor import extract_audio

        if ext in VIDEO_EXTENSIONS:
            wav_file = extract_audio(str(file_path), enable_cleaning=enable_audio_cleaning)
        else:
            wav_file = str(file_path)
            if enable_audio_cleaning:
                try:
                    from server.core.transcription.audio_cleaner import AudioCleaner
                    cleaner = AudioCleaner(sr=16000)
                    result  = cleaner.clean_audio(
                        wav_file, output_path=wav_file,
                        enable_noise_reduction=True, enable_compression=True, save_output=True,
                    )
                    logger.info(f"✓ Audio cleaned — SNR improvement: {result['snr_improvement_db']:+.1f}dB")
                except Exception as e:
                    logger.warning(f"Audio cleaning failed (non-fatal): {e}")

        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_file)
        logger.info(f"Transcription complete: {len(transcript)} characters")

        meeting_id = save_transcript_and_get_id(
            filename=file.filename, transcript=transcript, user_id=current_user.id,
        )

        from server.core.intelligence.workflow import analyze_transcript
        intelligence = analyze_transcript(transcript)
        save_meeting_intelligence(meeting_id, intelligence)
        slog.info("intelligence_saved", meeting_id=meeting_id,
                  actions=len(intelligence.action_items),
                  decisions=len(intelligence.decisions),
                  topics=len(intelligence.topics))

        try:
            from server.core.rag.indexer import index_meeting
            index_meeting(meeting_id=meeting_id, filename=file.filename,
                          transcript=transcript, created_at="")
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        transcript_file = TRANSCRIPT_DIR / f"{Path(file.filename).stem}.txt"
        transcript_file.write_text(transcript, encoding="utf-8")

        processing_time = round(time.time() - start_time, 2)
        slog.info("upload_complete", filename=file.filename, meeting_id=meeting_id,
                  processing_time=processing_time, user_id=current_user.id)

        return TranscriptResponse(
            meeting_id      = meeting_id,
            filename        = file.filename,
            transcript_file = str(transcript_file),
            transcript      = transcript,
            intelligence    = get_intelligence_for_response(meeting_id),
            processing_time = processing_time,
            file_size_mb    = file_size_mb,
        )

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# =====================================================
# YOUTUBE ENDPOINT
# =====================================================

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
                          transcript=transcript, created_at="")
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
        result = chat_with_meeting(query=body.query, meeting_id=body.meeting_id)
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
        result = chat_across_meetings(query=request.query)
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
        stream_chat_with_meeting(query=query, meeting_id=meeting_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/chat/search/stream", tags=["Chat"])
async def stream_chat_search(
    query:        str  = Query(...),
    current_user: User = Depends(get_current_user),
):
    from server.core.rag.chat import stream_chat_across_meetings
    return StreamingResponse(
        stream_chat_across_meetings(query=query),
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
def reindex_all(current_user: User = Depends(get_current_user)):
    try:
        from server.core.rag.indexer import index_meeting
        meetings = get_all_meetings_for_indexing(user_id=current_user.id)
        indexed  = 0
        for m in meetings:
            try:
                index_meeting(
                    meeting_id = m["id"],
                    filename   = m["filename"],
                    transcript = m["transcript"],
                    created_at = m["created_at"],
                    user_id    = m.get("user_id"),
                )
                indexed += 1
            except Exception as e:
                logger.warning(f"Failed to index meeting {m['id']}: {e}")
        return {"indexed": indexed, "total": len(meetings)}
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail="Reindex failed")


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
    async def step(name: str, message: str, pct: int):
        await progress.send(job_id, {
            "step": name, "message": message, "pct": pct,
            "ts": datetime.datetime.now().isoformat(),
        })

    try:
        await step("extract",    "Extracting audio...",                10)
        transcript = await asyncio.to_thread(transcript_fn)

        await step("transcribe", "Transcription complete",             40)
        meeting_id = await asyncio.to_thread(
            save_transcript_and_get_id, filename, transcript, None, user_id
        )

        await step("intel",      "Generating meeting intelligence...", 60)
        from server.core.intelligence.workflow import analyze_transcript
        intelligence = await asyncio.to_thread(analyze_transcript, transcript)

        await step("intel",      "Saving intelligence...",             75)
        await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

        await step("index",      "Indexing for RAG search...",         88)
        try:
            from server.core.rag.indexer import index_meeting
            await asyncio.to_thread(index_meeting, meeting_id, filename, transcript, "")
        except Exception as e:
            logger.warning(f"Index failed (non-fatal): {e}")

        await step("done",       "Processing complete!",               100)
        return meeting_id, transcript, intelligence

    except Exception as e:
        await progress.send(job_id, {"step": "error", "message": str(e), "pct": 0})
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

        supabase_filename = f"user_{current_user.id}/{file.filename}"
        upload_to_supabase(local_path=str(file_path), filename=supabase_filename)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

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

    def do_transcribe():
        from server.core.transcription.youtube_downloader import download_youtube
        from server.core.transcription.audio_extractor import extract_audio
        from server.core.transcription.transcribe import transcribe_audio
        yt_data = download_youtube(str(url))
        wav     = extract_audio(yt_data["audio_file"], enable_cleaning=enable_audio_cleaning)
        return transcribe_audio(wav), yt_data["title"]

    await progress.send(job_id, {"step": "download", "message": "Downloading YouTube audio...", "pct": 8})

    try:
        transcript, title = await asyncio.to_thread(do_transcribe)
    except Exception as e:
        await progress.send(job_id, {"step": "error", "message": str(e), "pct": 0})
        raise HTTPException(status_code=500, detail=str(e))

    await progress.send(job_id, {"step": "transcribe", "message": "Transcription complete", "pct": 40})

    meeting_id = await asyncio.to_thread(
        save_transcript_and_get_id, title, transcript, None, current_user.id
    )

    await progress.send(job_id, {"step": "intel", "message": "Generating intelligence...", "pct": 60})
    from server.core.intelligence.workflow import analyze_transcript
    intelligence = await asyncio.to_thread(analyze_transcript, transcript)
    await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

    await progress.send(job_id, {"step": "index", "message": "Indexing for RAG...", "pct": 88})
    try:
        from server.core.rag.indexer import index_meeting
        await asyncio.to_thread(index_meeting, meeting_id, title, transcript, "")
    except Exception as e:
        logger.warning(f"Index failed: {e}")

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
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.get("transcript"):
        raise HTTPException(status_code=400, detail="No transcript yet. Upload and process first.")

    cached = get_diarization(meeting_id)
    if cached:
        return {
            "meeting_id":   meeting_id,
            "transcript":   cached["transcript"],
            "talk_time":    cached["talk_time"],
            "num_speakers": cached["num_speakers"],
            "cached":       True,
        }

    filename = meeting["filename"]
    stem     = Path(filename).stem
    candidates = [
        AUDIO_DIR / f"{stem}.wav",
        AUDIO_DIR / filename,
        VIDEO_DIR / filename,
    ]
    audio_path = next((str(p) for p in candidates if p.exists()), None)

    if not audio_path:
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found. Looked in: {[str(p) for p in candidates]}",
        )

    try:
        from server.core.transcription.speaker_diarization import run_diarization
        pseudo_segments = [{"start": 0.0, "end": 9999.0, "text": meeting["transcript"]}]

        result = await asyncio.to_thread(
            run_diarization, audio_path=audio_path, whisper_segments=pseudo_segments,
        )
        save_diarization(
            meeting_id   = meeting_id,
            transcript   = result["transcript"],
            talk_time    = result["talk_time"],
            num_speakers = result["num_speakers"],
        )
        return {
            "meeting_id":   meeting_id,
            "transcript":   result["transcript"],
            "talk_time":    result["talk_time"],
            "num_speakers": result["num_speakers"],
            "cached":       False,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Diarization failed for meeting {meeting_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Diarization failed: {str(e)}")


@app.get("/meetings/{meeting_id}/diarization", tags=["Transcription"])
def get_diarization_result(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = get_diarization(meeting_id)
    if not result:
        raise HTTPException(status_code=404, detail="No diarization found. Run POST /meetings/{id}/diarize first.")

    return {
        "meeting_id":   meeting_id,
        "transcript":   result["transcript"],
        "talk_time":    result["talk_time"],
        "num_speakers": result["num_speakers"],
    }


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
    from server.core.tasks import get_job_status as _get_status
    status = _get_status(job_id)

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