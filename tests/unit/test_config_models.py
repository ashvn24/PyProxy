"""Tests for configuration data models and validation."""

from __future__ import annotations

import pytest

from pyproxy.config.models import (
    LoggingConfig,
    ProxyConfig,
    RouteConfig,
    ServerConfig,
    TlsConfig,
    UpstreamConfig,
    UpstreamTargetConfig,
)
from pyproxy.exceptions import ConfigValidationError


class TestServerConfig:
    """Tests for ServerConfig validation."""

    def test_defaults(self):
        config = ServerConfig()
        assert config.bind_host == "0.0.0.0"
        assert config.bind_port == 8080
        assert config.backlog == 1024
        assert config.keepalive_timeout == 75.0
        assert config.read_timeout == 30.0
        assert config.write_timeout == 30.0
        assert config.max_connections == 0
        assert config.shutdown_timeout == 30.0

    def test_custom_values(self):
        config = ServerConfig(
            bind_host="127.0.0.1",
            bind_port=9090,
            backlog=512,
        )
        assert config.bind_host == "127.0.0.1"
        assert config.bind_port == 9090
        assert config.backlog == 512

    def test_port_too_low(self):
        with pytest.raises(ConfigValidationError, match="Port must be between"):
            ServerConfig(bind_port=0)

    def test_port_too_high(self):
        with pytest.raises(ConfigValidationError, match="Port must be between"):
            ServerConfig(bind_port=65536)

    def test_port_boundary_low(self):
        config = ServerConfig(bind_port=1)
        assert config.bind_port == 1

    def test_port_boundary_high(self):
        config = ServerConfig(bind_port=65535)
        assert config.bind_port == 65535

    def test_negative_backlog(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            ServerConfig(backlog=-1)

    def test_zero_backlog(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            ServerConfig(backlog=0)

    def test_negative_keepalive(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            ServerConfig(keepalive_timeout=-1.0)

    def test_negative_read_timeout(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            ServerConfig(read_timeout=0.0)

    def test_negative_max_connections(self):
        with pytest.raises(ConfigValidationError, match="Value must be non-negative"):
            ServerConfig(max_connections=-1)

    def test_zero_max_connections_allowed(self):
        config = ServerConfig(max_connections=0)
        assert config.max_connections == 0

    def test_immutability(self):
        config = ServerConfig()
        with pytest.raises(AttributeError):
            config.bind_port = 9090  # type: ignore[misc]


class TestLoggingConfig:
    """Tests for LoggingConfig validation."""

    def test_defaults(self):
        config = LoggingConfig()
        assert config.level == "info"
        assert config.format == "json"
        assert config.access_log is True
        assert config.max_file_size_bytes == 10_485_760
        assert config.backup_count == 5

    def test_valid_levels(self):
        for level in ("debug", "info", "warning", "error", "critical"):
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_invalid_level(self):
        with pytest.raises(ConfigValidationError, match="Must be one of"):
            LoggingConfig(level="verbose")

    def test_valid_formats(self):
        for fmt in ("json", "text"):
            config = LoggingConfig(format=fmt)
            assert config.format == fmt

    def test_invalid_format(self):
        with pytest.raises(ConfigValidationError, match="Must be one of"):
            LoggingConfig(format="xml")

    def test_negative_max_file_size(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            LoggingConfig(max_file_size_bytes=-1)

    def test_negative_backup_count(self):
        with pytest.raises(ConfigValidationError, match="Value must be non-negative"):
            LoggingConfig(backup_count=-1)

    def test_zero_backup_count_allowed(self):
        config = LoggingConfig(backup_count=0)
        assert config.backup_count == 0


class TestUpstreamTargetConfig:
    """Tests for UpstreamTargetConfig validation."""

    def test_defaults(self):
        config = UpstreamTargetConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.weight == 1
        assert config.max_connections == 0

    def test_empty_host(self):
        with pytest.raises(ConfigValidationError, match="Host must not be empty"):
            UpstreamTargetConfig(host="")

    def test_invalid_port(self):
        with pytest.raises(ConfigValidationError, match="Port must be between"):
            UpstreamTargetConfig(port=0)

    def test_zero_weight(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            UpstreamTargetConfig(weight=0)

    def test_negative_max_connections(self):
        with pytest.raises(ConfigValidationError, match="Value must be non-negative"):
            UpstreamTargetConfig(max_connections=-1)


class TestUpstreamConfig:
    """Tests for UpstreamConfig validation."""

    def test_defaults(self):
        config = UpstreamConfig()
        assert config.targets == ()
        assert config.connect_timeout == 5.0
        assert config.pool_size == 64

    def test_negative_connect_timeout(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            UpstreamConfig(connect_timeout=0.0)

    def test_negative_max_retries(self):
        with pytest.raises(ConfigValidationError, match="Value must be non-negative"):
            UpstreamConfig(max_retries=-1)

    def test_zero_retries_allowed(self):
        config = UpstreamConfig(max_retries=0)
        assert config.max_retries == 0

    def test_zero_pool_size(self):
        with pytest.raises(ConfigValidationError, match="Value must be positive"):
            UpstreamConfig(pool_size=0)


class TestRouteConfig:
    """Tests for RouteConfig validation."""

    def test_defaults(self):
        config = RouteConfig()
        assert config.path == "/"
        assert config.methods == ()
        assert config.host == ""
        assert config.strip_prefix is False

    def test_empty_path(self):
        with pytest.raises(ConfigValidationError, match="Route path must not be empty"):
            RouteConfig(path="")

    def test_path_no_leading_slash(self):
        with pytest.raises(ConfigValidationError, match="Route path must start with"):
            RouteConfig(path="api")

    def test_valid_path_with_prefix(self):
        config = RouteConfig(path="/api/v1")
        assert config.path == "/api/v1"


class TestTlsConfig:
    """Tests for TlsConfig validation."""

    def test_defaults_disabled(self):
        config = TlsConfig()
        assert config.enabled is False
        assert config.cert_path == ""
        assert config.key_path == ""

    def test_enabled_without_cert(self):
        with pytest.raises(ConfigValidationError, match="TLS certificate path is required"):
            TlsConfig(enabled=True, cert_path="", key_path="/path/to/key")

    def test_enabled_without_key(self):
        with pytest.raises(ConfigValidationError, match="TLS key path is required"):
            TlsConfig(enabled=True, cert_path="/path/to/cert", key_path="")

    def test_enabled_with_paths(self):
        config = TlsConfig(
            enabled=True,
            cert_path="/path/to/cert.pem",
            key_path="/path/to/key.pem",
        )
        assert config.enabled is True
        assert config.cert_path == "/path/to/cert.pem"

    def test_invalid_min_version(self):
        with pytest.raises(ConfigValidationError, match="Must be one of"):
            TlsConfig(min_version="1.0")

    def test_valid_min_versions(self):
        for version in ("1.2", "1.3"):
            config = TlsConfig(min_version=version)
            assert config.min_version == version


class TestProxyConfig:
    """Tests for ProxyConfig.from_dict()."""

    def test_empty_dict(self):
        config = ProxyConfig.from_dict({})
        assert config.server.bind_host == "0.0.0.0"
        assert config.server.bind_port == 8080
        assert config.routes == ()

    def test_full_dict(self, sample_config_dict):
        config = ProxyConfig.from_dict(sample_config_dict)
        assert config.server.bind_host == "127.0.0.1"
        assert config.server.bind_port == 9090
        assert len(config.routes) == 2
        assert config.routes[0].path == "/api"
        assert config.routes[0].methods == ("GET", "POST")
        assert len(config.routes[0].upstream.targets) == 2
        assert config.routes[0].upstream.targets[0].host == "10.0.0.1"
        assert config.routes[0].upstream.targets[0].weight == 2

    def test_methods_uppercased(self):
        data = {
            "routes": [
                {
                    "path": "/test",
                    "methods": ["get", "post"],
                    "upstream": {"targets": [{"host": "localhost", "port": 3000}]},
                }
            ]
        }
        config = ProxyConfig.from_dict(data)
        assert config.routes[0].methods == ("GET", "POST")

    def test_unknown_keys_ignored(self):
        data = {"unknown_key": "value", "server": {"bind_port": 9090}}
        config = ProxyConfig.from_dict(data)
        assert config.server.bind_port == 9090

    def test_frozen_config(self):
        config = ProxyConfig.from_dict({})
        with pytest.raises(AttributeError):
            config.server = ServerConfig()  # type: ignore[misc]
