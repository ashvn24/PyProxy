"""PyProxy Routing Engine.

Manages active route rules and resolves incoming HTTP requests to their
optimal matching upstream target configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

from pyproxy.exceptions.routing import RouteNotFoundError
from pyproxy.routing.rule import RouteMatchType, RouteRule

if TYPE_CHECKING:
    from pyproxy.config.models import RouteConfig
    from pyproxy.protocol.request import HTTPRequest

logger = logging.getLogger("pyproxy.routing.router")


class Router:
    """Core request router supporting longest-prefix and priority matching."""

    __slots__ = ("_rules",)

    def __init__(self, rules: Sequence[RouteRule] | None = None) -> None:
        """Initialize Router.

        Args:
            rules: Initial sequence of RouteRule objects.
        """
        self._rules: list[RouteRule] = list(rules) if rules else []
        self._sort_rules()

    @property
    def routes(self) -> list[RouteRule]:
        """Get copy of active route rules in evaluation order.

        Returns:
            List of RouteRule objects.
        """
        return list(self._rules)

    def add_route(self, rule: RouteRule) -> None:
        """Add a new route rule to the router.

        Args:
            rule: RouteRule object to add.
        """
        self._rules.append(rule)
        self._sort_rules()

    def load_from_config(self, route_configs: Sequence[RouteConfig]) -> None:
        """Load and replace active routes from configuration models.

        Args:
            route_configs: Sequence of RouteConfig models.
        """
        self._rules = [RouteRule.from_config(config) for config in route_configs]
        self._sort_rules()
        logger.info("Loaded %d routes into routing table", len(self._rules))

    def match(self, request: HTTPRequest) -> RouteRule:
        """Find the highest-priority matching RouteRule for an HTTPRequest.

        Args:
            request: Incoming HTTPRequest model.

        Returns:
            The matching RouteRule instance.

        Raises:
            RouteNotFoundError: If no matching route is found.
        """
        for rule in self._rules:
            if rule.matches(request):
                logger.debug(
                    "Matched request %s %s to route pattern '%s'",
                    request.method,
                    request.path,
                    rule.path_pattern,
                )
                return rule

        raise RouteNotFoundError(
            path=request.path,
            method=request.method,
            host=request.host,
        )

    def _sort_rules(self) -> None:
        """Sort rules by priority DESC, then by prefix path length DESC."""
        def sort_key(rule: RouteRule) -> tuple[int, int, int]:
            # Priority first, then host specificity, then pattern length
            host_spec = len(rule.host_pattern)
            pattern_len = len(rule.path_pattern) if rule.match_type == RouteMatchType.PREFIX else 0
            return (rule.priority, host_spec, pattern_len)

        self._rules.sort(key=sort_key, reverse=True)
