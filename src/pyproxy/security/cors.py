"""CORS (Cross-Origin Resource Sharing) Middleware.

Handles CORS preflight OPTIONS requests and injects Access-Control response headers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyproxy.middleware.pipeline import BaseMiddleware
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.response import HTTPResponse

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest


class CORSMiddleware(BaseMiddleware):
    """CORS header processing and preflight handling middleware."""

    def __init__(
        self,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = False,
        max_age: int = 86400,
    ) -> None:
        self.allow_origins: list[str] = allow_origins or ["*"]
        self.allow_methods: list[str] = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
        self.allow_headers: list[str] = allow_headers or ["*"]
        self.allow_credentials: bool = allow_credentials
        self.max_age: int = max_age

    async def process_request(
        self,
        request: HTTPRequest,
    ) -> HTTPRequest | HTTPResponse | None:
        # Handle CORS OPTIONS preflight
        if request.method == "OPTIONS" and request.headers.contains("Access-Control-Request-Method"):
            origin = request.headers.get("Origin", "")
            headers = Headers()

            if "*" in self.allow_origins:
                headers.set("Access-Control-Allow-Origin", "*")
            elif origin in self.allow_origins:
                headers.set("Access-Control-Allow-Origin", origin)
                headers.set("Vary", "Origin")

            headers.set("Access-Control-Allow-Methods", ", ".join(self.allow_methods))
            headers.set("Access-Control-Allow-Headers", ", ".join(self.allow_headers))
            headers.set("Access-Control-Max-Age", str(self.max_age))

            if self.allow_credentials:
                headers.set("Access-Control-Allow-Credentials", "true")

            return HTTPResponse(status_code=204, headers=headers, body=b"")

        return None

    async def process_response(
        self,
        request: HTTPRequest,
        response: HTTPResponse,
    ) -> HTTPResponse:
        origin = request.headers.get("Origin", "")
        if origin:
            if "*" in self.allow_origins:
                response.headers.set("Access-Control-Allow-Origin", "*")
            elif origin in self.allow_origins:
                response.headers.set("Access-Control-Allow-Origin", origin)
                response.headers.set("Vary", "Origin")

            if self.allow_credentials:
                response.headers.set("Access-Control-Allow-Credentials", "true")

        return response
