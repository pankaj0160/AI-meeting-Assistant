<div align="center">

<br />

<img src="https://img.shields.io/badge/R-ResearchOS-0d9488?style=for-the-badge&logoColor=white&labelColor=0a0a0f" alt="ResearchOS" height="48" />

<br /><br />

# ResearchOS

### An operating system for AI research.

*Ask any topic · Upload a PDF · Track the news · Get live intelligence*

<br />

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-1C3C3C?style=flat-square&logo=chainlink&logoColor=white)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-LPU-F55036?style=flat-square&logoColor=white)](https://groq.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5+-FF6B35?style=flat-square&logoColor=white)](https://trychroma.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

<br />

```
┌─────────────────────────────────────────────────────────────┐
│   Search Agent → Reader Agent → Writer Agent → Critic Agent │
│        web          scrape         report         score      │
└─────────────────────────────────────────────────────────────┘
        Real-time SSE streaming · JWT auth · 21 API routes
```

<br />

[**Documentation**](#architecture) · [**Quick Start**](#quick-start) · [**API Reference**](#api-reference)

<br />

</div>

---

## What is ResearchOS?

ResearchOS is a **production-grade, full-stack AI research platform** that consolidates four intelligence workflows into a single authenticated workspace. Instead of juggling multiple tools, everything lives in one place — with a shared auth layer, shared design system, and a streaming-first backend.

| Module | What it does |
|--------|-------------|
| 🔬 **Topic Research** | 4-agent pipeline (Search → Read → Write → Review) with live SSE streaming and quality scoring |
| 📄 **PDF Chat** | Upload any PDF → ChromaDB RAG → page-cited streaming answers |
| 📰 **News Intelligence** | Tavily news search → 5-section AI briefing with article cards and category filters |
| 🌐 **AI Dashboard** | Live weather, travel safety scores, headlines, and a conversational multi-tool agent |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT  (React + Vite)                     │
│                                                                    │
│  Landing → Auth Pages → AppShell (Sidebar + Outlet)              │
│                          ├── ResearchPage  (useSSEStream)         │
│                          ├── PDFChatPage   (usePDFChat)           │
│                          ├── NewsPage      (useNews)              │
│                          └── AIDashboardPage (useDashboard)       │
└────────────────────────────┬─────────────────────────────────────┘
                             │  HTTP + SSE (Bearer JWT)
┌────────────────────────────▼─────────────────────────────────────┐
│                    SERVER  (FastAPI + Python)                      │
│                                                                    │
│  main.py  ──►  21 route handlers (auth · research · rag ·        │
│                                   news · dashboard)               │
│                                                                    │
│  agents.py        pipeline.py       rag.py                        │
│  ├─ get_tool_llm  ├─ run_real_pipeline  ├─ ingest_pdf            │
│  ├─ _run_tool_loop├─ run_pipeline_async ├─ chat_with_pdf         │
│  └─ build_chains  └─ Queue bridge       └─ get_top_sources        │
│                                                                    │
│  news.py          dashboard_agent.py    auth.py  database.py      │
│  ├─ search_news   ├─ get_weather        ├─ JWT    ├─ SQLite       │
│  └─ summarize     ├─ get_travel_safety  └─ bcrypt └─ 3 tables    │
│                   └─ get_headlines                                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
           ┌─────────────────┼──────────────────┐
           ▼                 ▼                  ▼
      Groq API          Tavily API        Open-Meteo API
   (LLaMA 70B)       (web + news)       (weather, free)
           │
    ChromaDB (local)  SQLite (local)
    HuggingFace Embed  JWT Sessions
```

### Key Design Patterns

**1. SSE Streaming — Sync → Async Bridge**
The research pipeline runs synchronous LangChain generators in a `ThreadPoolExecutor`. Events are pushed into an `asyncio.Queue` via `call_soon_threadsafe`, then drained by the async FastAPI route in real time — zero event-loop blocking.

**2. Manual Tool-Call Loop**
`_run_tool_loop()` uses `llm.bind_tools()` directly (not `create_react_agent`) to avoid LangChain's hidden ReAct system prompt — which caused Groq to emit XML tool calls instead of JSON, resulting in HTTP 400 errors.

**3. RAG Session Isolation**
Each PDF upload gets a UUID `session_id` → its own ChromaDB collection. An in-memory dict maps `session_id → owner user_id`, enforced on every request. No cross-user data leakage is structurally possible.

**4. API Key Rotation**
Both `GROQ_API_KEYS` and `TAVILY_API_KEYS` accept comma-separated lists. The system pings each key in order and uses the first that responds — zero user-visible errors from rate limiting or expired keys.

---

## Project Structure

```
researchos/
│
├── researchos-backend/
│   ├── main.py              # FastAPI app — 21 route handlers, SSE wrappers
│   ├── agents.py            # LLM factory, _run_tool_loop, chain builders
│   ├── pipeline.py          # 4-stage research orchestrator + async bridge
│   ├── rag.py               # PDF ingest, chunk, embed, retrieve, stream
│   ├── news.py              # Tavily news search + Groq summarisation
│   ├── dashboard_agent.py   # Weather, travel safety, headlines tools + agent
│   ├── auth.py              # JWT (python-jose) + bcrypt (passlib) + dependency
│   ├── database.py          # SQLite — runs, users, reset_tokens tables
│   ├── tools.py             # web_search, scrape_url LangChain @tool callables
│   ├── requirements.txt
│   └── .env.example
│
└── researchos-frontend/
    ├── src/
    │   ├── main.jsx                    # Router, ProtectedRoute, GuestRoute
    │   ├── index.css                   # 2800-line design system (CSS vars, dark/light)
    │   │
    │   ├── context/
    │   │   ├── AuthContext.jsx         # JWT persistence, rehydration, login/logout
    │   │   └── ThemeProvider.jsx       # Dark/light, localStorage, .dark class
    │   │
    │   ├── pages/
    │   │   ├── Landing.jsx             # Marketing page — pipeline demo, FAQ, support
    │   │   ├── LoginPage.jsx
    │   │   ├── RegisterPage.jsx        # Password strength meter
    │   │   ├── ForgotPasswordPage.jsx
    │   │   ├── ResearchPage.jsx        # Topic research workspace
    │   │   ├── PDFChatPage.jsx         # Split PDF + chat layout
    │   │   ├── NewsPage.jsx            # Two-column briefing + articles
    │   │   └── AIDashboardPage.jsx     # 3-card grid + chat
    │   │
    │   ├── components/
    │   │   ├── Layout/AppShell.jsx     # Collapsible sidebar (232px ↔ 60px)
    │   │   ├── Research/               # AgentCard, PipelineFlow, ReportViewer…
    │   │   ├── RAG/                    # PDFUploadZone, SessionSidebar, ChatMessage…
    │   │   ├── News/                   # NewsSearchBar, ArticleCard, NewsSummary…
    │   │   └── Dashboard/              # WeatherCard, TravelSafetyCard, HeadlinesFeed…
    │   │
    │   ├── hooks/
    │   │   ├── useSSEStream.js         # Research pipeline state machine
    │   │   ├── usePDFChat.js           # Upload, session, streaming chat
    │   │   ├── useNews.js              # Topic, category, articles, summary
    │   │   └── useDashboard.js         # Weather + safety + headlines + chat
    │   │
    │   └── services/
    │       ├── authApi.js
    │       ├── ragApi.js               # XHR upload with progress callbacks
    │       ├── newsApi.js
    │       └── dashboardApi.js
    │
    ├── package.json
    └── vite.config.js                  # Proxy /api → localhost:8000
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier available)
- A [Tavily API key](https://tavily.com) (free tier available)

### 1 — Clone & configure

```bash
git clone https://github.com/pankaj0160/AI-meeting-Assistant.git
cd AI-meeting-Assistant
```

### 2 — Backend setup

```bash
cd researchos-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Open `.env` and fill in:

```env
GROQ_API_KEYS=gsk_your_key_here           # comma-separated for rotation
TAVILY_API_KEYS=tvly_your_key_here        # comma-separated for rotation
JWT_SECRET_KEY=any-random-32-char-string  # openssl rand -hex 32
FRONTEND_ORIGIN=http://localhost:5173
```

```bash
# Start the backend
python main.py
# → http://localhost:8000
# → Swagger docs: http://localhost:8000/docs
```

### 3 — Frontend setup

```bash
cd researchos-frontend

npm install
npm run dev
# → http://localhost:5173
```

### 4 — First run

1. Open `http://localhost:5173`
2. Click **Get started** → create an account
3. Go to **Research** → enter any topic → click **Run Research**
4. Watch all 4 agents stream in real time

> **No API keys?** The system auto-switches to **simulation mode** — you'll see a realistic demo pipeline with streamed output and a sample report. Perfect for development.

---

## API Reference

All routes except `/api/health` and `/api/auth/*` require `Authorization: Bearer <token>`.

### Auth

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/auth/register` | Create account → returns JWT |
| `POST` | `/api/auth/login` | Authenticate → returns JWT |
| `POST` | `/api/auth/forgot-password` | Request password reset token |
| `POST` | `/api/auth/reset-password` | Consume token → update password |
| `GET`  | `/api/auth/me` | Current user profile |

### Research

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/research/stream?topic=` | **SSE** — 4-stage pipeline, streams events |
| `GET`  | `/api/history` | List past research runs |
| `GET`  | `/api/history/{id}` | Full run (report + feedback) |
| `DELETE` | `/api/history/{id}` | Delete a run |

### PDF Chat (RAG)

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/rag/upload` | Upload PDF → chunk → embed → returns `session_id` |
| `GET`  | `/api/rag/sessions` | List active PDF sessions |
| `POST` | `/api/rag/chat` | **SSE** — streams sources + answer |
| `GET`  | `/api/rag/history/{session_id}` | Full chat history |
| `DELETE` | `/api/rag/session/{session_id}` | Delete session + ChromaDB collection |

### News

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/news/search?topic=&category=&days=` | Articles only |
| `GET`  | `/api/news/summarize?topic=&category=&days=` | **SSE** — articles then AI briefing |

### Dashboard

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/dashboard/weather?city=` | Current + 7-day forecast (Open-Meteo) |
| `GET`  | `/api/dashboard/travel-safety?destination=` | AI safety briefing (1–5 score) |
| `GET`  | `/api/dashboard/headlines?topic=` | Top 5 headlines via Tavily |
| `POST` | `/api/dashboard/chat` | **SSE** — conversational multi-tool agent |

### SSE Event Format

All streaming endpoints emit newline-delimited JSON:

```
data: {"type": "chunk",    "chunk": "token text"}
data: {"type": "sources",  "sources": [{page, snippet, score}]}
data: {"type": "articles", "articles": [...], "count": 10}
data: {"type": "done"}
data: {"type": "error",    "msg": "..."}
```

---

## Feature Deep-Dive

<details>
<summary><strong>🔬 Research Pipeline — How it works internally</strong></summary>

<br />

The pipeline has 4 sequential stages, each emitting live SSE events:

```
User input
    │
    ▼
[Search Agent]  ──  llama-3.1-70b + bind_tools + web_search (Tavily)
    │               Returns: structured research summary
    ▼
[Reader Agent]  ──  llama-3.1-70b + bind_tools + scrape_url (BeautifulSoup)
    │               Returns: full-page extracted content from best URL
    ▼
[Writer Agent]  ──  llama-3.3-70b + LCEL chain + StrOutputParser
    │               Streams: Markdown report token-by-token
    ▼
[Critic Agent]  ──  llama-3.3-70b + LCEL chain
                    Streams: structured review + "Score: X/10"
                    Saved: to SQLite with regex-parsed score
```

**The async bridge problem:** LangChain generators are synchronous. FastAPI is async. Blocking the event loop would freeze all other requests during a 30-second research run.

**The solution:**
```python
queue = asyncio.Queue()
def _consume():
    for event in sync_generator:
        loop.call_soon_threadsafe(queue.put_nowait, event)

loop.run_in_executor(None, _consume)   # fire without await
while True:
    item = await queue.get()           # drain live
    yield item
```

</details>

<details>
<summary><strong>📄 PDF RAG — Chunking, embedding, retrieval</strong></summary>

<br />

```
PDF upload (up to 50 MB)
    │
    ├── PyPDFLoader          → extract text per page
    ├── RecursiveCharacterTextSplitter
    │     chunk_size=1000, overlap=200
    │     separators=["\n\n", "\n", ". ", " "]
    ├── HuggingFaceEmbeddings
    │     model: all-MiniLM-L6-v2 (384-dim, ~80MB, CPU)
    └── ChromaDB.from_documents()
          collection: session_{uuid}
          persist_directory: ./chroma_store/

User question
    │
    ├── embed question → 384-dim vector
    ├── similarity_search_with_relevance_scores(k=5)
    ├── build numbered context blocks with page numbers
    ├── inject last 6 turns of conversation history
    └── stream Groq answer token by token
          → emit {type:"sources"} first (UI renders citations)
          → emit {type:"chunk"} per token
```

The embedding model loads once and is cached as a singleton. First upload: ~5s warm-up. All subsequent uploads: instant.

</details>

<details>
<summary><strong>📰 News Intelligence — Articles-first SSE trick</strong></summary>

<br />

Fetching articles and summarising them are sequential on the server — you can't summarise what you haven't fetched. But from a UX perspective, article cards should populate immediately while the AI briefing streams.

**Solution:** emit two event types at different points in the generator:

```python
def stream():
    articles = search_news(topic, category, days)
    
    # ① Emit articles immediately — UI renders cards NOW
    yield f"data: {json.dumps({'type':'articles', 'articles':articles})}\n\n"
    
    # ② Start streaming summary — takes 5-15 seconds
    for chunk in summarize_news(articles, topic):
        yield f"data: {json.dumps({'type':'chunk', 'chunk':chunk})}\n\n"
    
    yield f"data: {json.dumps({'type':'done'})}\n\n"
```

The frontend listens for `type:"articles"` to render the right panel, and `type:"chunk"` to stream the left panel. Both panels fill simultaneously from the user's perspective.

</details>

<details>
<summary><strong>🌐 AI Dashboard — Multi-tool agent</strong></summary>

<br />

The dashboard conversational agent uses `_run_tool_loop()` with three `@tool`-decorated callables:

| Tool | API | Notes |
|------|-----|-------|
| `get_weather(city)` | Open-Meteo (free, no key) | Geocoding → forecast, WMO code → emoji |
| `get_travel_safety(destination)` | Groq LLM | Structured 5-point safety briefing |
| `get_headlines(topic)` | Tavily news | Returns top 5 as JSON for agent |

A single query like *"Is Tokyo safe and what's the weather like?"* triggers both `get_weather` and `get_travel_safety` in a single agent loop iteration — the model decides which tools to call and in what order.

</details>

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115+ | Async web framework, SSE, auto-docs |
| Uvicorn | 0.32+ | ASGI server with hot reload |
| LangChain | 0.3+ | LLM orchestration, tool binding, LCEL |
| LangChain-Groq | 0.2+ | Groq provider integration |
| Groq | 0.13+ | LLaMA 3.1/3.3 70B at ~500 tok/s |
| Tavily Python | 0.5+ | Web search + news search API |
| ChromaDB | 0.5+ | Embedded vector database |
| sentence-transformers | 3.0+ | all-MiniLM-L6-v2 local embeddings |
| PyPDF | 4.0+ | PDF text extraction |
| python-jose | 3.3+ | JWT creation + validation |
| passlib[bcrypt] | 1.7+ | Password hashing |
| SQLite3 | stdlib | ACID database, no server needed |
| BeautifulSoup4 | 4.12+ | Web page scraping |
| aiofiles | 23.2+ | Async file I/O for PDF upload |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18.3 | Component framework |
| Vite | 6.0 | Build tool, HMR, dev proxy |
| React Router | 6.28 | Client-side routing + route guards |
| react-markdown | 9.0 | Render AI output as formatted Markdown |
| remark-gfm | 4.0 | Tables, strikethrough, task lists |
| TailwindCSS | 3.4 | Utility classes for layout |
| Custom CSS | — | 2800-line design system (CSS vars, dark/light) |

---

## Environment Variables

```env
# ── Required ──────────────────────────────────────────────────────
GROQ_API_KEYS=gsk_key1,gsk_key2          # comma-separated, auto-rotated
TAVILY_API_KEYS=tvly_key1,tvly_key2      # comma-separated, auto-rotated
JWT_SECRET_KEY=change-this-to-random-32chars

# ── Optional ──────────────────────────────────────────────────────
FRONTEND_ORIGIN=http://localhost:5173    # CORS whitelist

# Email (for password reset delivery)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your_app_password
```

> **Tip:** Generate a secure JWT secret with `openssl rand -hex 32`

---

## Security

| Layer | Implementation |
|-------|---------------|
| **Passwords** | bcrypt via passlib — auto-salted, adaptive cost factor |
| **Sessions** | JWT (HS256) with 7-day expiry, validated on every request |
| **Authorization** | Every data route checks `resource.user_id == current_user.id` |
| **SQL Injection** | Parameterised queries only — no string concatenation |
| **Input validation** | Pydantic models on all request bodies, Query() constraints |
| **File uploads** | Type check + 50MB cap before any processing |
| **CORS** | Whitelist-only — `FRONTEND_ORIGIN` env var |
| **Email enumeration** | Forgot-password always returns the same message |
| **Reset tokens** | `secrets.token_urlsafe(32)`, 1-hour TTL, single-use |

---

## Roadmap

- [ ] **Redis** — Replace in-memory RAG session dict for multi-process durability
- [ ] **PostgreSQL** — Drop-in SQLite replacement for horizontal scaling
- [ ] **Email delivery** — SMTP integration for password reset links
- [ ] **Research History export** — PDF / Markdown download of saved reports
- [ ] **Celery task queue** — Background research jobs with status polling
- [ ] **PDF viewer** — Inline viewer with highlighted page citations
- [ ] **Research Workspaces** — Folders and collections for organising runs
- [ ] **Citation Manager** — Auto-format references as APA / MLA / BibTeX
- [ ] **Multi-language** — Translate final reports to Hindi, Spanish, French…
- [ ] **Refresh tokens** — Sliding session without re-login

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with clear messages: `git commit -m 'feat: add X'`
4. Push and open a Pull Request

For significant changes, open an issue first to discuss the approach.

---

## License

```
MIT License — Copyright (c) 2025 Pankaj Thakur

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

Built from scratch · 4 phases · 21 API routes · 54 files · 2800+ lines of design system

**FastAPI · LangChain · Groq · ChromaDB · React · SQLite**

<br />

*If this project helped you, consider giving it a ⭐*

</div>
