"""Protocol-related exceptions.

These exceptions are raised during HTTP parsing, WebSocket handling,
and TLS operations.
"""

from __future__ import annotations

from typing import Any

from pyproxy.exceptions.base import PyProxyError


class ProtocolError(PyProxyError):
    """Base exception for protocol-level errors."""

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "PROTOCOL_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a ProtocolError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code.
            context: Additional diagnostic key-value pairs.
        """
        super().__init__(detail, error_code=error_code, context=context)


class HttpParseError(ProtocolError):
    """Raised when an HTTP request or response cannot be parsed."""

    def __init__(self, cause: str, *, raw_data: bytes = b"") -> None:
        """Initialize an HttpParseError.

        Args:
            cause: Description of the parsing failure.
            raw_data: The raw bytes that failed to parse (truncated for safety).
        """
        # Truncate raw_data to prevent log flooding with large payloads
        truncated = raw_data[:256] if raw_data else b""
        super().__init__(
            f"HTTP parse error: {cause}",
            error_code="HTTP_PARSE_ERROR",
            context={"cause": cause, "raw_data_preview": repr(truncated)},
        )


class WebSocketError(ProtocolError):
    """Raised when a WebSocket protocol error occurs."""

    def __init__(self, cause: str, *, close_code: int = 1011) -> None:
        """Initialize a WebSocketError.

        Args:
            cause: Description of the WebSocket error.
            close_code: The WebSocket close status code.
        """
        super().__init__(
            f"WebSocket error: {cause}",
            error_code="WEBSOCKET_ERROR",
            context={"cause": cause, "close_code": close_code},
        )


class TlsError(ProtocolError):
    """Raised when a TLS handshake or certificate operation fails."""

    def __init__(self, cause: str) -> None:
        """Initialize a TlsError.

        Args:
            cause: Description of the TLS failure.
        """
        super().__init__(
            f"TLS error: {cause}",
            error_code="TLS_ERROR",
            context={"cause": cause},
        )
