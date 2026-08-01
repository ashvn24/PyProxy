"""Unit tests for HTTPParser, HTTPRequest, and Headers."""

from __future__ import annotations

import asyncio
import pytest

from pyproxy.exceptions import HttpParseError
from pyproxy.protocol import HTTPParser, HTTPRequest, Headers


class TestHeaders:
    """Tests for case-insensitive Headers container."""

    def test_case_insensitive_lookup(self):
        headers = Headers({"Content-Type": "application/json", "HOST": "example.com"})
        assert headers.get("content-type") == "application/json"
        assert headers.get("Content-Type") == "application/json"
        assert headers["host"] == "example.com"
        assert "Content-Length" not in headers

    def test_multi_value_headers(self):
        headers = Headers()
        headers.add("Set-Cookie", "a=1")
        headers.add("set-cookie", "b=2")

        assert headers.get("Set-Cookie") == "a=1"
        assert headers.get_all("set-cookie") == ["a=1", "b=2"]
        assert len(headers) == 2

    def test_to_dict_combines_values(self):
        headers = Headers([("Accept", "text/html"), ("Accept", "application/json")])
        as_dict = headers.to_dict()
        assert as_dict["Accept"] == "text/html, application/json"


class TestHTTPParserUnit:
    """Tests for HTTPParser static parsing routines."""

    def test_parse_request_line_valid(self):
        line = b"GET /api/v1/resource?query=test&page=1 HTTP/1.1\r\n"
        method, target, path, version, query_params = HTTPParser.parse_request_line(line)

        assert method == "GET"
        assert target == "/api/v1/resource?query=test&page=1"
        assert path == "/api/v1/resource"
        assert version == "HTTP/1.1"
        assert query_params == {"query": ["test"], "page": ["1"]}

    def test_parse_request_line_invalid_tokens(self):
        with pytest.raises(HttpParseError, match="Invalid request line format"):
            HTTPParser.parse_request_line(b"INVALID_LINE\r\n")

    def test_parse_request_line_invalid_method(self):
        with pytest.raises(HttpParseError, match="Unsupported or invalid HTTP method"):
            HTTPParser.parse_request_line(b"INVALID / HTTP/1.1\r\n")

    def test_parse_cookies(self):
        cookie_header = "session_id=xyz123; theme=dark; logged_in"
        cookies = HTTPParser.parse_cookies(cookie_header)
        assert cookies == {"session_id": "xyz123", "theme": "dark", "logged_in": ""}


class MockConnection:
    """Mock Connection object for socket stream tests."""

    def __init__(self, data: bytes) -> None:
        self.reader = asyncio.StreamReader()
        self.reader.feed_data(data)
        self.reader.feed_eof()
        self.client_host = "127.0.0.1"
        self.client_port = 54321

    async def read_line(self, timeout: float = 0.0) -> bytes:
        return await self.reader.readline()

    async def read(self, n: int = -1, timeout: float = 0.0) -> bytes:
        return await self.reader.read(n)

    async def read_exactly(self, n: int, timeout: float = 0.0) -> bytes:
        return await self.reader.readexactly(n)


class TestHTTPParserStream:
    """Tests for full request parsing from Connection streams."""

    @pytest.mark.asyncio
    async def test_parse_get_request(self):
        raw_request = (
            b"GET /index.html HTTP/1.1\r\n"
            b"Host: localhost:8080\r\n"
            b"User-Agent: pytest/1.0\r\n"
            b"Cookie: token=secret123\r\n"
            b"\r\n"
        )
        mock_conn = MockConnection(raw_request)
        request = await HTTPParser.parse_request(mock_conn)

        assert request.method == "GET"
        assert request.path == "/index.html"
        assert request.headers.get("Host") == "localhost:8080"
        assert request.cookies == {"token": "secret123"}
        assert request.is_keep_alive is True

    @pytest.mark.asyncio
    async def test_parse_post_with_content_length(self):
        raw_request = (
            b"POST /submit HTTP/1.1\r\n"
            b"Host: example.com\r\n"
            b"Content-Length: 11\r\n"
            b"\r\n"
            b"hello world"
        )
        mock_conn = MockConnection(raw_request)
        request = await HTTPParser.parse_request(mock_conn)

        assert request.method == "POST"
        assert request.content_length == 11
        body = await request.read_full_body()
        assert body == b"hello world"

    @pytest.mark.asyncio
    async def test_parse_chunked_body(self):
        raw_request = (
            b"POST /stream HTTP/1.1\r\n"
            b"Host: example.com\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"\r\n"
            b"5\r\nhello\r\n"
            b"6\r\n world\r\n"
            b"0\r\n\r\n"
        )
        mock_conn = MockConnection(raw_request)
        request = await HTTPParser.parse_request(mock_conn)

        assert request.is_chunked is True
        body = await request.read_full_body()
        assert body == b"hello world"
