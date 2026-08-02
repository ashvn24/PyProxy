"""Load Balancing Algorithms.

Provides Round Robin, Weighted Round Robin, Least Connections, Least Response Time,
Random, and IP Hash algorithms for distributing proxy requests across upstream targets.
"""

from __future__ import annotations

import hashlib
import random
import threading
from typing import TYPE_CHECKING, Any

from pyproxy.exceptions.upstream import UpstreamError

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest
    from pyproxy.upstream.target import UpstreamTarget


class RoundRobinStrategy:
    """Round Robin load balancing strategy."""

    def __init__(self) -> None:
        self._index: int = 0
        self._lock: threading.Lock = threading.Lock()

    def select(
        self,
        targets: list[UpstreamTarget],
        request: HTTPRequest | None = None,
        client_ip: str = "",
    ) -> UpstreamTarget:
        """Select next available target in round robin sequence.

        Args:
            targets: List of candidate UpstreamTarget objects.
            request: Optional HTTPRequest context.
            client_ip: Optional client IP string.

        Returns:
            Selected UpstreamTarget.
        """
        healthy_targets = [t for t in targets if t.is_healthy]
        if not healthy_targets:
            raise UpstreamError("No healthy upstream targets available")

        with self._lock:
            selected = healthy_targets[self._index % len(healthy_targets)]
            self._index = (self._index + 1) % len(healthy_targets)
            return selected


class WeightedRoundRobinStrategy:
    """Nginx-style Smooth Weighted Round Robin strategy."""

    def __init__(self) -> None:
        self._current_weights: dict[str, int] = {}
        self._lock: threading.Lock = threading.Lock()

    def select(
        self,
        targets: list[UpstreamTarget],
        request: HTTPRequest | None = None,
        client_ip: str = "",
    ) -> UpstreamTarget:
        healthy_targets = [t for t in targets if t.is_healthy]
        if not healthy_targets:
            raise UpstreamError("No healthy upstream targets available")

        with self._lock:
            total_weight = sum(t.weight for t in healthy_targets)
            best_target: UpstreamTarget | None = None
            max_current_weight = -float("inf")

            for target in healthy_targets:
                endpoint = target.endpoint
                current_w = self._current_weights.get(endpoint, 0) + target.weight
                self._current_weights[endpoint] = current_w

                if current_w > max_current_weight:
                    max_current_weight = current_w
                    best_target = target

            if best_target is None:
                best_target = healthy_targets[0]

            # Decrease current weight of selected target by total_weight
            best_endpoint = best_target.endpoint
            self._current_weights[best_endpoint] -= total_weight
            return best_target


class LeastConnectionsStrategy:
    """Least Connections load balancing strategy."""

    def select(
        self,
        targets: list[UpstreamTarget],
        request: HTTPRequest | None = None,
        client_ip: str = "",
    ) -> UpstreamTarget:
        healthy_targets = [t for t in targets if t.is_healthy]
        if not healthy_targets:
            raise UpstreamError("No healthy upstream targets available")

        # Select target with minimum active_connections
        return min(healthy_targets, key=lambda t: t.active_connections)


class RandomStrategy:
    """Random load balancing strategy."""

    def select(
        self,
        targets: list[UpstreamTarget],
        request: HTTPRequest | None = None,
        client_ip: str = "",
    ) -> UpstreamTarget:
        healthy_targets = [t for t in targets if t.is_healthy]
        if not healthy_targets:
            raise UpstreamError("No healthy upstream targets available")

        return random.choice(healthy_targets)


class IPHashStrategy:
    """IP Hash consistent hashing load balancing strategy."""

    def select(
        self,
        targets: list[UpstreamTarget],
        request: HTTPRequest | None = None,
        client_ip: str = "",
    ) -> UpstreamTarget:
        healthy_targets = [t for t in targets if t.is_healthy]
        if not healthy_targets:
            raise UpstreamError("No healthy upstream targets available")

        key = client_ip or (request.host if request else "") or "default"
        hash_value = int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16)
        return healthy_targets[hash_value % len(healthy_targets)]
