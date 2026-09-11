"""Structured JSON logging via structlog.

Every log line carries at minimum `event`, `request_id`, `level` and an ISO
timestamp. Request identity (user_id, school_id) is bound per-request via
contextvars and merged by `merge_contextvars`.
"""
from __future__ import annotations

import logging
import sys

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[object] = [
        merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        renderer: object = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Silence noisy library loggers; our middleware emits the structured access
    # log, so uvicorn's own access log is redundant.
    logging.basicConfig(level=level, format="%(message)s")
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def bind_request(request_id: str, user_id: str | None = None, school_id: str | None = None) -> None:
    clear_contextvars()
    bind_contextvars(request_id=request_id)
    if user_id:
        bind_contextvars(user_id=user_id)
    if school_id:
        bind_contextvars(school_id=school_id)
