# server/core/database.py
#
# Full replacement of the SQLite version.
# Every function has the SAME NAME and returns the SAME TYPE as before.
# main.py does not change at all.
#
# KEY DIFFERENCES FROM SQLite VERSION:
#   1. Import psycopg2 instead of sqlite3
#   2. Connection string from DATABASE_URL env var instead of a .db file
#   3. Parameters use %s instead of ?
#   4. AUTOINCREMENT → SERIAL (PostgreSQL syntax)
#   5. get_connection() instead of sqlite3.connect(DB_NAME) everywhere
#   6. RETURNING id to get the auto-generated ID after INSERT (PostgreSQL way)

import os
import logging
import datetime
import json
from contextlib import contextmanager

import psycopg2
import psycopg2.extras   # gives us RealDictCursor (rows as dicts, not tuples)
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


@contextmanager
def get_connection():
    """
    Context manager that opens a PostgreSQL connection and closes it when done.

    WHY A CONTEXT MANAGER?
        SQLite's sqlite3.connect() is cheap — opening and closing connections
        is nearly instant because it's just a local file.
        PostgreSQL connections are more expensive — they involve a TCP handshake
        with the database server. The context manager ensures we ALWAYS close
        the connection, even if an exception happens halfway through.

    Usage:
        with get_connection() as conn:
            conn.execute(...)
        # connection is automatically closed here

    WHY NOT A CONNECTION POOL?
        A pool reuses connections instead of opening/closing each time.
        That's the right approach for high-traffic production (use psycopg2.pool
        or SQLAlchemy). For Week 4 we keep it simple — one connection per request.
        Week 4's rate limiting will prevent us from being overwhelmed anyway.
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set.\n"
            "Add it to your .env file:\n"
            "  DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres\n"
            "Get it from: Supabase dashboard → Settings → Database → Connection string (Python)"
        )

    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# DATABASE INITIALISATION
# =============================================================================
# Run this once when the server starts to create all tables.
# IF NOT EXISTS makes it safe to run every startup — tables are only created
# if they don't already exist.

def init_db():
    """
    Create all tables. Safe to call on every startup.
    Call this in main.py's startup event (same as before).
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # ── Users ──────────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                full_name     TEXT        NOT NULL,
                email         TEXT        NOT NULL UNIQUE,
                password_hash TEXT        NOT NULL,
                profile_image TEXT,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_login    TIMESTAMPTZ
            )
        """)

        # ── Password reset ─────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id         SERIAL PRIMARY KEY,
                user_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token      TEXT        NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL
            )
        """)

        # ── Meetings ───────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id               SERIAL PRIMARY KEY,
                user_id          INTEGER REFERENCES users(id),
                filename         TEXT,
                transcript       TEXT,
                created_at       TIMESTAMPTZ DEFAULT NOW(),
                duration_seconds REAL
            )
        """)

        # ── Intelligence tables ────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_summaries (
                id           SERIAL PRIMARY KEY,
                meeting_id   INTEGER     NOT NULL REFERENCES meetings(id),
                summary      TEXT        NOT NULL,
                generated_at TEXT        NOT NULL,
                created_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id         SERIAL PRIMARY KEY,
                meeting_id INTEGER     NOT NULL REFERENCES meetings(id),
                task       TEXT        NOT NULL,
                owner      TEXT,
                deadline   TEXT,
                priority   TEXT        DEFAULT 'medium',
                status     TEXT        DEFAULT 'open',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id         SERIAL PRIMARY KEY,
                meeting_id INTEGER     NOT NULL REFERENCES meetings(id),
                decision   TEXT        NOT NULL,
                rationale  TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id          SERIAL PRIMARY KEY,
                meeting_id  INTEGER     NOT NULL REFERENCES meetings(id),
                title       TEXT        NOT NULL,
                description TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_health (
                id               SERIAL PRIMARY KEY,
                meeting_id       INTEGER NOT NULL UNIQUE REFERENCES meetings(id),
                overall_score    INTEGER NOT NULL,
                participation    INTEGER NOT NULL,
                decision_quality INTEGER NOT NULL,
                action_clarity   INTEGER NOT NULL,
                followup_risk    INTEGER NOT NULL,
                highlights       TEXT,
                concerns         TEXT,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_quotes (
                id         SERIAL PRIMARY KEY,
                meeting_id INTEGER NOT NULL REFERENCES meetings(id),
                quote      TEXT    NOT NULL,
                speaker    TEXT,
                context    TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_titles (
                id         SERIAL PRIMARY KEY,
                meeting_id INTEGER NOT NULL UNIQUE REFERENCES meetings(id),
                title      TEXT    NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_diarization (
                id           SERIAL PRIMARY KEY,
                meeting_id   INTEGER NOT NULL UNIQUE REFERENCES meetings(id),
                transcript   TEXT    NOT NULL,
                talk_time    JSONB   NOT NULL DEFAULT '{}',
                num_speakers INTEGER NOT NULL,
                created_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        logger.info("✓ Database tables verified / created")


# =============================================================================
# MEETINGS
# =============================================================================

def save_transcript(filename: str, transcript: str, duration=None):
    """Legacy function — kept so nothing breaks. Use save_transcript_and_get_id instead."""
    save_transcript_and_get_id(filename=filename, transcript=transcript, duration=duration)


def save_transcript_and_get_id(
    filename:   str,
    transcript: str,
    duration:   float = None,
    user_id:    int   = None,
) -> int:
    """
    Save a meeting transcript and return the new meeting's ID.

    PostgreSQL difference from SQLite:
        SQLite:     cursor.lastrowid
        PostgreSQL: RETURNING id  ← add this to the INSERT and fetchone() the result
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO meetings (filename, transcript, created_at, duration_seconds, user_id)
            VALUES (%s, %s, NOW(), %s, %s)
            RETURNING id
            """,
            (filename, transcript, duration, user_id),
        )
        return cur.fetchone()[0]


def get_all_transcripts(user_id: int = None):
    """Returns meetings, newest first. Filters by user_id if provided."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id is not None:
            cur.execute(
                "SELECT * FROM meetings WHERE user_id = %s ORDER BY id DESC",
                (user_id,),
            )
        else:
            cur.execute("SELECT * FROM meetings ORDER BY id DESC")
        return cur.fetchall()


def get_meeting_by_id(meeting_id: int, user_id: int = None) -> dict | None:
    """
    Fetch one meeting. If user_id provided, verifies ownership.
    Returns None if not found or not owned by this user.
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id is not None:
            cur.execute(
                """
                SELECT id, filename, transcript, created_at, duration_seconds, user_id
                FROM meetings WHERE id = %s AND user_id = %s
                """,
                (meeting_id, user_id),
            )
        else:
            cur.execute(
                "SELECT id, filename, transcript, created_at, duration_seconds, user_id FROM meetings WHERE id = %s",
                (meeting_id,),
            )
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_meetings_for_indexing(user_id: int = None) -> list[dict]:
    """Fetch all meetings for RAG indexing."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id is not None:
            cur.execute(
                "SELECT id, filename, transcript, created_at FROM meetings WHERE user_id = %s ORDER BY id ASC",
                (user_id,),
            )
        else:
            cur.execute("SELECT id, filename, transcript, created_at FROM meetings ORDER BY id ASC")
        rows = cur.fetchall()
        return [dict(r) for r in rows if r["transcript"]]


# =============================================================================
# INTELLIGENCE
# =============================================================================

def save_meeting_intelligence(meeting_id: int, intelligence) -> None:
    """
    Saves a MeetingIntelligence Pydantic object to all four intelligence tables.
    Identical interface to the SQLite version — main.py doesn't change.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO meeting_summaries (meeting_id, summary, generated_at) VALUES (%s, %s, %s)",
            (meeting_id, intelligence.summary, intelligence.generated_at),
        )

        for item in intelligence.action_items:
            cur.execute(
                "INSERT INTO action_items (meeting_id, task, owner, deadline, priority) VALUES (%s, %s, %s, %s, %s)",
                (meeting_id, item.task, item.owner, item.deadline, item.priority),
            )

        for d in intelligence.decisions:
            cur.execute(
                "INSERT INTO decisions (meeting_id, decision, rationale) VALUES (%s, %s, %s)",
                (meeting_id, d.decision, d.rationale),
            )

        for t in intelligence.topics:
            cur.execute(
                "INSERT INTO topics (meeting_id, title, description) VALUES (%s, %s, %s)",
                (meeting_id, t.title, t.description),
            )


def get_meeting_intelligence(meeting_id: int) -> dict | None:
    """Fetch the complete intelligence report for one meeting."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT summary, generated_at FROM meeting_summaries WHERE meeting_id = %s ORDER BY created_at DESC LIMIT 1",
            (meeting_id,),
        )
        summary_row = cur.fetchone()
        if not summary_row:
            return None

        cur.execute(
            "SELECT task, owner, deadline, priority, status FROM action_items WHERE meeting_id = %s ORDER BY id",
            (meeting_id,),
        )
        action_rows = cur.fetchall()

        cur.execute(
            "SELECT decision, rationale FROM decisions WHERE meeting_id = %s ORDER BY id",
            (meeting_id,),
        )
        decision_rows = cur.fetchall()

        cur.execute(
            "SELECT title, description FROM topics WHERE meeting_id = %s ORDER BY id",
            (meeting_id,),
        )
        topic_rows = cur.fetchall()

    return {
        "summary":      summary_row[0],
        "generated_at": summary_row[1],
        "action_items": [dict(zip(["task", "owner", "deadline", "priority", "status"], r)) for r in action_rows],
        "decisions":    [dict(zip(["decision", "rationale"], r)) for r in decision_rows],
        "topics":       [dict(zip(["title", "description"], r)) for r in topic_rows],
    }


# =============================================================================
# HEALTH, QUOTES, TITLES
# =============================================================================

def save_meeting_health(meeting_id: int, health: dict) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meeting_health WHERE meeting_id = %s", (meeting_id,))
        cur.execute(
            """
            INSERT INTO meeting_health
                (meeting_id, overall_score, participation, decision_quality,
                 action_clarity, followup_risk, highlights, concerns)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                meeting_id,
                health["overall_score"], health["participation"],
                health["decision_quality"], health["action_clarity"],
                health["followup_risk"],
                health.get("highlights", ""), health.get("concerns", ""),
            ),
        )


def get_meeting_health(meeting_id: int) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM meeting_health WHERE meeting_id = %s", (meeting_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {
        "overall_score": row[2], "participation": row[3],
        "decision_quality": row[4], "action_clarity": row[5],
        "followup_risk": row[6], "highlights": row[7], "concerns": row[8],
    }


def save_meeting_quotes(meeting_id: int, quotes: list[dict]) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meeting_quotes WHERE meeting_id = %s", (meeting_id,))
        for q in quotes:
            cur.execute(
                "INSERT INTO meeting_quotes (meeting_id, quote, speaker, context) VALUES (%s, %s, %s, %s)",
                (meeting_id, q["quote"], q.get("speaker"), q.get("context")),
            )


def get_meeting_quotes(meeting_id: int) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT quote, speaker, context FROM meeting_quotes WHERE meeting_id = %s", (meeting_id,))
        rows = cur.fetchall()
    return [{"quote": r[0], "speaker": r[1], "context": r[2]} for r in rows]


def save_meeting_title(meeting_id: int, title: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meeting_titles WHERE meeting_id = %s", (meeting_id,))
        cur.execute("INSERT INTO meeting_titles (meeting_id, title) VALUES (%s, %s)", (meeting_id, title))


def get_meeting_title(meeting_id: int) -> str | None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT title FROM meeting_titles WHERE meeting_id = %s", (meeting_id,))
        row = cur.fetchone()
    return row[0] if row else None


# =============================================================================
# ACTION ITEMS (full CRUD — from Week 3)
# =============================================================================

def update_action_item_status(item_id: int, status: str, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ai.id FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            WHERE ai.id = %s AND m.user_id = %s
            """,
            (item_id, user_id),
        )
        if not cur.fetchone():
            return False
        cur.execute("UPDATE action_items SET status = %s WHERE id = %s", (status, item_id))
    return True


def get_all_action_items(user_id: int) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT ai.id, ai.meeting_id, ai.task, ai.owner, ai.deadline,
                   ai.priority, ai.status, ai.created_at, m.filename,
                   m.created_at AS meeting_date
            FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            WHERE m.user_id = %s
            ORDER BY
                CASE ai.status
                    WHEN 'open'        THEN 1
                    WHEN 'in_progress' THEN 2
                    WHEN 'overdue'     THEN 3
                    WHEN 'done'        THEN 4
                    ELSE 5
                END,
                m.created_at DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_action_items_by_meeting(meeting_id: int) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, task, owner, deadline, priority, status, created_at FROM action_items WHERE meeting_id = %s ORDER BY id",
            (meeting_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def update_action_item_fields(
    item_id: int, user_id: int,
    owner: str = None, deadline: str = None,
    priority: str = None, status: str = None,
) -> bool:
    fields = {}
    if owner    is not None: fields["owner"]    = owner
    if deadline is not None: fields["deadline"] = deadline
    if priority is not None: fields["priority"] = priority
    if status   is not None: fields["status"]   = status

    if not fields:
        return True

    if "priority" in fields and fields["priority"] not in {"high", "medium", "low"}:
        raise ValueError(f"priority must be high/medium/low, got: {fields['priority']}")
    if "status" in fields and fields["status"] not in {"open", "in_progress", "done", "overdue"}:
        raise ValueError(f"status must be open/in_progress/done/overdue, got: {fields['status']}")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT ai.id FROM action_items ai JOIN meetings m ON m.id = ai.meeting_id WHERE ai.id = %s AND m.user_id = %s",
            (item_id, user_id),
        )
        if not cur.fetchone():
            return False

        set_clause = ", ".join(f"{col} = %s" for col in fields)
        cur.execute(f"UPDATE action_items SET {set_clause} WHERE id = %s", [*fields.values(), item_id])
    return True


def delete_action_item(item_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT ai.id FROM action_items ai JOIN meetings m ON m.id = ai.meeting_id WHERE ai.id = %s AND m.user_id = %s",
            (item_id, user_id),
        )
        if not cur.fetchone():
            return False
        cur.execute("DELETE FROM action_items WHERE id = %s", (item_id,))
    return True


def get_action_item_stats(user_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ai.status, COUNT(*) FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            WHERE m.user_id = %s GROUP BY ai.status
            """,
            (user_id,),
        )
        counts = {row[0]: row[1] for row in cur.fetchall()}
    return {
        "total":       sum(counts.values()),
        "open":        counts.get("open", 0),
        "in_progress": counts.get("in_progress", 0),
        "done":        counts.get("done", 0),
        "overdue":     counts.get("overdue", 0),
    }


# =============================================================================
# DIARIZATION (from Week 3)
# =============================================================================

def save_diarization(meeting_id: int, transcript: str, talk_time: dict, num_speakers: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meeting_diarization WHERE meeting_id = %s", (meeting_id,))
        cur.execute(
            "INSERT INTO meeting_diarization (meeting_id, transcript, talk_time, num_speakers) VALUES (%s, %s, %s, %s)",
            (meeting_id, transcript, json.dumps(talk_time), num_speakers),
        )


def get_diarization(meeting_id: int) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT transcript, talk_time, num_speakers FROM meeting_diarization WHERE meeting_id = %s",
            (meeting_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "transcript":   row[0],
        "talk_time":    row[1] if isinstance(row[1], dict) else json.loads(row[1]),
        "num_speakers": row[2],
    }


# =============================================================================
# AUTH (keep working exactly as before)
# =============================================================================

def get_user_by_email(email: str) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
        row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def create_user(full_name: str, email: str, password_hash: str) -> dict:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO users (full_name, email, password_hash, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING *
            """,
            (full_name, email, password_hash),
        )
        return dict(cur.fetchone())