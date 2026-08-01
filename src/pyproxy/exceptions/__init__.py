"""Exception hierarchy for PyProxy.

All exceptions inherit from :class:`PyProxyError` and carry structured context
for operational debugging and monitoring. Import exceptions directly from this
package::

    from pyproxy.exceptions import ConfigValidationError, RouteNotFoundError
"""

from __future__ import annotations

from pyproxy.exceptions.base import PyProxyError
from pyproxy.exceptions.config import (
    ConfigError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)
from pyproxy.exceptions.protocol import (
    HttpParseError,
    ProtocolError,
    TlsError,
    WebSocketError,
)
from pyproxy.exceptions.routing import (
    RouteConflictError,
    RouteNotFoundError,
    RoutingError,
)
from pyproxy.exceptions.security import (
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    SecurityError,
)
from pyproxy.exceptions.server import (
    BindError,
    ServerError,
    ShutdownError,
)
from pyproxy.exceptions.upstream import (
    UpstreamConnectionError,
    UpstreamError,
    UpstreamResponseError,
    UpstreamTimeoutError,
)

__all__: list[str] = [
    # Base
    "PyProxyError",
    # Config
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    "ConfigValidationError",
    # Server
    "ServerError",
    "BindError",
    "ShutdownError",
    # Routing
    "RoutingError",
    "RouteNotFoundError",
    "RouteConflictError",
    # Upstream
    "UpstreamError",
    "UpstreamConnectionError",
    "UpstreamTimeoutError",
    "UpstreamResponseError",
    # Security
    "SecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitExceededError",
    # Protocol
    "ProtocolError",
    "HttpParseError",
    "WebSocketError",
    "TlsError",
]
