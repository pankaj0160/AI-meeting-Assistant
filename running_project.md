# Backend
uvicorn main:app --reload

# Frontend (Streamlit)
streamlit run frontend/app.py



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