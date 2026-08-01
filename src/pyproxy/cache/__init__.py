"""Response caching package.

Example::

    from pyproxy.cache import CacheManager, MemoryCache

    cache_manager = CacheManager()
    key = cache_manager.compute_cache_key(request)
"""

from __future__ import annotations

from pyproxy.cache.manager import CacheManager
from pyproxy.cache.memory import MemoryCache

__all__: list[str] = [
    "CacheManager",
    "MemoryCache",
]
