"""Middleware Pipeline Engine.

Executes an ordered pipeline of pre-request and post-response middleware hooks,
allowing short-circuiting and custom transformations.
"""

from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING, Any

from pyproxy.protocol.request import HTTPRequest
from pyproxy.protocol.response import HTTPResponse

logger = logging.getLogger("pyproxy.middleware.pipeline")


class BaseMiddleware(abc.ABC):
    """Abstract base class for all PyProxy middleware components."""

    async def process_request(
        self,
        request: HTTPRequest,
    ) -> HTTPRequest | HTTPResponse | None:
        """Hook called before the request is routed to an upstream target.

        Args:
            request: The incoming client HTTPRequest.

        Returns:
            - Modifed HTTPRequest to continue pipeline.
            - HTTPResponse to short-circuit pipeline immediately.
            - None to continue with original HTTPRequest.
        """
        return None

    async def process_response(
        self,
        request: HTTPRequest,
        response: HTTPResponse,
    ) -> HTTPResponse:
        """Hook called after upstream response is received but before client transmission.

        Args:
            request: The client HTTPRequest.
            response: The received HTTPResponse.

        Returns:
            The (possibly modified) HTTPResponse.
        """
        return response


class MiddlewarePipeline:
    """Manages and executes ordered middleware pipelines."""

    def __init__(self) -> None:
        self._middlewares: list[BaseMiddleware] = []

    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """Append a middleware instance to the pipeline.

        Args:
            middleware: BaseMiddleware instance.
        """
        self._middlewares.append(middleware)
        logger.debug("Added middleware '%s' to pipeline", type(middleware).__name__)

    async def execute_request(self, request: HTTPRequest) -> HTTPRequest | HTTPResponse:
        """Execute pre-request hooks across all registered middlewares.

        Args:
            request: Incoming HTTPRequest object.

        Returns:
            HTTPRequest to continue to routing/proxying, or HTTPResponse if short-circuited.
        """
        current_request = request
        for middleware in self._middlewares:
            result = await middleware.process_request(current_request)
            if isinstance(result, HTTPResponse):
                logger.info(
                    "Request short-circuited by middleware '%s' (status %d)",
                    type(middleware).__name__,
                    result.status_code,
                )
                return result
            if isinstance(result, HTTPRequest):
                current_request = result

        return current_request

    async def execute_response(
        self,
        request: HTTPRequest,
        response: HTTPResponse,
    ) -> HTTPResponse:
        """Execute post-response hooks across registered middlewares in reverse order.

        Args:
            request: Client HTTPRequest object.
            response: Outgoing HTTPResponse object.

        Returns:
            Final HTTPResponse object.
        """
        current_response = response
        for middleware in reversed(self._middlewares):
            current_response = await middleware.process_response(request, current_response)

        return current_response
