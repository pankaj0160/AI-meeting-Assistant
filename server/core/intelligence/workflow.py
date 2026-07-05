# server/core/intelligence/workflow.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# After Whisper produces the transcript, this file runs 4 AI agents
# to extract intelligence from it:
#
#   Agent 1 — Summary:      "3-5 sentence executive summary of the meeting"
#   Agent 2 — Action Items: "who needs to do what by when"
#   Agent 3 — Decisions:    "what the team agreed to do"
#   Agent 4 — Topics:       "main themes discussed"
#
# All 4 agents call Groq's LLM API — each call is independent.
# They can run at the same time (in parallel) instead of one after another.
#
# SEQUENTIAL (old approach):
#   Summary → wait → Action Items → wait → Decisions → wait → Topics
#   Total: ~15s + ~12s + ~10s + ~8s = ~45 seconds
#
# PARALLEL (current approach with ThreadPoolExecutor):
#   Summary ─┐
#   Actions  ─┤ all fire at the same time
#   Decisions─┤
#   Topics   ─┘
#   Total: max(~15s, ~12s, ~10s, ~8s) = ~15 seconds (limited by slowest agent)
#
# HOW THREADPOOLEXECUTOR WORKS:
#   A "thread pool" is a group of threads kept ready to do work.
#   We create a pool of 4 threads (one per agent).
#   submit(fn, arg) puts the function in the queue and a thread picks it up.
#   result() waits for that future to complete and returns the value.
#
# PRODUCTION FIX IN THIS FILE:
# ─────────────────────────────
# FIX: Per-call executor instead of module-level global.
#
# OLD: _EXECUTOR = ThreadPoolExecutor(max_workers=4) at module level.
# PROBLEM: This is a SHARED global. Under high load:
#   User A uploads → submits 4 futures to the pool (fills all 4 workers)
#   User B uploads → submits 4 futures → they WAIT because the pool is full
#   User C uploads → queued behind B
#   Result: Users B and C are blocked by User A's processing.
#
# FIX: Create a fresh ThreadPoolExecutor per analyze_transcript() call.
#   Each upload gets its own 4-thread pool for the 0.15 seconds it needs.
#   The pool is immediately shut down (shutdown(wait=True)) after all 4
#   futures complete — no threads linger, no resource leaks.
#
# TRADEOFF:
#   Creating a ThreadPoolExecutor has ~1ms overhead.
#   vs saving ~30 seconds when multiple users upload simultaneously.
#   Clearly worth it.
#
# WHY NOT asyncio.gather?
#   Groq's Python SDK is synchronous — it uses blocking httpx.
#   asyncio.gather only parallelises async functions.
#   For synchronous blocking calls, ThreadPoolExecutor is the correct tool.
#   (asyncio.to_thread wraps sync functions in threads anyway — we just
#   do it directly here for finer control.)

import logging
import concurrent.futures
from datetime import datetime, timezone

from server.core.intelligence.agents import (
    run_summary_agent,
    run_action_item_agent,
    run_decision_agent,
    run_topic_agent,
)
from server.core.intelligence.schemas import MeetingIntelligence

logger = logging.getLogger(__name__)

# Minimum transcript length to bother analysing.
# Very short transcripts (< 50 chars) produce meaningless intelligence.
# Example: a 5-second test recording transcribed as "hello test okay" —
# no point calling 4 LLM agents for that.
MIN_TRANSCRIPT_CHARS = 50


# =============================================================================
# SAFE AGENT WRAPPERS
# =============================================================================
# These wrapper functions call each agent and catch any exception.
# If one agent fails (e.g. Groq timeout on that call), the others
# still complete and we return a partial result instead of failing entirely.
#
# The user gets 3/4 pieces of intelligence instead of nothing.
# The error is logged with full traceback for debugging.

def _safe_summary(transcript: str) -> str:
    try:
        result = run_summary_agent(transcript)
        logger.info("Summary agent complete (%d chars)", len(result))
        return result
    except Exception as e:
        logger.error("Summary agent failed: %s", e, exc_info=True)
        return "Summary unavailable — AI analysis encountered an error. Please try regenerating."


def _safe_action_items(transcript: str) -> list:
    try:
        items = run_action_item_agent(transcript)
        logger.info("Action items agent complete: %d items", len(items))
        return items
    except Exception as e:
        logger.error("Action items agent failed: %s", e, exc_info=True)
        return []


def _safe_decisions(transcript: str) -> list:
    try:
        decisions = run_decision_agent(transcript)
        logger.info("Decisions agent complete: %d decisions", len(decisions))
        return decisions
    except Exception as e:
        logger.error("Decisions agent failed: %s", e, exc_info=True)
        return []


def _safe_topics(transcript: str) -> list:
    try:
        topics = run_topic_agent(transcript)
        logger.info("Topics agent complete: %d topics", len(topics))
        return topics
    except Exception as e:
        logger.error("Topics agent failed: %s", e, exc_info=True)
        return []


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def analyze_transcript(transcript: str) -> MeetingIntelligence:
    """
    Run all 4 intelligence agents in parallel and return a MeetingIntelligence.

    This is called by:
      - tasks.py  (Celery background worker — for async uploads)
      - main.py   (FastAPI endpoint — for sync /upload)

    Both paths benefit from parallel execution.

    Args:
        transcript: full meeting transcript text

    Returns:
        MeetingIntelligence Pydantic object with:
            summary      : str
            action_items : list[ActionItem]
            decisions    : list[Decision]
            topics       : list[Topic]
            generated_at : str (ISO timestamp)

    Never raises an exception — each agent has its own error handler.
    Always returns a result, even if all agents fail.
    """
    if not transcript or len(transcript.strip()) < MIN_TRANSCRIPT_CHARS:
        logger.warning(
            "Transcript too short to analyse (%d chars) — returning empty intelligence",
            len(transcript.strip()) if transcript else 0,
        )
        return MeetingIntelligence(
            summary      = "Transcript too short to generate intelligence.",
            action_items = [],
            decisions    = [],
            topics       = [],
            generated_at = datetime.now(timezone.utc).isoformat(),
        )

    start_time = __import__("time").perf_counter()
    logger.info(
        "Starting parallel intelligence analysis (%d chars, %d words)",
        len(transcript),
        len(transcript.split()),
    )

    # FIX: Create a fresh executor per call — no shared state between users.
    #
    # max_workers=4: one thread per agent. Groq is the bottleneck, not CPU.
    # More workers wouldn't help because each thread is waiting for a network
    # response from Groq's API, not doing CPU work.
    #
    # with ... as executor ensures the pool is always shut down cleanly,
    # even if an exception occurs inside the block. No thread leaks.
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=4,
        thread_name_prefix="intel",
    ) as executor:
        # Submit all 4 agents simultaneously — they all start right now
        f_summary      = executor.submit(_safe_summary,      transcript)
        f_action_items = executor.submit(_safe_action_items, transcript)
        f_decisions    = executor.submit(_safe_decisions,    transcript)
        f_topics       = executor.submit(_safe_topics,       transcript)

        # .result() blocks until that specific future completes.
        # All 4 are running in parallel — this is just collecting results.
        # Total wait time = max(time for each agent), not sum.
        summary      = f_summary.result()
        action_items = f_action_items.result()
        decisions    = f_decisions.result()
        topics       = f_topics.result()

    elapsed = round(__import__("time").perf_counter() - start_time, 2)
    logger.info(
        "Parallel intelligence complete in %.2fs: "
        "summary=%s, actions=%d, decisions=%d, topics=%d",
        elapsed,
        "yes" if summary and "unavailable" not in summary else "fallback",
        len(action_items),
        len(decisions),
        len(topics),
    )

    return MeetingIntelligence(
        summary      = summary,
        action_items = action_items,
        decisions    = decisions,
        topics       = topics,
        generated_at = datetime.now(timezone.utc).isoformat(),
    )