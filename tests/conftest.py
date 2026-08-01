"""Shared test fixtures for PyProxy test suite."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyproxy.config.models import (
    LoggingConfig,
    ProxyConfig,
    RouteConfig,
    ServerConfig,
    TlsConfig,
    UpstreamConfig,
    UpstreamTargetConfig,
)
from pyproxy.core.container import Container


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_config_dict() -> dict[str, Any]:
    """Provide a sample configuration dictionary."""
    return {
        "server": {
            "bind_host": "127.0.0.1",
            "bind_port": 9090,
            "backlog": 512,
            "keepalive_timeout": 60.0,
            "read_timeout": 15.0,
            "write_timeout": 15.0,
            "max_connections": 1000,
            "shutdown_timeout": 10.0,
        },
        "logging": {
            "level": "debug",
            "format": "json",
            "access_log": True,
            "access_log_path": "",
            "error_log_path": "",
            "max_file_size_bytes": 5_242_880,
            "backup_count": 3,
        },
        "routes": [
            {
                "path": "/api",
                "methods": ["GET", "POST"],
                "strip_prefix": True,
                "upstream": {
                    "connect_timeout": 3.0,
                    "read_timeout": 10.0,
                    "write_timeout": 10.0,
                    "max_retries": 2,
                    "retry_delay": 0.25,
                    "pool_size": 32,
                    "targets": [
                        {"host": "10.0.0.1", "port": 3000, "weight": 2},
                        {"host": "10.0.0.2", "port": 3000, "weight": 1},
                    ],
                },
            },
            {
                "path": "/",
                "upstream": {
                    "targets": [
                        {"host": "10.0.0.3", "port": 8000},
                    ],
                },
            },
        ],
        "tls": {
            "enabled": False,
        },
    }


@pytest.fixture
def sample_yaml_file(tmp_dir: Path, sample_config_dict: dict[str, Any]) -> Path:
    """Create a sample YAML configuration file."""
    file_path = tmp_dir / "config.yaml"
    file_path.write_text(yaml.dump(sample_config_dict), encoding="utf-8")
    return file_path


@pytest.fixture
def sample_json_file(tmp_dir: Path, sample_config_dict: dict[str, Any]) -> Path:
    """Create a sample JSON configuration file."""
    file_path = tmp_dir / "config.json"
    file_path.write_text(json.dumps(sample_config_dict, indent=2), encoding="utf-8")
    return file_path


@pytest.fixture
def sample_toml_file(tmp_dir: Path) -> Path:
    """Create a sample TOML configuration file."""
    file_path = tmp_dir / "config.toml"
    content = textwrap.dedent("""\
        [server]
        bind_host = "127.0.0.1"
        bind_port = 9090
        backlog = 512
        keepalive_timeout = 60.0
        read_timeout = 15.0
        write_timeout = 15.0
        max_connections = 1000
        shutdown_timeout = 10.0

        [logging]
        level = "debug"
        format = "json"
        access_log = true
        access_log_path = ""
        error_log_path = ""
        max_file_size_bytes = 5_242_880
        backup_count = 3

        [[routes]]
        path = "/api"
        methods = ["GET", "POST"]
        strip_prefix = true

        [routes.upstream]
        connect_timeout = 3.0
        read_timeout = 10.0
        write_timeout = 10.0
        max_retries = 2
        retry_delay = 0.25
        pool_size = 32

        [[routes.upstream.targets]]
        host = "10.0.0.1"
        port = 3000
        weight = 2

        [[routes.upstream.targets]]
        host = "10.0.0.2"
        port = 3000
        weight = 1

        [[routes]]
        path = "/"

        [routes.upstream]

        [[routes.upstream.targets]]
        host = "10.0.0.3"
        port = 8000

        [tls]
        enabled = false
    """)
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def minimal_yaml_file(tmp_dir: Path) -> Path:
    """Create a minimal YAML config file with only required fields."""
    file_path = tmp_dir / "minimal.yaml"
    content = textwrap.dedent("""\
        server:
          bind_port: 8080
        routes:
          - path: "/"
            upstream:
              targets:
                - host: "127.0.0.1"
                  port: 3000
    """)
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_config() -> ProxyConfig:
    """Provide a pre-built ProxyConfig instance."""
    return ProxyConfig(
        server=ServerConfig(bind_host="127.0.0.1", bind_port=9090),
        logging=LoggingConfig(level="debug", format="json"),
        routes=(
            RouteConfig(
                path="/api",
                methods=("GET", "POST"),
                upstream=UpstreamConfig(
                    targets=(
                        UpstreamTargetConfig(host="10.0.0.1", port=3000, weight=2),
                        UpstreamTargetConfig(host="10.0.0.2", port=3000, weight=1),
                    ),
                ),
            ),
        ),
        tls=TlsConfig(enabled=False),
    )


@pytest.fixture
def container() -> Container:
    """Provide a fresh DI container."""
    return Container()
