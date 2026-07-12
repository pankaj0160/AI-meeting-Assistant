# Summly — AI Meeting Intelligence Platform

Upload a meeting recording (audio, video, or a YouTube link) and Summly transcribes it, figures out who said what, and turns it into a structured summary, action items, decisions, and topics — then lets you chat with the meeting directly.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-19-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791)
![Celery](https://img.shields.io/badge/Celery-Redis-37814A)
![Status](https://img.shields.io/badge/status-active-brightgreen)

---

## What it does

- **Transcribes** audio, video, or YouTube links using `faster-whisper`
- **Identifies speakers** with `pyannote.audio` speaker diarization
- **Extracts intelligence** — summary, action items, decisions, topics — via 4 parallel LLM agents (Groq)
- **Chat with any meeting** using a hybrid RAG pipeline: BM25 + vector search, reranked with a cross-encoder
- **Tool-using conversational agent** — a ReAct-style agent that decides which data to fetch based on your question
- **Workspaces & collaboration** — RBAC (owner/member/viewer), shared analytics, cross-meeting chat
- **Meeting analytics** — talk-time equity, meeting cost calculator, commitment/deadline tracking with reliability scoring
- **Integrations** — Google Calendar (read-only), signed webhooks (HMAC-SHA256), PDF export
- **Production-grade** — background job processing (Celery + Redis), connection pooling, rate limiting, Sentry error monitoring, Langfuse LLM tracing, GDPR export/delete, audit logs

---

## Architecture

```
┌─────────────┐      REST/JWT       ┌──────────────┐
│   React 19   │ ──────────────────▶ │   FastAPI     │
│   (Vite)     │ ◀────────────────── │   (main.py)   │
└─────────────┘   WebSocket progress └──────┬───────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          ▼                  ▼                  ▼
                   ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
                   │ PostgreSQL   │   │    Redis      │   │  ChromaDB     │
                   │ (Supabase)   │   │ (broker +     │   │ (vector store)│
                   │ pooled conns │   │  job status)  │   │               │
                   └─────────────┘   └──────┬───────┘   └──────────────┘
                                             ▼
                                   ┌───────────────────┐
                                   │  Celery Worker      │
                                   │  FFmpeg → Whisper → │
                                   │  pyannote → 4 LLM    │
                                   │  agents → ChromaDB   │
                                   └───────────────────┘
```

**Upload flow:** file lands on disk → FastAPI queues a Celery job in Redis → job ID returned instantly → worker runs extraction, transcription, diarization, and 4 parallel intelligence agents in the background → frontend polls/streams progress via WebSocket.

**Chat flow:** question comes in → hybrid search (BM25 + vector, cached per meeting) retrieves candidates → cross-encoder reranks the shortlist → top chunks + question go to the LLM → answer streams back.

---

## Tech stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite, React Router, Recharts, Sentry (client-side) |
| **Backend** | FastAPI, Python 3.11 |
| **Database** | PostgreSQL (Supabase), connection-pooled via `psycopg2.pool` |
| **Job queue** | Celery + Redis (broker & result backend), Flower for monitoring |
| **Vector store** | ChromaDB |
| **Transcription** | faster-whisper (CTranslate2 backend) |
| **Diarization** | pyannote.audio (`speaker-diarization-3.1`) |
| **Search / RAG** | rank-bm25 + sentence-transformers (`all-MiniLM-L6-v2`) + cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) |
| **LLM** | Groq (`llama-3.3-70b-versatile`) |
| **Auth** | JWT (python-jose) + bcrypt (passlib) |
| **Observability** | Sentry (errors), Langfuse (LLM tracing), structlog |
| **Eval** | RAGAS (faithfulness, context recall, answer relevancy) |
| **CI/CD** | GitHub Actions |

**RAG quality (RAGAS eval, 10 test queries):** Faithfulness `0.925` · Context Recall `1.0` · Overall `0.896`

---

## Project structure

```
Summly/
├── client/                    # React frontend (Vite)
│   └── src/
│       ├── api/client.js      # centralized API layer (auth headers, error handling)
│       ├── context/           # AuthContext, WorkspaceContext
│       ├── pages/             # Dashboard, Upload, MeetingDetail, Chat, Analytics, ...
│       └── components/        # shared UI (Navbar, Sidebar, FloatingChat, ...)
│
├── server/
│   └── core/
│       ├── auth/               # JWT auth, password hashing, dependencies
│       ├── transcription/      # audio_extractor, transcribe, speaker_diarization, youtube_downloader
│       ├── intelligence/       # 4 parallel LLM agents (summary/actions/decisions/topics), workflow.py
│       ├── rag/                # embedder, indexer, hybrid_search, reranker, chat
│       ├── agent/               # ReAct tool-calling conversational agent
│       ├── database.py          # connection pool, schema, RLS
│       ├── tasks.py             # Celery background pipeline
│       ├── webhooks.py          # signed webhook delivery
│       ├── calendar_integration.py
│       ├── deadline_parser.py
│       └── storage.py
│   ├── eval/                    # RAGAS evaluation harness
│   ├── tests/                   # pytest suite
│   └── main.py                  # FastAPI app, 80+ REST endpoints
│
├── docker-compose.yml          # api, worker, flower, redis
├── Dockerfile
├── requirements.txt
└── requirements-test.txt       # lightweight deps for CI (no torch/whisper/chromadb)
```

---

## Getting started

### Prerequisites
- Python 3.11
- Node.js 18+
- Redis
- A PostgreSQL database (Supabase recommended)
- A [Groq API key](https://console.groq.com)
- A [HuggingFace token](https://huggingface.co/settings/tokens) with access accepted for `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0`

### 1. Clone and configure environment
```bash
git clone https://github.com/<your-username>/summly.git
cd summly
cp .env.example .env
```
Fill in `.env`:
```env
GROQ_API_KEY=
JWT_SECRET_KEY=          # generate with: python -c "import secrets; print(secrets.token_hex(32))"
HF_TOKEN=
DATABASE_URL=postgresql://...
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
LANGFUSE_SECRET_KEY=     # optional — app runs fine without it
LANGFUSE_PUBLIC_KEY=
SENTRY_DSN=              # optional
```
> The app fails fast (on purpose) at startup if `JWT_SECRET_KEY` or `DATABASE_URL` are missing — no insecure defaults.

### 2. Run with Docker (recommended)
```bash
docker-compose up --build
```
This starts the API (`:8000`), Celery worker, Redis, and Flower (`:5555` — task monitoring dashboard).

### 3. Run locally without Docker
```bash
# Backend
pip install -r requirements.txt --break-system-packages
uvicorn server.main:app --reload

# In a second terminal — Celery worker
celery -A server.core.tasks.celery_app worker --loglevel=info

# In a third terminal — Redis (if not already running)
redis-server

# Frontend
cd client/client
npm install
npm run dev
```
Frontend runs at `http://localhost:3000`, API at `http://localhost:8000` (interactive docs at `/docs`).

### 4. Run tests
```bash
pip install -r requirements-test.txt --break-system-packages
pytest server/tests/
```

---

## Key engineering decisions

- **Async background processing** — heavy work (extraction, transcription, diarization, LLM calls) runs on a Celery worker, not the request thread, so uploads return in under a second and one user's processing never blocks another's.
- **Hybrid search + reranking, not vector-only RAG** — BM25 (30%) + vector similarity (70%) combined, then the top candidates are re-scored by a cross-encoder before reaching the LLM. This is the single biggest quality lever in the chat pipeline.
- **BM25 index caching** — rebuilding a BM25 index on every chat message was the original bottleneck; a TTL'd, thread-safe cache per meeting cut chat latency from ~500ms to ~50ms on repeat queries.
- **Connection pooling** — `ThreadedConnectionPool` (min 2, max 10) instead of opening a fresh Postgres connection per request.
- **Row Level Security** — enabled on every table to close Supabase's auto-exposed PostgREST API surface, in addition to the app's own ownership checks.
- **Fail loud, not silent** — missing secrets, misconfigured rate limiting, or a disabled monitoring dependency all log clearly and degrade visibly rather than failing silently.

---

## License

This project is currently unlicensed / all rights reserved. *(Update this if you decide to open-source it — MIT is the common choice for portfolio projects.)*

---

## Author

**Pankaj** — [GitHub](#) · [LinkedIn](#) · [Portfolio](#)
Built as a production-grade portfolio project to explore RAG pipelines, multi-agent AI systems, and async backend architecture end to end.
