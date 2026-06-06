# 📚 SUMMLY - AI-Powered Meeting Intelligence Platform

![Project Status](https://img.shields.io/badge/status-Completed-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-lightgrey)
![React](https://img.shields.io/badge/React-Frontend-blue)
![Whisper](https://img.shields.io/badge/Whisper-AI-orange)

---

## 📖 Table of Contents
- [📚 SUMMLY - AI-Powered Meeting Intelligence Platform](#-summly---ai-powered-meeting-intelligence-platform)
  - [📖 Table of Contents](#-table-of-contents)
  - [🌟 Project Overview](#-project-overview)
  - [🛠 Tech Stack](#-tech-stack)
  - [📂 Folder Structure](#-folder-structure)

---

## 🌟 Project Overview

**Summly** is an **AI-powered meeting intelligence platform** that:

- Accepts audio/video recordings or YouTube videos
- Extracts and cleans the audio
- Transcribes it into text using **Whisper AI**
- Analyzes transcripts for insights
- Stores results in a database
- Presents findings via a **beautiful, user-friendly UI**

> Think of it as a smart assistant that listens to your meetings, summarizes them, and highlights key decisions and action items.

---

## 🛠 Tech Stack

| Component | Purpose | Why It’s Used |
|-----------|--------|---------------|
| **FastAPI** | Backend API | Fast, modern, async-ready |
| **Streamlit / React** | Frontend Dashboard | Interactive UI, real-time updates |
| **Whisper AI** | Audio → Text Transcription | Accurate, OpenAI-powered |
| **FFmpeg** | Audio/Video Processing | Industry-standard, format-agnostic |
| **SQLite / PostgreSQL** | Database | Lightweight for dev, scalable for production |
| **ChromaDB** | Embeddings & Semantic Search | Supports RAG-based queries |
| **LangGraph + Groq LLM** | AI Workflow & Analysis | Generates summaries, action items, topics |

---

## 📂 Folder Structure

```text
AI-meeting-Assistant/
├── main.py                # Backend entry point
├── core/
│   ├── transcription/     # Audio extraction & cleaning
│   ├── intelligence/      # Transcript analysis
│   ├── rag/               # Semantic search / chat
│   ├── auth/              # Authentication
│   └── database.py        # DB operations
├── frontend/              # Streamlit UI
├── client/                # React frontend alternative
├── uploads/               # Temp storage: audio, video, transcripts
├── chroma_db/             # Vector DB for embeddings
├── meetings.db            # SQLite database
└── requirements.txt       # Python dependencies