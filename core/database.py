import sqlite3
import datetime
from pathlib import Path

DB_NAME = Path("meetings.db")


# ─── Phase 1 — unchanged ──────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            filename         TEXT,
            transcript       TEXT,
            created_at       TEXT,
            duration_seconds REAL
        )
    """)

    # Phase 2 tables added here — IF NOT EXISTS means safe on existing databases
    _init_intelligence_tables(conn)

    conn.commit()
    conn.close()


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


def get_all_transcripts():
    """Phase 1 function — unchanged."""
    conn = sqlite3.connect(DB_NAME)

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
) -> int:
    """
    Phase 2 version of save_transcript that also returns the new row ID.
    Use this in pipeline.py so you can link intelligence to the meeting.
    The original save_transcript() still works for anything that doesn't
    need the ID — no existing code breaks.
    """
    conn = sqlite3.connect(DB_NAME)

    cursor = conn.execute(
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


def get_meeting_by_id(meeting_id: int) -> dict | None:
    """
    Fetch a single meeting row by ID.
    Returns a plain dict or None if not found.
    """
    conn = sqlite3.connect(DB_NAME)

    row = conn.execute(
        """
        SELECT id, filename, transcript, created_at, duration_seconds
        FROM meetings WHERE id = ?
        """,
        (meeting_id,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return dict(
        zip(["id", "filename", "transcript", "created_at", "duration_seconds"], row)
    )