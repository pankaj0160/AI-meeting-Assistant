@echo off
title Summly — Full Reset
color 0C

echo.
echo  ==========================================
echo   SUMMLY - FULL DATA RESET
echo   This will delete ALL meetings, uploads,
echo   ChromaDB vectors, and temp files.
echo  ==========================================
echo.
echo  Press CTRL+C NOW to cancel.
echo  Press any key to continue with full reset...
pause >nul

cd /d C:\Projects\Summly

REM ── 1. Delete all uploaded audio/video files ─────────────────────────────────
echo.
echo  [1/4] Clearing uploads...
if exist "server\uploads\audio" (
    del /q "server\uploads\audio\*.*" 2>nul
    echo       Cleared uploads\audio
)
if exist "server\uploads\video" (
    del /q "server\uploads\video\*.*" 2>nul
    echo       Cleared uploads\video
)
if exist "server\uploads\transcripts" (
    del /q "server\uploads\transcripts\*.*" 2>nul
    echo       Cleared uploads\transcripts
)
if exist "uploads\audio" (
    del /q "uploads\audio\*.*" 2>nul
    echo       Cleared uploads\audio
)
if exist "uploads\video" (
    del /q "uploads\video\*.*" 2>nul
    echo       Cleared uploads\video
)

REM ── 2. Delete ChromaDB vector store ─────────────────────────────────────────
echo.
echo  [2/4] Clearing ChromaDB vector index...
if exist "chroma_db" (
    rmdir /s /q "chroma_db"
    echo       Cleared chroma_db
) else (
    echo       chroma_db not found, skipping
)

REM ── 3. Delete local SQLite file if it exists ─────────────────────────────────
echo.
echo  [3/4] Checking for local SQLite...
if exist "meetings.db" (
    del /q "meetings.db"
    echo       Deleted meetings.db
) else (
    echo       No meetings.db found (using Supabase - OK)
)

REM ── 4. Clear Python cache ─────────────────────────────────────────────────────
echo.
echo  [4/4] Clearing Python cache...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)
echo       Done

echo.
echo  ==========================================
echo   Local files cleared!
echo.
echo   IMPORTANT: Your Supabase database still
echo   has the old data. To clear it too, run
echo   the SQL commands shown below in your
echo   Supabase dashboard SQL editor.
echo  ==========================================
echo.
pause