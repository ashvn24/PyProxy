"""Load balancing algorithms and session affinity package.

Example::

    from pyproxy.load_balancer import LoadBalancer

    balancer = LoadBalancer(strategy="weighted_rr")
    target = balancer.select_target(targets, request)
"""

from __future__ import annotations

from pyproxy.load_balancer.balancer import LoadBalancer
from pyproxy.load_balancer.strategies import (
    IPHashStrategy,
    LeastConnectionsStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    WeightedRoundRobinStrategy,
)

__all__: list[str] = [
    "IPHashStrategy",
    "LeastConnectionsStrategy",
    "LoadBalancer",
    "RandomStrategy",
    "RoundRobinStrategy",
    "WeightedRoundRobinStrategy",
]
