"""Structured access log entries.

Provides the :class:`AccessLogger` that emits structured access log entries
for each proxied request. Each entry includes method, path, status code,
duration, bytes transferred, and client IP.

The actual population of these fields happens in Phase 3+ when the HTTP
parser and response builder are implemented.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from pyproxy.logging.context import get_correlation_id, get_request_id

_access_logger = logging.getLogger("pyproxy.access")


@dataclass(slots=True)
class AccessLogEntry:
    """Represents a single access log entry.

    Populated progressively as a request flows through the proxy pipeline:
    1. ``client_ip``, ``method``, ``path`` — set when request is parsed.
    2. ``status_code``, ``bytes_sent`` — set when response is sent.
    3. ``duration_ms`` — computed at log emission time.

    Attributes:
        client_ip: The client's IP address.
        method: The HTTP method (GET, POST, etc.).
        path: The request path.
        status_code: The response status code.
        bytes_sent: Number of bytes sent to the client.
        upstream_host: The upstream server that handled the request.
        upstream_port: The upstream server port.
        user_agent: The client's User-Agent header.
        referer: The Referer header.
        protocol: The HTTP protocol version (e.g., "HTTP/1.1").
        start_time_ns: Monotonic nanosecond timestamp when the request started.
        extra: Additional key-value pairs to include in the log entry.
    """

    client_ip: str = ""
    method: str = ""
    path: str = ""
    status_code: int = 0
    bytes_sent: int = 0
    upstream_host: str = ""
    upstream_port: int = 0
    user_agent: str = ""
    referer: str = ""
    protocol: str = "HTTP/1.1"
    start_time_ns: int = field(default_factory=time.monotonic_ns)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Calculate the request duration in milliseconds.

        Returns:
            Duration from ``start_time_ns`` to now, in milliseconds.
        """
        elapsed_ns = time.monotonic_ns() - self.start_time_ns
        return elapsed_ns / 1_000_000


class AccessLogger:
    """Emits structured access log entries.

    Delegates to Python's stdlib ``logging`` module under the
    ``pyproxy.access`` logger. Each entry is emitted as an INFO-level
    log with structured extra fields.

    Example::

        access_logger = AccessLogger()
        entry = AccessLogEntry(
            client_ip="192.168.1.1",
            method="GET",
            path="/api/v1/health",
            status_code=200,
            bytes_sent=42,
        )
        access_logger.log(entry)
    """

    def log(self, entry: AccessLogEntry) -> None:
        """Emit an access log entry.

        The entry is serialized as structured data (via the extra dict)
        so that the JSON formatter can include all fields in the JSON output.

        Args:
            entry: The access log entry to emit.
        """
        extra: dict[str, Any] = {
            "client_ip": entry.client_ip,
            "method": entry.method,
            "path": entry.path,
            "status_code": entry.status_code,
            "bytes_sent": entry.bytes_sent,
            "duration_ms": round(entry.duration_ms, 3),
            "protocol": entry.protocol,
        }

        # Add optional fields only if populated
        if entry.upstream_host:
            extra["upstream"] = f"{entry.upstream_host}:{entry.upstream_port}"
        if entry.user_agent:
            extra["user_agent"] = entry.user_agent
        if entry.referer:
            extra["referer"] = entry.referer

        # Include request context
        request_id = get_request_id()
        if request_id:
            extra["request_id"] = request_id
        correlation_id = get_correlation_id()
        if correlation_id:
            extra["correlation_id"] = correlation_id

        # Merge any extra fields
        extra.update(entry.extra)

        _access_logger.info(
            '%s %s %s %d %d %.3fms',
            entry.client_ip,
            entry.method,
            entry.path,
            entry.status_code,
            entry.bytes_sent,
            entry.duration_ms,
            extra=extra,
        )
