"""Routing-related exceptions.

These exceptions are raised during route matching and route table management.
"""

from __future__ import annotations

from typing import Any

from pyproxy.exceptions.base import PyProxyError


class RoutingError(PyProxyError):
    """Base exception for routing engine errors."""

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "ROUTING_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a RoutingError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code.
            context: Additional diagnostic key-value pairs.
        """
        super().__init__(detail, error_code=error_code, context=context)


class RouteNotFoundError(RoutingError):
    """Raised when no route matches the incoming request."""

    def __init__(self, path: str, method: str, host: str = "") -> None:
        """Initialize a RouteNotFoundError.

        Args:
            path: The request path that had no matching route.
            method: The HTTP method of the request.
            host: The Host header value, if any.
        """
        super().__init__(
            f"No route found for {method} {path}",
            error_code="ROUTE_NOT_FOUND",
            context={"path": path, "method": method, "host": host},
        )


class RouteConflictError(RoutingError):
    """Raised when a route definition conflicts with an existing route."""

    def __init__(self, path: str, conflict_with: str) -> None:
        """Initialize a RouteConflictError.

        Args:
            path: The new route path that conflicts.
            conflict_with: The existing route path it conflicts with.
        """
        super().__init__(
            f"Route '{path}' conflicts with existing route '{conflict_with}'",
            error_code="ROUTE_CONFLICT",
            context={"path": path, "conflict_with": conflict_with},
        )
