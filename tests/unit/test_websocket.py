"""Unit tests for WebSocketProxy."""

from __future__ import annotations

from pyproxy.websocket import WebSocketProxy


class TestWebSocketProxy:
    """Tests for RFC 6455 handshake accept key computation."""

    def test_compute_accept_key(self):
        # RFC 6455 Example Test Case
        sec_key = "dGhl IHNhbXBsZSBub25jZQ=="
        expected = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="

        result = WebSocketProxy.compute_accept_key(sec_key)
        assert result == expected
