"""WebSocket proxy engine package.

Example::

    from pyproxy.websocket import WebSocketProxy

    ws_proxy = WebSocketProxy()
    await ws_proxy.proxy_websocket(client_conn, request, upstream_conn)
"""

from __future__ import annotations

from pyproxy.websocket.proxy import WebSocketProxy

__all__: list[str] = [
    "WebSocketProxy",
]
