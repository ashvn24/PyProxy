"""Unit tests for HeaderRewriter and ProxyEngine."""

from __future__ import annotations

import pytest

from pyproxy.protocol import HTTPRequest, Headers
from pyproxy.proxy import HeaderRewriter


class DummyConnection:
    def __init__(self, host: str = "192.168.1.100", port: int = 45678):
        self.client_host = host
        self.client_port = port


class TestHeaderRewriter:
    """Tests for HeaderRewriter header manipulation."""

    def test_strip_hop_by_hop_headers(self):
        req = HTTPRequest(headers=Headers({
            "Host": "example.com",
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=5",
            "X-Custom": "value",
        }))
        client_conn = DummyConnection()

        rewritten = HeaderRewriter.prepare_upstream_headers(
            request=req,
            client_connection=client_conn,
            target_host="backend.local",
            target_port=8000,
        )

        assert rewritten.get("X-Custom") == "value"
        assert rewritten.get("Host") == "backend.local:8000"
        assert not rewritten.contains("Connection")
        assert not rewritten.contains("Keep-Alive")

    def test_x_forwarded_headers(self):
        req = HTTPRequest(headers=Headers({"Host": "example.com"}))
        client_conn = DummyConnection("10.0.0.50", 12345)

        rewritten = HeaderRewriter.prepare_upstream_headers(
            request=req,
            client_connection=client_conn,
            target_host="backend",
            target_port=80,
        )

        assert rewritten.get("X-Forwarded-For") == "10.0.0.50"
        assert rewritten.get("X-Real-IP") == "10.0.0.50"
        assert rewritten.get("X-Forwarded-Proto") == "http"
        assert "for=10.0.0.50" in rewritten.get("Forwarded", "")
