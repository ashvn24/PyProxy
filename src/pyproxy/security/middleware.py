"""Security Middlewares for PyProxy: Rate Limiting, IP Filtering, and CORS."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyproxy.middleware.pipeline import BaseMiddleware
from pyproxy.protocol.response import HTTPResponse
from pyproxy.security.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from pyproxy.config.models import RateLimiterConfig
    from pyproxy.protocol.request import HTTPRequest

logger = logging.getLogger("pyproxy.security.middleware")


class RateLimiterMiddleware(BaseMiddleware):
    """Token bucket rate limiter middleware per client IP."""

    def __init__(self, config: RateLimiterConfig) -> None:
        self.config: RateLimiterConfig = config
        self.limiter: RateLimiter = RateLimiter(
            requests_per_second=config.rate,
            burst=config.burst,
        )

    async def process_request(self, request: HTTPRequest) -> HTTPRequest | HTTPResponse | None:
        """Enforce rate limits per client IP."""
        if not self.config.enabled:
            return None

        # Extract client IP
        client_ip = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP") or "127.0.0.1"
        client_ip = client_ip.split(",")[0].strip()

        allowed = await self.limiter.is_allowed(client_ip)
        if not allowed:
            logger.warning("Rate limit exceeded for client IP %s on %s (HTTP 429)", client_ip, request.target)
            return HTTPResponse.create_error(
                status_code=429,
                detail="Too Many Requests: Rate limit exceeded",
            )
        return None
