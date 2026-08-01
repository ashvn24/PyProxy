"""Request context management using contextvars.

Provides request-scoped context (request ID, correlation ID) that is
automatically propagated through async call chains without explicit
parameter passing. The context is available to the logging formatter
for injection into every log line.

Usage::

    from pyproxy.logging.context import RequestContext

    async with RequestContext(request_id="abc-123", correlation_id="corr-456"):
        # All log lines within this scope will include request_id and correlation_id
        logger.info("Processing request")
"""

from __future__ import annotations

import contextvars
from types import TracebackType
from typing import Any


# Context variables for request-scoped data.
# These are automatically inherited by child tasks in asyncio.
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
_extra_context_var: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "extra_context", default={}
)


def get_request_id() -> str:
    """Get the current request ID from context.

    Returns:
        The request ID string, or empty string if not set.
    """
    return _request_id_var.get()


def set_request_id(request_id: str) -> contextvars.Token[str]:
    """Set the request ID in context.

    Args:
        request_id: The request ID to set.

    Returns:
        A token that can be used to reset the context variable.
    """
    return _request_id_var.set(request_id)


def get_correlation_id() -> str:
    """Get the current correlation ID from context.

    Returns:
        The correlation ID string, or empty string if not set.
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token[str]:
    """Set the correlation ID in context.

    Args:
        correlation_id: The correlation ID to set.

    Returns:
        A token that can be used to reset the context variable.
    """
    return _correlation_id_var.set(correlation_id)


def get_extra_context() -> dict[str, Any]:
    """Get additional context fields from the current scope.

    Returns:
        A dictionary of extra context key-value pairs.
    """
    return _extra_context_var.get()


def set_extra_context(extra: dict[str, Any]) -> contextvars.Token[dict[str, Any]]:
    """Set additional context fields in the current scope.

    Args:
        extra: Dictionary of extra context fields to add to log lines.

    Returns:
        A token that can be used to reset the context variable.
    """
    return _extra_context_var.set(extra)


class RequestContext:
    """Context manager that sets request-scoped logging context.

    Automatically sets and clears request ID, correlation ID, and any
    extra fields on enter and exit. Works with both sync and async
    ``with`` statements.

    Example::

        async with RequestContext(request_id="req-123"):
            logger.info("This log line will include request_id=req-123")
        # Outside the context, request_id is restored to its previous value.
    """

    def __init__(
        self,
        request_id: str = "",
        correlation_id: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the RequestContext.

        Args:
            request_id: Request identifier for this scope.
            correlation_id: Correlation identifier for distributed tracing.
            extra: Additional key-value pairs to include in log context.
        """
        self._request_id = request_id
        self._correlation_id = correlation_id
        self._extra = extra or {}

        # Tokens for restoring previous values on exit
        self._request_id_token: contextvars.Token[str] | None = None
        self._correlation_id_token: contextvars.Token[str] | None = None
        self._extra_token: contextvars.Token[dict[str, Any]] | None = None

    def __enter__(self) -> RequestContext:
        """Enter the context and set context variables.

        Returns:
            This context manager instance.
        """
        self._request_id_token = set_request_id(self._request_id)
        self._correlation_id_token = set_correlation_id(self._correlation_id)
        self._extra_token = set_extra_context(self._extra)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context and restore previous context variables.

        Args:
            exc_type: Exception type, if any.
            exc_val: Exception value, if any.
            exc_tb: Exception traceback, if any.
        """
        if self._request_id_token is not None:
            _request_id_var.reset(self._request_id_token)
        if self._correlation_id_token is not None:
            _correlation_id_var.reset(self._correlation_id_token)
        if self._extra_token is not None:
            _extra_context_var.reset(self._extra_token)

    async def __aenter__(self) -> RequestContext:
        """Async context manager entry.

        Returns:
            This context manager instance.
        """
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type, if any.
            exc_val: Exception value, if any.
            exc_tb: Exception traceback, if any.
        """
        self.__exit__(exc_type, exc_val, exc_tb)
