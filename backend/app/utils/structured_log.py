"""Structured logging with structlog and per-job context."""

from __future__ import annotations

import contextvars
import logging
from typing import Any

import structlog

_log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "log_context", default={}
)


def bind_context(**kwargs: Any) -> None:
    """Merge keys into the current logging context."""
    current = dict(_log_context.get())
    current.update(kwargs)
    _log_context.set(current)


def clear_context() -> None:
    _log_context.set({})


def get_bound_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a logger with request/job context bound."""
    ctx = _log_context.get()
    logger = structlog.get_logger(name or "appcompiler")
    if ctx:
        return logger.bind(**ctx)
    return logger


def configure_structlog(level: str = "INFO") -> None:
    """Configure structlog to emit JSON alongside stdlib logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
