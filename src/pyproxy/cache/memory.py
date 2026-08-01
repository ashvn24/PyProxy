"""In-Memory Response Cache Backend.

Thread-safe, TTL-aware in-memory cache implementing CacheBackend protocol.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pyproxy.core.types import CacheBackend


class CacheItem:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: bytes, ttl_seconds: float = 0.0) -> None:
        self.value: bytes = value
        self.expires_at: float = time.monotonic() + ttl_seconds if ttl_seconds > 0.0 else 0.0

    @property
    def is_expired(self) -> bool:
        if self.expires_at == 0.0:
            return False
        return time.monotonic() > self.expires_at


class MemoryCache(CacheBackend):
    """In-memory cache implementation."""

    def __init__(self, max_items: int = 1000) -> None:
        self.max_items: int = max_items
        self._store: dict[str, CacheItem] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, key: str) -> bytes | None:
        """Get cached value for key.

        Args:
            key: Cache key.

        Returns:
            Cached bytes or None if missing/expired.
        """
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            if item.is_expired:
                del self._store[key]
                return None
            return item.value

    async def set(self, key: str, value: bytes, ttl_seconds: int = 0) -> None:
        """Set cached value with optional TTL.

        Args:
            key: Cache key.
            value: Data bytes.
            ttl_seconds: Expiration delay in seconds.
        """
        async with self._lock:
            if len(self._store) >= self.max_items:
                # Simple evict expired or oldest key
                expired_keys = [k for k, item in self._store.items() if item.is_expired]
                if expired_keys:
                    for k in expired_keys:
                        del self._store[k]
                elif self._store:
                    first_key = next(iter(self._store))
                    del self._store[first_key]

            self._store[key] = CacheItem(value, float(ttl_seconds))

    async def delete(self, key: str) -> None:
        """Delete key from cache.

        Args:
            key: Cache key.
        """
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._store.clear()
