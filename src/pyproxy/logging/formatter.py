"""JSON log formatter using orjson for high-performance serialization.

Produces structured JSON log lines suitable for ingestion by log
aggregation systems (ELK, Datadog, Grafana Loki, etc.).
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime
from typing import Any

import orjson

from pyproxy.logging.context import get_correlation_id, get_request_id


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Each log line contains:
    - ``timestamp``: ISO 8601 UTC timestamp.
    - ``level``: Log level name (lowercase).
    - ``logger``: Logger name.
    - ``message``: The formatted log message.
    - ``request_id``: Request ID from contextvars (if set).
    - ``correlation_id``: Correlation ID from contextvars (if set).
    - Any extra fields attached to the log record.
    - ``exception``: Formatted traceback (if an exception is attached).

    Uses ``orjson`` for serialization — 3-10x faster than ``json.dumps()``.
    """

    # Fields that are part of the standard LogRecord and should not
    # appear as "extra" fields in the JSON output.
    _RESERVED_ATTRS: frozenset[str] = frozenset({
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    })

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string (no trailing newline).
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject context from contextvars
        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add source location for debug/error levels
        if record.levelno >= logging.WARNING:
            log_entry["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Extract extra fields (anything added via `extra={}` in the log call)
        for key, value in record.__dict__.items():
            if key not in self._RESERVED_ATTRS and key not in log_entry:
                log_entry[key] = value

        # Attach exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Stack info (for `stack_info=True` calls)
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info

        return orjson.dumps(
            log_entry,
            option=orjson.OPT_NON_STR_KEYS,
        ).decode("utf-8")


class TextFormatter(logging.Formatter):
    """Human-readable log formatter for development use.

    Produces colored, structured text output suitable for terminal viewing.
    Falls back gracefully when terminal does not support ANSI colors.
    """

    _LEVEL_COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as human-readable text.

        Args:
            record: The log record to format.

        Returns:
            A formatted text string with optional ANSI colors.
        """
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]

        color = self._LEVEL_COLORS.get(record.levelname, "")
        reset = self._RESET if color else ""

        parts = [
            f"{timestamp}",
            f"{color}{record.levelname:>8}{reset}",
            f"[{record.name}]",
            record.getMessage(),
        ]

        request_id = get_request_id()
        if request_id:
            parts.insert(3, f"req={request_id[:8]}")

        message = " ".join(parts)

        if record.exc_info and record.exc_info[0] is not None:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return message
