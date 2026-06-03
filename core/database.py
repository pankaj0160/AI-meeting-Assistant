import sqlite3
import datetime
from pathlib import Path

DB_NAME = Path("meetings.db")


# ─── Phase 1 — unchanged ──────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_NAME)

    # ── Phase 1 meetings table ─────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            filename         TEXT,
            transcript       TEXT,
            created_at       TEXT,
            duration_seconds REAL
        )
    """)

    # ── Phase 1 Auth tables ────────────────────────────────────────────────────
    _init_auth_tables(conn)

    # ── Phase 2 intelligence tables ───────────────────────────────────────────
    _init_intelligence_tables(conn)

    # ── Phase 1A migration — add user_id to meetings if missing ───────────────
    _migrate_add_user_id(conn)

    conn.commit()
    conn.close()


def _init_auth_tables(conn):
    """
    Creates users and password_reset_tokens tables.
    Safe to run on existing databases.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT    NOT NULL,
            profile_image TEXT,
            created_at    TEXT    NOT NULL,
            updated_at    TEXT    NOT NULL,
            last_login    TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            token      TEXT    NOT NULL UNIQUE,
            expires_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)


def _migrate_add_user_id(conn):
    """
    Phase 1A migration.
    Adds user_id column to meetings table if it does not already exist.
    Existing meetings get user_id = NULL (guest/legacy meetings).
    Safe to run multiple times.
    """
    cols = [
        row[1] for row in
        conn.execute("PRAGMA table_info(meetings)").fetchall()
    ]
    if "user_id" not in cols:
        conn.execute(
            "ALTER TABLE meetings ADD COLUMN user_id INTEGER REFERENCES users(id)"
        )
        print("✓ Migration: added user_id column to meetings table")
    else:
        print("✓ Migration: user_id column already exists, skipping")


def save_transcript(filename: str, transcript: str, duration=None):
    """Phase 1 function — unchanged. Still works for all existing code."""
    conn = sqlite3.connect(DB_NAME)

    conn.execute(
        """
        INSERT INTO meetings (filename, transcript, created_at, duration_seconds)
        VALUES (?, ?, ?, ?)
        """,
        (
            filename,
            transcript,
            datetime.datetime.now().isoformat(),
            duration,
        ),
    )

    conn.commit()
    conn.close()


def get_all_transcripts(user_id: int = None):
    """
    Returns meetings ordered by newest first.
    If user_id provided — returns only that user's meetings.
    If user_id is None — returns all (legacy/guest support).
    """
    conn = sqlite3.connect(DB_NAME)

    if user_id is not None:
        rows = conn.execute(
            "SELECT * FROM meetings WHERE user_id = ? ORDER BY id DESC",
            (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM meetings ORDER BY id DESC"
        ).fetchall()

    conn.close()
    return rows


# ─── Phase 2 — private table setup ───────────────────────────────────────────

def _init_intelligence_tables(conn):
    """
    Creates all Phase 2 tables.
    Called only by init_db() — never call this directly.
    IF NOT EXISTS means safe to run on an existing populated database.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meeting_summaries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id   INTEGER NOT NULL,
            summary      TEXT    NOT NULL,
            generated_at TEXT    NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS action_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id   INTEGER NOT NULL,
            task         TEXT    NOT NULL,
            owner        TEXT,
            deadline     TEXT,
            priority     TEXT    DEFAULT 'medium',
            status       TEXT    DEFAULT 'open',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id   INTEGER NOT NULL,
            decision     TEXT    NOT NULL,
            rationale    TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id   INTEGER NOT NULL,
            title        TEXT    NOT NULL,
            description  TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)


# ─── Phase 2 — public functions ───────────────────────────────────────────────
def save_transcript_and_get_id(
    filename: str,
    transcript: str,
    duration=None,
    user_id: int = None,
) -> int:
    """
    Phase 2 version of save_transcript that also returns the new row ID.
    Accepts optional user_id to link meeting to authenticated user.
    """
    conn = sqlite3.connect(DB_NAME)

    cursor = conn.execute(
        """
        INSERT INTO meetings (filename, transcript, created_at, duration_seconds, user_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            filename,
            transcript,
            datetime.datetime.now().isoformat(),
            duration,
            user_id,
        ),
    )

    meeting_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return meeting_id


def save_meeting_intelligence(meeting_id: int, intelligence) -> None:
    """
    Saves a MeetingIntelligence Pydantic object to all four intelligence tables.
    meeting_id must be a valid id from the meetings table.
    """
    conn = sqlite3.connect(DB_NAME)

    conn.execute(
        """
        INSERT INTO meeting_summaries (meeting_id, summary, generated_at)
        VALUES (?, ?, ?)
        """,
        (meeting_id, intelligence.summary, intelligence.generated_at),
    )

    for item in intelligence.action_items:
        conn.execute(
            """
            INSERT INTO action_items (meeting_id, task, owner, deadline, priority)
            VALUES (?, ?, ?, ?, ?)
            """,
            (meeting_id, item.task, item.owner, item.deadline, item.priority),
        )

    for d in intelligence.decisions:
        conn.execute(
            """
            INSERT INTO decisions (meeting_id, decision, rationale)
            VALUES (?, ?, ?)
            """,
            (meeting_id, d.decision, d.rationale),
        )

    for t in intelligence.topics:
        conn.execute(
            """
            INSERT INTO topics (meeting_id, title, description)
            VALUES (?, ?, ?)
            """,
            (meeting_id, t.title, t.description),
        )

    conn.commit()
    conn.close()


def get_meeting_intelligence(meeting_id: int) -> dict | None:
    """
    Fetches the complete intelligence report for one meeting.
    Returns a plain dict ready for Streamlit to consume.
    Returns None if no intelligence has been generated yet for this meeting.
    """
    conn = sqlite3.connect(DB_NAME)

    summary_row = conn.execute(
        """
        SELECT summary, generated_at
        FROM meeting_summaries
        WHERE meeting_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (meeting_id,),
    ).fetchone()

    if not summary_row:
        conn.close()
        return None

    action_rows = conn.execute(
        """
        SELECT task, owner, deadline, priority, status
        FROM action_items
        WHERE meeting_id = ?
        ORDER BY id
        """,
        (meeting_id,),
    ).fetchall()

    decision_rows = conn.execute(
        """
        SELECT decision, rationale
        FROM decisions
        WHERE meeting_id = ?
        ORDER BY id
        """,
        (meeting_id,),
    ).fetchall()

    topic_rows = conn.execute(
        """
        SELECT title, description
        FROM topics
        WHERE meeting_id = ?
        ORDER BY id
        """,
        (meeting_id,),
    ).fetchall()

    conn.close()

    return {
        "summary":      summary_row[0],
        "generated_at": summary_row[1],
        "action_items": [
            dict(zip(["task", "owner", "deadline", "priority", "status"], row))
            for row in action_rows
        ],
        "decisions": [
            dict(zip(["decision", "rationale"], row))
            for row in decision_rows
        ],
        "topics": [
            dict(zip(["title", "description"], row))
            for row in topic_rows
        ],
    }


def get_meeting_by_id(meeting_id: int, user_id: int = None) -> dict | None:
    """
    Fetch a single meeting row by ID.
    If user_id provided — verifies meeting belongs to that user.
    Returns None if not found or unauthorized.
    """
    conn = sqlite3.connect(DB_NAME)

    if user_id is not None:
        row = conn.execute(
            """
            SELECT id, filename, transcript, created_at, duration_seconds, user_id
            FROM meetings WHERE id = ? AND user_id = ?
            """,
            (meeting_id, user_id),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, filename, transcript, created_at, duration_seconds, user_id
            FROM meetings WHERE id = ?
            """,
            (meeting_id,),
        ).fetchone()

    conn.close()

    if not row:
        return None

    return dict(
        zip(["id", "filename", "transcript", "created_at", "duration_seconds", "user_id"], row)
    )




# ─── Phase 3 — new function only, zero existing code changed ──────────────────
def get_all_meetings_for_indexing(user_id: int = None) -> list[dict]:
    """
    Phase 3 — Fetch all meetings for RAG indexing.
    If user_id provided — only that user's meetings.
    """
    conn = sqlite3.connect(DB_NAME)

    if user_id is not None:
        rows = conn.execute(
            """
            SELECT id, filename, transcript, created_at
            FROM meetings
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, filename, transcript, created_at
            FROM meetings
            ORDER BY id ASC
            """
        ).fetchall()

    conn.close()

    return [
        {
            "id":         row[0],
            "filename":   row[1] or "",
            "transcript": row[2] or "",
            "created_at": row[3] or "",
        }
        for row in rows
        if row[2]
    ]