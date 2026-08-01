"""WebSocket Bidirectional Proxy Engine.

Handles WebSocket 101 Switching Protocols handshakes, frame streaming,
ping/pong passthrough, and connection tunneling.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from typing import TYPE_CHECKING

from pyproxy.exceptions.protocol import WebSocketError
from pyproxy.protocol.headers import Headers
from pyproxy.upstream.pool import UpstreamConnection

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest
    from pyproxy.server.connection import Connection
    from pyproxy.upstream.target import UpstreamTarget

logger = logging.getLogger("pyproxy.websocket.proxy")

_WEBSOCKET_GUID: bytes = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketProxy:
    """Handles WebSocket protocol upgrading and bidirectional tunneling."""

    @staticmethod
    def compute_accept_key(sec_key: str) -> str:
        """Compute Sec-WebSocket-Accept header value per RFC 6455.

        Args:
            sec_key: Client Sec-WebSocket-Key header value.

        Returns:
            Base64 encoded SHA-1 digest string.
        """
        combined = sec_key.strip().encode("ascii") + _WEBSOCKET_GUID
        digest = hashlib.sha1(combined).digest()
        return base64.b64encode(digest).decode("ascii")

    async def proxy_websocket(
        self,
        client_conn: Connection,
        request: HTTPRequest,
        upstream_conn: UpstreamConnection,
    ) -> None:
        """Tunnel bidirectional WebSocket frame stream between client and upstream server.

        Args:
            client_conn: Client Connection object.
            request: Initial HTTPRequest containing Upgrade headers.
            upstream_conn: Connected UpstreamConnection to target backend.
        """
        logger.info(
            "Establishing WebSocket proxy tunnel for %s -> %s",
            client_conn.client_host,
            upstream_conn.target.endpoint,
        )

        try:
            # 1. Forward client HTTP Upgrade request to upstream
            upstream_headers = Headers()
            for k, v in request.headers:
                upstream_headers.add(k, v)

            req_line = f"{request.method} {request.target} {request.version}\r\n"
            header_str = "\r\n".join(f"{k}: {v}" for k, v in upstream_headers)
            full_handshake = (req_line + header_str + "\r\n\r\n").encode("iso-8859-1")

            upstream_conn.writer.write(full_handshake)
            await upstream_conn.writer.drain()

            # 2. Read 101 Switching Protocols response from upstream
            status_line = await upstream_conn.reader.readline()
            if not status_line.startswith(b"HTTP/1.1 101") and not status_line.startswith(b"HTTP/1.0 101"):
                raise WebSocketError(f"Upstream rejected WebSocket upgrade: '{status_line.decode().strip()}'")

            # Read response headers from upstream
            resp_header_bytes = bytearray(status_line)
            while True:
                line = await upstream_conn.reader.readline()
                resp_header_bytes.extend(line)
                if line in (b"\r\n", b"\n", b""):
                    break

            # Forward 101 response to client
            client_conn.write(bytes(resp_header_bytes))
            await client_conn.drain()

            logger.info("WebSocket handshake complete; entering bidirectional tunnel mode")

            # 3. Bidirectional data pump
            async def pump_stream(
                reader: asyncio.StreamReader,
                writer: Connection | UpstreamConnection,
                direction: str,
            ) -> None:
                try:
                    while not client_conn.is_closed and not upstream_conn.is_closed:
                        chunk = await reader.read(65536)
                        if not chunk:
                            break
                        if isinstance(writer, Connection):
                            writer.write(chunk)
                            await writer.drain()
                        else:
                            writer.writer.write(chunk)
                            await writer.writer.drain()
                except Exception as ex:
                    logger.debug("WebSocket tunnel error (%s): %s", direction, ex)

            # Run client->upstream and upstream->client loops concurrently
            task_c2u = asyncio.create_task(pump_stream(client_conn._reader, upstream_conn, "c2u"))
            task_u2c = asyncio.create_task(pump_stream(upstream_conn.reader, client_conn, "u2c"))

            done, pending = await asyncio.wait(
                [task_c2u, task_u2c],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for p in pending:
                p.cancel()

        finally:
            await upstream_conn.close()
            await client_conn.close()
            logger.info("WebSocket tunnel closed")
