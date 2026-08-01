"""Graceful Shutdown Manager.

Intercepts process termination signals (SIGINT, SIGTERM) and manages
orderly server shutdown and connection draining.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import TYPE_CHECKING

from pyproxy.exceptions.server import ShutdownError

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("pyproxy.server.shutdown")


class ShutdownHandler:
    """Manages server shutdown signals and task cancellation."""

    def __init__(self, shutdown_timeout: float = 30.0) -> None:
        """Initialize the ShutdownHandler.

        Args:
            shutdown_timeout: Maximum time in seconds to wait for graceful shutdown.
        """
        self.shutdown_timeout: float = shutdown_timeout
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._callbacks: list[Callable[[], object]] = []
        self._signal_handlers_installed: bool = False

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown has been triggered.

        Returns:
            True if shutdown event is set.
        """
        return self._shutdown_event.is_set()

    def add_callback(self, callback: Callable[[], object]) -> None:
        """Add a callback function to be called on shutdown signal.

        Args:
            callback: Sync or async callable to run when shutdown begins.
        """
        self._callbacks.append(callback)

    def install_signal_handlers(self) -> None:
        """Install signal handlers for SIGINT and SIGTERM.

        Safely handles operating system differences (Windows vs Unix).
        """
        if self._signal_handlers_installed:
            return

        # Windows does not support loop.add_signal_handler for SIGTERM/SIGINT
        if sys.platform != "win32":
            try:
                event_loop = asyncio.get_running_loop()
                for target_signal in (signal.SIGINT, signal.SIGTERM):
                    event_loop.add_signal_handler(
                        target_signal,
                        self.trigger_shutdown,
                    )
                self._signal_handlers_installed = True
                logger.debug("Unix signal handlers registered for SIGINT and SIGTERM")
            except RuntimeError:
                logger.warning("Could not register signal handlers: no running event loop")
        else:
            logger.debug("Windows platform detected; relying on standard signal handlers")

    def trigger_shutdown(self) -> None:
        """Trigger the shutdown sequence manually or from a signal."""
        if self._shutdown_event.is_set():
            return
        logger.info("Shutdown signal received, initiating graceful shutdown")
        self._shutdown_event.set()

        for callback in self._callbacks:
            try:
                result = callback()
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as exception:
                logger.exception("Error executing shutdown callback: %s", exception)

    async def wait_for_shutdown(self) -> None:
        """Block until the shutdown signal is triggered."""
        await self._shutdown_event.wait()
