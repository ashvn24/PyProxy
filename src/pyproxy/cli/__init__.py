"""Command-line interface for PyProxy.

Provides the ``pyproxy`` CLI with subcommands for managing the
reverse proxy server.

Usage::

    pyproxy version
    pyproxy validate config.yaml
    pyproxy start config.yaml
"""

from __future__ import annotations

from pyproxy.cli.main import cli_entry_point, main

__all__: list[str] = [
    "cli_entry_point",
    "main",
]
