"""Tests for environment variable override processing."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from pyproxy.config.env import _coerce_value, apply_environment_overrides


class TestCoerceValue:
    """Tests for the _coerce_value helper function."""

    def test_bool_true_variants(self):
        for value in ("true", "True", "TRUE", "yes", "YES", "1", "on", "ON"):
            assert _coerce_value(value) is True

    def test_bool_false_variants(self):
        for value in ("false", "False", "FALSE", "no", "NO", "0", "off", "OFF"):
            assert _coerce_value(value) is False

    def test_integer(self):
        assert _coerce_value("42") == 42
        assert _coerce_value("-1") == -1
        assert _coerce_value("0") is False  # "0" matches bool first

    def test_float(self):
        assert _coerce_value("3.14") == 3.14
        assert _coerce_value("-0.5") == -0.5

    def test_string_fallback(self):
        assert _coerce_value("hello") == "hello"
        assert _coerce_value("/path/to/file") == "/path/to/file"
        assert _coerce_value("") == ""


class TestApplyEnvironmentOverrides:
    """Tests for apply_environment_overrides."""

    def test_simple_override(self):
        with mock.patch.dict(os.environ, {"PYPROXY_SERVER__BIND_PORT": "9090"}):
            data = {"server": {"bind_port": 8080}}
            result = apply_environment_overrides(data)
            assert result["server"]["bind_port"] == 9090

    def test_nested_override(self):
        with mock.patch.dict(os.environ, {"PYPROXY_LOGGING__LEVEL": "debug"}):
            data = {"logging": {"level": "info"}}
            result = apply_environment_overrides(data)
            assert result["logging"]["level"] == "debug"

    def test_boolean_override(self):
        with mock.patch.dict(os.environ, {"PYPROXY_LOGGING__ACCESS_LOG": "false"}):
            data = {"logging": {"access_log": True}}
            result = apply_environment_overrides(data)
            assert result["logging"]["access_log"] is False

    def test_creates_intermediate_dicts(self):
        with mock.patch.dict(os.environ, {"PYPROXY_NEW_SECTION__KEY": "value"}):
            data = {}
            result = apply_environment_overrides(data)
            assert result["new_section"]["key"] == "value"

    def test_ignores_non_pyproxy_vars(self):
        with mock.patch.dict(os.environ, {"OTHER_VAR": "value"}, clear=True):
            data = {"server": {"bind_port": 8080}}
            result = apply_environment_overrides(data)
            assert result == {"server": {"bind_port": 8080}}

    def test_case_insensitive_keys(self):
        with mock.patch.dict(os.environ, {"PYPROXY_SERVER__BIND_HOST": "localhost"}):
            data = {"server": {"bind_host": "0.0.0.0"}}
            result = apply_environment_overrides(data)
            assert result["server"]["bind_host"] == "localhost"

    def test_does_not_corrupt_scalar_intermediate(self):
        """If an intermediate path segment is a scalar, skip the override."""
        with mock.patch.dict(os.environ, {"PYPROXY_SERVER__BIND_PORT__NESTED": "value"}):
            data = {"server": {"bind_port": 8080}}
            result = apply_environment_overrides(data)
            # bind_port should remain a scalar, not be converted to a dict
            assert result["server"]["bind_port"] == 8080

    def test_multiple_overrides(self):
        env_vars = {
            "PYPROXY_SERVER__BIND_PORT": "9090",
            "PYPROXY_LOGGING__LEVEL": "error",
        }
        with mock.patch.dict(os.environ, env_vars):
            data = {"server": {"bind_port": 8080}, "logging": {"level": "info"}}
            result = apply_environment_overrides(data)
            assert result["server"]["bind_port"] == 9090
            assert result["logging"]["level"] == "error"

    def test_empty_segments_ignored(self):
        """Environment variables with empty segments (e.g., PYPROXY__KEY) are ignored."""
        with mock.patch.dict(os.environ, {"PYPROXY___KEY": "value"}):
            data = {}
            result = apply_environment_overrides(data)
            # Should not add anything since there's an empty segment
            assert "key" not in result
