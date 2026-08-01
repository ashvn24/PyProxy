"""Streaming HTTP/1.1 Request Parser.

Parses HTTP request lines, headers, cookies, query parameters, Content-Length bodies,
and Transfer-Encoding chunked body streams directly from Connection sockets.
"""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

from pyproxy.exceptions.protocol import HttpParseError
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.request import HTTPRequest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pyproxy.server.connection import Connection

_VALID_METHODS: frozenset[str] = frozenset({
    "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "TRACE", "CONNECT",
})
_DEFAULT_CHUNK_SIZE: int = 65536


class HTTPParser:
    """High-performance HTTP/1.1 streaming request parser."""

    @staticmethod
    def parse_request_line(
        raw_line: bytes,
    ) -> tuple[str, str, str, str, dict[str, list[str]]]:
        """Parse HTTP request line (e.g. b"GET /users?id=1 HTTP/1.1\\r\\n").

        Args:
            raw_line: Raw bytes of the request line.

        Returns:
            Tuple of (method, target, path, version, query_params_dict).

        Raises:
            HttpParseError: If request line format is invalid.
        """
        try:
            line_str = raw_line.decode("ascii").strip()
        except UnicodeDecodeError as exception:
            raise HttpParseError(
                "Request line contains non-ASCII characters",
                raw_data=raw_line,
            ) from exception

        parts = line_str.split(" ")
        if len(parts) != 3:
            raise HttpParseError(
                f"Invalid request line format (expected 3 tokens, got {len(parts)})",
                raw_data=raw_line,
            )

        method, target, version = parts[0].upper(), parts[1], parts[2].upper()

        if method not in _VALID_METHODS:
            raise HttpParseError(
                f"Unsupported or invalid HTTP method '{method}'",
                raw_data=raw_line,
            )

        if not version.startswith("HTTP/"):
            raise HttpParseError(
                f"Invalid HTTP version string '{version}'",
                raw_data=raw_line,
            )

        # Parse target URL path and query parameters
        url_parts = urllib.parse.urlsplit(target)
        path = url_parts.path or "/"
        query_string = url_parts.query
        query_params = urllib.parse.parse_qs(query_string, keep_blank_values=True)

        return (method, target, path, version, query_params)

    @staticmethod
    def parse_cookies(cookie_header: str) -> dict[str, str]:
        """Parse Cookie header into name-value pairs.

        Args:
            cookie_header: Raw Cookie header string value.

        Returns:
            Dictionary of cookie names to cookie values.
        """
        cookies: dict[str, str] = {}
        if not cookie_header:
            return cookies

        for item in cookie_header.split(";"):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                cookie_name, cookie_val = item.split("=", 1)
                cookies[cookie_name.strip()] = cookie_val.strip()
            else:
                cookies[item] = ""
        return cookies

    @classmethod
    async def parse_request(
        cls,
        connection: Connection,
        read_timeout: float = 30.0,
        max_header_size: int = 65536,
    ) -> HTTPRequest:
        """Parse request line and headers from a Connection socket.

        Args:
            connection: Active client Connection object.
            read_timeout: Timeout in seconds for socket reads.
            max_header_size: Maximum total size allowed for request headers.

        Returns:
            Parsed HTTPRequest object with initialized body stream.

        Raises:
            HttpParseError: On invalid syntax or header limit violation.
        """
        # Read request line
        request_line_bytes = await connection.read_line(timeout=read_timeout)
        if not request_line_bytes:
            raise HttpParseError("Client closed connection before sending request line")

        method, target, path, version, query_params = cls.parse_request_line(request_line_bytes)

        # Read headers
        headers = Headers()
        total_header_bytes = len(request_line_bytes)

        while True:
            line_bytes = await connection.read_line(timeout=read_timeout)
            if not line_bytes:
                raise HttpParseError("Connection closed while reading headers")

            total_header_bytes += len(line_bytes)
            if total_header_bytes > max_header_size:
                raise HttpParseError(
                    f"Request headers size exceeded limit of {max_header_size} bytes",
                )

            # Blank line terminates headers
            if line_bytes in (b"\r\n", b"\n"):
                break

            line_str = line_bytes.decode("iso-8859-1").strip()
            if ":" not in line_str:
                raise HttpParseError(f"Invalid header line format: '{line_str}'")

            name, value = line_str.split(":", 1)
            headers.add(name.strip(), value.strip())

        # Determine connection keep-alive state
        connection_hdr = headers.get("Connection", "").lower()
        if version == "HTTP/1.1":
            is_keep_alive = connection_hdr != "close"
        else:
            is_keep_alive = connection_hdr == "keep-alive"

        # Determine Content-Length and Transfer-Encoding
        content_length_str = headers.get("Content-Length")
        content_length: int | None = None
        if content_length_str is not None:
            try:
                content_length = int(content_length_str)
                if content_length < 0:
                    raise ValueError
            except ValueError as exception:
                raise HttpParseError(
                    f"Invalid Content-Length header value '{content_length_str}'",
                ) from exception

        transfer_encoding = headers.get("Transfer-Encoding", "").lower()
        is_chunked = "chunked" in transfer_encoding

        # Parse cookies
        cookies = cls.parse_cookies(headers.get("Cookie", ""))

        request = HTTPRequest(
            method=method,
            target=target,
            path=path,
            query_string=urllib.parse.urlsplit(target).query,
            query_params=query_params,
            version=version,
            headers=headers,
            cookies=cookies,
            content_length=content_length,
            is_chunked=is_chunked,
            is_keep_alive=is_keep_alive,
        )

        # Attach streaming body iterator
        request.body_stream = cls.stream_body(connection, request, read_timeout=read_timeout)
        return request

    @classmethod
    async def stream_body(
        cls,
        connection: Connection,
        request: HTTPRequest,
        read_timeout: float = 30.0,
    ) -> AsyncIterator[bytes]:
        """Stream the HTTP request body from the connection socket.

        Args:
            connection: Active client Connection object.
            request: The parsed HTTPRequest metadata object.
            read_timeout: Timeout in seconds for reading body chunks.

        Yields:
            Byte chunks of the request body.
        """
        if request.is_chunked:
            async for chunk in cls._stream_chunked_body(connection, read_timeout):
                yield chunk
        elif request.content_length is not None and request.content_length > 0:
            remaining_bytes = request.content_length
            while remaining_bytes > 0:
                bytes_to_read = min(remaining_bytes, _DEFAULT_CHUNK_SIZE)
                chunk = await connection.read(bytes_to_read, timeout=read_timeout)
                if not chunk:
                    raise HttpParseError(
                        f"Premature EOF while reading body: expected {remaining_bytes} more bytes",
                    )
                remaining_bytes -= len(chunk)
                yield chunk

    @staticmethod
    async def _stream_chunked_body(
        connection: Connection,
        read_timeout: float = 30.0,
    ) -> AsyncIterator[bytes]:
        """Stream body chunks for Transfer-Encoding: chunked.

        Args:
            connection: Active client Connection object.
            read_timeout: Read timeout in seconds.

        Yields:
            Decoded body byte chunks.
        """
        while True:
            chunk_header_line = await connection.read_line(timeout=read_timeout)
            if not chunk_header_line:
                raise HttpParseError("Premature EOF reading chunk size header")

            chunk_header_str = chunk_header_line.decode("ascii").split(";")[0].strip()
            try:
                chunk_size = int(chunk_header_str, 16)
            except ValueError as exception:
                raise HttpParseError(
                    f"Invalid chunk size hex header '{chunk_header_str}'",
                ) from exception

            if chunk_size == 0:
                # Read trailing CRLF after 0 chunk
                await connection.read_line(timeout=read_timeout)
                break

            # Read chunk data
            chunk_data = await connection.read_exactly(chunk_size, timeout=read_timeout)
            yield chunk_data

            # Read trailing CRLF after chunk data
            crlf = await connection.read_line(timeout=read_timeout)
            if crlf not in (b"\r\n", b"\n"):
                raise HttpParseError("Malformed chunked encoding: missing trailing CRLF")
