"""Unit tests for TCPServer, Connection, ConnectionManager, and ShutdownHandler."""

from __future__ import annotations

import asyncio
import pytest

from pyproxy.config.models import ServerConfig
from pyproxy.exceptions import BindError, ServerError
from pyproxy.server.connection import Connection
from pyproxy.server.manager import ConnectionManager
from pyproxy.server.shutdown import ShutdownHandler
from pyproxy.server.tcp import TCPServer


class TestConnectionManager:
    """Tests for ConnectionManager connection tracking and limits."""

    @pytest.mark.asyncio
    async def test_register_and_unregister(self):
        manager = ConnectionManager(max_connections=2)
        mock_reader = asyncio.StreamReader()
        mock_writer = unittest_mock_writer()

        conn1 = Connection(mock_reader, mock_writer)
        conn2 = Connection(mock_reader, mock_writer)
        conn3 = Connection(mock_reader, mock_writer)

        assert await manager.register(conn1) is True
        assert await manager.register(conn2) is True
        assert manager.active_count == 2

        # Exceed max_connections limit
        assert await manager.register(conn3) is False
        assert manager.active_count == 2

        await manager.unregister(conn1)
        assert manager.active_count == 1

        # Now registration should succeed
        assert await manager.register(conn3) is True
        assert manager.active_count == 2

    @pytest.mark.asyncio
    async def test_close_all(self):
        manager = ConnectionManager()
        mock_reader = asyncio.StreamReader()
        mock_writer = unittest_mock_writer()

        conn1 = Connection(mock_reader, mock_writer)
        conn2 = Connection(mock_reader, mock_writer)

        await manager.register(conn1)
        await manager.register(conn2)

        closed = await manager.close_all(timeout=1.0)
        assert manager.active_count == 0


class TestShutdownHandler:
    """Tests for ShutdownHandler trigger and callbacks."""

    def test_shutdown_trigger(self):
        handler = ShutdownHandler()
        assert handler.is_shutting_down is False

        called = []

        def callback():
            called.append(True)

        handler.add_callback(callback)
        handler.trigger_shutdown()

        assert handler.is_shutting_down is True
        assert called == [True]


class TestTCPServerUnit:
    """Tests for TCPServer lifecycle."""

    @pytest.mark.asyncio
    async def test_server_bind_and_stop(self):
        config = ServerConfig(bind_host="127.0.0.1", bind_port=0)  # OS assigned port
        server = TCPServer(config=config)

        await server.start()
        assert server.is_running is True
        addr = server.server_address
        assert addr is not None
        assert addr[0] == "127.0.0.1"
        assert addr[1] > 0

        await server.stop()
        assert server.is_running is False

    @pytest.mark.asyncio
    async def test_invalid_port_bind_raises(self):
        # Trying to bind to port 1 on non-root or invalid address
        config = ServerConfig(bind_host="255.255.255.255", bind_port=80)
        server = TCPServer(config=config)

        with pytest.raises(BindError):
            await server.start()


def unittest_mock_writer() -> asyncio.StreamWriter:
    """Create a lightweight mock StreamWriter for unit tests."""
    class DummyTransport(asyncio.Transport):
        def get_extra_info(self, name, default=None):
            if name == "peername":
                return ("127.0.0.1", 12345)
            return default
        def is_closing(self):
            return False
        def close(self):
            pass

    transport = DummyTransport()
    protocol = asyncio.StreamReaderProtocol(asyncio.StreamReader())
    loop = asyncio.get_event_loop()
    return asyncio.StreamWriter(transport, protocol, None, loop)
