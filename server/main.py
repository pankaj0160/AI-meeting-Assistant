"""
Summly FastAPI Backend
Phase 2 Complete with Meeting Intelligence Engine
"""

import uuid
import datetime
from server.core.auth.dependencies import get_current_user, get_optional_user
from server.core.auth.models import User
from typing import Optional
from server.core.auth.router import router as auth_router
from fastapi import Depends, FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel, HttpUrl
import shutil
import time
import logging

# ── Lazy-loaded at first use (heavy AI / ML deps) ──────────────────────────
# from server.core.transcription.audio_extractor import extract_audio       # FFmpeg-heavy
# from server.core.transcription.transcribe import transcribe_audio          # Whisper
# from server.core.transcription.youtube_downloader import download_youtube  # yt-dlp
# from server.core.intelligence.workflow import analyze_transcript            # LLM
# from server.core.rag.indexer import index_meeting                          # ChromaDB
# from server.core.rag.chat import chat_with_meeting, chat_across_meetings   # SentenceTransformer
# ───────────────────────────────────────────────────────────────────────────

from server.core.database import (
    init_db,
    get_all_transcripts,
    save_transcript_and_get_id,
    save_meeting_intelligence,
    get_meeting_intelligence,
    get_meeting_by_id,
)

from server.core.intelligence.health  import analyze_meeting_health
from server.core.intelligence.quotes  import extract_key_quotes
from server.core.intelligence.titles  import generate_meeting_title
from server.core.database import (
    init_db,
    get_all_transcripts,
    save_transcript_and_get_id,
    save_meeting_intelligence,
    get_meeting_intelligence,
    get_meeting_by_id,
    save_meeting_health,
    get_meeting_health,
    save_meeting_quotes,
    get_meeting_quotes,
    save_meeting_title,
    get_meeting_title,
    update_action_item_status,
)

from server.core.intelligence.followup import generate_followup_email
from server.core.database import get_meeting_title
from fastapi.responses import StreamingResponse
import io

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)

# =====================================================
# APP SETUP
# =====================================================

app = FastAPI(
    title="Summly API",
    version="2.0.0",
    description="AI Meeting Intelligence Platform Backend"
)


@app.middleware("http")
async def request_logger(request, call_next):
    print(f"REQUEST >>> {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"RESPONSE <<< {response.status_code}")
    return response

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()
logger.info("Database initialized")

# Register routers
app.include_router(auth_router)

# =====================================================
# REQUEST MODELS
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
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }

class ChatRequest(BaseModel):
    query: str
    meeting_id: int | None = None



class AgentRequest(BaseModel):
    """
    Request body for the /agent/chat endpoint.
 
    query      : the user's question in plain English
    meeting_id : which meeting to answer about
    """
    query:      str
    meeting_id: int


# =====================================================
# RESPONSE MODELS
# =====================================================

class IntelligenceResponse(BaseModel):
    summary: str
    action_items: list = []
    decisions: list = []
    topics: list = []
    generated_at: str

class MeetingBasic(BaseModel):
    id: int
    filename: str
    created_at: str
    duration_seconds: float | None = None

class TranscriptResponse(BaseModel):
    meeting_id: int
    filename: str
    transcript_file: str
    transcript: str
    intelligence: IntelligenceResponse | None = None
    processing_time: float
    file_size_mb: float

class YouTubeResponse(BaseModel):
    meeting_id: int
    title: str
    transcript_file: str
    transcript: str
    intelligence: IntelligenceResponse | None = None
    processing_time: float

class MeetingDetail(BaseModel):
    id: int
    filename: str
    transcript: str
    created_at: str
    duration_seconds: float | None = None
    intelligence: IntelligenceResponse | None = None

# =====================================================
# CONFIGURATION
# =====================================================

VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "webm"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac", "flac"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

# =====================================================
# FOLDER STRUCTURE
# =====================================================

AUDIO_DIR = Path("uploads/audio")
VIDEO_DIR = Path("uploads/video")
TRANSCRIPT_DIR = Path("uploads/transcripts")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Upload directories created: {AUDIO_DIR}, {VIDEO_DIR}, {TRANSCRIPT_DIR}")

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def serialize_intelligence(intel_obj) -> dict:
    """
    Convert MeetingIntelligence Pydantic model to dict.
    Handles both Pydantic v1 and v2.
    """
    if intel_obj is None:
        return None
    if hasattr(intel_obj, 'model_dump'):
        return intel_obj.model_dump()
    elif hasattr(intel_obj, 'dict'):
        return intel_obj.dict()
    else:
        return intel_obj


def get_intelligence_for_response(meeting_id: int):
    """Fetch and serialize intelligence for API response."""
    try:
        intel = get_meeting_intelligence(meeting_id)
        if intel:
            return IntelligenceResponse(
                summary=intel.get("summary", ""),
                action_items=intel.get("action_items", []),
                decisions=intel.get("decisions", []),
                topics=intel.get("topics", []),
                generated_at=intel.get("generated_at", "")
            )
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch intelligence for meeting {meeting_id}: {e}")
        return None

# =====================================================
# HEALTH ENDPOINTS
# =====================================================

@app.get("/", tags=["System"])
def root():
    return {
        "service":  "Summly Backend",
        "version":  "2.0.0",
        "status":   "running",
        "features": ["Audio Upload", "YouTube Download", "Speech-to-Text", "Meeting Intelligence"]
    }

@app.get("/health", tags=["System"])
def health():
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# =====================================================
# UPLOAD ENDPOINT
# =====================================================

@app.post("/upload", response_model=TranscriptResponse, tags=["Processing"])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True, description="Enable audio noise reduction and normalization"),
):
    """
    Upload and process an audio or video file.
    Returns transcript + AI intelligence.
    """

    start_time = time.time()

    ext = file.filename.split(".")[-1].lower()

    if ext in VIDEO_EXTENSIONS:
        file_path = VIDEO_DIR / file.filename
    elif ext in AUDIO_EXTENSIONS:
        file_path = AUDIO_DIR / file.filename
    else:
        logger.error(f"Unsupported file type: {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}"
        )

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved: {file_path}")
    except Exception as e:
        logger.error(f"File save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        logger.error(f"File exceeds size limit: {file_size / 1024 / 1024:.2f} MB")
        raise HTTPException(status_code=400, detail="File size exceeds 500 MB limit")

    file_size_mb = round(file_size / (1024 * 1024), 2)
    logger.info(f"Processing file: {file.filename} ({file_size_mb} MB)")

    try:
        # Lazy import — FFmpeg-heavy
        from server.core.transcription.audio_extractor import extract_audio

        if ext in VIDEO_EXTENSIONS:
            logger.info("Extracting audio from video...")
            wav_file = extract_audio(str(file_path), enable_cleaning=enable_audio_cleaning)
        else:
            wav_file = str(file_path)

            if enable_audio_cleaning:
                try:
                    logger.info("Cleaning uploaded audio file...")
                    from server.core.transcription.audio_cleaner import AudioCleaner
                    cleaner = AudioCleaner(sr=16000)
                    result = cleaner.clean_audio(
                        wav_file,
                        output_path=wav_file,
                        enable_noise_reduction=True,
                        enable_compression=True,
                        save_output=True
                    )
                    logger.info(f"✓ Audio cleaned - SNR improvement: {result['snr_improvement_db']:+.1f}dB")
                except Exception as e:
                    logger.warning(f"Audio cleaning failed (non-fatal): {e}")

        # Lazy import — loads Whisper model
        logger.info("Transcribing audio...")
        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_file)
        logger.info(f"Transcription complete: {len(transcript)} characters")

        logger.info("Saving to database...")
        meeting_id = save_transcript_and_get_id(
            filename=file.filename,
            transcript=transcript,
            user_id=current_user.id,
        )

        # Lazy import — LLM call
        logger.info(f"Generating intelligence for meeting {meeting_id}...")
        from server.core.intelligence.workflow import analyze_transcript
        intelligence = analyze_transcript(transcript)

        save_meeting_intelligence(meeting_id, intelligence)
        logger.info(f"Intelligence saved: {len(intelligence.action_items)} items, "
                    f"{len(intelligence.decisions)} decisions, {len(intelligence.topics)} topics")

        # Lazy import — loads ChromaDB
        try:
            from server.core.rag.indexer import index_meeting
            index_meeting(
                meeting_id=meeting_id,
                filename=file.filename,
                transcript=transcript,
                created_at="",
            )
            logger.info(f"ChromaDB indexed for meeting {meeting_id}")
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        transcript_file = TRANSCRIPT_DIR / f"{Path(file.filename).stem}.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript)

        processing_time = round(time.time() - start_time, 2)
        logger.info(f"Processing complete in {processing_time}s")

        return TranscriptResponse(
            meeting_id=meeting_id,
            filename=file.filename,
            transcript_file=str(transcript_file),
            transcript=transcript,
            intelligence=get_intelligence_for_response(meeting_id),
            processing_time=processing_time,
            file_size_mb=file_size_mb
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
    request: YouTubeRequest,
    current_user: User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True, description="Enable audio noise reduction"),
):
    """
    Download, transcribe, and analyze YouTube video.
    Returns transcript + AI intelligence.
    """

    start_time = time.time()

    try:
        logger.info(f"Processing YouTube URL: {request.url}")

        # Lazy import — yt-dlp
        logger.info("Downloading audio from YouTube...")
        from server.core.transcription.youtube_downloader import download_youtube
        youtube_data = download_youtube(str(request.url))

        mp3_file = youtube_data["audio_file"]
        title = youtube_data["title"]
        logger.info(f"Downloaded: {title}")

        # Lazy import — FFmpeg-heavy
        logger.info("Converting audio format...")
        from server.core.transcription.audio_extractor import extract_audio
        wav_file = extract_audio(mp3_file, enable_cleaning=enable_audio_cleaning)

        # Lazy import — loads Whisper model
        logger.info("Transcribing audio...")
        from server.core.transcription.transcribe import transcribe_audio
        transcript = transcribe_audio(wav_file)
        logger.info(f"Transcription complete: {len(transcript)} characters")

        logger.info("Saving to database...")
        meeting_id = save_transcript_and_get_id(
            filename=title,
            transcript=transcript,
            user_id=current_user.id,
        )

        # Lazy import — LLM call
        logger.info(f"Generating intelligence for meeting {meeting_id}...")
        from server.core.intelligence.workflow import analyze_transcript
        intelligence = analyze_transcript(transcript)

        save_meeting_intelligence(meeting_id, intelligence)
        logger.info(f"Intelligence saved: {len(intelligence.action_items)} items, "
                    f"{len(intelligence.decisions)} decisions, {len(intelligence.topics)} topics")

        # Lazy import — loads ChromaDB
        try:
            from server.core.rag.indexer import index_meeting
            index_meeting(
                meeting_id=meeting_id,
                filename=title,
                transcript=transcript,
                created_at="",
            )
            logger.info(f"ChromaDB indexed for meeting {meeting_id}")
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        transcript_file = TRANSCRIPT_DIR / f"{title}.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript)

        processing_time = round(time.time() - start_time, 2)
        logger.info(f"Processing complete in {processing_time}s")

        return YouTubeResponse(
            meeting_id=meeting_id,
            title=title,
            transcript_file=str(transcript_file),
            transcript=transcript,
            intelligence=get_intelligence_for_response(meeting_id),
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"YouTube processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# =====================================================
# MEETING ENDPOINTS
# =====================================================

@app.get("/meetings", response_model=list[MeetingBasic], tags=["Meetings"])
def list_meetings(current_user: User = Depends(get_current_user)):
    """Get all meetings for the authenticated user."""
    try:
        records = get_all_transcripts(user_id=current_user.id)
        return [
            MeetingBasic(
                id=row[0],
                filename=row[1],
                created_at=row[3],
                duration_seconds=row[4]
            )
            for row in records
        ]
    except Exception as e:
        logger.error(f"Failed to fetch meetings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch meetings")

@app.get("/meetings/{meeting_id}", response_model=MeetingDetail, tags=["Meetings"])
def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific meeting."""
    try:
        meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)

        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        intelligence = get_intelligence_for_response(meeting_id)

        return MeetingDetail(
            id=meeting["id"],
            filename=meeting["filename"],
            transcript=meeting["transcript"],
            created_at=meeting["created_at"],
            duration_seconds=meeting["duration_seconds"],
            intelligence=intelligence
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch meeting {meeting_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch meeting")

@app.get("/meetings/{meeting_id}/intelligence", response_model=IntelligenceResponse, tags=["Meetings"])
def meeting_intelligence(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get intelligence report for a specific meeting."""
    try:
        meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        intelligence = get_meeting_intelligence(meeting_id)

        if intelligence is None:
            raise HTTPException(
                status_code=404,
                detail="No intelligence found for this meeting"
            )

        return IntelligenceResponse(
            summary=intelligence.get("summary", ""),
            action_items=intelligence.get("action_items", []),
            decisions=intelligence.get("decisions", []),
            topics=intelligence.get("topics", []),
            generated_at=intelligence.get("generated_at", "")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch intelligence for meeting {meeting_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch intelligence")


# =====================================================
# CHAT ENDPOINTS
# =====================================================

@app.post("/chat/meeting", tags=["Chat"])
def chat_meeting(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Answer a question grounded in a single meeting.
    Requires meeting_id in the request body.
    """
    if not request.meeting_id:
        raise HTTPException(
            status_code=400,
            detail="meeting_id is required for single meeting chat"
        )

    try:
        meeting = get_meeting_by_id(request.meeting_id, user_id=current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Lazy import — loads SentenceTransformer + ChromaDB
        from server.core.rag.chat import chat_with_meeting
        result = chat_with_meeting(
            query=request.query,
            meeting_id=request.meeting_id,
        )
        return {
            "answer":     result["answer"],
            "sources":    result["sources"],
            "meeting_id": request.meeting_id,
            "mode":       "single",
        }
    except Exception as e:
        logger.error(f"Chat failed for meeting {request.meeting_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/chat/search", tags=["Chat"])
def chat_search(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Answer a question by searching across ALL meetings.
    """
    try:
        # Lazy import — loads SentenceTransformer + ChromaDB
        from server.core.rag.chat import chat_across_meetings
        result = chat_across_meetings(query=request.query)
        return {
            "answer":  result["answer"],
            "sources": result["sources"],
            "mode":    "cross",
        }
    except Exception as e:
        logger.error(f"Cross-meeting chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
    







@app.get("/chat/meeting/stream", tags=["Chat"])
async def stream_chat_meeting(
    query: str = Query(..., description="The question to ask about the meeting"),
    meeting_id: int = Query(..., description="The ID of the meeting to query"),
    current_user: User = Depends(get_current_user),
):
    """
    Stream an answer about a single meeting using Server-Sent Events.
 
    Returns tokens one by one as the LLM generates them.
    The final event contains {"done": true, "sources": [...]} with citations.
 
    Use this instead of POST /chat/meeting when you want the response
    to appear word-by-word in the UI (much better user experience).
 
    Example curl:
        curl -N -H "Authorization: Bearer <token>" \\
          "http://localhost:8000/chat/meeting/stream?query=What+were+the+decisions&meeting_id=1"
    """
    # Verify the meeting exists and belongs to this user
    # (same auth check as the non-streaming endpoint)
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
 
    # Lazy import — loads SentenceTransformer + ChromaDB on first call
    from server.core.rag.chat import stream_chat_with_meeting
 
    # StreamingResponse wraps our generator and sends each yielded string
    # to the client as it's produced — no buffering.
    #
    # media_type="text/event-stream" is the MIME type for SSE.
    # Without it, the browser would treat this as a regular text download
    # instead of a live event stream.
    #
    # headers["Cache-Control"] = "no-cache" is required by the SSE spec.
    # It tells browsers and proxies never to cache the stream.
    #
    # headers["X-Accel-Buffering"] = "no" disables Nginx buffering.
    # Without this, Nginx would collect the whole response before sending it,
    # completely defeating the purpose of streaming.
    return StreamingResponse(
        stream_chat_with_meeting(query=query, meeting_id=meeting_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":      "keep-alive",
        },
    )
 
 
@app.get("/chat/search/stream", tags=["Chat"])
async def stream_chat_search(
    query: str = Query(..., description="The question to ask across all meetings"),
    current_user: User = Depends(get_current_user),
):
    """
    Stream an answer by searching across ALL meetings using Server-Sent Events.
 
    Returns tokens one by one as the LLM generates them.
    The final event contains {"done": true, "sources": [...]} with citations.
 
    Example curl:
        curl -N -H "Authorization: Bearer <token>" \\
          "http://localhost:8000/chat/search/stream?query=What+decisions+were+made"
    """
    from server.core.rag.chat import stream_chat_across_meetings
 
    return StreamingResponse(
        stream_chat_across_meetings(query=query),
        media_type="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":      "keep-alive",
        },
    )
 


 
 
# ── Add this endpoint after your /chat/search/stream endpoint ─────────────────
 
@app.post("/agent/chat", tags=["Agent"])
async def agent_chat(
    request: AgentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Tool-calling ReAct agent that answers questions about a meeting.
 
    Unlike /chat/meeting (which always does RAG), this agent DECIDES which
    tool(s) to use based on the question:
 
      "What were the action items?"  → calls get_action_items()
      "How did the meeting go?"      → calls get_health_score()
      "What was decided about X?"    → calls get_decisions() and/or search_transcript()
      "Give me a full recap"         → calls summarize_meeting() + get_action_items() + get_decisions()
 
    The agent runs a ReAct loop: Think → Act (call tool) → Observe (read result) → repeat.
    It stops when it has enough information to give a final answer.
 
    Returns:
        answer     : the agent's final answer
        tools_used : which tools were called (useful for debugging)
        iterations : how many reasoning steps it took
        meeting_id : echoed back for convenience
    """
    # Verify the meeting exists and belongs to this user
    # (same check as /chat/meeting — never let a user query another user's meeting)
    meeting = get_meeting_by_id(request.meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
 
    try:
        # Lazy import — avoids loading the agent module at startup
        from server.core.agent.meeting_agent import run_agent
 
        result = run_agent(
            query=request.query,
            meeting_id=request.meeting_id,
        )
 
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
# STATS ENDPOINT
# =====================================================

@app.get("/stats", tags=["System"])
def get_stats(current_user: User = Depends(get_current_user)):
    """Aggregate stats across all meetings."""
    try:
        from server.core.database import get_all_transcripts, get_meeting_intelligence
        meetings = get_all_transcripts(user_id=current_user.id)
        total_meetings   = len(meetings)
        total_decisions  = 0
        total_actions    = 0
        total_topics     = 0

        for row in meetings:
            meeting_id = row[0]
            try:
                intel = get_meeting_intelligence(meeting_id)
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
# REINDEX ENDPOINT
# =====================================================

@app.post("/rag/reindex", tags=["RAG"])
def reindex_all(current_user: User = Depends(get_current_user)):
    try:
        from server.core.database import get_all_meetings_for_indexing
        # Lazy import — loads ChromaDB
        from server.core.rag.indexer import index_meeting
        meetings = get_all_meetings_for_indexing(user_id=current_user.id)
        indexed = 0
        for m in meetings:
            try:
                index_meeting(
                    meeting_id=m["id"],
                    filename=m["filename"],
                    transcript=m["transcript"],
                    created_at=m["created_at"],
                    user_id=m.get("user_id"),
                )
                indexed += 1
            except Exception as e:
                logger.warning(f"Failed to index meeting {m['id']}: {e}")
        return { "indexed": indexed, "total": len(meetings) }
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail="Reindex failed")

# =====================================================
# WEBSOCKET PROGRESS ENDPOINT
# =====================================================

class ProgressManager:
    """
    Manages active WebSocket connections keyed by job_id.
    Each upload gets a unique job_id — frontend connects
    before upload starts and receives live step updates.
    """
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, job_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[job_id] = ws
        logger.info(f"WebSocket connected: {job_id}")

    def disconnect(self, job_id: str):
        self.connections.pop(job_id, None)
        logger.info(f"WebSocket disconnected: {job_id}")

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


# =====================================================
# UPLOAD WITH PROGRESS
# =====================================================

class ProgressRequest(BaseModel):
    job_id: str

async def _run_with_progress(job_id: str, filename: str, transcript_fn, user_id: int = None):
    """
    Shared progress-aware processing pipeline.
    Sends step updates over WebSocket as each phase completes.
    """
    import datetime

    async def step(name: str, message: str, pct: int):
        await progress.send(job_id, {
            "step":    name,
            "message": message,
            "pct":     pct,
            "ts":      datetime.datetime.now().isoformat(),
        })

    try:
        await step("extract",    "Extracting audio...",           10)
        transcript = await asyncio.to_thread(transcript_fn)

        await step("transcribe", "Transcription complete",        40)

        meeting_id = await asyncio.to_thread(
            save_transcript_and_get_id, filename, transcript, None, user_id
        )

        await step("intel",      "Generating meeting intelligence...", 60)
        # Lazy import — LLM call
        from server.core.intelligence.workflow import analyze_transcript
        intelligence = await asyncio.to_thread(analyze_transcript, transcript)

        await step("intel",      "Saving intelligence...",        75)
        await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

        await step("index",      "Indexing for RAG search...",    88)
        try:
            # Lazy import — loads ChromaDB
            from server.core.rag.indexer import index_meeting
            await asyncio.to_thread(
                index_meeting, meeting_id, filename, transcript, ""
            )
        except Exception as e:
            logger.warning(f"Index failed (non-fatal): {e}")

        await step("done",       "Processing complete!",          100)

        return meeting_id, transcript, intelligence

    except Exception as e:
        await progress.send(job_id, {
            "step":    "error",
            "message": str(e),
            "pct":     0,
        })
        raise


@app.post("/upload/progress", tags=["Processing"])
async def upload_file_with_progress(
    file:   UploadFile = File(...),
    job_id: str = Query(default=None),
    current_user: User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True),
):
    """
    Upload endpoint that streams progress over WebSocket.
    Pass job_id as a query param: /upload/progress?job_id=xyz
    """
    from fastapi import Query
    start_time = time.time()
    ext = file.filename.split(".")[-1].lower()

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
        raise HTTPException(status_code=500, detail="Failed to save file")

    file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)

    def do_transcribe():
        # Lazy imports — FFmpeg + Whisper
        from server.core.transcription.audio_extractor import extract_audio
        from server.core.transcription.transcribe import transcribe_audio
        if ext in VIDEO_EXTENSIONS:
            wav = extract_audio(str(file_path), enable_cleaning=enable_audio_cleaning)
        else:
            wav = str(file_path)
        return transcribe_audio(wav)

    meeting_id, transcript, intelligence = await _run_with_progress(
        job_id        = job_id or "noop",
        filename      = file.filename,
        transcript_fn = do_transcribe,
        user_id       = current_user.id,
    )

    processing_time = round(time.time() - start_time, 2)

    return TranscriptResponse(
        meeting_id      = meeting_id,
        filename        = file.filename,
        transcript_file = "",
        transcript      = transcript,
        intelligence    = get_intelligence_for_response(meeting_id),
        processing_time = processing_time,
        file_size_mb    = file_size_mb,
    )


@app.post("/youtube/progress", tags=["Processing"])
async def youtube_with_progress(
    request: dict,
    job_id: str = None,
    current_user: User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True),
):
    """
    YouTube endpoint that streams progress over WebSocket.
    Pass job_id as query param: /youtube/progress?job_id=xyz
    Body: { "url": "...", "job_id": "..." }
    """
    url    = request.get("url", "")
    job_id = request.get("job_id") or job_id or "noop"
    start_time = time.time()

    def do_transcribe():
        # Lazy imports — yt-dlp + FFmpeg + Whisper
        from server.core.transcription.youtube_downloader import download_youtube
        from server.core.transcription.audio_extractor import extract_audio
        from server.core.transcription.transcribe import transcribe_audio
        yt_data = download_youtube(str(url))
        wav     = extract_audio(yt_data["audio_file"], enable_cleaning=enable_audio_cleaning)
        return transcribe_audio(wav), yt_data["title"]

    await progress.send(job_id, {
        "step": "download", "message": "Downloading YouTube audio...", "pct": 8
    })

    try:
        transcript_result = await asyncio.to_thread(do_transcribe)
        transcript, title = transcript_result
    except Exception as e:
        await progress.send(job_id, {"step": "error", "message": str(e), "pct": 0})
        raise HTTPException(status_code=500, detail=str(e))

    await progress.send(job_id, {
        "step": "transcribe", "message": "Transcription complete", "pct": 40
    })

    meeting_id = await asyncio.to_thread(
        save_transcript_and_get_id, title, transcript, None, current_user.id
    )

    await progress.send(job_id, {
        "step": "intel", "message": "Generating intelligence...", "pct": 60
    })
    # Lazy import — LLM call
    from server.core.intelligence.workflow import analyze_transcript
    intelligence = await asyncio.to_thread(analyze_transcript, transcript)
    await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

    await progress.send(job_id, {
        "step": "index", "message": "Indexing for RAG...", "pct": 88
    })
    try:
        # Lazy import — loads ChromaDB
        from server.core.rag.indexer import index_meeting
        await asyncio.to_thread(index_meeting, meeting_id, title, transcript, "")
    except Exception as e:
        logger.warning(f"Index failed: {e}")

    await progress.send(job_id, {
        "step": "done", "message": "Processing complete!", "pct": 100
    })

    processing_time = round(time.time() - start_time, 2)

    return YouTubeResponse(
        meeting_id      = meeting_id,
        title           = title,
        transcript_file = "",
        transcript      = transcript,
        intelligence    = get_intelligence_for_response(meeting_id),
        processing_time = processing_time,
    )




@app.post("/upload/async", tags=["Processing"])
async def upload_file_async(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    enable_audio_cleaning: bool = Query(default=True),
):
    """
    Async upload endpoint — returns a job_id immediately, processes in background.
 
    HOW THIS IS DIFFERENT FROM /upload/progress:
        /upload/progress  → FastAPI processes the file itself (blocks until done)
                            Browser must stay connected the whole time
        /upload/async     → FastAPI saves the file and hands off to Celery (<1 second)
                            Browser gets job_id immediately and can poll for progress
                            Works even if the user closes the tab
 
    WORKFLOW:
        1. Client calls POST /upload/async with the file
        2. FastAPI saves file to disk
        3. FastAPI calls process_meeting_task.delay(...) → drops job into Redis
        4. FastAPI returns {"job_id": "abc123", "status": "queued"} immediately
        5. Celery worker (separate process) picks up the job and starts processing
        6. Client polls GET /jobs/{job_id}/status to see progress
        7. Client can also connect to ws://localhost:8000/ws/progress/{job_id}
           to get live WebSocket updates (reuses your existing WebSocket system)
 
    Returns:
        job_id   : unique identifier for this job
        status   : "queued"
        filename : the uploaded file's name
        message  : human-readable confirmation
    """
    ext = file.filename.split(".")[-1].lower()
 
    VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}
    AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "aac"}
 
    if ext in VIDEO_EXTENSIONS:
        file_path = VIDEO_DIR / file.filename
    elif ext in AUDIO_EXTENSIONS:
        file_path = AUDIO_DIR / file.filename
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: mp4, mov, avi, mp3, wav, m4a"
        )
 
    # Save file to disk first — Celery worker will read it from here
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
 
    # Generate a unique job ID for this upload
    # uuid4() generates a random UUID: e.g. "550e8400-e29b-41d4-a716-446655440000"
    job_id = str(uuid.uuid4())
 
    # Write initial "queued" status to Redis so /jobs/{job_id}/status works immediately
    from server.core.tasks import set_job_status
    set_job_status(job_id, {
        "step":       "queued",
        "message":    "Job queued — waiting for worker",
        "pct":        0,
        "meeting_id": None,
        "error":      None,
    })
 
    # Drop the job into the Celery queue (returns immediately — does NOT block)
    # .delay() is shorthand for .apply_async() with default options
    from server.core.tasks import process_meeting_task
    process_meeting_task.delay(
        job_id=job_id,
        file_path=str(file_path.resolve()),   # absolute path so worker can find it
        filename=file.filename,
        user_id=current_user.id,
        enable_audio_cleaning=enable_audio_cleaning,
    )
 
    logger.info(f"Queued async job {job_id} for file {file.filename} (user {current_user.id})")
 
    return {
        "job_id":   job_id,
        "status":   "queued",
        "filename": file.filename,
        "message":  "File uploaded. Processing started in background.",
    }
 
 
@app.get("/jobs/{job_id}/status", tags=["Processing"])
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Poll the status of a background processing job.
 
    Call this repeatedly after POST /upload/async to check progress.
    Typical polling interval: every 2-3 seconds.
 
    Returns:
        job_id     : the job ID you passed in
        step       : current step name
                     "queued"      → waiting in queue
                     "extract"     → extracting audio
                     "transcribe"  → running Whisper
                     "intel"       → running LLM intelligence agents
                     "index"       → indexing into ChromaDB
                     "done"        → finished successfully
                     "error"       → failed (see error field)
        message    : human-readable description of current step
        pct        : progress percentage 0-100
        meeting_id : the new meeting's ID (only set when step == "done")
        error      : error message (only set when step == "error")
 
    Example polling loop in JavaScript:
        const poll = async (jobId) => {
            const res = await fetch(`/jobs/${jobId}/status`, { headers: { Authorization: `Bearer ${token}` } });
            const data = await res.json();
            console.log(`${data.pct}% — ${data.message}`);
            if (data.step !== "done" && data.step !== "error") {
                setTimeout(() => poll(jobId), 2000);  // poll every 2 seconds
            }
        };
    """
    from server.core.tasks import get_job_status as _get_status
 
    status = _get_status(job_id)
 
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired (jobs are kept for 1 hour)."
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
# CONTACT ENDPOINT
# =====================================================

@app.post("/contact", tags=["Support"])
async def contact(request: ContactRequest):
    """
    Saves contact form submission.
    In production: send via SMTP or Resend.
    For now: logs and saves to a local file.
    """
    import json
    from pathlib import Path

    try:
        entry = {
            "name":    request.name,
            "email":   request.email,
            "subject": request.subject,
            "message": request.message,
            "sent_at": datetime.datetime.now().isoformat(),
        }

        path = Path("contact_submissions.json")
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
# PHASE 6 — ADVANCED INTELLIGENCE ENDPOINTS
# =====================================================

@app.get("/meetings/{meeting_id}/health", tags=["Intelligence"])
def get_health_score(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Get or generate meeting health score.
    Generates on first call, returns cached on subsequent calls.
    """
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    cached = get_meeting_health(meeting_id)
    if cached:
        return cached

    intel = get_meeting_intelligence(meeting_id)
    if not intel:
        raise HTTPException(
            status_code=404,
            detail="No intelligence data found. Process meeting first."
        )

    health = analyze_meeting_health(
        transcript=meeting["transcript"],
        intelligence=intel,
    )
    save_meeting_health(meeting_id, health)
    return health


@app.get("/meetings/{meeting_id}/quotes", tags=["Intelligence"])
def get_quotes(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Get or generate key quotes for a meeting.
    """
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
    meeting_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Get or generate an AI meeting title.
    """
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    cached = get_meeting_title(meeting_id)
    if cached:
        return {"title": cached}

    intel = get_meeting_intelligence(meeting_id)
    summary = intel.get("summary", "") if intel else ""

    title = generate_meeting_title(
        transcript=meeting["transcript"],
        summary=summary,
    )
    save_meeting_title(meeting_id, title)
    return {"title": title}


@app.put("/tasks/{item_id}/status", tags=["Intelligence"])
def update_task_status(
    item_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Update action item status.
    Body: { "status": "open" | "in_progress" | "done" | "overdue" }
    """
    status = body.get("status", "").lower()
    valid  = {"open", "in_progress", "done", "overdue"}

    if status not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid}"
        )

    updated = update_action_item_status(item_id, status, current_user.id)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Action item not found or access denied"
        )

    return {"message": "Status updated", "status": status}


# =====================================================
# PHASE 7 — PDF EXPORT + FOLLOW-UP EMAIL
# =====================================================

@app.get("/meetings/{meeting_id}/export/pdf", tags=["Export"])
def export_pdf(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Generate and stream a formatted PDF report for a meeting.
    """
    from reportlab.lib.pagesizes  import A4
    from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units      import cm
    from reportlab.lib            import colors
    from reportlab.platypus       import (
        SimpleDocTemplate, Paragraph, Spacer,
        HRFlowable, Table, TableStyle,
    )
    from reportlab.lib.enums      import TA_LEFT, TA_CENTER

    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    intel    = get_meeting_intelligence(meeting_id)
    health   = get_meeting_health(meeting_id)
    quotes   = get_meeting_quotes(meeting_id)
    ai_title = get_meeting_title(meeting_id)

    title = ai_title or meeting.get("filename", "Meeting Report")

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    W = A4[0] - 4*cm

    def style(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    S_title   = style('T',  fontSize=22, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#0e1117'), spaceAfter=4,
                      alignment=TA_LEFT)
    S_meta    = style('M',  fontSize=10, textColor=colors.HexColor('#6b748f'),
                      spaceAfter=4)
    S_section = style('S',  fontSize=13, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#4f46e5'),
                      spaceBefore=24, spaceAfter=10)
    S_body    = style('B',  fontSize=10, leading=16,
                      textColor=colors.HexColor('#2e3650'), spaceAfter=4)
    S_bullet  = style('BL', fontSize=10, leading=15,
                      textColor=colors.HexColor('#2e3650'),
                      leftIndent=14, spaceAfter=3)
    S_quote   = style('Q',  fontSize=10, leading=15,
                      textColor=colors.HexColor('#4f46e5'),
                      leftIndent=14, fontName='Helvetica-Oblique', spaceAfter=4)
    S_label   = style('L',  fontSize=9,  fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#9aa3bc'), spaceAfter=2)

    gray = colors.HexColor('#e2e8f0')

    def hr():
        return HRFlowable(
            width='100%', thickness=1,
            color=gray, spaceAfter=10, spaceBefore=10,
        )

    def section(text):
        return Paragraph(text, S_section)

    def body(text):
        return Paragraph(text, S_body)

    def bullet(text):
        return Paragraph(f"- {text}", S_bullet)

    def label(text):
        return Paragraph(text, S_label)

    story = []

    story.append(Table(
        [[Paragraph(title, S_title)]],
        colWidths=[W],
        style=TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#f5f7ff')),
            ('TOPPADDING',    (0,0), (-1,-1), 14),
            ('BOTTOMPADDING', (0,0), (-1,-1), 14),
            ('LEFTPADDING',   (0,0), (-1,-1), 16),
            ('RIGHTPADDING',  (0,0), (-1,-1), 16),
            ('BOX',           (0,0), (-1,-1), 1, colors.HexColor('#dde3f0')),
        ]),
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"{meeting.get('created_at', '')[:10]}   |   "
        f"{meeting.get('filename', '')}   |   "
        f"AI Generated Report",
        S_meta,
    ))

    if health:
        score = health.get("overall_score", 0)
        score_color = (
            '#10b981' if score >= 75 else
            '#f59e0b' if score >= 50 else
            '#ef4444'
        )
        story.append(Paragraph(
            f"Meeting Health Score: "
            f"<font color='{score_color}'><b>{score}/100</b></font>",
            S_meta,
        ))

    story.append(Spacer(1, 6))
    story.append(hr())

    if intel and intel.get("summary"):
        story.append(section("Executive Summary"))
        story.append(body(intel["summary"]))
        story.append(hr())

    if intel and intel.get("topics"):
        story.append(section("Topics Discussed"))
        topics_str = "   |   ".join([t["title"] for t in intel["topics"]])
        story.append(body(topics_str))
        story.append(hr())

    if intel and intel.get("decisions"):
        story.append(section("Decisions Made"))
        for d in intel["decisions"]:
            story.append(bullet(d["decision"]))
            if d.get("rationale"):
                story.append(Paragraph(f"  {d['rationale']}", S_label))
        story.append(hr())

    if intel and intel.get("action_items"):
        story.append(section("Action Items"))

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
            ('BACKGROUND',     (0,0), (-1,0),  colors.HexColor('#f5f7ff')),
            ('TEXTCOLOR',      (0,0), (-1,0),  colors.HexColor('#4f46e5')),
            ('FONTNAME',       (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',       (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [colors.white, colors.HexColor('#f9faff')]),
            ('GRID',           (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING',     (0,0), (-1,-1), 7),
            ('BOTTOMPADDING',  (0,0), (-1,-1), 7),
            ('LEFTPADDING',    (0,0), (-1,-1), 8),
            ('RIGHTPADDING',   (0,0), (-1,-1), 8),
            ('ALIGN',          (0,0), (-1,-1), 'LEFT'),
            ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(hr())

    if quotes:
        story.append(section("Key Quotes"))
        for q in quotes:
            story.append(Paragraph(f'"{q["quote"]}"', S_quote))
            if q.get("speaker"):
                story.append(Paragraph(
                    f"- {q['speaker']}"
                    + (f"  |  {q['context']}" if q.get("context") else ""),
                    S_label,
                ))
            story.append(Spacer(1, 4))
        story.append(hr())

    if health:
        story.append(section("Meeting Health Analysis"))
        health_data = [
            ["Metric",          "Score"],
            ["Participation",   f"{health['participation']}/100"],
            ["Decision Quality",f"{health['decision_quality']}/100"],
            ["Action Clarity",  f"{health['action_clarity']}/100"],
            ["Follow-up Risk",  f"{health['followup_risk']}/100"],
            ["Overall Score",   f"{health['overall_score']}/100"],
        ]
        ht = Table(health_data, colWidths=[W*0.6, W*0.4])
        ht.setStyle(TableStyle([
            ('BACKGROUND',     (0,0),  (-1,0),  colors.HexColor('#f5f7ff')),
            ('TEXTCOLOR',      (0,0),  (-1,0),  colors.HexColor('#4f46e5')),
            ('FONTNAME',       (0,0),  (-1,0),  'Helvetica-Bold'),
            ('FONTNAME',       (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',       (0,0),  (-1,-1), 9),
            ('GRID',           (0,0),  (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0,1),  (-1,-2),
             [colors.white, colors.HexColor('#f9faff')]),
            ('TOPPADDING',     (0,0),  (-1,-1), 7),
            ('BOTTOMPADDING',  (0,0),  (-1,-1), 7),
            ('LEFTPADDING',    (0,0),  (-1,-1), 8),
            ('RIGHTPADDING',   (0,0),  (-1,-1), 8),
        ]))
        story.append(ht)

        if health.get("highlights"):
            story.append(Spacer(1, 8))
            story.append(label("Highlights"))
            story.append(body(health["highlights"]))
        if health.get("concerns"):
            story.append(Spacer(1, 4))
            story.append(label("To Improve"))
            story.append(body(health["concerns"]))

        story.append(hr())

    transcript = meeting.get("transcript", "")
    if transcript:
        story.append(section("Transcript"))
        for para in transcript.split('\n'):
            para = para.strip()
            if para:
                story.append(body(para))

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
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_report.pdf"'
        },
    )

@app.get("/meetings/{meeting_id}/followup-email", tags=["Export"])
def get_followup_email(
    meeting_id:   int,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a follow-up email for a meeting.
    """
    meeting = get_meeting_by_id(meeting_id, user_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    intel = get_meeting_intelligence(meeting_id)
    if not intel:
        raise HTTPException(
            status_code=404,
            detail="No intelligence data found."
        )

    ai_title = get_meeting_title(meeting_id)
    title    = ai_title or meeting.get("filename", "Our Meeting")

    email = generate_followup_email(
        meeting_title=title,
        intelligence=intel,
    )

    return {"email": email, "title": title}


# =====================================================
# ERROR HANDLERS
# =====================================================

import traceback
from fastapi import HTTPException as FastAPIHTTPException

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if isinstance(exc, FastAPIHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )

    import traceback
    traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "status_code": 500}
    )

# =====================================================
# STARTUP
# =====================================================

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Summly Backend on http://localhost:8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )