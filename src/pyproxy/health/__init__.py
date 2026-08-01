"""Health checking and circuit breaker package.

Example::

    from pyproxy.health import HealthChecker, CircuitBreaker

    checker = HealthChecker()
    await checker.probe_target(target)
"""

from __future__ import annotations

from pyproxy.health.checker import HealthChecker
from pyproxy.health.circuit_breaker import CircuitBreaker, CircuitState

__all__: list[str] = [
    "CircuitBreaker",
    "CircuitState",
    "HealthChecker",
]
