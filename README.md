# 🚀 Summly – AI-Powered Meeting Intelligence Platform


<p align="center">
  <b>Transform Meeting Recordings into Actionable Insights using AI</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/FastAPI-Backend-green?style=for-the-badge&logo=fastapi">
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react">
  <img src="https://img.shields.io/badge/Whisper-AI-orange?style=for-the-badge">
  <img src="https://img.shields.io/badge/ChromaDB-VectorDB-purple?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge">
</p>

---

# 📖 Overview

Summly is an AI-powered Meeting Intelligence Platform designed to automate the process of understanding and managing meetings.

Instead of manually reviewing lengthy recordings, users can upload audio files, video recordings, or YouTube links and receive:

✅ Accurate Transcriptions
✅ Executive Summaries
✅ Action Items
✅ Key Decisions
✅ Discussion Topics
✅ Semantic Search & AI Chat

Summly acts as a virtual meeting assistant that listens, understands, organizes, and retrieves important information from conversations.

---

# ✨ Key Features

## 🎙️ AI Transcription

Convert meeting recordings into text using Whisper AI.

* Audio transcription
* Video transcription
* Multi-format support
* Multi-language support
* High accuracy speech recognition

---

## 🔊 Audio Processing

Automatic preprocessing for better transcription quality.

### Features

* Audio extraction from videos
* Noise reduction
* Silence trimming
* Volume normalization
* Audio enhancement

---

## 🧠 Meeting Intelligence

Generate valuable insights automatically.

### Outputs

* Executive Summary
* Action Items
* Key Decisions
* Discussion Topics
* Meeting Health Analysis

---

## 🔍 AI-Powered Search (RAG)

Ask questions directly about your meetings.

### Example

**Question**

```text
What decisions were made regarding the project budget?
```

**Answer**

```text
The team approved a 20% increase in the development budget
for the next quarter.
```

---

## 👤 User Authentication

Secure user management with:

* Registration
* Login
* JWT Authentication
* Protected Routes
* Multi-user support

---

## 📁 Meeting History

Store and revisit previous meetings.

Features:

* Meeting archive
* Transcript history
* Searchable records
* Download transcripts
* Meeting metadata

---

# 🏗️ System Architecture

```text
┌──────────────────────────────┐
│          USER                │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      React / Streamlit UI    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│         FastAPI API          │
└──────────────┬───────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
 Whisper    SQLite    ChromaDB
    │          │          │
    ▼          ▼          ▼
Transcript  Storage   Vector Search
    │
    ▼
LangGraph + Groq
    │
    ▼
Insights & Summaries
```

---

# 🔄 End-to-End Workflow

```text
Upload File
      │
      ▼
File Validation
      │
      ▼
Audio Extraction
      │
      ▼
Audio Cleaning
      │
      ▼
Whisper Transcription
      │
      ▼
AI Analysis
      │
      ▼
Database Storage
      │
      ▼
Vector Indexing
      │
      ▼
Dashboard Results
```

---

# ⚙️ Tech Stack

## Backend

| Technology | Purpose          |
| ---------- | ---------------- |
| FastAPI    | REST API         |
| Python     | Core Development |
| JWT        | Authentication   |
| SQLite     | Database         |
| SQLAlchemy | ORM              |

---

## AI & Machine Learning

| Technology            | Purpose                 |
| --------------------- | ----------------------- |
| Whisper               | Speech-to-Text          |
| Faster-Whisper        | Optimized Transcription |
| LangGraph             | AI Workflow             |
| Groq LLM              | Intelligence Generation |
| Sentence Transformers | Embeddings              |

---

## Search & Retrieval

| Technology | Purpose                        |
| ---------- | ------------------------------ |
| ChromaDB   | Vector Database                |
| RAG        | Retrieval-Augmented Generation |

---

## Media Processing

| Technology | Purpose                |
| ---------- | ---------------------- |
| FFmpeg     | Audio/Video Processing |
| Librosa    | Audio Analysis         |

---

## Frontend

| Technology   | Purpose               |
| ------------ | --------------------- |
| React        | Frontend Application  |
| Streamlit    | Interactive Dashboard |
| Tailwind CSS | Styling               |

---

# 📂 Project Structure

```text
summly/
│
├── backend/
│   ├── auth/
│   ├── intelligence/
│   ├── rag/
│   ├── transcription/
│   ├── database.py
│   └── main.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── uploads/
│   ├── audio/
│   ├── video/
│   └── transcripts/
│
├── chroma_db/
│
├── meetings.db
│
├── requirements.txt
│
└── README.md
```

---

# 🎯 Core Capabilities

### Audio Processing

* Audio extraction
* Noise removal
* Audio normalization
* Silence trimming

### AI Transcription

* Speech recognition
* Multi-language support
* Speaker-ready transcripts

### Intelligence Layer

* Meeting summaries
* Action extraction
* Decision detection
* Topic clustering

### Search Layer

* Semantic search
* Context retrieval
* Question answering

### Security Layer

* JWT Authentication
* User isolation
* Protected APIs

---

# 📈 Performance Optimizations

### Faster Whisper

* 4x faster transcription
* Lower memory usage
* Production-ready performance

### Async Processing

```python
transcript = await asyncio.to_thread(
    transcribe_audio,
    audio_path
)
```

Benefits:

* Non-blocking operations
* Better responsiveness
* Improved scalability

---

# 🚀 Future Roadmap

## Phase 1 ✅

* Audio Transcription
* Database Storage
* User Authentication
* Audio Cleaning

## Phase 2 🔄

* AI Summaries
* Action Item Detection
* RAG Search
* Meeting Health Scoring

## Phase 3 🚀

### Speaker Identification

Determine:

* Who spoke
* Speaking duration
* Speaker contributions

### Collaboration

* Team sharing
* Real-time collaboration
* Permissions

### Integrations

* Slack
* Google Calendar
* Outlook
* Jira

### Mobile App

* React Native
* Notifications
* Meeting access on-the-go

### Cloud Scaling

* Docker
* Kubernetes
* PostgreSQL
* AWS/GCP/Azure

---

# 💡 Challenges Solved

### Challenge 1

Meeting recordings are difficult to review manually.

### Solution

Automated AI transcription and summarization.

---

### Challenge 2

Important action items get lost.

### Solution

Automatic extraction of tasks and responsibilities.

---

### Challenge 3

Searching through hours of recordings is inefficient.

### Solution

RAG-powered semantic search using ChromaDB.

---

# 🏆 Achievements

✅ End-to-End AI Pipeline

✅ Speech-to-Text Automation

✅ AI-Powered Meeting Analysis

✅ Semantic Search & Retrieval

✅ Authentication & Security

✅ Modular Architecture

✅ Production-Oriented Design

✅ Scalable Foundation

---

# 📊 Example Use Cases

### Corporate Meetings

Extract:

* Decisions
* Tasks
* Action plans

### Team Standups

Track:

* Progress
* Blockers
* Next steps

### Interviews

Generate:

* Interview summaries
* Key highlights

### Educational Sessions

Create:

* Notes
* Study summaries
* Searchable transcripts

---

# 👨‍💻 Author

**Pankaj**

B.Tech – Artificial Intelligence & Data Science

Passionate about:

* Artificial Intelligence
* Machine Learning
* Full Stack Development
* Generative AI
* System Design

---

# ⭐ Support

If you found this project useful:

⭐ Star the repository

🍴 Fork the project

💬 Share feedback

🚀 Connect on LinkedIn

---

<p align="center">
  Built with ❤️ using FastAPI, Whisper, LangGraph, ChromaDB, and React
</p>
