"""Core Reverse Proxy Engine.

Orchestrates client request forwarding, path rewriting, upstream target connection,
retry policies, and streaming response delivery.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from pyproxy.exceptions.protocol import HttpParseError
from pyproxy.exceptions.upstream import UpstreamError
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.response import HTTPResponse
from pyproxy.protocol.response_builder import HTTPResponseBuilder
from pyproxy.proxy.headers import HeaderRewriter
from pyproxy.upstream.pool import UpstreamConnection, UpstreamConnectionPool
from pyproxy.upstream.target import UpstreamTarget

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest
    from pyproxy.routing.rule import RouteRule
    from pyproxy.server.connection import Connection

logger = logging.getLogger("pyproxy.proxy.engine")


class ProxyEngine:
    """High-performance Reverse Proxy Engine."""

    def __init__(
        self,
        connection_pool: UpstreamConnectionPool | None = None,
        middleware_pipeline: Any | None = None,
    ) -> None:
        """Initialize ProxyEngine.

        Args:
            connection_pool: UpstreamConnectionPool instance for connection reuse.
            middleware_pipeline: Optional MiddlewarePipeline instance for response processing.
        """
        self.connection_pool: UpstreamConnectionPool = connection_pool or UpstreamConnectionPool()
        self.middleware_pipeline: Any | None = middleware_pipeline

    async def forward(
        self,
        client_conn: Connection,
        request: HTTPRequest,
        route_rule: RouteRule,
        target: UpstreamTarget,
    ) -> int:
        """Forward an incoming client request to target and stream response back.

        Supports retries on connection failures.

        Args:
            client_conn: Active client Connection socket.
            request: Incoming HTTPRequest model.
            route_rule: Matching RouteRule instance.
            target: Destination UpstreamTarget server.

        Returns:
            Total count of response bytes transmitted to client.

        Raises:
            UpstreamError: If all retry attempts fail.
        """
        upstream_config = route_rule.upstream_config
        max_retries = max(1, upstream_config.max_retries)
        last_exception: Exception | None = None

        # Compute rewritten target path
        forward_path = route_rule.rewrite_path(request.path)
        if request.query_string:
            forward_target = f"{forward_path}?{request.query_string}"
        else:
            forward_target = forward_path

        for attempt in range(1, max_retries + 1):
            try:
                return await self._execute_forward(
                    client_conn=client_conn,
                    request=request,
                    forward_target=forward_target,
                    target=target,
                    upstream_config=upstream_config,
                )
            except (UpstreamError, OSError, HttpParseError) as exception:
                last_exception = exception
                logger.warning(
                    "Attempt %d/%d failed forwarding to %s: %s",
                    attempt,
                    max_retries,
                    target.endpoint,
                    exception,
                )
                if attempt < max_retries and upstream_config.retry_delay > 0.0:
                    await asyncio.sleep(upstream_config.retry_delay)

        raise UpstreamError(
            f"All {max_retries} attempts to forward request to {target.endpoint} failed",
            context={"host": target.host, "port": target.port, "cause": str(last_exception)},
        ) from last_exception

    async def _execute_forward(
        self,
        client_conn: Connection,
        request: HTTPRequest,
        forward_target: str,
        target: UpstreamTarget,
        upstream_config: Any,
    ) -> int:
        """Execute single attempt to transmit request to upstream and stream response.

        Args:
            client_conn: Client Connection socket.
            request: HTTPRequest object.
            forward_target: Rewritten target URI string.
            target: UpstreamTarget object.
            upstream_config: UpstreamConfig configuration.

        Returns:
            Total bytes transmitted to client.
        """
        upstream_conn: UpstreamConnection = await self.connection_pool.acquire(
            target=target,
            connect_timeout=upstream_config.connect_timeout,
        )

        reusable = True
        try:
            # 1. Prepare rewritten upstream headers
            upstream_headers = HeaderRewriter.prepare_upstream_headers(
                request=request,
                client_connection=client_conn,
                target_host=target.host,
                target_port=target.port,
            )

            # 2. Serialize request line and headers to upstream
            req_line = f"{request.method} {forward_target} {request.version}\r\n"
            header_lines = [f"{k}: {v}" for k, v in upstream_headers]
            header_lines.append("\r\n")
            serialized_headers = (req_line + "\r\n".join(header_lines)).encode("iso-8859-1")

            upstream_conn.writer.write(serialized_headers)
            await asyncio.wait_for(
                upstream_conn.writer.drain(),
                timeout=upstream_config.write_timeout,
            )

            # 3. Stream request body to upstream if present
            if request.body:
                upstream_conn.writer.write(request.body)
                await asyncio.wait_for(
                    upstream_conn.writer.drain(),
                    timeout=upstream_config.write_timeout,
                )
            elif request.body_stream is not None:
                async for chunk in request.body_stream:
                    if chunk:
                        upstream_conn.writer.write(chunk)
                        await asyncio.wait_for(
                            upstream_conn.writer.drain(),
                            timeout=upstream_config.write_timeout,
                        )

            # 4. Read response status line and headers from upstream
            status_line = await asyncio.wait_for(
                upstream_conn.reader.readline(),
                timeout=upstream_config.read_timeout,
            )
            if not status_line:
                reusable = False
                raise HttpParseError("Upstream server closed connection without response")

            status_str = status_line.decode("ascii").strip()
            parts = status_str.split(" ", 2)
            if len(parts) < 2:
                reusable = False
                raise HttpParseError(f"Invalid status line from upstream: '{status_str}'")

            version, status_code_str = parts[0], parts[1]
            reason_phrase = parts[2] if len(parts) > 2 else ""
            status_code = int(status_code_str)

            # Read response headers
            resp_headers = Headers()
            while True:
                line_bytes = await asyncio.wait_for(
                    upstream_conn.reader.readline(),
                    timeout=upstream_config.read_timeout,
                )
                if line_bytes in (b"\r\n", b"\n", b""):
                    break
                line_str = line_bytes.decode("iso-8859-1").strip()
                if ":" in line_str:
                    name, val = line_str.split(":", 1)
                    resp_headers.add(name.strip(), val.strip())

            # 5. Create streaming response body iterator
            async def stream_upstream_body() -> AsyncGenerator[bytes, None]:
                nonlocal reusable
                try:
                    content_len_str = resp_headers.get("Content-Length")
                    is_chunked = "chunked" in resp_headers.get("Transfer-Encoding", "").lower()

                    if is_chunked:
                        while True:
                            hdr = await upstream_conn.reader.readline()
                            if not hdr:
                                break
                            sz = int(hdr.decode("ascii").split(";")[0].strip(), 16)
                            if sz == 0:
                                await upstream_conn.reader.readline()
                                break
                            chunk_data = await upstream_conn.reader.readexactly(sz)
                            await upstream_conn.reader.readline()
                            yield chunk_data
                    elif content_len_str is not None:
                        remaining = int(content_len_str)
                        while remaining > 0:
                            chunk_sz = min(remaining, 65536)
                            data = await upstream_conn.reader.read(chunk_sz)
                            if not data:
                                break
                            remaining -= len(data)
                            yield data
                    else:
                        # Stream until EOF
                        while True:
                            data = await upstream_conn.reader.read(65536)
                            if not data:
                                break
                            yield data
                except Exception as ex:
                    reusable = False
                    logger.error("Error streaming body from upstream %s: %s", target.endpoint, ex)
                    raise

            response = HTTPResponse(
                status_code=status_code,
                reason_phrase=reason_phrase,
                version=version,
                headers=resp_headers,
                body_stream=stream_upstream_body(),
            )

            # Process post-response middleware (e.g. CacheMiddleware)
            if self.middleware_pipeline:
                response = await self.middleware_pipeline.execute_response(request, response)

            # 6. Stream response to client via HTTPResponseBuilder
            bytes_sent = await HTTPResponseBuilder.send_response(
                connection=client_conn,
                response=response,
            )
            return bytes_sent
        except Exception:
            reusable = False
            raise
        finally:
            await self.connection_pool.release(upstream_conn, reusable=reusable)
