"""Core infrastructure: dependency injection and shared type definitions.

This package provides the DI container and the protocol interfaces
that define contracts between subsystems.

Example::

    from pyproxy.core import Container, Lifetime

    container = Container()
    container.register_singleton(MyService, lambda: MyService())
"""

from __future__ import annotations

from pyproxy.core.container import Container, Lifetime
from pyproxy.core.types import (
    CacheBackend,
    HealthChecker,
    LoadBalancerStrategy,
    Middleware,
)

__all__: list[str] = [
    "CacheBackend",
    "Container",
    "HealthChecker",
    "Lifetime",
    "LoadBalancerStrategy",
    "Middleware",
]
