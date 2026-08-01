"""Active and Passive Health Checker.

Monitors upstream target operational status via active probes and passive error tracking.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pyproxy.health.circuit_breaker import CircuitBreaker

if TYPE_CHECKING:
    from pyproxy.upstream.target import UpstreamTarget

logger = logging.getLogger("pyproxy.health.checker")


class HealthChecker:
    """Manages active probing and passive monitoring of upstream targets."""

    def __init__(
        self,
        check_interval: float = 10.0,
        check_timeout: float = 3.0,
        unhealthy_threshold: int = 3,
        healthy_threshold: int = 2,
    ) -> None:
        """Initialize HealthChecker.

        Args:
            check_interval: Seconds between active probes.
            check_timeout: Active probe socket timeout in seconds.
            unhealthy_threshold: Failures to mark target unhealthy.
            healthy_threshold: Successes to mark target healthy.
        """
        self.check_interval: float = check_interval
        self.check_timeout: float = check_timeout
        self.unhealthy_threshold: int = unhealthy_threshold
        self.healthy_threshold: int = healthy_threshold

        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._running: bool = False
        self._task: asyncio.Task[None] | None = None

    def get_circuit_breaker(self, target: UpstreamTarget) -> CircuitBreaker:
        """Get or create CircuitBreaker for an upstream target.

        Args:
            target: UpstreamTarget object.

        Returns:
            CircuitBreaker instance for target.
        """
        endpoint = target.endpoint
        if endpoint not in self._circuit_breakers:
            self._circuit_breakers[endpoint] = CircuitBreaker(
                failure_threshold=self.unhealthy_threshold,
                success_threshold=self.healthy_threshold,
            )
        return self._circuit_breakers[endpoint]

    def record_passive_success(self, target: UpstreamTarget) -> None:
        """Record passive HTTP request success from proxy forwarding engine.

        Args:
            target: UpstreamTarget object.
        """
        cb = self.get_circuit_breaker(target)
        cb.record_success()
        target.is_healthy = cb.allow_request()

    def record_passive_failure(self, target: UpstreamTarget) -> None:
        """Record passive HTTP request failure from proxy forwarding engine.

        Args:
            target: UpstreamTarget object.
        """
        cb = self.get_circuit_breaker(target)
        cb.record_failure()
        target.is_healthy = cb.allow_request()
        if not target.is_healthy:
            logger.warning("Target %s marked UNHEALTHY via passive failure", target.endpoint)

    async def probe_target(self, target: UpstreamTarget) -> bool:
        """Perform an active TCP probe against target.

        Args:
            target: UpstreamTarget object.

        Returns:
            True if socket connection succeeds.
        """
        try:
            async with asyncio.timeout(self.check_timeout):
                reader, writer = await asyncio.open_connection(target.host, target.port)
                writer.close()
                await writer.wait_closed()
                self.record_passive_success(target)
                return True
        except Exception:
            self.record_passive_failure(target)
            return False

    async def start(self, targets: list[UpstreamTarget]) -> None:
        """Start active health checking background loop.

        Args:
            targets: List of UpstreamTarget objects to monitor.
        """
        self._running = True
        self._task = asyncio.create_task(self._run_loop(targets))
        logger.info("Started active health checker loop (%ds interval)", self.check_interval)

    async def stop(self) -> None:
        """Stop active health checking background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Stopped active health checker loop")

    async def _run_loop(self, targets: list[UpstreamTarget]) -> None:
        while self._running:
            try:
                probe_tasks = [self.probe_target(t) for t in targets]
                if probe_tasks:
                    await asyncio.gather(*probe_tasks, return_exceptions=True)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exception:
                logger.error("Error in health check loop: %s", exception)
                await asyncio.sleep(self.check_interval)
