"""Structured logging setup.

Deliberately dependency-free (no structlog/python-json-logger) — a ~40-line
custom JSON formatter plus the standard library's `logging` module is enough
for this project's scale, per Phase 8's "not enterprise infrastructure" goal.

Every log record automatically carries the current request's id (via a
contextvar set by the request-ID middleware in app/main.py), so log lines
from anywhere in the call stack — a route, a service, a repository — can be
correlated to one HTTP request without threading a parameter through every
function signature.
"""

import contextvars
import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

# Standard LogRecord attributes — anything else set on a record (via `extra=`)
# is assumed to be a deliberately-attached structured field and gets included
# in the JSON output.
_STANDARD_LOG_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


def set_request_id(request_id: str | None) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_var.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _PlainFormatter(logging.Formatter):
    """Human-readable format for local development — a JSON blob per line is
    hard to scan in a terminal while actively developing."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None)
        prefix = f"[{request_id[:8]}] " if request_id else ""
        base = f"{record.levelname:<8} {record.name}: {prefix}{record.getMessage()}"
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_ATTRS and key != "request_id"
        }
        if extras:
            base += " | " + " ".join(f"{k}={v}" for k, v in extras.items())
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging(settings: Settings) -> None:
    """Called once at app startup (app/main.py). JSON output in production
    (machine-parseable by whatever log aggregator is in front of it); plain,
    readable output otherwise.
    """
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    if settings.environment == "production":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_PlainFormatter())

    root.handlers = [handler]

    # This library logs an informational "automatic function calling" notice
    # on every single Gemini call at INFO level, which would otherwise drown
    # out this project's own structured logs — see app/services/llm_service.py
    # for the equivalent, narrower suppression that predates this module.
    logging.getLogger("google_genai").setLevel(logging.WARNING)
