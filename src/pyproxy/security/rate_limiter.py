"""Token Bucket Rate Limiter.

Provides sliding window token bucket rate limiting per client IP address.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any


class TokenBucket:
    __slots__ = ("capacity", "refill_rate", "tokens", "last_update")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity: int = capacity
        self.refill_rate: float = refill_rate
        self.tokens: float = float(capacity)
        self.last_update: float = time.monotonic()

    def consume(self, tokens_requested: int = 1) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Add refilled tokens
        self.tokens = min(float(self.capacity), self.tokens + elapsed * self.refill_rate)

        if self.tokens >= tokens_requested:
            self.tokens -= tokens_requested
            return True
        return False


class RateLimiter:
    """Per-IP Token Bucket Rate Limiter."""

    def __init__(self, requests_per_second: float = 100.0, burst: int = 200) -> None:
        """Initialize RateLimiter.

        Args:
            requests_per_second: Allowed sustained requests per second.
            burst: Maximum burst bucket capacity.
        """
        self.requests_per_second: float = requests_per_second
        self.burst: int = burst
        self._buckets: dict[str, TokenBucket] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def is_allowed(self, client_identifier: str) -> bool:
        """Check if request from client_identifier is within rate limits.

        Args:
            client_identifier: Client IP or identifier string.

        Returns:
            True if allowed; False if rate limit exceeded.
        """
        if not client_identifier:
            return True

        async with self._lock:
            if client_identifier not in self._buckets:
                self._buckets[client_identifier] = TokenBucket(
                    capacity=self.burst,
                    refill_rate=self.requests_per_second,
                )
            bucket = self._buckets[client_identifier]
            return bucket.consume(1)
