"""Unit tests for Compressor."""

from __future__ import annotations

import gzip

import pytest

from pyproxy.compression import Compressor
from pyproxy.protocol import HTTPRequest, HTTPResponse, Headers


class TestCompressor:
    """Tests for gzip compression and negotiation."""

    def test_compress_gzip(self):
        data = b"hello world " * 100
        compressed = Compressor.compress_gzip(data)
        assert len(compressed) < len(data)
        assert gzip.decompress(compressed) == data

    def test_process_response_negotiates_gzip(self):
        req = HTTPRequest(headers=Headers({"Accept-Encoding": "gzip, deflate"}))
        resp = HTTPResponse(status_code=200, body=b"A" * 1024)

        compressed_resp = Compressor.process_response(req, resp, min_length=100)
        assert compressed_resp.headers.get("Content-Encoding") == "gzip"
        assert len(compressed_resp.body) < 1024
