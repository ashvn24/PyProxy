"""Request routing engine package.

Provides path, method, host, regex, and longest-prefix route matching.

Example::

    from pyproxy.routing import Router, RouteRule, RouteMatchType

    router = Router()
    router.add_route(RouteRule(path_pattern="/api", priority=10))
    matched_rule = router.match(request)
"""

from __future__ import annotations

from pyproxy.routing.rule import RouteMatchType, RouteRule
from pyproxy.routing.router import Router

__all__: list[str] = [
    "RouteMatchType",
    "RouteRule",
    "Router",
]
