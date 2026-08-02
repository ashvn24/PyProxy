"""Cache Manager & HTTP Cache-Control Logic.

Handles Cache-Control header parsing, ETag generation, conditional request processing
(304 Not Modified), and cache storage integration.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

from pyproxy.cache.memory import MemoryCache
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.response import HTTPResponse

if TYPE_CHECKING:
    from pyproxy.core.types import CacheBackend
    from pyproxy.protocol.request import HTTPRequest

logger = logging.getLogger("pyproxy.cache.manager")


class CacheManager:
    """Manages HTTP caching and conditional request verification."""

    def __init__(self, backend: CacheBackend | None = None) -> None:
        """Initialize CacheManager.

        Args:
            backend: CacheBackend instance (defaults to MemoryCache).
        """
        self.backend: CacheBackend = backend or MemoryCache()

    @staticmethod
    def compute_cache_key(request: HTTPRequest) -> str:
        """Generate unique cache key for a request based on method and target path."""
        raw_key = f"GET:{request.target}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_etag(body: bytes) -> str:
        """Generate strong ETag for response body.

        Args:
            body: Body bytes.

        Returns:
            Quoted ETag string (e.g. '"a1b2c3d4"').
        """
        digest = hashlib.md5(body).hexdigest()[:16]
        return f'"{digest}"'

    def process_conditional_request(
        self,
        request: HTTPRequest,
        response: HTTPResponse,
    ) -> HTTPResponse:
        """Check If-None-Match header and return 304 Not Modified if matched.

        Args:
            request: Client HTTPRequest.
            response: Outgoing HTTPResponse.

        Returns:
            304 Not Modified HTTPResponse if matched; otherwise original response.
        """
        if request.method not in ("GET", "HEAD"):
            return response

        client_if_none_match = request.headers.get("If-None-Match")
        if not client_if_none_match:
            return response

        # Ensure response has ETag
        etag = response.headers.get("ETag")
        if not etag and response.body:
            etag = self.generate_etag(response.body)
            response.headers.set("ETag", etag)

        if etag and (client_if_none_match == etag or client_if_none_match == "*"):
            logger.debug("Conditional request 304 match for ETag %s", etag)
            headers = response.headers.copy()
            headers.remove("Content-Length")
            return HTTPResponse(status_code=304, headers=headers, body=b"")

        return response
