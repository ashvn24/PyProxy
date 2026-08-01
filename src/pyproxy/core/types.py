"""Shared type definitions, protocols, and type aliases.

Defines the abstract interfaces (using :class:`typing.Protocol`) that
components implement in later phases. This module establishes the
contract boundaries between subsystems without creating concrete
dependencies.

All protocols are runtime-checkable where feasible to support
``isinstance()`` checks in validation code.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Middleware(Protocol):
    """Protocol for middleware components.

    Middleware processes requests before they reach the upstream and
    responses before they are sent to the client. Implemented in Phase 11.
    """

    async def process_request(self, request: Any) -> Any:
        """Process an incoming request before forwarding.

        Args:
            request: The incoming request object.

        Returns:
            The (possibly modified) request, or a response to short-circuit.
        """
        ...  # pragma: no cover

    async def process_response(self, response: Any) -> Any:
        """Process an outgoing response before sending to the client.

        Args:
            response: The outgoing response object.

        Returns:
            The (possibly modified) response.
        """
        ...  # pragma: no cover


@runtime_checkable
class HealthChecker(Protocol):
    """Protocol for health checking backends.

    Determines whether an upstream target is healthy and capable of
    receiving traffic. Implemented in Phase 8.
    """

    async def check(self, host: str, port: int) -> bool:
        """Perform a health check on the specified target.

        Args:
            host: The upstream host to check.
            port: The upstream port to check.

        Returns:
            True if the target is healthy, False otherwise.
        """
        ...  # pragma: no cover


@runtime_checkable
class LoadBalancerStrategy(Protocol):
    """Protocol for load balancing strategies.

    Selects the next upstream target from a pool of available targets.
    Implemented in Phase 7.
    """

    def select(self, targets: list[Any]) -> Any:
        """Select the next target from the available pool.

        Args:
            targets: List of available upstream targets.

        Returns:
            The selected target.

        Raises:
            UpstreamError: If no targets are available.
        """
        ...  # pragma: no cover


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for cache storage backends.

    Abstracts the cache storage mechanism (in-memory, Redis, etc.).
    Implemented in Phase 12.
    """

    async def get(self, key: str) -> bytes | None:
        """Retrieve a cached value by key.

        Args:
            key: The cache key.

        Returns:
            The cached bytes, or None if not found or expired.
        """
        ...  # pragma: no cover

    async def set(self, key: str, value: bytes, ttl_seconds: int = 0) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key.
            value: The bytes to cache.
            ttl_seconds: Time-to-live in seconds (0 = no expiry).
        """
        ...  # pragma: no cover

    async def delete(self, key: str) -> None:
        """Remove a value from the cache.

        Args:
            key: The cache key to remove.
        """
        ...  # pragma: no cover
