"""End-to-end integration test for PyProxy reverse proxy engine."""

from __future__ import annotations

import asyncio
import pytest

from pyproxy.config.models import (
    LoggingConfig,
    ProxyConfig,
    RouteConfig,
    ServerConfig,
    UpstreamConfig,
    UpstreamTargetConfig,
)
from pyproxy.proxy_app import Proxy


@pytest.mark.integration
class TestFullProxyIntegration:
    """Full E2E test: Client -> PyProxy -> Upstream TCP Server -> PyProxy -> Client."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_full_reverse_proxy_flow(self):
        # 1. Start mock upstream HTTP server
        async def upstream_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            request_line = await reader.readline()
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break

            body = b"Hello from Backend Server!"
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                f"Content-Length: {len(body)}\r\n"
                b"Connection: close\r\n"
                b"\r\n" + body
            )
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        upstream_server = await asyncio.start_server(upstream_handler, host="127.0.0.1", port=0)
        up_host, up_port = upstream_server.sockets[0].getsockname()

        # 2. Build PyProxy configuration pointing to mock upstream
        config = ProxyConfig(
            server=ServerConfig(bind_host="127.0.0.1", bind_port=0),
            logging=LoggingConfig(level="info", format="json"),
            routes=(
                RouteConfig(
                    path="/api",
                    upstream=UpstreamConfig(
                        targets=(UpstreamTargetConfig(host=up_host, port=up_port),),
                    ),
                ),
            ),
        )

        proxy = Proxy(config=config)
        await proxy.start()
        proxy_host, proxy_port = proxy.tcp_server.server_address  # type: ignore[union-attr]

        # 3. Client sends request to PyProxy
        reader, writer = await asyncio.open_connection(proxy_host, proxy_port)
        req_data = (
            b"GET /api/hello HTTP/1.1\r\n"
            f"Host: {proxy_host}:{proxy_port}\r\n"
            b"User-Agent: PytestClient/1.0\r\n"
            b"Connection: close\r\n"
            b"\r\n"
        )
        writer.write(req_data)
        await writer.drain()

        # 4. Read response from PyProxy
        resp_data = await reader.read(4096)
        assert b"200 OK" in resp_data
        assert b"Hello from Backend Server!" in resp_data

        writer.close()
        await writer.wait_closed()

        # 5. Clean up
        await proxy.stop()
        upstream_server.close()
        await upstream_server.wait_closed()
