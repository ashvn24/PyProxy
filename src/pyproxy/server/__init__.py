"""Low-level asyncio TCP server and connection lifecycle package.

Provides high-performance, asynchronous TCP socket handling, connection pooling,
timeout enforcement, and graceful shutdown capabilities.

Example::

    from pyproxy.server import TCPServer, Connection
    from pyproxy.config import ServerConfig

    async def handle_client(connection: Connection) -> None:
        data = await connection.read(1024)
        connection.write(b"HTTP/1.1 200 OK\\r\\nContent-Length: 2\\r\\n\\r\\nOK")
        await connection.drain()

    config = ServerConfig(bind_host="127.0.0.1", bind_port=8080)
    server = TCPServer(config=config, connection_handler=handle_client)
    await server.serve_forever()
"""

from __future__ import annotations

from pyproxy.server.connection import Connection
from pyproxy.server.manager import ConnectionManager
from pyproxy.server.shutdown import ShutdownHandler
from pyproxy.server.tcp import TCPServer

__all__: list[str] = [
    "Connection",
    "ConnectionManager",
    "ShutdownHandler",
    "TCPServer",
]
