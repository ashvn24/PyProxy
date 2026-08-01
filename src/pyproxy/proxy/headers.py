"""Header Rewriting and Forwarding Engine.

Handles RFC 7239 Forwarded, X-Forwarded-For, X-Real-IP, Host header rewriting,
and hop-by-hop header removal for proxy security and compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyproxy.protocol.headers import Headers

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest
    from pyproxy.server.connection import Connection

_HOP_BY_HOP_HEADERS: frozenset[str] = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
})


class HeaderRewriter:
    """Modifies HTTP headers for proxy forwarding."""

    @classmethod
    def prepare_upstream_headers(
        cls,
        request: HTTPRequest,
        client_connection: Connection,
        target_host: str,
        target_port: int,
        scheme: str = "http",
        preserve_host: bool = False,
    ) -> Headers:
        """Create a new set of Headers suitable for forwarding to an upstream server.

        Args:
            request: Client HTTPRequest.
            client_connection: Active client Connection socket.
            target_host: Destination upstream host.
            target_port: Destination upstream port.
            scheme: Request scheme ("http" or "https").
            preserve_host: True to preserve incoming Host header, False to rewrite.

        Returns:
            Prepared Headers object for upstream request.
        """
        upstream_headers = Headers()

        # Copy non-hop-by-hop headers
        for name, val in request.headers:
            lower_name = name.lower()
            if lower_name not in _HOP_BY_HOP_HEADERS:
                upstream_headers.add(name, val)

        # 1. Host header rewriting
        if preserve_host:
            upstream_headers.set("Host", request.host or f"{target_host}:{target_port}")
        else:
            if (scheme == "http" and target_port == 80) or (scheme == "https" and target_port == 443):
                upstream_headers.set("Host", target_host)
            else:
                upstream_headers.set("Host", f"{target_host}:{target_port}")

        # 2. X-Forwarded-For
        client_ip = client_connection.client_host
        existing_xff = request.headers.get("X-Forwarded-For")
        if existing_xff:
            upstream_headers.set("X-Forwarded-For", f"{existing_xff}, {client_ip}")
        else:
            upstream_headers.set("X-Forwarded-For", client_ip)

        # 3. X-Real-IP
        if not upstream_headers.contains("X-Real-IP"):
            upstream_headers.set("X-Real-IP", client_ip)

        # 4. X-Forwarded-Proto & Host
        if not upstream_headers.contains("X-Forwarded-Proto"):
            upstream_headers.set("X-Forwarded-Proto", scheme)

        if not upstream_headers.contains("X-Forwarded-Host"):
            upstream_headers.set("X-Forwarded-Host", request.host)

        # 5. RFC 7239 Forwarded header
        forwarded_entry = f"for={client_ip};proto={scheme};by=pyproxy"
        existing_forwarded = request.headers.get("Forwarded")
        if existing_forwarded:
            upstream_headers.set("Forwarded", f"{existing_forwarded}, {forwarded_entry}")
        else:
            upstream_headers.set("Forwarded", forwarded_entry)

        return upstream_headers
