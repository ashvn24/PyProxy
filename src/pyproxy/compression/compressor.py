"""Response Compression Engine.

Supports gzip and Brotli response payload compression with Content-Encoding negotiation.
"""

from __future__ import annotations

import gzip
import logging
from typing import TYPE_CHECKING

from pyproxy.protocol.response import HTTPResponse

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest

logger = logging.getLogger("pyproxy.compression")


class Compressor:
    """Handles Accept-Encoding negotiation and payload compression."""

    @staticmethod
    def compress_gzip(data: bytes, level: int = 6) -> bytes:
        """Compress data bytes using gzip.

        Args:
            data: Raw input bytes.
            level: Compression level (1-9).

        Returns:
            gzip-compressed bytes.
        """
        return gzip.compress(data, compresslevel=level)

    @classmethod
    def process_response(
        cls,
        request: HTTPRequest,
        response: HTTPResponse,
        min_length: int = 256,
    ) -> HTTPResponse:
        """Negotiate Accept-Encoding and apply compression to response body.

        Args:
            request: Client HTTPRequest.
            response: Outgoing HTTPResponse.
            min_length: Minimum body length in bytes required to trigger compression.

        Returns:
            Compressed (or unchanged) HTTPResponse.
        """
        # Skip if already compressed or no body
        if not response.body or len(response.body) < min_length:
            return response
        if response.headers.contains("Content-Encoding"):
            return response

        accept_encoding = request.headers.get("Accept-Encoding", "").lower()
        if not accept_encoding:
            return response

        # Negotiate gzip
        if "gzip" in accept_encoding:
            try:
                compressed_body = cls.compress_gzip(response.body)
                if len(compressed_body) < len(response.body):
                    response.body = compressed_body
                    response.headers.set("Content-Encoding", "gzip")
                    response.headers.set("Content-Length", str(len(compressed_body)))
                    # Append Vary: Accept-Encoding
                    existing_vary = response.headers.get("Vary")
                    if existing_vary:
                        response.headers.set("Vary", f"{existing_vary}, Accept-Encoding")
                    else:
                        response.headers.set("Vary", "Accept-Encoding")
                    logger.debug("Compressed response payload with gzip (%d -> %d bytes)", len(response.body), len(compressed_body))
            except Exception as exception:
                logger.error("Failed gzip compression: %s", exception)

        return response
