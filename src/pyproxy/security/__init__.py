"""Security enforcement package.

Provides IP filtering (allowlist/denylist), token bucket rate limiting, and CORS handling.

Example::

    from pyproxy.security import IPFilter, RateLimiter, CORSMiddleware

    ip_filter = IPFilter(denylist=["192.168.1.100"])
    is_ok = ip_filter.is_allowed(client_ip)
"""

from __future__ import annotations

from pyproxy.security.cors import CORSMiddleware
from pyproxy.security.ip_filter import IPFilter
from pyproxy.security.rate_limiter import RateLimiter

__all__: list[str] = [
    "CORSMiddleware",
    "IPFilter",
    "RateLimiter",
]
