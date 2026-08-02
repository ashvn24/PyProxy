"""Connection Manager for PyProxy.

Tracks active client connections, enforces connection limits, and handles
mass connection closure during server shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyproxy.server.connection import Connection

logger = logging.getLogger("pyproxy.server.manager")


class ConnectionManager:
    """Tracks active client connections and manages limits.

    Attributes:
        max_connections: Maximum allowed concurrent connections (0 = unlimited).
    """

    __slots__ = ("max_connections", "_connections", "_lock")

    def __init__(self, max_connections: int = 0) -> None:
        """Initialize the ConnectionManager.

        Args:
            max_connections: Limit on active client connections. 0 means unlimited.
        """
        self.max_connections: int = max_connections
        self._connections: set[Connection] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        """Get the current count of active connections.

        Returns:
            The number of open connections currently tracked.
        """
        return len(self._connections)

    async def register(self, connection: Connection) -> bool:
        """Register a new connection if under max_connections limit.

        Args:
            connection: The client Connection to track.

        Returns:
            True if connection accepted and registered; False if limit reached.
        """
        async with self._lock:
            if self.max_connections > 0 and len(self._connections) >= self.max_connections:
                logger.warning(
                    "Connection rejected from %s:%d: max connections (%d) reached",
                    connection.client_host,
                    connection.client_port,
                    self.max_connections,
                )
                return False
            self._connections.add(connection)
            logger.debug(
                "Registered connection from %s:%d (active: %d)",
                connection.client_host,
                connection.client_port,
                len(self._connections),
            )
            return True

    async def unregister(self, connection: Connection) -> None:
        """Unregister a connection when it terminates.

        Args:
            connection: The client Connection to remove.
        """
        async with self._lock:
            self._connections.discard(connection)
            logger.debug(
                "Unregistered connection from %s:%d (active: %d)",
                connection.client_host,
                connection.client_port,
                len(self._connections),
            )

    async def close_all(self, timeout: float = 10.0) -> int:  # noqa: ASYNC109
        """Close all tracked active connections within a timeout duration.

        Args:
            timeout: Seconds to wait for connections to close.

        Returns:
            Number of connections closed.
        """
        async with self._lock:
            connections_to_close = list(self._connections)

        if not connections_to_close:
            return 0

        logger.info(
            "Closing %d active connections (timeout: %.1fs)",
            len(connections_to_close),
            timeout,
        )

        close_tasks = [
            asyncio.create_task(connection.close())
            for connection in connections_to_close
        ]

        try:
            if timeout > 0.0:
                async with asyncio.timeout(timeout):
                    await asyncio.gather(*close_tasks, return_exceptions=True)
            else:
                await asyncio.gather(*close_tasks, return_exceptions=True)
        except TimeoutError:
            logger.warning(
                "Timed out waiting for %d connections to close gracefully",
                len(connections_to_close),
            )

        async with self._lock:
            closed_count = len(connections_to_close) - len(self._connections)
            self._connections.clear()

        return closed_count
