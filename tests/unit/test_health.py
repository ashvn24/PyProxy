"""Unit tests for CircuitBreaker and HealthChecker."""

from __future__ import annotations

import pytest

from pyproxy.health import CircuitBreaker, CircuitState, HealthChecker
from pyproxy.upstream import UpstreamTarget


class TestCircuitBreaker:
    """Tests for CircuitBreaker state transitions."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=2)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_trips_to_open_on_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED


class TestHealthChecker:
    """Tests for HealthChecker passive and active methods."""

    def test_passive_record(self):
        checker = HealthChecker(unhealthy_threshold=2)
        target = UpstreamTarget(host="127.0.0.1", port=80)

        checker.record_passive_failure(target)
        assert target.is_healthy is True

        checker.record_passive_failure(target)
        assert target.is_healthy is False
