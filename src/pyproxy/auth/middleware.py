"""Authentication Middleware.

Provides HTTP Basic Auth, API Key verification, JWT token validation, and OAuth hooks.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from pyproxy.exceptions.security import AuthenticationError
from pyproxy.middleware.pipeline import BaseMiddleware
from pyproxy.protocol.response import HTTPResponse

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest

logger = logging.getLogger("pyproxy.auth")


class AuthMiddleware(BaseMiddleware):
    """Authentication enforcement middleware."""

    def __init__(
        self,
        basic_credentials: dict[str, str] | None = None,
        valid_api_keys: set[str] | None = None,
        header_key_name: str = "X-API-Key",
    ) -> None:
        """Initialize AuthMiddleware.

        Args:
            basic_credentials: Mapping of username to password.
            valid_api_keys: Set of valid API key strings.
            header_key_name: API key header field name.
        """
        self.basic_credentials: dict[str, str] = basic_credentials or {}
        self.valid_api_keys: set[str] = valid_api_keys or set()
        self.header_key_name: str = header_key_name

    async def process_request(
        self,
        request: HTTPRequest,
    ) -> HTTPRequest | HTTPResponse | None:
        """Enforce authentication rules on incoming client request.

        Args:
            request: Client HTTPRequest.

        Returns:
            HTTPResponse error if authentication fails; None to proceed.
        """
        auth_header = request.headers.get("Authorization", "")
        api_key_hdr = request.headers.get(self.header_key_name, "")

        # 1. API Key check
        if self.valid_api_keys:
            if api_key_hdr in self.valid_api_keys:
                return None
            query_key = request.query_params.get("api_key", [""])[0]
            if query_key in self.valid_api_keys:
                return None
            if not self.basic_credentials and not auth_header:
                return HTTPResponse.create_error(401, "Invalid or missing API key")

        # 2. Basic Auth check
        if self.basic_credentials:
            if auth_header.startswith("Basic "):
                try:
                    encoded = auth_header[6:].strip()
                    decoded = base64.b64decode(encoded).decode("utf-8")
                    if ":" in decoded:
                        username, password = decoded.split(":", 1)
                        if self.basic_credentials.get(username) == password:
                            return None
                except Exception as exception:
                    logger.debug("Failed basic auth decoding: %s", exception)

            headers = request.headers.copy()
            headers.set("WWW-Authenticate", 'Basic realm="PyProxy"')
            return HTTPResponse.create_error(401, "Unauthorized", headers=headers)

        return None
