"""Integration test for TCPServer client interactions and graceful shutdown."""

from __future__ import annotations

import asyncio
import pytest

from pyproxy.config.models import ServerConfig
from pyproxy.server import Connection, TCPServer


@pytest.mark.integration
class TestServerLifecycleIntegration:
    """Integration tests for TCP server client handling."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_client_echo_interaction(self):
        """Verify that server accepts a client, handles custom logic, and echoes data."""
        async def echo_handler(connection: Connection) -> None:
            data = await connection.read(1024, timeout=5.0)
            if data:
                connection.write(b"ECHO:" + data)
                await connection.drain(timeout=5.0)

        config = ServerConfig(bind_host="127.0.0.1", bind_port=0)
        server = TCPServer(config=config, connection_handler=echo_handler)
        await server.start()

        host, port = server.server_address

        # Connect client
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(b"Hello PyProxy")
        await writer.drain()

        response = await reader.read(1024)
        assert response == b"ECHO:Hello PyProxy"

        writer.close()
        await writer.wait_closed()
        await server.stop()

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_graceful_shutdown_with_active_clients(self):
        """Verify that server gracefully closes active connections upon stop."""
        async def hold_handler(connection: Connection) -> None:
            try:
                await connection.read(1024, timeout=30.0)
            except Exception:
                pass

        config = ServerConfig(bind_host="127.0.0.1", bind_port=0, shutdown_timeout=2.0)
        server = TCPServer(config=config, connection_handler=hold_handler)
        await server.start()

        host, port = server.server_address
        reader, writer = await asyncio.open_connection(host, port)

        assert server.connection_manager.active_count == 1

        await server.stop()
        assert server.connection_manager.active_count == 0

        writer.close()
        await writer.wait_closed()
