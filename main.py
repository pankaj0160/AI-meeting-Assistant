"""
Summly FastAPI Backend
Phase 2 Complete with Meeting Intelligence Engine
"""

from core.auth.dependencies import get_current_user, get_optional_user
from core.auth.models import User
from typing import Optional
from core.auth.router import router as auth_router
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

from core.transcription.audio_extractor import extract_audio
from core.transcription.transcribe import transcribe_audio
from core.transcription.youtube_downloader import download_youtube

from core.database import (
    init_db,
    get_all_transcripts,
    save_transcript_and_get_id,
    save_meeting_intelligence,
    get_meeting_intelligence,
    get_meeting_by_id,
)

from core.intelligence.workflow import analyze_transcript
from core.rag.indexer import index_meeting
from core.rag.chat import chat_with_meeting, chat_across_meetings

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
    
    # Pydantic v2
    if hasattr(intel_obj, 'model_dump'):
        return intel_obj.model_dump()
    # Pydantic v1
    elif hasattr(intel_obj, 'dict'):
        return intel_obj.dict()
    # Already a dict
    else:
        return intel_obj


def get_intelligence_for_response(meeting_id: int):
    """Fetch and serialize intelligence for API response."""
    try:
        intel = get_meeting_intelligence(meeting_id)
        if intel:
            # DB returns a dict, serialize properly
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
):
    """
    Upload and process an audio or video file.
    Returns transcript + AI intelligence.
    """
    
    start_time = time.time()
    
    ext = file.filename.split(".")[-1].lower()
    
    # Determine upload location
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
    
    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved: {file_path}")
    except Exception as e:
        logger.error(f"File save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")
    
    # Validate file size
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        logger.error(f"File exceeds size limit: {file_size / 1024 / 1024:.2f} MB")
        raise HTTPException(status_code=400, detail="File size exceeds 500 MB limit")
    
    file_size_mb = round(file_size / (1024 * 1024), 2)
    logger.info(f"Processing file: {file.filename} ({file_size_mb} MB)")
    
    try:
        # Convert video to wav if needed
        if ext in VIDEO_EXTENSIONS:
            logger.info("Extracting audio from video...")
            wav_file = extract_audio(str(file_path))
        else:
            wav_file = str(file_path)
        
        # Transcribe
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(wav_file)
        logger.info(f"Transcription complete: {len(transcript)} characters")
        
        # Save to database
        logger.info("Saving to database...")
        meeting_id = save_transcript_and_get_id(
            filename=file.filename,
            transcript=transcript,
            user_id=current_user.id,
        )
        
        # Generate intelligence
        logger.info(f"Generating intelligence for meeting {meeting_id}...")
        intelligence = analyze_transcript(transcript)
        
# Save intelligence
        save_meeting_intelligence(meeting_id, intelligence)
        logger.info(f"Intelligence saved: {len(intelligence.action_items)} items, "
                    f"{len(intelligence.decisions)} decisions, {len(intelligence.topics)} topics")

        # Index into ChromaDB for RAG
        try:
            index_meeting(
                meeting_id=meeting_id,
                filename=file.filename,
                transcript=transcript,
                created_at="",
            )
            logger.info(f"ChromaDB indexed for meeting {meeting_id}")
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        # Save transcript to file
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
):
    """
    Download, transcribe, and analyze YouTube video.
    Returns transcript + AI intelligence.
    """
    
    start_time = time.time()
    
    try:
        logger.info(f"Processing YouTube URL: {request.url}")
        
        # Download audio
        logger.info("Downloading audio from YouTube...")
        youtube_data = download_youtube(str(request.url))
        
        mp3_file = youtube_data["audio_file"]
        title = youtube_data["title"]
        logger.info(f"Downloaded: {title}")
        
        # Convert mp3 to wav
        logger.info("Converting audio format...")
        wav_file = extract_audio(mp3_file)
        
        # Transcribe
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(wav_file)
        logger.info(f"Transcription complete: {len(transcript)} characters")
        
        # Save to database
        logger.info("Saving to database...")
        meeting_id = save_transcript_and_get_id(
            filename=title,
            transcript=transcript,
            user_id=current_user.id,
        )
        
        # Generate intelligence
        logger.info(f"Generating intelligence for meeting {meeting_id}...")
        intelligence = analyze_transcript(transcript)
        
# Save intelligence
        save_meeting_intelligence(meeting_id, intelligence)
        logger.info(f"Intelligence saved: {len(intelligence.action_items)} items, "
                    f"{len(intelligence.decisions)} decisions, {len(intelligence.topics)} topics")

        # Index into ChromaDB for RAG
        try:
            index_meeting(
                meeting_id=meeting_id,
                filename=title,
                transcript=transcript,
                created_at="",
            )
            logger.info(f"ChromaDB indexed for meeting {meeting_id}")
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed (non-fatal): {e}")

        # Save transcript
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
        # Verify ownership
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
        # Verify meeting belongs to user
        meeting = get_meeting_by_id(request.meeting_id, user_id=current_user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

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
        result = chat_across_meetings(query=request.query)
        return {
            "answer":  result["answer"],
            "sources": result["sources"],
            "mode":    "cross",
        }
    except Exception as e:
        logger.error(f"Cross-meeting chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
    

# =====================================================
# STATS ENDPOINT
# =====================================================


@app.get("/stats", tags=["System"])
def get_stats(current_user: User = Depends(get_current_user)):
    """Aggregate stats across all meetings."""
    try:
        from core.database import get_all_transcripts, get_meeting_intelligence
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
        from core.database import get_all_meetings_for_indexing
        from core.rag.indexer import index_meeting
        meetings = get_all_meetings_for_indexing(user_id=current_user.id)
        indexed = 0
        for m in meetings:
            try:
                index_meeting(
                    meeting_id=m["id"],
                    filename=m["filename"],
                    transcript=m["transcript"],
                    created_at=m["created_at"],
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
        # Keep connection alive until client disconnects
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
        intelligence = await asyncio.to_thread(analyze_transcript, transcript)

        await step("intel",      "Saving intelligence...",        75)
        await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

        await step("index",      "Indexing for RAG search...",    88)
        try:
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
        if ext in VIDEO_EXTENSIONS:
            wav = extract_audio(str(file_path))
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
        yt_data = download_youtube(str(url))
        wav     = extract_audio(yt_data["audio_file"])
        return transcribe_audio(wav), yt_data["title"]

    # Run download+transcribe in thread
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
    intelligence = await asyncio.to_thread(analyze_transcript, transcript)
    await asyncio.to_thread(save_meeting_intelligence, meeting_id, intelligence)

    await progress.send(job_id, {
        "step": "index", "message": "Indexing for RAG...", "pct": 88
    })
    try:
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


# =====================================================
# ERROR HANDLERS
# =====================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500
        }
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