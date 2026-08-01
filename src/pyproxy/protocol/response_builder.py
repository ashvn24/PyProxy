"""HTTP Response Serializer and Streaming Engine.

Serializes HTTPResponse models and streams buffered or chunked bodies
to client connections with backpressure and Range support.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pyproxy.exceptions.protocol import ProtocolError
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.response import HTTPResponse

if TYPE_CHECKING:
    from pyproxy.server.connection import Connection

_RANGE_HEADER_PATTERN = re.compile(r"^bytes=(\d*)-(\d*)$")


class HTTPResponseBuilder:
    """Serializes HTTP responses and handles socket streaming."""

    @staticmethod
    def serialize_headers(response: HTTPResponse) -> bytes:
        """Serialize status line and headers into wire format bytes.

        Args:
            response: HTTPResponse object to serialize.

        Returns:
            Header block bytes ending in b"\\r\\n\\r\\n".
        """
        lines: list[str] = [
            f"{response.version} {response.status_code} {response.reason_phrase}"
        ]

        for orig_name, val in response.headers:
            lines.append(f"{orig_name}: {val}")

        lines.append("")
        lines.append("")
        return "\r\n".join(lines).encode("iso-8859-1")

    @classmethod
    async def send_response(
        cls,
        connection: Connection,
        response: HTTPResponse,
        write_timeout: float = 30.0,
    ) -> int:
        """Send complete HTTP response (headers and body) over a client Connection.

        Args:
            connection: Active client Connection object.
            response: HTTPResponse model to send.
            write_timeout: Timeout in seconds for socket writes.

        Returns:
            Total count of bytes transmitted to client.
        """
        # Ensure Content-Length or Transfer-Encoding is set
        if response.body_stream is not None and not response.body:
            if not response.headers.contains("Transfer-Encoding") and not response.headers.contains("Content-Length"):
                response.headers.set("Transfer-Encoding", "chunked")
                response.is_chunked = True
        elif response.body and not response.headers.contains("Content-Length"):
            response.headers.set("Content-Length", str(len(response.body)))

        # Send status line and headers
        header_bytes = cls.serialize_headers(response)
        connection.write(header_bytes)
        await connection.drain(timeout=write_timeout)
        total_bytes_sent = len(header_bytes)

        # Send body
        if response.body:
            connection.write(response.body)
            await connection.drain(timeout=write_timeout)
            total_bytes_sent += len(response.body)
        elif response.body_stream is not None:
            if response.is_chunked:
                async for chunk in response.body_stream:
                    if not chunk:
                        continue
                    chunk_size_hex = f"{len(chunk):X}\r\n".encode("ascii")
                    connection.write(chunk_size_hex + chunk + b"\r\n")
                    await connection.drain(timeout=write_timeout)
                    total_bytes_sent += len(chunk_size_hex) + len(chunk) + 2
                # Send terminal 0 chunk
                connection.write(b"0\r\n\r\n")
                await connection.drain(timeout=write_timeout)
                total_bytes_sent += 5
            else:
                async for chunk in response.body_stream:
                    if chunk:
                        connection.write(chunk)
                        await connection.drain(timeout=write_timeout)
                        total_bytes_sent += len(chunk)

        return total_bytes_sent

    @staticmethod
    def parse_range_header(
        range_header_value: str,
        total_content_length: int,
    ) -> tuple[int, int] | None:
        """Parse HTTP Range header value (e.g. 'bytes=0-499').

        Args:
            range_header_value: Value string of Range header.
            total_content_length: Complete byte length of the body resource.

        Returns:
            Tuple of (start_byte, end_byte) inclusive, or None if invalid.
        """
        match = _RANGE_HEADER_PATTERN.match(range_header_value.strip())
        if not match:
            return None

        start_str, end_str = match.groups()

        if start_str and end_str:
            start = int(start_str)
            end = int(end_str)
        elif start_str:
            start = int(start_str)
            end = total_content_length - 1
        elif end_str:
            suffix_len = int(end_str)
            start = max(0, total_content_length - suffix_len)
            end = total_content_length - 1
        else:
            return None

        if start > end or start >= total_content_length:
            return None

        end = min(end, total_content_length - 1)
        return (start, end)
