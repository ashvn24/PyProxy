"""HTTP Protocol parsing, serialization, and data model package.

Provides HTTP request parsing, response building, case-insensitive headers,
and status code mappings.

Example::

    from pyproxy.protocol import HTTPResponse, HTTPResponseBuilder, Headers

    response = HTTPResponse(status_code=200, body=b"Hello")
    await HTTPResponseBuilder.send_response(connection, response)
"""

from __future__ import annotations

from pyproxy.protocol.headers import Headers
from pyproxy.protocol.parser import HTTPParser
from pyproxy.protocol.request import HTTPRequest
from pyproxy.protocol.response import STATUS_PHRASES, HTTPResponse
from pyproxy.protocol.response_builder import HTTPResponseBuilder

__all__: list[str] = [
    "HTTPParser",
    "HTTPRequest",
    "HTTPResponse",
    "HTTPResponseBuilder",
    "Headers",
    "STATUS_PHRASES",
]
