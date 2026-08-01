"""Configuration loading, validation, and hot reload.

This package provides a complete configuration system supporting YAML, JSON,
and TOML file formats, environment variable overrides, and async hot reload.

Example::

    from pyproxy.config import ConfigLoader
    from pathlib import Path

    loader = ConfigLoader(Path("config.yaml"))
    config = loader.load()
    print(config.server.bind_port)
"""

from __future__ import annotations

from pyproxy.config.loader import ConfigLoader
from pyproxy.config.models import (
    LoggingConfig,
    ProxyConfig,
    RouteConfig,
    ServerConfig,
    TlsConfig,
    UpstreamConfig,
    UpstreamTargetConfig,
)
from pyproxy.config.watcher import ConfigWatcher

__all__: list[str] = [
    "ConfigLoader",
    "ConfigWatcher",
    "LoggingConfig",
    "ProxyConfig",
    "RouteConfig",
    "ServerConfig",
    "TlsConfig",
    "UpstreamConfig",
    "UpstreamTargetConfig",
]
