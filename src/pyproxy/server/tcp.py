"""Asyncio TCP Server Implementation.

High-performance, event-driven TCP server supporting connection management,
graceful shutdown, keep-alive, socket option tuning, and backpressure.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import TYPE_CHECKING

from pyproxy.config.models import ServerConfig
from pyproxy.exceptions.server import BindError, ServerError
from pyproxy.server.connection import Connection
from pyproxy.server.manager import ConnectionManager
from pyproxy.server.shutdown import ShutdownHandler

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger("pyproxy.server.tcp")


class TCPServer:
    """Asyncio TCP Server for PyProxy reverse proxy engine."""

    def __init__(
        self,
        config: ServerConfig,
        connection_handler: Callable[[Connection], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the TCPServer instance.

        Args:
            config: ServerConfig instance containing port, timeouts, etc.
            connection_handler: Async callback invoked for each accepted Connection.
        """
        self.config: ServerConfig = config
        self.connection_handler: Callable[[Connection], Awaitable[None]] | None = connection_handler

        self.connection_manager: ConnectionManager = ConnectionManager(
            max_connections=config.max_connections,
        )
        self.shutdown_handler: ShutdownHandler = ShutdownHandler(
            shutdown_timeout=config.shutdown_timeout,
        )

        self._server: asyncio.Server | None = None
        self._is_running: bool = False
        self._active_tasks: set[asyncio.Task[None]] = set()

    @property
    def is_running(self) -> bool:
        """Check if the TCP server is currently listening and accepting connections.

        Returns:
            True if server is running.
        """
        return self._is_running

    @property
    def server_address(self) -> tuple[str, int] | None:
        """Get host and port the server is bound to.

        Returns:
            Tuple of (host, port) or None if not bound.
        """
        if self._server and self._server.sockets:
            sock_name = self._server.sockets[0].getsockname()
            if isinstance(sock_name, tuple) and len(sock_name) >= 2:
                return (str(sock_name[0]), int(sock_name[1]))
        return None

    async def start(self) -> None:
        """Bind socket and start listening for TCP client connections.

        Raises:
            BindError: If binding to host and port fails.
            ServerError: If server start fails unexpectedly.
        """
        if self._is_running:
            return

        logger.info(
            "Starting TCP server on %s:%d",
            self.config.bind_host,
            self.config.bind_port,
        )

        try:
            self._server = await asyncio.start_server(
                self._handle_client_socket,
                host=self.config.bind_host,
                port=self.config.bind_port,
                backlog=self.config.backlog,
                reuse_address=True,
            )

            # Apply socket performance tuning (TCP_NODELAY)
            for sock in self._server.sockets:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Install custom loop exception handler to handle Windows WinError 10054 proactor noise
            loop = asyncio.get_running_loop()
            existing_handler = loop.get_exception_handler()

            def _custom_exception_handler(event_loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
                exc = context.get("exception")
                if isinstance(exc, ConnectionResetError) or (
                    isinstance(exc, OSError) and getattr(exc, "winerror", None) == 10054
                ):
                    return
                if existing_handler:
                    existing_handler(event_loop, context)
                else:
                    event_loop.default_exception_handler(context)

            loop.set_exception_handler(_custom_exception_handler)

            self._is_running = True
            bound_addr = self.server_address
            logger.info(
                "TCP server listening on %s:%d",
                bound_addr[0] if bound_addr else self.config.bind_host,
                bound_addr[1] if bound_addr else self.config.bind_port,
            )

            self.shutdown_handler.install_signal_handlers()
        except OSError as exception:
            raise BindError(
                host=self.config.bind_host,
                port=self.config.bind_port,
                cause=str(exception),
            ) from exception
        except Exception as exception:
            raise ServerError(
                f"Failed to start TCP server: {exception}",
                error_code="SERVER_START_ERROR",
            ) from exception

    async def serve_forever(self) -> None:
        """Start the server and block until a shutdown signal is received."""
        await self.start()
        if self._server:
            async with self._server:
                await self.shutdown_handler.wait_for_shutdown()
            await self.stop()

    async def _handle_client_socket(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle newly accepted client TCP socket.

        Args:
            reader: asyncio StreamReader for accepted client socket.
            writer: asyncio StreamWriter for accepted client socket.
        """
        connection = Connection(reader, writer)

        # Enforce max connections limit
        registered = await self.connection_manager.register(connection)
        if not registered:
            await connection.close()
            return

        current_task = asyncio.current_task()
        if current_task:
            self._active_tasks.add(current_task)
            current_task.add_done_callback(self._active_tasks.discard)

        try:
            if self.connection_handler:
                await self.connection_handler(connection)
            else:
                # Default echo/hold behavior if no handler registered
                await self._default_connection_loop(connection)
        except Exception as exception:
            logger.error(
                "Unhandled error in connection handler for %s:%d: %s",
                connection.client_host,
                connection.client_port,
                exception,
                exc_info=True,
            )
        finally:
            await connection.close()
            await self.connection_manager.unregister(connection)

    async def _default_connection_loop(self, connection: Connection) -> None:
        """Default connection handler when none is specified.

        Args:
            connection: The client Connection object.
        """
        try:
            while not connection.is_closed and not self.shutdown_handler.is_shutting_down:
                data = await connection.read(
                    n=8192,
                    timeout=self.config.keepalive_timeout,
                )
                if not data:
                    break
                connection.write(data)
                await connection.drain(timeout=self.config.write_timeout)
        except ServerError:
            pass

    async def stop(self) -> None:
        """Gracefully stop the server and close active connections."""
        if not self._is_running:
            return

        logger.info("Stopping TCP server...")
        self._is_running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Close all active tracked connections
        await self.connection_manager.close_all(
            timeout=self.config.shutdown_timeout,
        )

        # Cancel remaining tasks
        if self._active_tasks:
            for task in list(self._active_tasks):
                task.cancel()
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
            self._active_tasks.clear()

        logger.info("TCP server stopped successfully")
