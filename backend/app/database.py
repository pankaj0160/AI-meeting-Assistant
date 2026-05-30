import sqlite3
import datetime

from pathlib import Path

DATA_DIR = Path("Database")
DATA_DIR.mkdir(exist_ok=True)

DB_NAME = DATA_DIR / "meetings.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            transcript TEXT,
            created_at TEXT,
            duration_seconds REAL
        )
    """)

    conn.commit()
    conn.close()


def save_transcript(
    filename: str,
    transcript: str,
    duration=None
):
    conn = sqlite3.connect(DB_NAME)

    conn.execute(
        """
        INSERT INTO meetings (
            filename,
            transcript,
            created_at,
            duration_seconds
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            filename,
            transcript,
            datetime.datetime.now().isoformat(),
            duration
        )
    )

    conn.commit()
    conn.close()


def get_all_transcripts():

    conn = sqlite3.connect(DB_NAME)

    rows = conn.execute(
        """
        SELECT *
        FROM meetings
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows