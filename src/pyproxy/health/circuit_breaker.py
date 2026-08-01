"""Circuit Breaker Pattern for Upstream Targets.

Prevents cascade failures by isolating failing upstream backends and managing
half-open state recovery.
"""

from __future__ import annotations

import enum
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyproxy.upstream.target import UpstreamTarget

logger = logging.getLogger("pyproxy.health.circuit_breaker")


class CircuitState(enum.Enum):
    """Circuit breaker operational state."""

    CLOSED = "closed"        # Normal operation: traffic flows freely
    OPEN = "open"            # Target failing: traffic blocked
    HALF_OPEN = "half_open"  # Recovery testing: limited trial requests allowed


class CircuitBreaker:
    """Circuit Breaker manager for individual or pooled upstream targets.

    Attributes:
        failure_threshold: Consecutive failures to trip circuit OPEN.
        recovery_timeout: Seconds in OPEN state before trying HALF_OPEN recovery.
        success_threshold: Consecutive successes in HALF_OPEN to return CLOSED.
    """

    __slots__ = (
        "failure_threshold",
        "recovery_timeout",
        "success_threshold",
        "_state",
        "_consecutive_failures",
        "_consecutive_successes",
        "_last_state_change_time",
    )

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ) -> None:
        """Initialize CircuitBreaker.

        Args:
            failure_threshold: Failure count to trip OPEN.
            recovery_timeout: Delay before probing HALF_OPEN.
            success_threshold: Success count to reset CLOSED.
        """
        self.failure_threshold: int = failure_threshold
        self.recovery_timeout: float = recovery_timeout
        self.success_threshold: int = success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._consecutive_successes: int = 0
        self._last_state_change_time: float = time.monotonic()

    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state, checking for recovery timeout transition.

        Returns:
            Current CircuitState.
        """
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_state_change_time
            if elapsed >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def allow_request(self) -> bool:
        """Check if request is allowed through circuit breaker.

        Returns:
            True if state is CLOSED or HALF_OPEN.
        """
        current_state = self.state
        return current_state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful upstream request."""
        current_state = self.state
        self._consecutive_failures = 0

        if current_state == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def record_failure(self) -> None:
        """Record an upstream request failure."""
        current_state = self.state
        self._consecutive_successes = 0
        self._consecutive_failures += 1

        if current_state == CircuitState.CLOSED:
            if self._consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
        elif current_state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        logger.info(
            "CircuitBreaker state transition: %s -> %s",
            self._state.value,
            new_state.value,
        )
        self._state = new_state
        self._last_state_change_time = time.monotonic()
        self._consecutive_failures = 0
        self._consecutive_successes = 0
