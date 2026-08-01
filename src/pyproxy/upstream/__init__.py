"""Upstream backend connection and pooling package.

Provides backend server target models and connection pools for idle socket reuse.

Example::

    from pyproxy.upstream import UpstreamTarget, UpstreamConnectionPool

    pool = UpstreamConnectionPool()
    target = UpstreamTarget(host="127.0.0.1", port=3000)
    conn = await pool.acquire(target)
"""

from __future__ import annotations

from pyproxy.upstream.pool import UpstreamConnection, UpstreamConnectionPool
from pyproxy.upstream.target import UpstreamTarget

__all__: list[str] = [
    "UpstreamConnection",
    "UpstreamConnectionPool",
    "UpstreamTarget",
]
