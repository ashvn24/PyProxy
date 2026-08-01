"""Upstream-related exceptions.

These exceptions are raised during communication with upstream/backend servers.
"""

from __future__ import annotations

from typing import Any

from pyproxy.exceptions.base import PyProxyError


class UpstreamError(PyProxyError):
    """Base exception for upstream communication errors."""

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "UPSTREAM_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an UpstreamError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code.
            context: Additional diagnostic key-value pairs.
        """
        super().__init__(detail, error_code=error_code, context=context)


class UpstreamConnectionError(UpstreamError):
    """Raised when a connection to an upstream server fails."""

    def __init__(self, host: str, port: int, cause: str) -> None:
        """Initialize an UpstreamConnectionError.

        Args:
            host: The upstream host that failed.
            port: The upstream port that failed.
            cause: Description of the connection failure.
        """
        super().__init__(
            f"Failed to connect to upstream {host}:{port}: {cause}",
            error_code="UPSTREAM_CONNECTION_ERROR",
            context={"host": host, "port": port, "cause": cause},
        )


class UpstreamTimeoutError(UpstreamError):
    """Raised when an upstream request exceeds the configured timeout."""

    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        """Initialize an UpstreamTimeoutError.

        Args:
            host: The upstream host that timed out.
            port: The upstream port that timed out.
            timeout_seconds: The timeout duration that was exceeded.
        """
        super().__init__(
            f"Upstream {host}:{port} timed out after {timeout_seconds}s",
            error_code="UPSTREAM_TIMEOUT",
            context={
                "host": host,
                "port": port,
                "timeout_seconds": timeout_seconds,
            },
        )


class UpstreamResponseError(UpstreamError):
    """Raised when the upstream returns an invalid or unexpected response."""

    def __init__(self, host: str, port: int, cause: str) -> None:
        """Initialize an UpstreamResponseError.

        Args:
            host: The upstream host.
            port: The upstream port.
            cause: Description of the response error.
        """
        super().__init__(
            f"Invalid response from upstream {host}:{port}: {cause}",
            error_code="UPSTREAM_RESPONSE_ERROR",
            context={"host": host, "port": port, "cause": cause},
        )
