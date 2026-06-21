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
import json

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

        _init_workspace_tables(conn)
        _init_week6_tables(cur)
        _init_sentiment_table(cur) 

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
    



# =============================================================================
# WEEK 5 — WORKSPACE TABLES + FUNCTIONS (PostgreSQL version)
# Paste at the very bottom of server/core/database.py
# =============================================================================


def _init_workspace_tables(conn) -> None:
    """
    Creates three workspace tables. Called from init_db() — shares the same
    connection/transaction. Pass the open conn object, not a cursor.
    """
    cur = conn.cursor()

    # ── Workspaces ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id          SERIAL PRIMARY KEY,
            owner_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name        TEXT        NOT NULL,
            description TEXT,
            type        TEXT        NOT NULL DEFAULT 'individual',
            color       TEXT                 DEFAULT '#6366f1',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── Workspace meetings ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_meetings (
            id           SERIAL PRIMARY KEY,
            workspace_id INTEGER     NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            meeting_id   INTEGER     NOT NULL REFERENCES meetings(id)   ON DELETE CASCADE,
            added_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (workspace_id, meeting_id)
        )
    """)

    # ── Workspace members ──────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_members (
            id           SERIAL PRIMARY KEY,
            workspace_id INTEGER     NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id      INTEGER     NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
            role         TEXT        NOT NULL DEFAULT 'owner',
            joined_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (workspace_id, user_id)
        )
    """)

    logger.info("✓ Workspace tables verified / created")


def _init_week6_tables(cur) -> None:
    """
    Creates all Week 6 tables.
    Called from init_db() — safe to run on every startup (IF NOT EXISTS).
 
    Tables created:
      workspace_members  — already exists from Week 5 but now gets a 'role' column
                           we add it safely with ADD COLUMN IF NOT EXISTS
      webhook_endpoints  — where to send event notifications
      webhook_events     — log of every webhook delivery attempt
      audit_logs         — immutable record of every action in the system
    """
 
    # ── workspace_members role enforcement ─────────────────────────────────
    # In Week 5 we created workspace_members with a role column.
    # We add a CHECK constraint now to enforce valid values.
    # We use IF NOT EXISTS so this is safe to re-run.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_members (
            id           SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id      INTEGER NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
            role         TEXT    NOT NULL DEFAULT 'member'
                         CHECK (role IN ('owner', 'member', 'viewer')),
            invited_by   INTEGER REFERENCES users(id),
            joined_at    TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (workspace_id, user_id)
        )
    """)
 
    # ── workspaces (in case Week 5 wasn't applied yet) ────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id          SERIAL PRIMARY KEY,
            owner_id    INTEGER NOT NULL REFERENCES users(id),
            name        TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            type        TEXT    NOT NULL DEFAULT 'individual'
                        CHECK (type IN ('individual', 'project')),
            color       TEXT    DEFAULT '#6366f1',
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_meetings (
            id           SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            meeting_id   INTEGER NOT NULL REFERENCES meetings(id)   ON DELETE CASCADE,
            added_at     TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (workspace_id, meeting_id)
        )
    """)
 
    # ── webhook_endpoints ──────────────────────────────────────────────────
    # Each row is one URL that the user wants us to POST events to.
    # events_subscribed is a text array — e.g. '{meeting.processed,task.updated}'
    cur.execute("""
        CREATE TABLE IF NOT EXISTS webhook_endpoints (
            id                 SERIAL PRIMARY KEY,
            user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            url                TEXT    NOT NULL,
            secret             TEXT    NOT NULL,
            events_subscribed  TEXT[]  NOT NULL DEFAULT '{}',
            is_active          BOOLEAN NOT NULL DEFAULT TRUE,
            created_at         TIMESTAMPTZ DEFAULT NOW()
        )
    """)
 
    # ── webhook_events ─────────────────────────────────────────────────────
    # Every delivery attempt is logged here (success or failure).
    # This lets users see "did my webhook fire?" and retry failed ones.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS webhook_events (
            id              SERIAL PRIMARY KEY,
            endpoint_id     INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
            event_type      TEXT    NOT NULL,
            payload         JSONB   NOT NULL,
            status_code     INTEGER,
            success         BOOLEAN NOT NULL DEFAULT FALSE,
            error_message   TEXT,
            delivered_at    TIMESTAMPTZ DEFAULT NOW()
        )
    """)
 
    # ── audit_logs ─────────────────────────────────────────────────────────
    # Immutable record of everything that happens.
    # We never UPDATE or DELETE rows here — only INSERT.
    # resource_type: 'meeting' | 'workspace' | 'task' | 'user' | 'webhook'
    # action: 'created' | 'updated' | 'deleted' | 'viewed' | 'exported' | 'invited'
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id            SERIAL PRIMARY KEY,
            user_id       INTEGER REFERENCES users(id),
            resource_type TEXT    NOT NULL,
            resource_id   INTEGER,
            action        TEXT    NOT NULL,
            metadata      JSONB   DEFAULT '{}',
            ip_address    TEXT,
            user_agent    TEXT,
            created_at    TIMESTAMPTZ DEFAULT NOW()
        )
    """)
 
    # Index on user_id so "show me everything this user did" is fast
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
        ON audit_logs (user_id, created_at DESC)
    """)
 
    # Index on resource so "show me everything that happened to meeting 5" is fast
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_resource
        ON audit_logs (resource_type, resource_id, created_at DESC)
    """)
 
 
# =============================================================================
# WORKSPACE RBAC FUNCTIONS
# (Replace the Week 5 SQLite versions with these PostgreSQL versions)
# =============================================================================
 
def create_workspace(
    owner_id:    int,
    name:        str,
    description: str = "",
    type:        str = "individual",
    color:       str = "#6366f1",
) -> dict:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO workspaces (owner_id, name, description, type, color)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (owner_id, name, description, type, color),
        )
        workspace = dict(cur.fetchone())
        # Add the creator as owner in workspace_members
        cur.execute(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, 'owner')",
            (workspace["id"], owner_id),
        )
    return workspace
 
 
def get_workspaces_for_user(user_id: int) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT
                w.id, w.owner_id, w.name, w.description, w.type, w.color,
                w.created_at, wm.role,
                (SELECT COUNT(*) FROM workspace_meetings wmt WHERE wmt.workspace_id = w.id) AS meeting_count
            FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE wm.user_id = %s
            ORDER BY w.created_at DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]
 
 
def get_workspace_by_id(workspace_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT w.id, w.owner_id, w.name, w.description, w.type, w.color, w.created_at, wm.role
            FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE w.id = %s AND wm.user_id = %s
            """,
            (workspace_id, user_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None
 
 
def update_workspace(
    workspace_id: int,
    owner_id:     int,
    name:         str = None,
    description:  str = None,
    color:        str = None,
) -> bool:
    fields = {}
    if name        is not None: fields["name"]        = name
    if description is not None: fields["description"] = description
    if color       is not None: fields["color"]       = color
    if not fields:
        return True
 
    fields["updated_at"] = "NOW()"
 
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM workspaces WHERE id = %s AND owner_id = %s",
            (workspace_id, owner_id),
        )
        if not cur.fetchone():
            return False
 
        # Build SET clause — updated_at uses NOW() function, not a parameter
        parts = []
        values = []
        for col, val in fields.items():
            if col == "updated_at":
                parts.append("updated_at = NOW()")
            else:
                parts.append(f"{col} = %s")
                values.append(val)
 
        values.append(workspace_id)
        cur.execute(
            f"UPDATE workspaces SET {', '.join(parts)} WHERE id = %s",
            values,
        )
    return True
 
 
def delete_workspace(workspace_id: int, owner_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM workspaces WHERE id = %s AND owner_id = %s",
            (workspace_id, owner_id),
        )
        if not cur.fetchone():
            return False
        cur.execute("DELETE FROM workspaces WHERE id = %s", (workspace_id,))
    return True
 
 
def get_workspace_members(workspace_id: int, user_id: int) -> list[dict] | None:
    """
    Get all members of a workspace.
    Returns None if user_id is not a member (access denied).
    Returns list of members (with user details) if user has access.
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
 
        # Check caller is a member
        cur.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id),
        )
        if not cur.fetchone():
            return None
 
        # Get all members with their user info
        cur.execute(
            """
            SELECT
                wm.user_id, wm.role, wm.joined_at,
                u.full_name, u.email, u.profile_image
            FROM workspace_members wm
            JOIN users u ON u.id = wm.user_id
            WHERE wm.workspace_id = %s
            ORDER BY
                CASE wm.role WHEN 'owner' THEN 1 WHEN 'member' THEN 2 ELSE 3 END,
                wm.joined_at
            """,
            (workspace_id,),
        )
        return [dict(r) for r in cur.fetchall()]
 
 
def invite_member_to_workspace(
    workspace_id: int,
    inviter_id:   int,
    invitee_email: str,
    role:         str = "member",
) -> dict:
    """
    Invite a user to a workspace by their email address.
 
    Rules:
      - The inviter must be the owner or a member with 'member' role
        (only owners can invite; viewers cannot)
      - The invitee must already have a Summly account
      - Valid roles: 'member', 'viewer' (cannot invite as 'owner')
 
    Returns:
      {"success": True, "user_id": int, "email": str}  if added
      {"success": False, "reason": str}                 if failed
 
    Why return a dict instead of raising an exception?
      Because there are several expected failure cases (user not found,
      already a member, etc.) that aren't really errors — they're
      business logic outcomes. Returning a dict lets the endpoint
      give a clear message for each case.
    """
    if role not in ("member", "viewer"):
        return {"success": False, "reason": "role must be 'member' or 'viewer'"}
 
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
 
        # Check inviter has permission (must be owner)
        cur.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, inviter_id),
        )
        inviter_row = cur.fetchone()
        if not inviter_row or inviter_row["role"] != "owner":
            return {"success": False, "reason": "Only workspace owners can invite members"}
 
        # Find the invitee by email
        cur.execute(
            "SELECT id, email, full_name FROM users WHERE LOWER(email) = LOWER(%s)",
            (invitee_email,),
        )
        invitee = cur.fetchone()
        if not invitee:
            return {
                "success": False,
                "reason": f"No Summly account found for {invitee_email}. "
                          f"They need to register first.",
            }
 
        # Check not already a member
        cur.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, invitee["id"]),
        )
        if cur.fetchone():
            return {
                "success": False,
                "reason": f"{invitee['full_name']} is already a member of this workspace",
            }
 
        # Add them
        cur.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, role, invited_by)
            VALUES (%s, %s, %s, %s)
            """,
            (workspace_id, invitee["id"], role, inviter_id),
        )
 
    return {
        "success":   True,
        "user_id":   invitee["id"],
        "email":     invitee["email"],
        "full_name": invitee["full_name"],
        "role":      role,
    }
 
 
def remove_member_from_workspace(
    workspace_id: int,
    owner_id:     int,
    target_user_id: int,
) -> bool:
    """
    Remove a member from a workspace.
    Only the owner can remove members.
    The owner cannot remove themselves (use delete_workspace instead).
    Returns True if removed, False if not found or not authorized.
    """
    if owner_id == target_user_id:
        return False   # Owner can't remove themselves
 
    with get_connection() as conn:
        cur = conn.cursor()
 
        # Verify the caller is the owner
        cur.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, owner_id),
        )
        row = cur.fetchone()
        if not row or row[0] != "owner":
            return False
 
        cur.execute(
            "DELETE FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, target_user_id),
        )
    return True
 
 
def add_meeting_to_workspace(workspace_id: int, meeting_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id),
        )
        if not cur.fetchone():
            return False
        cur.execute(
            "SELECT id FROM meetings WHERE id = %s AND user_id = %s",
            (meeting_id, user_id),
        )
        if not cur.fetchone():
            return False
        cur.execute(
            """
            INSERT INTO workspace_meetings (workspace_id, meeting_id)
            VALUES (%s, %s)
            ON CONFLICT (workspace_id, meeting_id) DO NOTHING
            """,
            (workspace_id, meeting_id),
        )
    return True
 
 
def remove_meeting_from_workspace(workspace_id: int, meeting_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id),
        )
        if not cur.fetchone():
            return False
        cur.execute(
            "DELETE FROM workspace_meetings WHERE workspace_id = %s AND meeting_id = %s",
            (workspace_id, meeting_id),
        )
    return True
 
 
def get_meetings_in_workspace(workspace_id: int, user_id: int) -> list[dict] | None:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id),
        )
        if not cur.fetchone():
            return None
 
        cur.execute(
            """
            SELECT m.id, m.filename, m.created_at, m.duration_seconds,
                   mt.title AS ai_title, wm.added_at
            FROM meetings m
            JOIN workspace_meetings wm ON wm.meeting_id = m.id
            LEFT JOIN meeting_titles mt ON mt.meeting_id = m.id
            WHERE wm.workspace_id = %s
            ORDER BY wm.added_at DESC
            """,
            (workspace_id,),
        )
        return [dict(r) for r in cur.fetchall()]
 
 
def get_workspace_for_meeting(meeting_id: int) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT w.id, w.name, w.type, w.color
            FROM workspaces w
            JOIN workspace_meetings wm ON wm.workspace_id = w.id
            WHERE wm.meeting_id = %s
            """,
            (meeting_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None
 
 
# =============================================================================
# WEBHOOK FUNCTIONS
# =============================================================================
 
def create_webhook(user_id: int, url: str, events: list[str]) -> dict:
    """
    Register a new webhook endpoint for a user.
 
    A webhook is a URL on the user's server that we POST to when events happen.
    Example events: 'meeting.processed', 'task.updated', 'member.invited'
 
    We generate a secret that the user uses to verify the POST came from us.
    They should check:  HMAC-SHA256(secret, body) == X-Summly-Signature header
 
    Returns the new webhook with its id and secret.
    """
    import secrets
    webhook_secret = secrets.token_hex(32)   # 64-char hex string
 
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO webhook_endpoints (user_id, url, secret, events_subscribed)
            VALUES (%s, %s, %s, %s)
            RETURNING id, url, events_subscribed, is_active, created_at
            """,
            (user_id, url, webhook_secret, events),
        )
        row = dict(cur.fetchone())
 
    row["secret"] = webhook_secret   # return secret on creation — never shown again
    return row
 
 
def get_webhooks_for_user(user_id: int) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT id, url, events_subscribed, is_active, created_at
            FROM webhook_endpoints
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]
 
 
def delete_webhook(webhook_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM webhook_endpoints WHERE id = %s AND user_id = %s",
            (webhook_id, user_id),
        )
        if not cur.fetchone():
            return False
        cur.execute("DELETE FROM webhook_endpoints WHERE id = %s", (webhook_id,))
    return True
 
 
def log_webhook_event(
    endpoint_id:   int,
    event_type:    str,
    payload:       dict,
    status_code:   int,
    success:       bool,
    error_message: str = None,
) -> None:
    """Log one webhook delivery attempt (success or failure)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO webhook_events (endpoint_id, event_type, payload, status_code, success, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (endpoint_id, event_type, json.dumps(payload), status_code, success, error_message),
        )
 
 
def get_webhook_events(webhook_id: int, user_id: int, limit: int = 50) -> list[dict]:
    """Get delivery history for one webhook (most recent first)."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Verify ownership first
        cur.execute(
            "SELECT id FROM webhook_endpoints WHERE id = %s AND user_id = %s",
            (webhook_id, user_id),
        )
        if not cur.fetchone():
            return []
        cur.execute(
            """
            SELECT id, event_type, status_code, success, error_message, delivered_at
            FROM webhook_events
            WHERE endpoint_id = %s
            ORDER BY delivered_at DESC
            LIMIT %s
            """,
            (webhook_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]
 
 
# =============================================================================
# AUDIT LOG FUNCTIONS
# =============================================================================
 
def write_audit_log(
    user_id:       int,
    resource_type: str,
    action:        str,
    resource_id:   int  = None,
    metadata:      dict = None,
    ip_address:    str  = None,
    user_agent:    str  = None,
) -> None:
    """
    Write one immutable audit log entry.
 
    Call this whenever something important happens:
        write_audit_log(user_id=5, resource_type="meeting", resource_id=12, action="exported")
        write_audit_log(user_id=5, resource_type="workspace", resource_id=3, action="member_invited",
                        metadata={"invitee_email": "alice@co.com", "role": "member"})
 
    We never raise an exception here — a logging failure should never
    break the actual operation. If the INSERT fails, we log the error and move on.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_logs (user_id, resource_type, resource_id, action, metadata, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    resource_type,
                    resource_id,
                    action,
                    json.dumps(metadata or {}),
                    ip_address,
                    user_agent,
                ),
            )
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).error(f"Audit log write failed: {e}")
 
 
def get_audit_logs(
    user_id:       int,
    resource_type: str  = None,
    resource_id:   int  = None,
    limit:         int  = 100,
) -> list[dict]:
    """
    Fetch audit log entries for a user with optional filters.
 
    Examples:
      get_audit_logs(user_id=5)                               → all activity for user 5
      get_audit_logs(user_id=5, resource_type='meeting')      → only meeting events
      get_audit_logs(user_id=5, resource_type='meeting', resource_id=12) → one meeting's history
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
 
        # Build WHERE clause dynamically based on which filters are provided
        conditions = ["user_id = %s"]
        values     = [user_id]
 
        if resource_type:
            conditions.append("resource_type = %s")
            values.append(resource_type)
        if resource_id:
            conditions.append("resource_id = %s")
            values.append(resource_id)
 
        where = " AND ".join(conditions)
        values.append(limit)
 
        cur.execute(
            f"""
            SELECT id, user_id, resource_type, resource_id, action,
                   metadata, ip_address, created_at
            FROM audit_logs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            values,
        )
        return [dict(r) for r in cur.fetchall()]
 
 
# =============================================================================
# GDPR FUNCTIONS
# =============================================================================
 
def export_user_data(user_id: int) -> dict:
    """
    Export all data belonging to a user.
    Required by GDPR Article 20 (Right to data portability).
 
    Returns a single dict with every piece of data we hold about the user.
    The endpoint serialises this to JSON for the user to download.
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
 
        # User profile
        cur.execute(
            "SELECT id, full_name, email, profile_image, created_at, last_login FROM users WHERE id = %s",
            (user_id,),
        )
        user_row = cur.fetchone()
        if not user_row:
            return {}
 
        # Meetings (without transcripts in the index — too large)
        cur.execute(
            "SELECT id, filename, created_at, duration_seconds FROM meetings WHERE user_id = %s ORDER BY id",
            (user_id,),
        )
        meetings = [dict(r) for r in cur.fetchall()]
 
        meeting_ids = [m["id"] for m in meetings]
 
        # Action items
        action_items = []
        if meeting_ids:
            cur.execute(
                """
                SELECT task, owner, deadline, priority, status, created_at, meeting_id
                FROM action_items WHERE meeting_id = ANY(%s) ORDER BY created_at
                """,
                (meeting_ids,),
            )
            action_items = [dict(r) for r in cur.fetchall()]
 
        # Workspaces owned by user
        cur.execute(
            "SELECT id, name, description, type, created_at FROM workspaces WHERE owner_id = %s",
            (user_id,),
        )
        workspaces = [dict(r) for r in cur.fetchall()]
 
        # Audit log
        cur.execute(
            "SELECT resource_type, resource_id, action, metadata, created_at FROM audit_logs WHERE user_id = %s ORDER BY created_at",
            (user_id,),
        )
        audit = [dict(r) for r in cur.fetchall()]
 
    return {
        "exported_at":   datetime.datetime.utcnow().isoformat(),
        "user":          dict(user_row),
        "meetings":      meetings,
        "action_items":  action_items,
        "workspaces":    workspaces,
        "audit_history": audit,
    }
 
 
def delete_user_data(user_id: int) -> bool:
    """
    Delete all data belonging to a user.
    Required by GDPR Article 17 (Right to erasure / "Right to be forgotten").
 
    What gets deleted (in order to respect FK constraints):
      1. audit_logs         (references user)
      2. webhook_events     (via webhook_endpoints → user)
      3. webhook_endpoints  (references user)
      4. workspace_members  (references user)
      5. workspace_meetings → workspaces owned by user (CASCADE handles this)
      6. workspaces         (owned by user — CASCADE removes members + meetings links)
      7. action_items       → via meetings (CASCADE)
      8. decisions          → via meetings (CASCADE)
      9. topics             → via meetings (CASCADE)
     10. meeting_summaries  → via meetings (CASCADE)
     11. meeting_health     → via meetings (CASCADE)
     12. meeting_titles     → via meetings (CASCADE)
     13. meeting_diarization → via meetings (CASCADE)
     14. meeting_quotes     → via meetings (CASCADE)
     15. meetings           (references user)
     16. password_reset_tokens (CASCADE on user delete)
     17. users              (the user row itself)
 
    The PostgreSQL ON DELETE CASCADE rules handle steps 6-15 automatically
    once we delete the meetings and workspaces rows.
 
    Returns True if user was found and deleted.
    """
    with get_connection() as conn:
        cur = conn.cursor()
 
        # Check user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            return False
 
        # Delete in FK-safe order
        cur.execute("DELETE FROM audit_logs WHERE user_id = %s", (user_id,))
        cur.execute(
            "DELETE FROM webhook_events WHERE endpoint_id IN (SELECT id FROM webhook_endpoints WHERE user_id = %s)",
            (user_id,),
        )
        cur.execute("DELETE FROM webhook_endpoints WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM workspace_members WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM workspaces WHERE owner_id = %s", (user_id,))
        cur.execute("DELETE FROM meetings WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
 
    return True





def _init_sentiment_table(cur) -> None:
    """
    Creates the meeting_sentiment table.
    Called from init_db() — safe to run on every startup.
 
    We store the full analysis as JSONB because:
    - The structure is nested (overall scores + per-speaker list)
    - We query the whole thing at once, never individual fields
    - JSONB in PostgreSQL is fast and queryable if we ever need it
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meeting_sentiment (
            id          SERIAL PRIMARY KEY,
            meeting_id  INTEGER NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE,
            result      JSONB   NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
 
    # Index so "get sentiment for meeting X" is instant
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_meeting_sentiment_meeting_id
        ON meeting_sentiment (meeting_id)
    """)
 
 
def save_sentiment_analysis(meeting_id: int, result: dict) -> None:
    """
    Save the full sentiment + talk-time analysis result for a meeting.
    Replaces any existing result for this meeting (safe to re-run).
 
    Args:
        meeting_id : the meeting this analysis belongs to
        result     : the full dict returned by run_full_analysis() in sentiment.py
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO meeting_sentiment (meeting_id, result)
            VALUES (%s, %s)
            ON CONFLICT (meeting_id)
            DO UPDATE SET result = EXCLUDED.result, created_at = NOW()
            """,
            (meeting_id, json.dumps(result)),
        )
 
 
def get_sentiment_analysis(meeting_id: int) -> dict | None:
    """
    Fetch stored sentiment analysis for a meeting.
    Returns None if analysis hasn't been run yet.
 
    The endpoint calls this first — if it returns something, we skip
    the LLM call and return the cached result immediately.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT result FROM meeting_sentiment WHERE meeting_id = %s",
            (meeting_id,),
        )
        row = cur.fetchone()
 
    if not row:
        return None
 
    # PostgreSQL returns JSONB as a Python dict already — no json.loads needed
    result = row[0]
    if isinstance(result, str):
        result = json.loads(result)
    return result
 