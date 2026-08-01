"""Unit tests for LoadBalancer strategies."""

from __future__ import annotations

import pytest

from pyproxy.load_balancer import (
    IPHashStrategy,
    LeastConnectionsStrategy,
    LoadBalancer,
    RoundRobinStrategy,
    WeightedRoundRobinStrategy,
)
from pyproxy.upstream import UpstreamTarget


class TestLoadBalancerStrategies:
    """Tests for individual load balancing algorithms."""

    def test_round_robin(self):
        t1 = UpstreamTarget(host="10.0.0.1", port=80)
        t2 = UpstreamTarget(host="10.0.0.2", port=80)
        targets = [t1, t2]

        strategy = RoundRobinStrategy()
        assert strategy.select(targets) is t1
        assert strategy.select(targets) is t2
        assert strategy.select(targets) is t1

    def test_least_connections(self):
        t1 = UpstreamTarget(host="10.0.0.1", active_connections=5)
        t2 = UpstreamTarget(host="10.0.0.2", active_connections=1)
        targets = [t1, t2]

        strategy = LeastConnectionsStrategy()
        assert strategy.select(targets) is t2

    def test_ip_hash_consistency(self):
        t1 = UpstreamTarget(host="10.0.0.1", port=80)
        t2 = UpstreamTarget(host="10.0.0.2", port=80)
        targets = [t1, t2]

        strategy = IPHashStrategy()
        res1 = strategy.select(targets, client_ip="192.168.1.50")
        res2 = strategy.select(targets, client_ip="192.168.1.50")

        assert res1 is res2

    def test_weighted_round_robin(self):
        t1 = UpstreamTarget(host="10.0.0.1", weight=3)
        t2 = UpstreamTarget(host="10.0.0.2", weight=1)
        targets = [t1, t2]

        strategy = WeightedRoundRobinStrategy()
        selected = [strategy.select(targets) for _ in range(4)]
        # Target 1 (weight 3) should be selected 3 times out of 4
        assert selected.count(t1) == 3
        assert selected.count(t2) == 1
