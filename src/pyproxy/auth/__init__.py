"""Authentication middleware package.

Example::

    from pyproxy.auth import AuthMiddleware

    auth = AuthMiddleware(valid_api_keys={"secret-key-123"})
"""

from __future__ import annotations

from pyproxy.auth.middleware import AuthMiddleware

__all__: list[str] = [
    "AuthMiddleware",
]
