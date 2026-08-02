"""TCP Client Connection Wrapper.

Provides an encapsulated, timed, and flow-controlled wrapper around
asyncio StreamReader and StreamWriter pairs.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

from pyproxy.exceptions.server import ServerError
from pyproxy.utils.time import monotonic_ns

if TYPE_CHECKING:
    from collections.abc import Sequence


class Connection:
    """Encapsulates a single client TCP connection.

    Wraps the underlying asyncio StreamReader and StreamWriter to provide
    safe timed reading, buffered writing with explicit backpressure, and
    lifecycle state tracking.

    Attributes:
        client_host: Client IP address.
        client_port: Client port number.
        connected_at_ns: Monotonic timestamp (nanoseconds) when connection established.
        last_active_at_ns: Monotonic timestamp (nanoseconds) of last I/O activity.
    """

    __slots__ = (
        "_reader",
        "_writer",
        "client_host",
        "client_port",
        "connected_at_ns",
        "last_active_at_ns",
        "_is_closed",
    )

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Initialize a Connection instance.

        Args:
            reader: The asyncio StreamReader for this client.
            writer: The asyncio StreamWriter for this client.
        """
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer

        peername: Sequence[object] | None = writer.get_extra_info("peername")
        if peername and len(peername) >= 2:
            self.client_host: str = str(peername[0])
            self.client_port: int = int(peername[1])
        else:
            self.client_host = "0.0.0.0"
            self.client_port = 0

        now_nanoseconds: int = monotonic_ns()
        self.connected_at_ns: int = now_nanoseconds
        self.last_active_at_ns: int = now_nanoseconds
        self._is_closed: bool = False

    @property
    def is_closed(self) -> bool:
        """Whether the underlying connection is closed or closing.

        Returns:
            True if the connection has been closed.
        """
        return self._is_closed or self._writer.is_closing()

    def update_activity(self) -> None:
        """Update the last activity timestamp to the current monotonic time."""
        self.last_active_at_ns = monotonic_ns()

    async def read(self, n: int = -1, timeout: float = 0.0) -> bytes:  # noqa: ASYNC109
        """Read up to n bytes from the client.

        Args:
            n: Number of bytes to read (-1 for all available).
            timeout: Read timeout in seconds (0.0 for no timeout).

        Returns:
            The raw bytes read from the socket.

        Raises:
            ServerError: If a timeout or socket error occurs.
        """
        self.update_activity()
        try:
            if timeout > 0.0:
                async with asyncio.timeout(timeout):
                    data = await self._reader.read(n)
            else:
                data = await self._reader.read(n)
            self.update_activity()
            return data
        except TimeoutError as exception:
            raise ServerError(
                f"Read timed out after {timeout} seconds",
                error_code="CONNECTION_READ_TIMEOUT",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception
        except OSError as exception:
            raise ServerError(
                f"Socket read error: {exception}",
                error_code="CONNECTION_READ_ERROR",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception

    async def read_line(self, timeout: float = 0.0) -> bytes:  # noqa: ASYNC109
        """Read a single line (ending in b'\\n') from the client.

        Args:
            timeout: Read timeout in seconds.

        Returns:
            Raw bytes of the line including the newline character.

        Raises:
            ServerError: If timeout or socket error occurs.
        """
        self.update_activity()
        try:
            if timeout > 0.0:
                async with asyncio.timeout(timeout):
                    line = await self._reader.readline()
            else:
                line = await self._reader.readline()
            self.update_activity()
            return line
        except TimeoutError as exception:
            raise ServerError(
                f"Read line timed out after {timeout} seconds",
                error_code="CONNECTION_READ_TIMEOUT",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception
        except OSError as exception:
            raise ServerError(
                f"Socket read line error: {exception}",
                error_code="CONNECTION_READ_ERROR",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception

    async def read_exactly(self, number_of_bytes: int, timeout: float = 0.0) -> bytes:  # noqa: ASYNC109
        """Read exactly the specified number of bytes from the client.

        Args:
            number_of_bytes: Exact byte count to read.
            timeout: Read timeout in seconds.

        Returns:
            Exact bytes read.

        Raises:
            ServerError: On timeout, EOF, or socket error.
        """
        self.update_activity()
        try:
            if timeout > 0.0:
                async with asyncio.timeout(timeout):
                    data = await self._reader.readexactly(number_of_bytes)
            else:
                data = await self._reader.readexactly(number_of_bytes)
            self.update_activity()
            return data
        except TimeoutError as exception:
            raise ServerError(
                f"Read exactly timed out after {timeout} seconds",
                error_code="CONNECTION_READ_TIMEOUT",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception
        except asyncio.IncompleteReadError as exception:
            raise ServerError(
                f"Incomplete read: expected {number_of_bytes} bytes, got {len(exception.partial)}",
                error_code="CONNECTION_INCOMPLETE_READ",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception
        except OSError as exception:
            raise ServerError(
                f"Socket read error: {exception}",
                error_code="CONNECTION_READ_ERROR",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception

    def write(self, data: bytes) -> None:
        """Queue bytes to be written to the underlying socket output buffer.

        Args:
            data: Data bytes to write.
        """
        if self.is_closed:
            return
        self._writer.write(data)

    async def drain(self, timeout: float = 0.0) -> None:  # noqa: ASYNC109
        """Flush the underlying socket write buffer, applying backpressure.

        Args:
            timeout: Write timeout in seconds.

        Raises:
            ServerError: If write buffer flush times out or fails.
        """
        if self.is_closed:
            return
        try:
            if timeout > 0.0:
                async with asyncio.timeout(timeout):
                    await self._writer.drain()
            else:
                await self._writer.drain()
            self.update_activity()
        except TimeoutError as exception:
            raise ServerError(
                f"Write drain timed out after {timeout} seconds",
                error_code="CONNECTION_WRITE_TIMEOUT",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception
        except OSError as exception:
            raise ServerError(
                f"Socket write error: {exception}",
                error_code="CONNECTION_WRITE_ERROR",
                context={"client_host": self.client_host, "client_port": self.client_port},
            ) from exception

    async def close(self) -> None:
        """Close the client connection gracefully."""
        if self._is_closed:
            return
        self._is_closed = True
        with suppress(OSError):
            self._writer.close()
            await self._writer.wait_closed()
