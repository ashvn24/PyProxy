"""Tests for the exception hierarchy."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyproxy.exceptions import (
    AuthenticationError,
    BindError,
    ConfigError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    HttpParseError,
    PyProxyError,
    RateLimitExceededError,
    RouteConflictError,
    RouteNotFoundError,
    SecurityError,
    ServerError,
    ShutdownError,
    TlsError,
    UpstreamConnectionError,
    UpstreamTimeoutError,
    WebSocketError,
)


class TestPyProxyError:
    """Tests for the base PyProxyError class."""

    def test_default_error_code(self):
        exc = PyProxyError("test error")
        assert exc.error_code == "PYPROXY_ERROR"
        assert exc.detail == "test error"
        assert exc.context == {}

    def test_custom_error_code(self):
        exc = PyProxyError("test", error_code="CUSTOM_CODE")
        assert exc.error_code == "CUSTOM_CODE"

    def test_context_dict(self):
        exc = PyProxyError("test", context={"key": "value"})
        assert exc.context == {"key": "value"}

    def test_str_includes_error_code(self):
        exc = PyProxyError("something failed", error_code="MY_CODE")
        assert "[MY_CODE]" in str(exc)
        assert "something failed" in str(exc)

    def test_str_includes_context(self):
        exc = PyProxyError("test", context={"file": "config.yaml"})
        assert "file=" in str(exc)
        assert "config.yaml" in str(exc)

    def test_to_dict(self):
        exc = PyProxyError("test error", error_code="CODE", context={"k": "v"})
        result = exc.to_dict()
        assert result["error_code"] == "CODE"
        assert result["detail"] == "test error"
        assert result["context"] == {"k": "v"}
        assert result["type"] == "PyProxyError"

    def test_is_exception(self):
        exc = PyProxyError("test")
        assert isinstance(exc, Exception)


class TestConfigExceptions:
    """Tests for configuration exception hierarchy."""

    def test_config_error_inherits_base(self):
        exc = ConfigError("config issue")
        assert isinstance(exc, PyProxyError)
        assert exc.error_code == "CONFIG_ERROR"

    def test_config_file_not_found(self):
        exc = ConfigFileNotFoundError(Path("/tmp/missing.yaml"))
        assert isinstance(exc, ConfigError)
        assert exc.file_path == Path("/tmp/missing.yaml")
        assert "CONFIG_FILE_NOT_FOUND" in exc.error_code
        assert "missing.yaml" in str(exc)

    def test_config_validation_error(self):
        exc = ConfigValidationError(
            field="server.bind_port",
            value=99999,
            reason="Port must be between 1 and 65535",
        )
        assert isinstance(exc, ConfigError)
        assert exc.field == "server.bind_port"
        assert exc.value == 99999
        assert exc.reason == "Port must be between 1 and 65535"
        assert "CONFIG_VALIDATION_ERROR" in exc.error_code

    def test_config_parse_error(self):
        exc = ConfigParseError(
            file_path=Path("/tmp/config.yaml"),
            file_format="yaml",
            cause="invalid syntax at line 5",
        )
        assert isinstance(exc, ConfigError)
        assert exc.file_path == Path("/tmp/config.yaml")
        assert exc.file_format == "yaml"
        assert "CONFIG_PARSE_ERROR" in exc.error_code


class TestServerExceptions:
    """Tests for server exception hierarchy."""

    def test_server_error_inherits_base(self):
        exc = ServerError("server issue")
        assert isinstance(exc, PyProxyError)

    def test_bind_error(self):
        exc = BindError("0.0.0.0", 80, "permission denied")
        assert isinstance(exc, ServerError)
        assert "0.0.0.0" in str(exc)
        assert "80" in str(exc)

    def test_shutdown_error(self):
        exc = ShutdownError("timed out waiting for connections")
        assert isinstance(exc, ServerError)


class TestRoutingExceptions:
    """Tests for routing exception hierarchy."""

    def test_route_not_found(self):
        exc = RouteNotFoundError("/unknown", "GET")
        assert isinstance(exc, PyProxyError)
        assert "ROUTE_NOT_FOUND" in exc.error_code
        assert "/unknown" in str(exc)

    def test_route_conflict(self):
        exc = RouteConflictError("/api", "/api/v1")
        assert isinstance(exc, PyProxyError)
        assert "ROUTE_CONFLICT" in exc.error_code


class TestUpstreamExceptions:
    """Tests for upstream exception hierarchy."""

    def test_upstream_connection_error(self):
        exc = UpstreamConnectionError("10.0.0.1", 3000, "connection refused")
        assert isinstance(exc, PyProxyError)
        assert "10.0.0.1" in str(exc)

    def test_upstream_timeout(self):
        exc = UpstreamTimeoutError("10.0.0.1", 3000, 5.0)
        assert isinstance(exc, PyProxyError)
        assert "5.0s" in str(exc)


class TestSecurityExceptions:
    """Tests for security exception hierarchy."""

    def test_authentication_error(self):
        exc = AuthenticationError("invalid token", scheme="bearer")
        assert isinstance(exc, SecurityError)
        assert exc.context["scheme"] == "bearer"

    def test_rate_limit_exceeded(self):
        exc = RateLimitExceededError("192.168.1.1", 100, 60)
        assert isinstance(exc, SecurityError)
        assert "RATE_LIMIT_EXCEEDED" in exc.error_code


class TestProtocolExceptions:
    """Tests for protocol exception hierarchy."""

    def test_http_parse_error(self):
        exc = HttpParseError("malformed request line", raw_data=b"GET /\r\n")
        assert isinstance(exc, PyProxyError)
        assert "HTTP_PARSE_ERROR" in exc.error_code

    def test_http_parse_truncates_raw_data(self):
        long_data = b"x" * 1000
        exc = HttpParseError("too long", raw_data=long_data)
        # Should truncate to 256 bytes
        preview = exc.context["raw_data_preview"]
        assert len(preview) < 500  # repr of 256 bytes

    def test_websocket_error(self):
        exc = WebSocketError("unexpected close", close_code=1006)
        assert isinstance(exc, PyProxyError)
        assert exc.context["close_code"] == 1006

    def test_tls_error(self):
        exc = TlsError("certificate expired")
        assert isinstance(exc, PyProxyError)
        assert "TLS_ERROR" in exc.error_code
