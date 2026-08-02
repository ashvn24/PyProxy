"""PyProxy — A modern, production-grade reverse proxy built on Python asyncio.

This package provides a complete reverse proxy server with load balancing,
health checking, TLS termination, WebSocket support, caching, compression,
authentication, and observability — all built from scratch on asyncio.

Basic usage::

    from pyproxy import Proxy

    proxy = Proxy(config_path="config.yaml")
    proxy.run()

Or via CLI::

    pyproxy start config.yaml
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pyproxy.asgi import PyProxyGateway, PyProxyRouter
from pyproxy.proxy_app import Proxy

try:
    __version__: str = version("python-pyproxy")
except PackageNotFoundError:  # pragma: no cover
    try:
        __version__ = version("pyproxy")
    except PackageNotFoundError:
        __version__ = "0.2.0"

__all__: list[str] = [
    "Proxy",
    "PyProxyGateway",
    "PyProxyRouter",
    "__version__",
]
