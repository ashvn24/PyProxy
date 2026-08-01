"""Load Balancer Engine.

Combines pluggable selection strategies with optional sticky session affinity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyproxy.load_balancer.strategies import (
    IPHashStrategy,
    LeastConnectionsStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    WeightedRoundRobinStrategy,
)

if TYPE_CHECKING:
    from pyproxy.core.types import LoadBalancerStrategy
    from pyproxy.protocol.request import HTTPRequest
    from pyproxy.upstream.target import UpstreamTarget

logger = logging.getLogger("pyproxy.load_balancer")


class LoadBalancer:
    """Main Load Balancer component for upstream target selection."""

    def __init__(
        self,
        strategy: str = "round_robin",
        sticky_cookie: str = "PYPROXY_SESSION",
    ) -> None:
        """Initialize LoadBalancer.

        Args:
            strategy: Strategy algorithm identifier ("round_robin", "weighted_rr", "least_conn", "ip_hash", "random").
            sticky_cookie: Name of cookie used for sticky session affinity.
        """
        self.sticky_cookie: str = sticky_cookie
        self._strategy: Any = self._resolve_strategy(strategy)
        self._sticky_sessions: dict[str, UpstreamTarget] = {}

    def _resolve_strategy(self, name: str) -> Any:
        strategies = {
            "round_robin": RoundRobinStrategy(),
            "weighted_rr": WeightedRoundRobinStrategy(),
            "least_conn": LeastConnectionsStrategy(),
            "ip_hash": IPHashStrategy(),
            "random": RandomStrategy(),
        }
        return strategies.get(name.lower(), RoundRobinStrategy())

    def select_target(
        self,
        targets: list[UpstreamTarget],
        request: HTTPRequest | None = None,
        client_ip: str = "",
        sticky: bool = False,
    ) -> UpstreamTarget:
        """Select an upstream target for the current request.

        Args:
            targets: List of candidate UpstreamTarget objects.
            request: Optional HTTPRequest context.
            client_ip: Client IP address string.
            sticky: Whether to enforce sticky session affinity.

        Returns:
            Selected UpstreamTarget object.
        """
        if not targets:
            raise UpstreamError("No upstream targets specified in pool")

        # 1. Sticky session check
        if sticky and request:
            session_key = request.cookies.get(self.sticky_cookie)
            if session_key and session_key in self._sticky_sessions:
                pinned_target = self._sticky_sessions[session_key]
                if pinned_target in targets and pinned_target.is_healthy:
                    logger.debug("Sticky session hit for key %s -> %s", session_key, pinned_target.endpoint)
                    return pinned_target

        # 2. Delegate to active load balancing strategy
        selected = self._strategy.select(targets=targets, request=request, client_ip=client_ip)

        # 3. Associate sticky session if requested
        if sticky and request:
            session_key = request.cookies.get(self.sticky_cookie)
            if session_key:
                self._sticky_sessions[session_key] = selected

        return selected
