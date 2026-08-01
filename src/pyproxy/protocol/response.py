"""HTTP Response data model and status code mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pyproxy.protocol.headers import Headers

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Standard HTTP status code reason phrases
STATUS_PHRASES: dict[int, str] = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    206: "Partial Content",
    301: "Moved Permanently",
    302: "Found",
    304: "Not Modified",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    408: "Request Timeout",
    409: "Conflict",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


@dataclass(slots=True)
class HTTPResponse:
    """Represents an HTTP response to be serialized and sent to a client.

    Attributes:
        status_code: Numeric HTTP status code (e.g. 200, 404, 502).
        reason_phrase: Standard or custom HTTP reason phrase (e.g. "OK").
        version: HTTP protocol version string (e.g. "HTTP/1.1").
        headers: Case-insensitive Headers object.
        body: Buffered response body bytes.
        body_stream: Async iterator yielding body byte chunks for streaming responses.
        is_chunked: True if Transfer-Encoding chunked should be used.
    """

    status_code: int = 200
    reason_phrase: str = ""
    version: str = "HTTP/1.1"
    headers: Headers = field(default_factory=Headers)
    body: bytes = b""
    body_stream: AsyncIterator[bytes] | None = None
    is_chunked: bool = False

    def __post_init__(self) -> None:
        """Set default reason phrase if not explicitly provided."""
        if not self.reason_phrase:
            self.reason_phrase = STATUS_PHRASES.get(self.status_code, "Unknown Status")

    @classmethod
    def create_error(
        cls,
        status_code: int,
        detail: str = "",
        headers: Headers | None = None,
    ) -> HTTPResponse:
        """Construct a standard JSON error response.

        Args:
            status_code: HTTP status code.
            detail: Diagnostic error detail string.
            headers: Optional additional headers.

        Returns:
            Constructed HTTPResponse instance.
        """
        response_headers = headers.copy() if headers else Headers()
        response_headers.set("Content-Type", "application/json")
        reason = STATUS_PHRASES.get(status_code, "Error")

        error_json = (
            f'{{"error": "{reason}", "code": {status_code}, '
            f'"detail": "{detail or reason}"}}'
        ).encode("utf-8")

        response_headers.set("Content-Length", str(len(error_json)))

        return cls(
            status_code=status_code,
            reason_phrase=reason,
            headers=response_headers,
            body=error_json,
        )
