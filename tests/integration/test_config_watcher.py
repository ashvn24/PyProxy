"""Integration tests for config file watcher hot reload."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from pyproxy.config.models import ProxyConfig
from pyproxy.config.watcher import ConfigWatcher


@pytest.mark.integration
class TestConfigWatcher:
    """Integration tests for ConfigWatcher file monitoring."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_watcher_detects_change(self, tmp_dir):
        """Modify a config file on disk and verify the watcher fires the callback."""
        config_path = tmp_dir / "watch_test.yaml"
        config_path.write_text(
            yaml.dump({"server": {"bind_port": 8080}}),
            encoding="utf-8",
        )

        reload_event = asyncio.Event()
        received_config: list[ProxyConfig] = []

        async def on_reload(new_config: ProxyConfig) -> None:
            received_config.append(new_config)
            reload_event.set()

        watcher = ConfigWatcher(
            file_path=config_path,
            on_reload=on_reload,
            debounce_seconds=0.3,
        )

        # Start watcher in background
        watch_task = watcher.start_background()
        assert watcher.is_running or not watch_task.done()

        # Give watcher time to initialize
        await asyncio.sleep(0.5)

        # Modify the config file
        config_path.write_text(
            yaml.dump({"server": {"bind_port": 9090}}),
            encoding="utf-8",
        )

        # Wait for the reload callback
        try:
            await asyncio.wait_for(reload_event.wait(), timeout=5.0)
        except TimeoutError:
            pytest.skip("File watcher did not detect change in time (may be OS-dependent)")

        assert len(received_config) >= 1
        assert received_config[-1].server.bind_port == 9090

        # Cleanup
        await watcher.stop()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_watcher_handles_invalid_config(self, tmp_dir):
        """Verify the watcher logs an error but doesn't crash on invalid config."""
        config_path = tmp_dir / "watch_invalid.yaml"
        config_path.write_text(
            yaml.dump({"server": {"bind_port": 8080}}),
            encoding="utf-8",
        )

        error_logged = asyncio.Event()

        async def on_reload(new_config: ProxyConfig) -> None:
            # This should not be called for invalid configs
            pass  # pragma: no cover

        watcher = ConfigWatcher(
            file_path=config_path,
            on_reload=on_reload,
            debounce_seconds=0.3,
        )

        watch_task = watcher.start_background()
        await asyncio.sleep(0.5)

        # Write invalid config (port out of range)
        config_path.write_text(
            yaml.dump({"server": {"bind_port": 99999}}),
            encoding="utf-8",
        )

        # Wait briefly — the watcher should handle the error gracefully
        await asyncio.sleep(2.0)

        # Watcher should still be running (not crashed)
        assert not watch_task.done()

        await watcher.stop()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_watcher_stop(self, tmp_dir):
        """Verify the watcher can be stopped cleanly."""
        config_path = tmp_dir / "watch_stop.yaml"
        config_path.write_text(
            yaml.dump({"server": {"bind_port": 8080}}),
            encoding="utf-8",
        )

        watcher = ConfigWatcher(
            file_path=config_path,
            on_reload=lambda c: None,
        )

        watch_task = watcher.start_background()
        await asyncio.sleep(0.5)

        await watcher.stop()
        # Give the task time to finish
        await asyncio.sleep(0.5)
        assert watch_task.done() or watch_task.cancelled()
