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
import json                          # FIX: removed duplicate import of json
import secrets
from contextlib import contextmanager

import psycopg2
import psycopg2.extras               # gives us RealDictCursor (rows as dicts, not tuples)
import psycopg2.pool                 # FIX: added for connection pool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


# ---------------------------------------------------------------------------
# FIX: Connection pool — created ONCE when the server starts.
#
# Before: every database function called psycopg2.connect() which opened a
# brand new TCP connection to Supabase, used it, then closed it.
# That open+close costs 10-20ms every time and hits Supabase connection limits.
#
# After: 2 connections are opened at startup and kept alive.
# Every function borrows one, uses it, returns it — takes <1ms.
# Up to 10 connections can open under load. Max 10 — safe for Supabase limits.
#
# ThreadedConnectionPool because FastAPI handles requests in multiple threads —
# this version has an internal lock so two threads cannot grab the same
# connection at the same time.
# ---------------------------------------------------------------------------
_pool = None


def _get_pool():
    """
    Returns the shared connection pool, creating it on the very first call.
    You never call this directly — get_connection() calls it automatically.
    """
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set.\n"
                "Add it to your .env file:\n"
                "  DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres\n"
                "Get it from: Supabase dashboard -> Settings -> Database -> Connection string (Python)"
            )
        # FIX: create pool once at startup — connections reused across all requests
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,   # 2 connections always open and ready
            maxconn=10,  # never more than 10 open at once
            dsn=DATABASE_URL,
        )
        logger.info("Database connection pool created (min=2, max=10)")
    return _pool


@contextmanager
def get_connection():
    """
    Borrows a connection from the pool, yields it, then returns it.

    Usage is IDENTICAL to before — zero changes needed in any other file:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(...)

    What changed internally:
      Old: psycopg2.connect()  -> opens new TCP connection every time (~15ms)
           conn.close()        -> tears it down after use

      New: pool.getconn()      -> borrows already-open connection (<1ms)
           pool.putconn(conn)  -> returns to pool for the next request
    """
    pool = _get_pool()
    # FIX: borrow from pool instead of opening a fresh connection
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # FIX: return to pool instead of closing — stays alive for next request
        pool.putconn(conn)


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

        # PHASE 2 — commitment tracking migration.
        # CREATE TABLE IF NOT EXISTS above is a no-op on an existing table,
        # so new columns on an already-deployed action_items table need an
        # explicit, idempotent ALTER TABLE. Safe to run on every startup —
        # ADD COLUMN IF NOT EXISTS is a no-op once the column exists.
        #   due_date:     the parsed, actual date behind `deadline`'s free
        #                 text (see core/deadline_parser.py). NULL when the
        #                 text couldn't be parsed — "overdue"/"reliability"
        #                 math simply skips items with no due_date rather
        #                 than guessing.
        #   completed_at: stamped when status is set to 'done'. Needed to
        #                 tell "done on time" apart from "done late" for
        #                 the commitment reliability score.
        cur.execute("ALTER TABLE action_items ADD COLUMN IF NOT EXISTS due_date DATE")
        cur.execute("ALTER TABLE action_items ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ")

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

        # FIX: Missing indexes — without these every query that filters by
        # user_id or meeting_id does a full table scan (reads every row).
        #
        # Example without index:  "get meetings for user 42"
        #   → PostgreSQL reads ALL meetings rows, checks each one's user_id
        #   → 10,000 meetings = 10,000 row reads on every dashboard load
        #
        # Example with index:     "get meetings for user 42"
        #   → PostgreSQL jumps directly to user 42's rows via the index
        #   → 10,000 meetings = ~5 reads, regardless of total table size
        #
        # IF NOT EXISTS = safe to run every startup — skips if already created.

        # meetings.user_id — hit on: dashboard, tasks page, stats, GDPR export
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meetings_user_id
            ON meetings (user_id)
        """)

        # action_items.meeting_id — hit on: tasks page, meeting detail page
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_action_items_meeting_id
            ON action_items (meeting_id)
        """)

        # workspace_members.user_id — hit on: every workspace page load
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id
            ON workspace_members (user_id)
        """)

        # meeting_titles.meeting_id — hit on: meetings list (joins titles)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_meeting_titles_meeting_id
            ON meeting_titles (meeting_id)
        """)

        # ── Row Level Security ───────────────────────────────────────────────
        # FIX: Supabase's security Advisor flags every public table without
        # RLS as CRITICAL — Supabase auto-exposes a REST API (PostgREST) over
        # the whole public schema, gated only by an `anon` API key that's
        # meant to be public. Without RLS, anyone with that key can read/
        # write these tables directly, bypassing this app's auth entirely.
        #
        # This app connects via DATABASE_URL as the `postgres` role (see
        # get_connection() above), not through PostgREST — and Postgres RLS
        # never applies to the table owner/superuser regardless of policies.
        # So enabling RLS here has zero effect on this app; it only closes
        # the separate, unused PostgREST attack surface. Also mirrored as a
        # standalone script at migrations/enable_rls.sql for running
        # directly in the Supabase SQL Editor against an existing database
        # (this block only helps on the NEXT fresh `init_db()` run, e.g. a
        # new environment or a teammate's local setup).
        for table in (
            "users", "password_reset_tokens", "meetings", "meeting_summaries",
            "action_items", "decisions", "topics", "meeting_health",
            "meeting_quotes", "meeting_titles", "meeting_diarization",
            "meeting_sentiment", "workspaces", "workspace_meetings",
            "workspace_members", "webhook_endpoints", "webhook_events",
            "audit_logs",
        ):
            cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        logger.info("✓ Database tables and indexes verified / created")

def get_analytics_data(user_id: int) -> dict:
    """
    Single query that returns everything the Analytics page needs.
    Replaces the old N+1 loop (getMeetings + getMeetingIntelligence per meeting).

    Returns:
      - total counts (meetings, decisions, actions, topics)
      - weekly_trend: meetings per day for last 30 days
      - task_status_breakdown: open/in_progress/done counts
      - top_topics: most frequent topic titles across all meetings
      - health_trend: health scores over time (last 10 meetings)
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1 — totals (reuses same pattern as get_user_stats)
        cur.execute("""
            SELECT
                COUNT(DISTINCT m.id)  AS total_meetings,
                COUNT(DISTINCT d.id)  AS total_decisions,
                COUNT(DISTINCT ai.id) AS total_actions,
                COUNT(DISTINCT t.id)  AS total_topics
            FROM meetings m
            LEFT JOIN decisions    d  ON d.meeting_id  = m.id
            LEFT JOIN action_items ai ON ai.meeting_id = m.id
            LEFT JOIN topics       t  ON t.meeting_id  = m.id
            WHERE m.user_id = %s
        """, (user_id,))
        totals = dict(cur.fetchone() or {})

        # 2 — meetings per day for last 30 days
        cur.execute("""
            SELECT
                DATE(created_at)::text AS day,
                COUNT(*)               AS count
            FROM meetings
            WHERE user_id = %s
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY day ASC
        """, (user_id,))
        weekly_trend = [dict(r) for r in cur.fetchall()]

        # 3 — task status breakdown
        cur.execute("""
            SELECT ai.status, COUNT(*) AS count
            FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            WHERE m.user_id = %s
            GROUP BY ai.status
        """, (user_id,))
        task_rows = cur.fetchall()
        task_status = {r['status']: r['count'] for r in task_rows}

        # 4 — top 8 topics by frequency
        cur.execute("""
            SELECT t.title, COUNT(*) AS count
            FROM topics t
            JOIN meetings m ON m.id = t.meeting_id
            WHERE m.user_id = %s
            GROUP BY t.title
            ORDER BY count DESC
            LIMIT 8
        """, (user_id,))
        top_topics = [dict(r) for r in cur.fetchall()]

        # 5 — health score trend (last 10 meetings that have health data)
        cur.execute("""
            SELECT
                m.filename,
                DATE(m.created_at)::text AS day,
                mh.overall_score
            FROM meeting_health mh
            JOIN meetings m ON m.id = mh.meeting_id
            WHERE m.user_id = %s
            ORDER BY m.created_at DESC
            LIMIT 10
        """, (user_id,))
        health_trend = [dict(r) for r in reversed(cur.fetchall())]

        # 6 — PHASE 2: commitment reliability per person (headline feature).
        # Extracted into its own function (see get_commitment_reliability
        # below) so a lightweight dashboard widget can call it directly
        # without paying for the other 5 queries in this function.
        commitment_reliability = get_commitment_reliability(user_id, _cur=cur)

    return {
        "totals":       totals,
        "weekly_trend": weekly_trend,
        "task_status":  task_status,
        "top_topics":   top_topics,
        "health_trend": health_trend,
        "commitment_reliability": commitment_reliability,
    }


def get_commitment_reliability(user_id: int, _cur=None) -> list[dict]:
    """
    PHASE 2 — headline differentiator feature.

    Computes, per person, whether they follow through on commitments ON
    TIME across every meeting they've been assigned an action item in —
    not just whether it eventually got done.

    Definitions (see core/deadline_parser.py for how due_date is populated):
      done_on_time — marked done, and either no due_date was parseable
                     or it was completed on/before that date
      done_late    — marked done, but after its due_date had passed
      missed       — still open/in_progress and due_date has passed
      open_not_due — still open/in_progress but not yet due (or no
                     due_date at all) — excluded from reliability math
                     entirely, since nothing has been resolved yet

    reliability_pct = done_on_time / (done_on_time + done_late + missed)
    Only counts RESOLVED commitments — an item that's simply still
    pending doesn't count for or against anyone yet.

    Owners are grouped case-insensitively (LOWER(TRIM(...))) since the LLM
    extracts names as spoken — "Pankaj" vs "pankaj" vs " Pankaj " would
    otherwise be treated as different people. The most recently used
    casing is kept for display via array_agg ordered by meeting date.

    Args:
        _cur: internal — lets get_analytics_data reuse an open cursor
              instead of opening a second connection. Callers outside
              this module should never pass this.
    """
    owns_connection = _cur is None
    conn = get_connection() if owns_connection else None
    try:
        cur = _cur if _cur is not None else conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT
                (array_agg(ai.owner ORDER BY m.created_at DESC))[1] AS owner,
                COUNT(*) FILTER (
                    WHERE ai.status = 'done'
                      AND (ai.due_date IS NULL OR ai.completed_at IS NULL
                           OR ai.completed_at::date <= ai.due_date)
                ) AS done_on_time,
                COUNT(*) FILTER (
                    WHERE ai.status = 'done'
                      AND ai.due_date IS NOT NULL AND ai.completed_at IS NOT NULL
                      AND ai.completed_at::date > ai.due_date
                ) AS done_late,
                COUNT(*) FILTER (
                    WHERE ai.status IN ('open', 'in_progress')
                      AND ai.due_date IS NOT NULL AND ai.due_date < CURRENT_DATE
                ) AS missed,
                COUNT(*) FILTER (
                    WHERE ai.status IN ('open', 'in_progress')
                      AND (ai.due_date IS NULL OR ai.due_date >= CURRENT_DATE)
                ) AS open_not_due,
                COUNT(*) AS total,
                MAX(m.created_at) AS last_commitment_at
            FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            WHERE m.user_id = %s
              AND ai.owner IS NOT NULL AND TRIM(ai.owner) != ''
            GROUP BY LOWER(TRIM(ai.owner))
            ORDER BY total DESC
        """, (user_id,))

        results = []
        for r in cur.fetchall():
            done_on_time = r["done_on_time"]
            done_late    = r["done_late"]
            missed       = r["missed"]
            resolved = done_on_time + done_late + missed
            results.append({
                "owner":              r["owner"],
                "reliability_pct":    round(done_on_time / resolved * 100) if resolved > 0 else None,
                "done_on_time":       done_on_time,
                "done_late":          done_late,
                "missed":             missed,
                "open_not_due":       r["open_not_due"],
                "resolved_count":     resolved,
                "total_commitments":  r["total"],
                # Below this, a single miss/hit swings the percentage
                # wildly — surface that instead of a misleadingly precise number.
                "has_enough_data":    resolved >= 3,
                "last_commitment_at": r["last_commitment_at"].isoformat() if r["last_commitment_at"] else None,
            })
        return results
    finally:
        if owns_connection and conn is not None:
            conn.close()


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


def get_meetings_page(
    user_id: int,
    limit:   int = 20,
    cursor:  int = None,
) -> dict:
    """
    FIX: Paginated meetings list — returns one page at a time.

    How cursor-based pagination works:
      First call:  cursor=None  → returns first 20 meetings (newest first)
      Next call:   cursor=42    → returns next 20 meetings with id < 42
      And so on until has_more=False

    Why cursor (id) instead of OFFSET?
      OFFSET skips rows by counting from the start every time.
      With 1000 meetings, "page 50" = scan and skip 980 rows = slow.
      Cursor uses the index on id — always fast, any page.

    Returns:
      {
        "items":    [...],   list of meeting dicts
        "has_more": True,    whether more pages exist
        "next_cursor": 38,   pass this as cursor on next call (None if last page)
      }
    """
    # Fetch limit+1 rows — if we get limit+1 back, there IS a next page.
    # We only return limit rows to the user but use the extra one to know
    # whether has_more should be True.
    fetch_count = limit + 1

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if cursor is not None:
            # cursor = id of the last item we already showed the user
            # "give me meetings older than that id"
            cur.execute(
                """
                SELECT id, filename, created_at, duration_seconds
                FROM   meetings
                WHERE  user_id = %s
                  AND  id < %s
                ORDER  BY id DESC
                LIMIT  %s
                """,
                (user_id, cursor, fetch_count),
            )
        else:
            # First page — no cursor yet
            cur.execute(
                """
                SELECT id, filename, created_at, duration_seconds
                FROM   meetings
                WHERE  user_id = %s
                ORDER  BY id DESC
                LIMIT  %s
                """,
                (user_id, fetch_count),
            )
        rows = [dict(r) for r in cur.fetchall()]

    has_more = len(rows) == fetch_count
    items    = rows[:limit]           # trim the extra probe row
    next_cursor = items[-1]["id"] if has_more and items else None

    return {
        "items":       items,
        "has_more":    has_more,
        "next_cursor": next_cursor,
        "count":       len(items),
    }


def get_tasks_page(
    user_id:  int,
    limit:    int = 20,
    cursor:   int = None,
    status:   str = None,
    priority: str = None,
    owner:    str = None,
) -> dict:
    """
    FIX: Paginated tasks list with optional filters.

    Same cursor-based approach as get_meetings_page.
    Tasks are joined to meetings to enforce user ownership —
    a user can only see tasks from their own meetings.
    """
    fetch_count = limit + 1
    conditions  = ["m.user_id = %s"]
    params      = [user_id]

    if cursor is not None:
        conditions.append("ai.id < %s")
        params.append(cursor)
    if status:
        status = status.lower()
        if status == "overdue":
            # PHASE 2: 'overdue' is never actually stored in ai.status
            # (see display_status below) — it's derived from due_date at
            # read time, so filtering on it needs the same condition.
            conditions.append(
                "(ai.status IN ('open', 'in_progress') AND ai.due_date IS NOT NULL AND ai.due_date < CURRENT_DATE)"
            )
        else:
            conditions.append("ai.status = %s")
            params.append(status)
    if priority:
        conditions.append("ai.priority = %s")
        params.append(priority.lower())
    if owner:
        conditions.append("ai.owner ILIKE %s")
        params.append(f"%{owner}%")

    where = " AND ".join(conditions)
    params.append(fetch_count)

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            f"""
            SELECT ai.id, ai.task, ai.status, ai.owner,
                   ai.deadline, ai.priority, ai.meeting_id, ai.due_date,
                   m.filename AS meeting_filename,
                   -- PHASE 2: overdue is DERIVED here, not a status you have
                   -- to remember to set by hand. An item shows as overdue
                   -- the moment its due_date passes while still open/in
                   -- progress — no cron job, no manual step, always correct
                   -- at read time.
                   CASE
                       WHEN ai.status IN ('open', 'in_progress')
                            AND ai.due_date IS NOT NULL
                            AND ai.due_date < CURRENT_DATE
                       THEN 'overdue'
                       ELSE ai.status
                   END AS display_status
            FROM   action_items ai
            JOIN   meetings     m ON m.id = ai.meeting_id
            WHERE  {where}
            ORDER  BY ai.id DESC
            LIMIT  %s
            """,
            params,
        )
        rows = [dict(r) for r in cur.fetchall()]

    has_more    = len(rows) == fetch_count
    items       = rows[:limit]
    next_cursor = items[-1]["id"] if has_more and items else None

    return {
        "items":       items,
        "has_more":    has_more,
        "next_cursor": next_cursor,
        "count":       len(items),
    }


def get_user_stats(user_id: int) -> dict:
    """
    FIX: Returns dashboard stats for a user in ONE database query.

    Old approach in get_stats() endpoint:
        meetings = get_all_transcripts(user_id)     # query 1
        for meeting in meetings:                    # loop
            intel = get_meeting_intelligence(id)    # query per meeting!
        # 50 meetings = 51 queries. 200 meetings = 201 queries.

    New approach — one SQL query with JOINs and COUNT():
        The database counts everything in one pass.
        50 meetings = 1 query. 10,000 meetings = still 1 query.

    How it works:
        LEFT JOIN means: include the meeting even if it has no decisions/actions/topics.
        COUNT(DISTINCT d.id) counts unique decision rows joined to this user's meetings.
        DISTINCT is needed because JOINing multiple tables can create duplicate rows.
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT
                COUNT(DISTINCT m.id)            AS total_meetings,
                COUNT(DISTINCT d.id)            AS total_decisions,
                COUNT(DISTINCT ai.id)           AS total_actions,
                COUNT(DISTINCT t.id)            AS total_topics
            FROM meetings m
            LEFT JOIN decisions    d  ON d.meeting_id  = m.id
            LEFT JOIN action_items ai ON ai.meeting_id = m.id
            LEFT JOIN topics       t  ON t.meeting_id  = m.id
            WHERE m.user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return {
        "total_meetings":  int(row["total_meetings"]  or 0),
        "total_decisions": int(row["total_decisions"] or 0),
        "total_actions":   int(row["total_actions"]   or 0),
        "total_topics":    int(row["total_topics"]    or 0),
    }


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
    """
    Fetch all meetings for RAG indexing.

    FIX: this previously did NOT select `user_id` at all — every caller
    that reindexes meetings (POST /rag/reindex and the reindex job) reads
    `m.get("user_id")` expecting it to be here, got None every time, and
    that None became a `user_id: 0` ("unknown owner") tag on every chunk
    in ChromaDB. That's the root cause of why user-scoped chat filtering
    had to special-case user_id=0 as legacy data — the reindex path meant
    to populate it correctly was never actually doing so. Fixed here so
    reindexing now correctly restores real ownership on every chunk.
    """
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id is not None:
            cur.execute(
                "SELECT id, filename, transcript, created_at, user_id FROM meetings WHERE user_id = %s ORDER BY id ASC",
                (user_id,),
            )
        else:
            cur.execute("SELECT id, filename, transcript, created_at, user_id FROM meetings ORDER BY id ASC")
        rows = cur.fetchall()
        return [dict(r) for r in rows if r["transcript"]]


# FIX: There was previously no way to delete a single meeting anywhere in
# the app — not in the API, not in the frontend. The only option was to
# delete the row directly in Supabase, which:
#   1. Leaves every derived-intelligence row (summaries, action items,
#      decisions, topics, health score, quotes, title, diarization) behind
#      as an orphan, since none of those tables cascade on `meetings`
#      deletion except workspace_meetings and meeting_sentiment.
#   2. Never touches ChromaDB at all — Chroma is a completely separate
#      datastore from Postgres, so a Supabase-side delete can't cascade
#      into it. The meeting's transcript chunks stay indexed forever,
#      under the same meeting_id.
#   3. Since Postgres's own id sequence eventually gets reused if the table
#      is ever truncated/reseeded, a *future* meeting can be assigned that
#      same id — and its chat will then silently retrieve the old deleted
#      meeting's orphaned chunks alongside its own, because ChromaDB has no
#      way to know the old meeting_id's owner changed.
#
# This function handles the Postgres side correctly (all child tables,
# in one transaction). The caller (DELETE /meetings/{id} in main.py) is
# responsible for also purging ChromaDB via delete_meeting_index() and
# clearing the BM25 cache via invalidate_meeting_cache() — this module
# doesn't import from core.rag to avoid a circular/heavy dependency.
def delete_meeting(meeting_id: int, user_id: int) -> bool:
    """
    Permanently delete a meeting and everything derived from it in Postgres.

    Returns False (and deletes nothing) if the meeting doesn't exist or
    isn't owned by user_id — never reveals whether an id exists to a
    non-owner.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM meetings WHERE id = %s AND user_id = %s",
            (meeting_id, user_id),
        )
        if cur.fetchone() is None:
            return False

        # These tables reference meetings(id) WITHOUT on delete cascade,
        # so they must be cleared explicitly or the final DELETE below
        # would fail with a foreign-key violation.
        for table in (
            "meeting_summaries", "action_items", "decisions", "topics",
            "meeting_health", "meeting_quotes", "meeting_titles",
            "meeting_diarization",
        ):
            cur.execute(f"DELETE FROM {table} WHERE meeting_id = %s", (meeting_id,))

        # workspace_meetings and meeting_sentiment DO cascade automatically.
        cur.execute("DELETE FROM meetings WHERE id = %s", (meeting_id,))
        return True


def get_all_meeting_ids() -> list[int]:
    """
    Every meeting id currently in Postgres, across ALL users.

    Used exclusively for reconciling ChromaDB against Postgres (see
    core.rag.indexer.find_orphaned_meeting_ids). Meeting ids are globally
    unique (a single SERIAL sequence, not per-user), so "does this id
    exist at all" is the same question regardless of which user is asking
    — there's no per-user narrowing to do here. No meeting content is
    read or returned, just bare ids.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM meetings")
        return [row[0] for row in cur.fetchall()]


def get_meeting_owner_map() -> dict[int, int]:
    """
    { meeting_id: user_id } for every meeting in Postgres.

    Used to backfill ChromaDB chunks that were indexed before user_id was
    reliably threaded through the indexing pipeline (see the FIX notes on
    get_all_meetings_for_indexing and the two index_meeting() call sites
    in main.py that used to omit user_id entirely). Those chunks are
    tagged `user_id: 0`; this map lets us look up their real owner by
    meeting_id and correct the tag in place. Like get_all_meeting_ids(),
    this is bare ids only — no meeting content.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, user_id FROM meetings")
        return {row[0]: row[1] for row in cur.fetchall()}


# =============================================================================
# INTELLIGENCE
# =============================================================================

def save_meeting_intelligence(meeting_id: int, intelligence) -> None:
    """
    Saves a MeetingIntelligence Pydantic object to all four intelligence tables.
    Identical interface to the SQLite version — main.py doesn't change.
    """
    from server.core.deadline_parser import parse_deadline

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO meeting_summaries (meeting_id, summary, generated_at) VALUES (%s, %s, %s)",
            (meeting_id, intelligence.summary, intelligence.generated_at),
        )

        # Need the meeting's own date to anchor relative deadlines
        # ("next Friday" means next Friday relative to when it was SAID).
        cur.execute("SELECT created_at FROM meetings WHERE id = %s", (meeting_id,))
        row = cur.fetchone()
        meeting_date = row[0].date() if row and row[0] else None

        for item in intelligence.action_items:
            # PHASE 2: parse the freeform deadline into an actual date.
            # Best-effort — a parse failure must never block saving the
            # action item itself, it just means due_date stays NULL and
            # this item is excluded from overdue/reliability math.
            due_date = None
            try:
                due_date = parse_deadline(item.deadline, reference_date=meeting_date)
            except Exception as e:
                logger.warning("Deadline parse failed for %r: %s", item.deadline, e)

            cur.execute(
                """
                INSERT INTO action_items (meeting_id, task, owner, deadline, priority, due_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (meeting_id, item.task, item.owner, item.deadline, item.priority, due_date),
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
        # FIX: Use RealDictCursor so rows come back as dicts {col_name: value}
        # instead of tuples (value at position 0, 1, 2...).
        #
        # Old (fragile):  row[2], row[3], row[4]...
        #   If any column is ever added or reordered, all position numbers
        #   shift silently — returns WRONG DATA with no error or warning.
        #
        # New (safe):  row["overall_score"], row["participation"]...
        #   Column names never change meaning. Self-documenting. Safe forever.
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM meeting_health WHERE meeting_id = %s", (meeting_id,))
        row = cur.fetchone()
    if not row:
        return None
    # FIX: named column access — replaces fragile row[2], row[3], row[4]...
    return {
        "overall_score":    row["overall_score"],
        "participation":    row["participation"],
        "decision_quality": row["decision_quality"],
        "action_clarity":   row["action_clarity"],
        "followup_risk":    row["followup_risk"],
        "highlights":       row["highlights"],
        "concerns":         row["concerns"],
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

        # PHASE 2: stamp completed_at when marking done, so we can later
        # tell "done on time" apart from "done late" (see
        # get_commitment_reliability). Clear it if the item is reopened —
        # otherwise reopening and re-completing later would keep the
        # original timestamp and silently corrupt the reliability score.
        if status == "done":
            cur.execute(
                "UPDATE action_items SET status = %s, completed_at = NOW() WHERE id = %s",
                (status, item_id),
            )
        else:
            cur.execute(
                "UPDATE action_items SET status = %s, completed_at = NULL WHERE id = %s",
                (status, item_id),
            )
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

    # PHASE 2: keep completed_at in sync whenever status is patched here too
    # (not just via the dedicated /status endpoint) — see
    # update_action_item_status for why this matters for reliability scoring.
    if "status" in fields:
        fields["completed_at"] = "NOW()" if fields["status"] == "done" else None

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT ai.id, m.created_at FROM action_items ai JOIN meetings m ON m.id = ai.meeting_id WHERE ai.id = %s AND m.user_id = %s",
            (item_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return False

        # PHASE 2: if the deadline text is being edited, re-parse due_date
        # too, anchored to this item's own meeting date — otherwise editing
        # "next Friday" to "next Monday" would silently leave the OLD
        # parsed due_date in place and corrupt overdue/reliability math.
        if "deadline" in fields:
            from server.core.deadline_parser import parse_deadline
            meeting_date = row[1].date() if row[1] else None
            fields["due_date"] = parse_deadline(fields["deadline"], reference_date=meeting_date)

        set_parts = []
        values = []
        for col, val in fields.items():
            if col == "completed_at" and val == "NOW()":
                set_parts.append("completed_at = NOW()")
            else:
                set_parts.append(f"{col} = %s")
                values.append(val)
        values.append(item_id)
        cur.execute(f"UPDATE action_items SET {', '.join(set_parts)} WHERE id = %s", values)
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
        # PHASE 2: 'overdue' derived from due_date, same logic as
        # get_tasks_page — this used to GROUP BY the raw status column,
        # but nothing ever actually set status='overdue', so the overdue
        # count was always silently zero.
        cur.execute(
            """
            SELECT
                CASE
                    WHEN ai.status IN ('open', 'in_progress')
                         AND ai.due_date IS NOT NULL
                         AND ai.due_date < CURRENT_DATE
                    THEN 'overdue'
                    ELSE ai.status
                END AS display_status,
                COUNT(*)
            FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            WHERE m.user_id = %s
            GROUP BY display_status
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
            color       TEXT                 DEFAULT '#10b981',
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
            color       TEXT    DEFAULT '#10b981',
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
    color:       str = "#10b981",
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
 
 # hello

    # PostgreSQL returns JSONB as a Python dict already — no json.loads needed
    result = row[0]
    if isinstance(result, str):
        result = json.loads(result)
    return result