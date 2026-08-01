"""Structured logging for PyProxy.

Provides JSON-formatted structured logging with context-aware request
and correlation ID injection via ``contextvars``.

Example::

    from pyproxy.logging import setup_logging, get_logger, RequestContext
    from pyproxy.config import LoggingConfig

    setup_logging(LoggingConfig(level="info", format="json"))
    logger = get_logger("my_module")

    async with RequestContext(request_id="req-123"):
        logger.info("Processing request")  # Includes request_id in JSON
"""

from __future__ import annotations

from pyproxy.logging.access import AccessLogEntry, AccessLogger
from pyproxy.logging.context import (
    RequestContext,
    get_correlation_id,
    get_request_id,
    set_correlation_id,
    set_request_id,
)
from pyproxy.logging.setup import get_logger, setup_logging

__all__: list[str] = [
    "AccessLogEntry",
    "AccessLogger",
    "RequestContext",
    "get_correlation_id",
    "get_logger",
    "get_request_id",
    "set_correlation_id",
    "set_request_id",
    "setup_logging",
]
