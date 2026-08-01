"""Middleware pipeline engine package.

Example::

    from pyproxy.middleware import BaseMiddleware, MiddlewarePipeline

    pipeline = MiddlewarePipeline()
    pipeline.add_middleware(MyCustomMiddleware())
"""

from __future__ import annotations

from pyproxy.middleware.pipeline import BaseMiddleware, MiddlewarePipeline

__all__: list[str] = [
    "BaseMiddleware",
    "MiddlewarePipeline",
]
