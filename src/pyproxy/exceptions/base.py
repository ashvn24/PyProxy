"""Base exception classes for PyProxy.

All PyProxy exceptions inherit from :class:`PyProxyError`, which carries
structured context for operational debugging and monitoring.
"""

from __future__ import annotations

from typing import Any


class PyProxyError(Exception):
    """Base exception for all PyProxy errors.

    Every PyProxy exception carries structured context beyond a simple string
    message. This enables structured error logging, error-code-based alerting,
    and deterministic error handling across the proxy pipeline.

    Attributes:
        error_code: A machine-readable error code (e.g., ``"CONFIG_PARSE_ERROR"``).
        detail: A human-readable explanation of what went wrong.
        context: Arbitrary key-value pairs providing additional diagnostic data
            (file paths, line numbers, invalid values, etc.).
    """

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "PYPROXY_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a PyProxyError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code for monitoring and alerting.
            context: Additional diagnostic key-value pairs.
        """
        self.detail: str = detail
        self.error_code: str = error_code
        self.context: dict[str, Any] = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the exception message for display.

        Returns:
            A formatted string combining error code, detail, and context.
        """
        parts: list[str] = [f"[{self.error_code}] {self.detail}"]
        if self.context:
            context_str = ", ".join(f"{key}={value!r}" for key, value in self.context.items())
            parts.append(f"({context_str})")
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the exception to a dictionary for structured logging.

        Returns:
            A dictionary representation of the error suitable for JSON serialization.
        """
        return {
            "error_code": self.error_code,
            "detail": self.detail,
            "context": self.context,
            "type": type(self).__name__,
        }
