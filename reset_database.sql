-- ============================================================
-- SUMMLY - Full Database Reset
-- Run in Supabase dashboard → SQL Editor → New query
-- Only truncates tables that actually exist in your schema.
-- ============================================================

-- Meetings and all related intelligence (safe order)
TRUNCATE TABLE meeting_sentiment    RESTART IDENTITY CASCADE;
TRUNCATE TABLE meeting_diarization  RESTART IDENTITY CASCADE;
TRUNCATE TABLE meeting_titles       RESTART IDENTITY CASCADE;
TRUNCATE TABLE meeting_quotes       RESTART IDENTITY CASCADE;
TRUNCATE TABLE meeting_health       RESTART IDENTITY CASCADE;
TRUNCATE TABLE topics               RESTART IDENTITY CASCADE;
TRUNCATE TABLE decisions            RESTART IDENTITY CASCADE;
TRUNCATE TABLE action_items         RESTART IDENTITY CASCADE;
TRUNCATE TABLE meeting_summaries    RESTART IDENTITY CASCADE;

-- Workspaces
TRUNCATE TABLE workspace_members    RESTART IDENTITY CASCADE;
TRUNCATE TABLE workspace_meetings   RESTART IDENTITY CASCADE;
TRUNCATE TABLE workspaces           RESTART IDENTITY CASCADE;

-- Webhooks (only if they exist — ignore error if not)
DO $$ BEGIN
    TRUNCATE TABLE webhook_events RESTART IDENTITY CASCADE;
EXCEPTION WHEN undefined_table THEN NULL; END $$;

DO $$ BEGIN
    TRUNCATE TABLE webhook_endpoints RESTART IDENTITY CASCADE;
EXCEPTION WHEN undefined_table THEN NULL; END $$;

DO $$ BEGIN
    TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE;
EXCEPTION WHEN undefined_table THEN NULL; END $$;

-- Meetings last (parent of everything above)
TRUNCATE TABLE meetings RESTART IDENTITY CASCADE;

-- Keep users — just remove their data
-- TRUNCATE TABLE users RESTART IDENTITY CASCADE;

-- Confirm all clear
SELECT 'meetings'          AS tbl, COUNT(*) AS rows FROM meetings
UNION ALL
SELECT 'action_items',              COUNT(*) FROM action_items
UNION ALL
SELECT 'meeting_summaries',         COUNT(*) FROM meeting_summaries
UNION ALL
SELECT 'workspaces',                COUNT(*) FROM workspaces;