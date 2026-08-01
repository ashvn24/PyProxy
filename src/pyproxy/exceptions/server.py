"""Server-related exceptions.

These exceptions are raised during TCP server lifecycle operations
including binding, connection handling, and shutdown.
"""

from __future__ import annotations

from typing import Any

from pyproxy.exceptions.base import PyProxyError


class ServerError(PyProxyError):
    """Base exception for server lifecycle errors."""

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "SERVER_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a ServerError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code.
            context: Additional diagnostic key-value pairs.
        """
        super().__init__(detail, error_code=error_code, context=context)


class BindError(ServerError):
    """Raised when the server fails to bind to the specified address and port."""

    def __init__(self, host: str, port: int, cause: str) -> None:
        """Initialize a BindError.

        Args:
            host: The bind address that failed.
            port: The port number that failed.
            cause: Description of the bind failure.
        """
        super().__init__(
            f"Failed to bind to {host}:{port}: {cause}",
            error_code="SERVER_BIND_ERROR",
            context={"host": host, "port": port, "cause": cause},
        )


class ShutdownError(ServerError):
    """Raised when an error occurs during graceful server shutdown."""

    def __init__(self, detail: str) -> None:
        """Initialize a ShutdownError.

        Args:
            detail: Description of what went wrong during shutdown.
        """
        super().__init__(
            detail,
            error_code="SERVER_SHUTDOWN_ERROR",
        )
