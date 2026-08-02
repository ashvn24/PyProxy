"""Unit tests for HTTPResponse and HTTPResponseBuilder."""

from __future__ import annotations

import asyncio
import pytest

from pyproxy.protocol import HTTPResponse, HTTPResponseBuilder, Headers


class MockWriteConnection:
    """Mock Connection for testing response serialization and writes."""

    def __init__(self) -> None:
        self.written_bytes: bytearray = bytearray()
        self.is_closed = False

    def write(self, data: bytes) -> None:
        self.written_bytes.extend(data)

    async def drain(self, timeout: float = 0.0) -> None:
        pass


class TestHTTPResponse:
    """Tests for HTTPResponse model."""

    def test_default_status_phrase(self):
        response = HTTPResponse(status_code=200)
        assert response.reason_phrase == "OK"

        response404 = HTTPResponse(status_code=404)
        assert response404.reason_phrase == "Not Found"

    def test_create_error_json(self):
        response = HTTPResponse.create_error(502, detail="Upstream connection refused")
        assert response.status_code == 502
        assert response.headers.get("Content-Type") == "application/json"
        assert b"Upstream connection refused" in response.body


class TestHTTPResponseBuilder:
    """Tests for HTTPResponseBuilder serialization and streaming."""

    def test_serialize_headers(self):
        headers = Headers({"Server": "PyProxy", "Content-Type": "text/plain"})
        response = HTTPResponse(status_code=200, headers=headers)

        serialized = HTTPResponseBuilder.serialize_headers(response)
        assert serialized.startswith(b"HTTP/1.1 200 OK\r\n")
        assert b"Server: PyProxy\r\n" in serialized
        assert serialized.endswith(b"\r\n\r\n")

    @pytest.mark.asyncio
    async def test_send_buffered_response(self):
        conn = MockWriteConnection()
        headers = Headers({"Content-Type": "text/plain"})
        response = HTTPResponse(status_code=200, headers=headers, body=b"Hello PyProxy")

        bytes_sent = await HTTPResponseBuilder.send_response(conn, response)
        assert bytes_sent > 0
        assert b"HTTP/1.1 200 OK\r\n" in conn.written_bytes
        assert b"Content-Length: 13\r\n" in conn.written_bytes
        assert conn.written_bytes.endswith(b"Hello PyProxy")

    @pytest.mark.asyncio
    async def test_send_chunked_stream_response(self):
        conn = MockWriteConnection()

        async def generate_chunks():
            yield b"chunk1"
            yield b"chunk2"

        response = HTTPResponse(status_code=200, body_stream=generate_chunks(), is_chunked=True)
        await HTTPResponseBuilder.send_response(conn, response)

        assert b"Transfer-Encoding: chunked\r\n" in conn.written_bytes
        assert b"6\r\nchunk1\r\n" in conn.written_bytes
        assert b"6\r\nchunk2\r\n" in conn.written_bytes
        assert conn.written_bytes.endswith(b"0\r\n\r\n")

    def test_parse_range_header_valid(self):
        parsed = HTTPResponseBuilder.parse_range_header("bytes=0-499", 1000)
        assert parsed == (0, 499)

        parsed_suffix = HTTPResponseBuilder.parse_range_header("bytes=-500", 1000)
        assert parsed_suffix == (500, 999)

        parsed_open = HTTPResponseBuilder.parse_range_header("bytes=500-", 1000)
        assert parsed_open == (500, 999)

    def test_parse_range_header_invalid(self):
        assert HTTPResponseBuilder.parse_range_header("bytes=1000-2000", 500) is None
        assert HTTPResponseBuilder.parse_range_header("invalid", 1000) is None
