"""HTTP Caching Middleware for PyProxy.

Intercepts GET/HEAD requests to return cached responses (Cache HIT) directly
from in-memory storage, short-circuiting upstream calls. Also handles 304 Not Modified
conditional responses and purges cache entries on mutating requests (POST, PUT, DELETE, PATCH).
"""

from __future__ import annotations

import logging
import pickle
from typing import TYPE_CHECKING

from pyproxy.cache.manager import CacheManager
from pyproxy.middleware.pipeline import BaseMiddleware
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.response import HTTPResponse

if TYPE_CHECKING:
    from pyproxy.config.models import CacheConfig
    from pyproxy.protocol.request import HTTPRequest

logger = logging.getLogger("pyproxy.cache.middleware")


class CacheMiddleware(BaseMiddleware):
    """Middleware for HTTP Caching, TTL management, and Cache Invalidation."""

    def __init__(self, config: CacheConfig) -> None:
        self.config: CacheConfig = config
        self.manager: CacheManager = CacheManager()

    async def process_request(self, request: HTTPRequest) -> HTTPRequest | HTTPResponse | None:
        """Process incoming request: check cache for GET/HEAD, purge cache on POST/PUT/DELETE."""
        if not self.config.enabled:
            return None

        cache_key = self.manager.compute_cache_key(request)

        # 1. Invalidate cache entry on state-changing requests
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            await self.manager.backend.delete(cache_key)
            logger.info("Invalidated cache entry for mutating request %s %s", request.method, request.target)
            return None

        if request.method not in ("GET", "HEAD"):
            return None

        # 2. Retrieve from cache
        cached_bytes = await self.manager.backend.get(cache_key)

        if cached_bytes is not None:
            logger.info("Cache HIT for %s — short-circuiting upstream call", request.target)
            status_code, reason_phrase, header_tuples, body = pickle.loads(cached_bytes)
            headers = Headers(header_tuples)
            headers.set("X-Cache", "HIT")
            response = HTTPResponse(
                status_code=status_code,
                reason_phrase=reason_phrase,
                headers=headers,
                body=body,
            )
            return self.manager.process_conditional_request(request, response)

        logger.debug("Cache MISS for %s", request.target)
        return None

    async def process_response(self, request: HTTPRequest, response: HTTPResponse) -> HTTPResponse:
        """Process outgoing response to store in cache if eligible."""
        if not self.config.enabled or request.method not in ("GET", "HEAD") or response.status_code != 200:
            return response

        response.headers.set("X-Cache", "MISS")

        cache_key = self.manager.compute_cache_key(request)

        # Collect body bytes if streaming
        if response.body_stream is not None and not response.body:
            chunks = []
            async for chunk in response.body_stream:
                chunks.append(chunk)
            response.body = b"".join(chunks)
            response.body_stream = None

        # Prepare clean cached headers (strip Transfer-Encoding chunked, enforce Content-Length)
        cached_headers = response.headers.copy()
        cached_headers.remove("Transfer-Encoding")
        cached_headers.set("Content-Length", str(len(response.body)))

        # Generate ETag if not present
        etag = cached_headers.get("ETag")
        if not etag and response.body:
            etag = self.manager.generate_etag(response.body)
            cached_headers.set("ETag", etag)

        # Serialize HTTPResponse data to bytes
        serialized = pickle.dumps((
            response.status_code,
            response.reason_phrase,
            list(cached_headers),
            response.body,
        ))

        await self.manager.backend.set(cache_key, serialized, ttl_seconds=self.config.ttl)
        logger.info("Saved response to cache for %s (TTL: %.1fs)", request.target, self.config.ttl)

        return self.manager.process_conditional_request(request, response)
