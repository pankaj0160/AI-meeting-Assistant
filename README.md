# 🎙️ Summly

AI Meeting Intelligence Platform that transforms audio, video, and YouTube recordings into searchable transcripts.

<img width="1821" height="844" alt="SC1" src="https://github.com/user-attachments/assets/803828b2-4bf4-4d81-b627-0e78cb313477" />

---

## 🚀 Overview

Summly is an AI-powered meeting transcription platform built using FastAPI, Streamlit, Whisper, and SQLite.

Users can:

* Upload meeting recordings
* Transcribe audio and video files
* Transcribe YouTube videos
* Store transcripts permanently
* View previous meetings
* Download transcripts for future reference

The project demonstrates full-stack AI application development with a production-style architecture.

---

## ✨ Features

### Transcription

* Upload MP3 files
* Upload WAV files
* Upload MP4 videos
* Upload M4A recordings
* YouTube transcription support

### Transcript Management

* Automatic transcript generation using OpenAI Whisper
* Save transcripts to SQLite database
* Transcript history
* Download transcripts as text files

### User Interface

* Modern Streamlit dashboard
* Meeting analytics
* Past meetings sidebar
* Responsive layout

---

## 🛠️ Tech Stack

### Backend

* FastAPI
* Python
* SQLite
* Whisper
* FFmpeg
* yt-dlp

### Frontend

* Streamlit
* Requests

### AI

* OpenAI Whisper

---

## 📂 Project Structure

```text
SUMMLY/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── transcriber.py
│   │   ├── audio_utils.py
│   │   └── youtube_downloader.py
│   │
│   ├── uploads/
│   ├── output/
│   ├── downloads/
│   └── data/
│       └── meetings.db
│
├── frontend/
│   ├── app.py
│   └── requirements.txt
│
├── README.md
└── requirements.txt
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/pankaj0160/summly.git

cd summly
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Mac/Linux

```bash
source .venv/bin/activate
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend

pip install -r requirements.txt
```

### 5. Install FFmpeg

Download and install FFmpeg:

https://ffmpeg.org/download.html

Verify installation:

```bash
ffmpeg -version
```

---

## ▶️ Running the Application

### Start Backend

Open Terminal 1

```bash
cd backend

uvicorn app.main:app --reload --port 8080
```

Backend runs at:

```text
http://localhost:8080
```

API Docs:

```text
http://localhost:8080/docs
```

---

### Start Frontend

Open Terminal 2

```bash
cd frontend

streamlit run app.py
```

Frontend runs at:

```text
http://localhost:8501
```

---

## 📸 Screenshots

### Dashboard


<img width="1821" height="844" alt="SC1" src="https://github.com/user-attachments/assets/4daaabcc-2ff6-47ac-9bc5-5161d522e191" />

<img width="1774" height="862" alt="SC2" src="https://github.com/user-attachments/assets/f28a687a-2779-4704-ad1b-e658cd77f35e" />


## 🧪 Example Workflow

1. Upload a meeting recording
2. Audio is processed using FFmpeg
3. Whisper generates transcript
4. Transcript is stored in SQLite
5. Transcript appears in dashboard
6. User downloads transcript
7. Meeting is visible in history

---

## 📊 Database

Transcripts are stored in SQLite:

```text
backend/data/meetings.db
```

Schema:

```sql
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    transcript TEXT,
    created_at TEXT,
    duration_seconds REAL
);
```

---

## 🔮 Roadmap

Upcoming features:

* AI Meeting Summaries
* Key Takeaways
* Action Items Extraction
* Speaker Identification
* Chat With Transcript (RAG)
* Search Across Meetings
* User Authentication
* Cloud Deployment

---

## 👨‍💻 Author

Pankaj Thakur

Built as part of an AI Engineering project focused on practical applications of LLMs, speech-to-text systems, and full-stack AI development.

## License
MIT
