"""Configuration file watcher for hot reload.

Uses ``watchfiles`` to monitor configuration files for changes and
invoke a callback when a change is detected. Includes debouncing to
prevent rapid successive reloads.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyproxy.config.models import ProxyConfig

logger = logging.getLogger("pyproxy.config.watcher")


class ConfigWatcher:
    """Watches a configuration file for changes and triggers a reload callback.

    Uses ``watchfiles.awatch()`` for efficient, async-native file monitoring
    backed by Rust's ``notify`` crate. Changes are debounced to avoid
    reloading on partial writes (e.g., when an editor writes, truncates,
    then writes again).

    Example::

        async def on_reload(new_config: ProxyConfig) -> None:
            print(f"Reloaded: {new_config.server.bind_port}")

        watcher = ConfigWatcher(
            file_path=Path("config.yaml"),
            on_reload=on_reload,
        )
        await watcher.start()  # Runs until cancelled
    """

    def __init__(
        self,
        file_path: Path,
        on_reload: Callable[[ProxyConfig], object],
        debounce_seconds: float = 1.0,
    ) -> None:
        """Initialize the ConfigWatcher.

        Args:
            file_path: Path to the configuration file to watch.
            on_reload: Callback invoked with the new ``ProxyConfig`` after
                a successful reload. May be sync or async.
            debounce_seconds: Minimum seconds between reload attempts.
                Prevents rapid-fire reloads on partial writes.
        """
        self._file_path: Path = file_path
        self._on_reload = on_reload
        self._debounce_seconds: float = debounce_seconds
        self._running: bool = False
        self._watch_task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        """Whether the watcher is currently active.

        Returns:
            True if the watcher loop is running.
        """
        return self._running

    async def start(self) -> None:
        """Start watching the configuration file for changes.

        This method runs indefinitely until :meth:`stop` is called or the
        task is cancelled. It should be launched as a background task::

            task = asyncio.create_task(watcher.start())

        Raises:
            ImportError: If ``watchfiles`` is not installed.
        """
        try:
            from watchfiles import awatch
        except ImportError as exc:
            logger.error(
                "watchfiles is required for hot reload. "
                "Install it with: pip install watchfiles"
            )
            raise ImportError(
                "watchfiles is required for config hot reload"
            ) from exc

        self._running = True
        watch_directory = self._file_path.parent
        file_name = self._file_path.name

        logger.info(
            "Config watcher started for %s (debounce: %ss)",
            self._file_path,
            self._debounce_seconds,
        )

        try:
            async for changes in awatch(
                watch_directory,
                debounce=int(self._debounce_seconds * 1000),
                step=100,
                rust_timeout=5000,
            ):
                if not self._running:
                    break

                # Filter for changes to our specific config file
                relevant_changes = [
                    (change_type, path)
                    for change_type, path in changes
                    if Path(path).name == file_name
                ]

                if relevant_changes:
                    logger.info(
                        "Configuration file changed: %s",
                        [(str(ct), p) for ct, p in relevant_changes],
                    )
                    await self._handle_reload()
        except asyncio.CancelledError:
            logger.info("Config watcher cancelled")
        finally:
            self._running = False
            logger.info("Config watcher stopped")

    async def stop(self) -> None:
        """Stop the configuration file watcher.

        Signals the watch loop to exit on the next iteration. If the watcher
        was started via :meth:`start_background`, also cancels the background task.
        """
        self._running = False
        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None
        logger.info("Config watcher stop requested")

    def start_background(self) -> asyncio.Task[None]:
        """Start the watcher as a background asyncio task.

        Returns:
            The asyncio Task running the watcher loop.
        """
        self._watch_task = asyncio.create_task(self.start())
        return self._watch_task

    async def _handle_reload(self) -> None:
        """Handle a detected configuration file change.

        Loads the new configuration, validates it, and invokes the
        reload callback. Errors during reload are logged but do not
        crash the watcher — the proxy continues with the previous
        valid configuration.
        """
        from pyproxy.config.loader import ConfigLoader
        from pyproxy.exceptions import PyProxyError

        try:
            loader = ConfigLoader(self._file_path)
            new_config = loader.load()
            logger.info("Configuration reloaded successfully from %s", self._file_path)

            result = self._on_reload(new_config)
            if asyncio.iscoroutine(result):
                await result

        except PyProxyError as exc:
            logger.error(
                "Failed to reload configuration: %s",
                exc.detail,
                extra={"error_context": exc.to_dict()},
            )
        except Exception:
            logger.exception("Unexpected error during configuration reload")
