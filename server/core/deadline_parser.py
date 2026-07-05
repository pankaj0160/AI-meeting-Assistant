# server/core/deadline_parser.py
"""
PHASE 2 — Commitment tracking, supporting piece.

WHY THIS EXISTS:
    action_items.deadline is free text extracted by the LLM from natural
    speech — "next Friday", "by EOD Monday", "in two weeks", "July 15".
    You can't compute "overdue" or "on time" from a string like that
    directly; you need an actual date to compare against today.

    This module converts that free text into a real `date`, anchored to
    the MEETING'S date (not today) — "next Friday" means next Friday
    relative to when it was said, not relative to whenever this function
    happens to run.

SCOPE / HONEST LIMITATIONS:
    This is a pragmatic heuristic parser tuned for how people actually
    phrase deadlines in meetings, not a general NLP date parser. It
    handles the common cases well (see PATTERNS below) and falls back to
    dateutil's fuzzy parser for absolute dates ("July 15", "2026-07-10").
    Genuinely ambiguous phrasing ("soon", "eventually", "when we can")
    correctly returns None rather than guessing — a missing due_date is
    safer than a wrong one, since a wrong one silently corrupts the
    reliability score this feeds into.

USAGE:
    from server.core.deadline_parser import parse_deadline
    due = parse_deadline("next Friday", reference_date=meeting_date)
"""

import re
import logging
from datetime import date, datetime, timedelta
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

_WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def _next_weekday(reference: date, target_weekday: int) -> date:
    """Next occurrence of target_weekday strictly after reference."""
    days_ahead = (target_weekday - reference.weekday()) % 7
    days_ahead = days_ahead or 7  # if it's the same day, jump a full week
    return reference + timedelta(days=days_ahead)


def parse_deadline(deadline_text: str | None, reference_date: date | None = None) -> date | None:
    """
    Parse a freeform deadline string into an actual date.

    Args:
        deadline_text:  e.g. "next Friday", "in 3 days", "2026-07-10", None
        reference_date: the date to interpret relative phrases against —
                         should be the MEETING's date, not today's date.
                         Defaults to today only if not provided (fallback
                         for callers that don't have a meeting date handy).

    Returns:
        A date, or None if the text is empty, "no deadline mentioned",
        or genuinely unparseable.
    """
    if not deadline_text or not deadline_text.strip():
        return None

    text = deadline_text.strip().lower()
    ref = reference_date or date.today()

    # Common "no real deadline" phrasings the LLM sometimes extracts —
    # returning None here is correct; there's nothing to parse.
    if text in {"none", "n/a", "na", "tbd", "no deadline", "not specified", "unspecified", "asap"}:
        # Note: "asap" deliberately excluded from date math — it means
        # "no fixed date", not "today". Treating it as a date would make
        # everything ASAP either always-overdue or arbitrarily due today.
        return None

    # ── Relative day phrases ────────────────────────────────────────────
    if "today" in text or "eod" == text or "end of day" in text:
        return ref
    if "tomorrow" in text:
        return ref + timedelta(days=1)

    # "end of week" / "eow" — defined as the coming Friday (business week).
    if "end of week" in text or re.search(r"\beow\b", text):
        return _next_weekday(ref, 4) if ref.weekday() != 4 else ref

    # "end of month" / "eom"
    if "end of month" in text or re.search(r"\beom\b", text):
        next_month = ref.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)

    # "in N days" / "in N day"
    m = re.search(r"in\s+(\d+)\s+day", text)
    if m:
        return ref + timedelta(days=int(m.group(1)))

    # "in N weeks"
    m = re.search(r"in\s+(\d+)\s+week", text)
    if m:
        return ref + timedelta(weeks=int(m.group(1)))

    if "next week" in text:
        return ref + timedelta(days=7)

    # "next <weekday>" / "this <weekday>" / bare "<weekday>"
    for name, wd in _WEEKDAYS.items():
        if re.search(rf"\b{name}\b", text):
            return _next_weekday(ref, wd)

    # ── Fallback: absolute dates via dateutil fuzzy parsing ─────────────
    # e.g. "July 15", "2026-07-10", "15th of July", "Jul 15th"
    try:
        parsed = dateutil_parser.parse(
            deadline_text,
            fuzzy=True,
            default=datetime.combine(ref, datetime.min.time()),
        )
        result = parsed.date()
        # Sanity guard: if the parsed date lands more than ~2 years from
        # the meeting, it's more likely a parsing artifact (dateutil
        # grabbing a stray number as a year) than a real deadline.
        if abs((result - ref).days) > 730:
            logger.debug("Discarding implausible parsed deadline %r -> %s", deadline_text, result)
            return None
        return result
    except (ValueError, OverflowError):
        logger.debug("Could not parse deadline text: %r", deadline_text)
        return None