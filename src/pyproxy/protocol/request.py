"""HTTP Request representation model.

Encapsulates parsed HTTP request line, headers, cookies, query parameters,
and streaming body reader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pyproxy.protocol.headers import Headers

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass(slots=True)
class HTTPRequest:
    """Represents an incoming HTTP request.

    Attributes:
        method: HTTP method (e.g. GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD).
        target: Raw request target line (e.g. "/api/v1/users?name=john").
        path: Parsed URL path (e.g. "/api/v1/users").
        query_string: Raw query string (e.g. "name=john").
        query_params: Dictionary of query parameters mapping to lists of values.
        version: HTTP protocol version (e.g. "HTTP/1.1").
        headers: Case-insensitive Headers object.
        cookies: Dictionary of parsed request cookies.
        content_length: Content-Length value if present in headers, or None.
        is_chunked: True if Transfer-Encoding includes "chunked".
        is_keep_alive: True if persistent connection is requested.
        body: Buffered request body bytes (if fully read into memory).
        body_stream: Async iterator yielding chunks of the request body.
    """

    method: str = "GET"
    target: str = "/"
    path: str = "/"
    query_string: str = ""
    query_params: dict[str, list[str]] = field(default_factory=dict)
    version: str = "HTTP/1.1"
    headers: Headers = field(default_factory=Headers)
    cookies: dict[str, str] = field(default_factory=dict)
    content_length: int | None = None
    is_chunked: bool = False
    is_keep_alive: bool = True
    body: bytes = b""
    body_stream: AsyncIterator[bytes] | None = None

    @property
    def is_websocket_upgrade(self) -> bool:
        """Check if request contains a WebSocket upgrade header sequence.

        Returns:
            True if Connection: Upgrade and Upgrade: websocket headers are present.
        """
        connection_hdr = self.headers.get("Connection", "").lower()
        upgrade_hdr = self.headers.get("Upgrade", "").lower()
        return "upgrade" in connection_hdr and upgrade_hdr == "websocket"

    @property
    def host(self) -> str:
        """Get Host header value or empty string.

        Returns:
            Host header value string.
        """
        return self.headers.get("Host", "")

    async def read_full_body(self) -> bytes:
        """Read and buffer the entire request body into memory.

        Returns:
            The complete request body bytes.
        """
        if self.body:
            return self.body
        if self.body_stream is None:
            return b""

        chunks: list[bytes] = []
        async for chunk in self.body_stream:
            chunks.append(chunk)

        self.body = b"".join(chunks)
        return self.body
