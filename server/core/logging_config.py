# server/core/logging_config.py
#
# New file. Create it at this path.
# Call setup_logging() once in main.py before anything else runs.
#
# WHAT THIS FILE DOES:
#   Configures structlog to:
#   1. Add a timestamp to every log line
#   2. Add a unique request_id to every log line within a request
#      (so you can grep all logs from one specific request)
#   3. Output JSON in production (easy to search/filter)
#   4. Output pretty colored text in development (easy to read)

import logging
import logging.config
import os
import structlog


def setup_logging() -> None:
    """
    Configure structlog + Python standard logging.
    Call this at the very top of main.py, before app = FastAPI(...).

    After calling this:
        - All existing logger.info(), logger.error() calls keep working
        - They now output JSON instead of plain text (in production)
        - structlog.get_logger() gives you richer logging with key=value fields
    """

    # Are we in production or development?
    # Set LOG_LEVEL=DEBUG in .env for verbose output
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Are we running in a container / production environment?
    # JSON output is better for log aggregators (Datadog, Papertrail, etc.)
    # Pretty output is better for humans reading a terminal
    json_logs = os.getenv("JSON_LOGS", "false").lower() == "true"

    # ── Step 1: Configure Python's standard logging ───────────────────────────
    # structlog sits ON TOP of Python's standard logging.
    # We configure standard logging first, then tell structlog to use it.
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "format": "%(message)s",   # structlog handles formatting
            }
        },
        "handlers": {
            "console": {
                "class":     "logging.StreamHandler",
                "formatter": "plain",
                "stream":    "ext://sys.stdout",
            }
        },
        "root": {
            "level":    log_level_name,
            "handlers": ["console"],
        },
    })

    # ── Step 2: Configure structlog processors ────────────────────────────────
    # "Processors" are functions that transform a log event before output.
    # They run in order — each one gets the output of the previous.
    #
    # add_log_level         → adds "level": "info" to every event
    # add_logger_name       → adds "logger": "server.main" (which file logged it)
    # TimeStamper           → adds "timestamp": "2024-01-15T14:32:01Z"
    # StackInfoRenderer     → formats exception stack traces nicely
    # JSONRenderer/ConsoleRenderer → final output format

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: output compact JSON (one line per event)
        # {"timestamp": "...", "level": "info", "logger": "server.main",
        #  "event": "file_saved", "user_id": 5, "duration_ms": 134}
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: output colored, human-readable text
        # 2024-01-15 14:32:01 [info     ] file_saved  [server.main] user_id=5 duration_ms=134
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )