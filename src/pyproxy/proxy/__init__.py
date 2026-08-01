"""Reverse proxy engine package.

Handles request forwarding, path rewriting, header manipulation, and response streaming.

Example::

    from pyproxy.proxy import ProxyEngine

    engine = ProxyEngine()
    bytes_sent = await engine.forward(client_conn, request, route_rule, target)
"""

from __future__ import annotations

from pyproxy.proxy.engine import ProxyEngine
from pyproxy.proxy.headers import HeaderRewriter

__all__: list[str] = [
    "HeaderRewriter",
    "ProxyEngine",
]
