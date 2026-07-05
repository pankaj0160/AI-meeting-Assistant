# server/core/logging_config.py
#
# WHAT THIS FILE DOES:
# ────────────────────
# Configures structured logging for the Summly backend.
#
# GRACEFUL DEGRADATION FIX:
# ──────────────────────────
# The old version imported structlog at module level.
# If structlog was not installed, the entire server failed to start.
# This is a startup blocker that has nothing to do with core functionality.
#
# New version: structlog is optional.
#   - If installed → rich structured JSON/console logging
#   - If not installed → standard Python logging (still works perfectly)
#
# To install structlog: pip install structlog==24.4.0
# It is listed in requirements.txt — just not always installed in dev envs.

import logging
import logging.config
import os


def setup_logging() -> None:
    """
    Configure logging. Works with or without structlog installed.
    Call once at the very top of main.py before app = FastAPI(...).
    """
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level      = getattr(logging, log_level_name, logging.INFO)
    json_logs      = os.getenv("JSON_LOGS", "false").lower() == "true"

    # ── Try structlog first ───────────────────────────────────────────────────
    try:
        import structlog

        logging.config.dictConfig({
            "version":                  1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {"format": "%(message)s"},
            },
            "handlers": {
                "console": {
                    "class":     "logging.StreamHandler",
                    "formatter": "plain",
                    "stream":    "ext://sys.stdout",
                },
            },
            "root": {
                "level":    log_level_name,
                "handlers": ["console"],
            },
        })

        shared = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
        ]

        processors = shared + (
            [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
            if json_logs
            else [structlog.dev.ConsoleRenderer(colors=True)]
        )

        structlog.configure(
            processors             = processors,
            wrapper_class          = structlog.stdlib.BoundLogger,
            context_class          = dict,
            logger_factory         = structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use = True,
        )

        logging.getLogger(__name__).info("structlog configured (json=%s)", json_logs)

    # ── Fallback: standard Python logging ────────────────────────────────────
    except ImportError:
        # structlog not installed — use standard logging with a clean format.
        # All logger.info() / logger.error() calls still work identically.
        fmt = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
        logging.basicConfig(
            level   = log_level,
            format  = fmt,
            datefmt = "%Y-%m-%dT%H:%M:%S",
        )
        logging.getLogger(__name__).info(
            "structlog not installed — using standard logging. "
            "Install it with: pip install structlog==24.4.0"
        )