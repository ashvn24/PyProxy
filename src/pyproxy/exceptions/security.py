"""Security-related exceptions.

These exceptions are raised during authentication, authorization,
and security policy enforcement.
"""

from __future__ import annotations

from typing import Any

from pyproxy.exceptions.base import PyProxyError


class SecurityError(PyProxyError):
    """Base exception for security-related errors."""

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "SECURITY_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a SecurityError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code.
            context: Additional diagnostic key-value pairs.
        """
        super().__init__(detail, error_code=error_code, context=context)


class AuthenticationError(SecurityError):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""

    def __init__(self, detail: str, *, scheme: str = "unknown") -> None:
        """Initialize an AuthenticationError.

        Args:
            detail: Description of the authentication failure.
            scheme: The authentication scheme that failed (e.g., "bearer", "basic").
        """
        super().__init__(
            detail,
            error_code="AUTHENTICATION_ERROR",
            context={"scheme": scheme},
        )


class AuthorizationError(SecurityError):
    """Raised when an authenticated user lacks permission for the requested action."""

    def __init__(self, detail: str, *, resource: str = "") -> None:
        """Initialize an AuthorizationError.

        Args:
            detail: Description of the authorization failure.
            resource: The resource that was denied access to.
        """
        super().__init__(
            detail,
            error_code="AUTHORIZATION_ERROR",
            context={"resource": resource},
        )


class RateLimitExceededError(SecurityError):
    """Raised when a client exceeds the configured rate limit."""

    def __init__(
        self,
        client_identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        """Initialize a RateLimitExceededError.

        Args:
            client_identifier: The identifier of the rate-limited client (IP, API key, etc.).
            limit: The maximum allowed requests in the window.
            window_seconds: The rate limit window duration in seconds.
        """
        super().__init__(
            f"Rate limit exceeded for {client_identifier}: {limit} requests per {window_seconds}s",
            error_code="RATE_LIMIT_EXCEEDED",
            context={
                "client_identifier": client_identifier,
                "limit": limit,
                "window_seconds": window_seconds,
            },
        )
