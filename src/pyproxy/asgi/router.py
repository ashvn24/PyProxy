"""PyProxy FastAPI Router Extension.

Provides PyProxyRouter to mount dynamic reverse proxy routes directly on
FastAPI / Starlette applications or APIRouter instances.
"""

from __future__ import annotations

from typing import Any
from pyproxy.asgi.gateway import PyProxyGateway


class PyProxyRouter:
    """Convenience router wrapper for FastAPI application integration.

    Example::

        from fastapi import FastAPI
        from pyproxy.asgi import PyProxyRouter

        app = FastAPI()
        proxy_router = PyProxyRouter()
        proxy_router.add_route("/api", target="http://127.0.0.1:8001")
        app.mount("/proxy", proxy_router.gateway)
    """

    def __init__(self, routes: list[dict[str, Any]] | None = None) -> None:
        """Initialize PyProxyRouter.

        Args:
            routes: Optional initial route list.
        """
        self.gateway = PyProxyGateway(routes=routes)

    def add_route(
        self,
        path: str,
        target: str,
        strip_prefix: bool = False,
        methods: set[str] | list[str] | None = None,
    ) -> None:
        """Add a proxy route target.

        Args:
            path: Route path prefix.
            target: Upstream service target URL.
            strip_prefix: Whether to strip prefix before forwarding.
            methods: HTTP methods filter.
        """
        self.gateway.add_route(
            path=path,
            target=target,
            strip_prefix=strip_prefix,
            methods=methods,
        )
