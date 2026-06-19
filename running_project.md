# Backend
uvicorn server.main:app --reload

# Frontend (Streamlit)
cd client && npm run dev


# kill all terminals

taskkill /F /IM python.exe


## implementation plan currently
Phase 1A  → User model + DB migration
Phase 1B  → Auth backend (JWT, register, login)
Phase 1C  → Auth frontend (Login, Register pages)
Phase 1D  → Protected routes + meeting ownership
Phase 1E  → Dynamic greeting from auth user
Phase 1F  → Google OAuth (backend + frontend)

Phase 2A  → Landing page structure + hero
Phase 2B  → Demo meeting (preload + page)
Phase 2C  → Guest upload (1 file limit)
Phase 2D  → Guest chat (3 question limit)
Phase 2E  → Guest intelligence preview

Phase 3   → Creator page

Phase 4A  → FAQ page
Phase 4B  → Contact form + email

Phase 5   → Settings redesign

Phase 6A  → Meeting health score
Phase 6B  → AI generated titles
Phase 6C  → Key quotes extraction
Phase 6D  → Action item tracker

Phase 7A  → PDF export
Phase 7B  → Follow-up email generator

Phase 8   → Calendar integration

Phase 9A  → Faster-Whisper migration
Phase 9B  → Background job queue


Summly — Production Roadmap
🔴 Week 3 (Current) — Infrastructure
✅ Redis + Celery async pipeline
✅ Multi-meeting RAG chat
⬜ Action Item Tracker (Instructor structured extraction)
⬜ Speaker Diarization (pyannote.audio)
🟡 Week 4 — Scale & Reliability
⬜ S3/R2 file storage (get off local disk)
⬜ PostgreSQL migration (SQLite won't survive production)
⬜ Rate limiting + API throttling (slowapi)
⬜ Structured logging (structlog + correlation IDs)
🟢 Week 5 — Intelligence Layer
⬜ Cross-meeting contradiction detection
⬜ Meeting series intelligence (recurring meeting trends)
⬜ Sentiment + talk-time analysis per speaker
⬜ Smart agenda generation from open action items
🔵 Week 6 — Platform
⬜ Team workspaces + RBAC (roles: admin/member/viewer)
⬜ Webhooks (push events to user systems)
⬜ Audit logs (who accessed what, when)
⬜ GDPR tooling (delete, export, retention)
⚫ Week 7 — Monetization Ready
⬜ Stripe billing + subscription tiers
⬜ Usage analytics dashboard
⬜ Admin panel
⬜ Docker Compose → Kubernetes manifests