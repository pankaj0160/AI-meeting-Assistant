from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
from pydantic import BaseModel, HttpUrl
import shutil
import time

from app.audio_utils import extract_audio
from app.transcriber import transcribe_audio
from app.youtube_downloader import download_youtube

from app.database import (
    init_db,
    save_transcript,
    get_all_transcripts
)

app = FastAPI(
    title="Summly API",
    version="1.0.0"
)

init_db()

# ==================================================
# Request Models
# ==================================================

class YouTubeRequest(BaseModel):
    url: HttpUrl


# ==================================================
# Response Models
# ==================================================

class TranscriptResponse(BaseModel):
    filename: str
    transcript_file: str
    transcript: str
    processing_time: float
    file_size_mb: float


class YouTubeResponse(BaseModel):
    title: str
    transcript_file: str
    transcript: str
    processing_time: float


# ==================================================
# Configuration
# ==================================================

VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a"}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


# ==================================================
# Folder Structure
# ==================================================

AUDIO_DIR = Path("uploads/audio")
VIDEO_DIR = Path("uploads/video")

OUTPUT_AUDIO_DIR = Path("output/audio")
TRANSCRIPT_DIR = Path("output/transcripts")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# Health Endpoints
# ==================================================

@app.get("/")
def root():
    return {
        "message": "Summly Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ==================================================
# Upload Endpoint
# ==================================================

@app.post(
    "/upload",
    response_model=TranscriptResponse
)
async def upload_file(
    file: UploadFile = File(...)
):

    ext = file.filename.split(".")[-1].lower()

    # Determine upload location
    if ext in VIDEO_EXTENSIONS:
        file_path = VIDEO_DIR / file.filename

    elif ext in AUDIO_EXTENSIONS:
        file_path = AUDIO_DIR / file.filename

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    # Validate file size
    file_size = file_path.stat().st_size

    if file_size > MAX_FILE_SIZE:

        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="File size exceeds 100 MB limit"
        )

    file_size_mb = round(
        file_size / (1024 * 1024),
        2
    )

    start_time = time.time()

    # Convert video → wav
    if ext in VIDEO_EXTENSIONS:
        wav_file = extract_audio(
            str(file_path)
        )
    else:
        wav_file = str(file_path)

    # Transcribe
    transcript = transcribe_audio(
        wav_file
    )


    save_transcript(
        filename=file.filename,
        transcript=transcript
    )

    processing_time = round(
        time.time() - start_time,
        2
    )

    # Save transcript
    transcript_file = (
        TRANSCRIPT_DIR /
        f"{Path(file.filename).stem}.txt"
    )

    with open(
        transcript_file,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(transcript)

    return {
        "filename": file.filename,
        "transcript_file": str(transcript_file),
        "transcript": transcript,
        "processing_time": processing_time,
        "file_size_mb": file_size_mb
    }


# ==================================================
# YouTube Endpoint
# ==================================================

@app.post(
    "/youtube",
    response_model=YouTubeResponse
)
async def process_youtube(
    request: YouTubeRequest
):

    try:

        start_time = time.time()

        # Download audio
        youtube_data = download_youtube(
            str(request.url)
        )

        mp3_file = youtube_data[
            "audio_file"
        ]

        # Convert mp3 → wav
        wav_file = extract_audio(
            mp3_file
        )

        # Transcribe
        transcript = transcribe_audio(
            wav_file
        )

        from app.database import save_transcript

        save_transcript(
            filename=youtube_data["title"],
            transcript=transcript
        )

        processing_time = round(
            time.time() - start_time,
            2
        )

        # Save transcript
        transcript_file = (
            TRANSCRIPT_DIR /
            f"{youtube_data['title']}.txt"
        )

        with open(
            transcript_file,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(transcript)

        return {
            "title": youtube_data["title"],
            "transcript_file": str(
                transcript_file
            ),
            "transcript": transcript,
            "processing_time": processing_time
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    

@app.get("/history")
def history():

    records = get_all_transcripts()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "created_at": row[3],
            "duration_seconds": row[4]
        }
        for row in records
    ]