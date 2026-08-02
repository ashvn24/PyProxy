"""Upstream Connection Pool.

Manages reusable socket connection pools to backend targets with timeout
enforcement and automatic failure detection.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pyproxy.exceptions.upstream import UpstreamConnectionError, UpstreamTimeoutError
from pyproxy.upstream.target import UpstreamTarget

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger("pyproxy.upstream.pool")


class UpstreamConnection:
    """Encapsulates a pooled connection to an upstream target server.

    Attributes:
        target: Target backend server object.
        reader: asyncio StreamReader for target socket.
        writer: asyncio StreamWriter for target socket.
    """

    __slots__ = ("target", "reader", "writer", "_is_closed")

    def __init__(
        self,
        target: UpstreamTarget,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self.target: UpstreamTarget = target
        self.reader: asyncio.StreamReader = reader
        self.writer: asyncio.StreamWriter = writer
        self._is_closed: bool = False

    @property
    def is_closed(self) -> bool:
        """Check if socket connection is closed, closing, or at EOF.

        Returns:
            True if socket is closing, closed, or reached EOF.
        """
        return self._is_closed or self.writer.is_closing() or self.reader.at_eof()

    async def close(self) -> None:
        """Close the socket connection cleanly."""
        if self._is_closed:
            return
        self._is_closed = True
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except OSError:
            pass


class UpstreamConnectionPool:
    """Manages connection pools across multiple upstream targets."""

    def __init__(self, pool_size: int = 64) -> None:
        """Initialize UpstreamConnectionPool.

        Args:
            pool_size: Maximum idle connections per target endpoint.
        """
        self.pool_size: int = pool_size
        self._idle_pools: dict[str, asyncio.Queue[UpstreamConnection]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def acquire(
        self,
        target: UpstreamTarget,
        connect_timeout: float = 5.0,
    ) -> UpstreamConnection:
        """Acquire a connection to target, reusing an idle connection if available.

        Args:
            target: UpstreamTarget server object.
            connect_timeout: Connection attempt timeout in seconds.

        Returns:
            Connected UpstreamConnection instance.

        Raises:
            UpstreamConnectionError: If TCP connection fails.
            UpstreamTimeoutError: If connection times out.
        """
        endpoint = target.endpoint

        # 1. Attempt to reuse idle connection
        async with self._lock:
            pool_queue = self._idle_pools.get(endpoint)

        if pool_queue:
            while not pool_queue.empty():
                try:
                    conn = pool_queue.get_nowait()
                    if not conn.is_closed:
                        target.active_connections += 1
                        logger.debug("Reused idle connection to %s", endpoint)
                        return conn
                except asyncio.QueueEmpty:
                    break

        # 2. Establish new connection
        try:
            async with asyncio.timeout(connect_timeout):
                reader, writer = await asyncio.open_connection(
                    host=target.host,
                    port=target.port,
                )
        except TimeoutError as exception:
            raise UpstreamTimeoutError(
                host=target.host,
                port=target.port,
                timeout_seconds=connect_timeout,
            ) from exception
        except OSError as exception:
            raise UpstreamConnectionError(
                host=target.host,
                port=target.port,
                cause=str(exception),
            ) from exception

        conn = UpstreamConnection(target, reader, writer)
        target.active_connections += 1
        logger.debug("Opened new connection to %s", endpoint)
        return conn

    async def release(self, conn: UpstreamConnection, reusable: bool = True) -> None:
        """Release a connection back to the idle pool or close it.

        Args:
            conn: UpstreamConnection object.
            reusable: Flag indicating whether connection is healthy and reusable.
        """
        conn.target.active_connections = max(0, conn.target.active_connections - 1)
        endpoint = conn.target.endpoint

        if not reusable or conn.is_closed:
            await conn.close()
            return

        async with self._lock:
            if endpoint not in self._idle_pools:
                self._idle_pools[endpoint] = asyncio.Queue(maxsize=self.pool_size)
            pool_queue = self._idle_pools[endpoint]

        try:
            pool_queue.put_nowait(conn)
            logger.debug("Released connection to idle pool for %s", endpoint)
        except asyncio.QueueFull:
            # Pool full, close connection
            await conn.close()

    async def close_all(self) -> None:
        """Close all idle pooled connections."""
        async with self._lock:
            for endpoint, pool_queue in self._idle_pools.items():
                while not pool_queue.empty():
                    try:
                        conn = pool_queue.get_nowait()
                        await conn.close()
                    except asyncio.QueueEmpty:
                        break
            self._idle_pools.clear()
        logger.info("Closed all idle connections in upstream pool")
