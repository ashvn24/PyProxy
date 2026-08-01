"""Tests for ConfigLoader — file loading, parsing, and format detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pyproxy.config.loader import ConfigLoader
from pyproxy.exceptions import ConfigFileNotFoundError, ConfigParseError, ConfigValidationError


class TestFormatDetection:
    """Tests for automatic format detection from file extension."""

    def test_yaml_extension(self, tmp_dir):
        path = tmp_dir / "config.yaml"
        path.write_text("server:\n  bind_port: 8080\n", encoding="utf-8")
        loader = ConfigLoader(path)
        assert loader.file_format == "yaml"

    def test_yml_extension(self, tmp_dir):
        path = tmp_dir / "config.yml"
        path.write_text("server:\n  bind_port: 8080\n", encoding="utf-8")
        loader = ConfigLoader(path)
        assert loader.file_format == "yaml"

    def test_json_extension(self, tmp_dir):
        path = tmp_dir / "config.json"
        path.write_text("{}", encoding="utf-8")
        loader = ConfigLoader(path)
        assert loader.file_format == "json"

    def test_toml_extension(self, tmp_dir):
        path = tmp_dir / "config.toml"
        path.write_text("[server]\n", encoding="utf-8")
        loader = ConfigLoader(path)
        assert loader.file_format == "toml"

    def test_unsupported_extension(self, tmp_dir):
        path = tmp_dir / "config.xml"
        with pytest.raises(ConfigValidationError, match="Unsupported file extension"):
            ConfigLoader(path)

    def test_no_extension(self, tmp_dir):
        path = tmp_dir / "config"
        with pytest.raises(ConfigValidationError, match="Unsupported file extension"):
            ConfigLoader(path)


class TestYamlLoading:
    """Tests for YAML configuration loading."""

    def test_load_valid_yaml(self, sample_yaml_file):
        loader = ConfigLoader(sample_yaml_file)
        config = loader.load()
        assert config.server.bind_host == "127.0.0.1"
        assert config.server.bind_port == 9090
        assert len(config.routes) == 2

    def test_load_empty_yaml(self, tmp_dir):
        path = tmp_dir / "empty.yaml"
        path.write_text("", encoding="utf-8")
        loader = ConfigLoader(path)
        config = loader.load()
        assert config.server.bind_port == 8080  # defaults

    def test_load_yaml_syntax_error(self, tmp_dir):
        path = tmp_dir / "bad.yaml"
        path.write_text("invalid: yaml: content: [", encoding="utf-8")
        loader = ConfigLoader(path)
        with pytest.raises(ConfigParseError, match="YAML"):
            loader.load()

    def test_load_yaml_non_mapping(self, tmp_dir):
        path = tmp_dir / "list.yaml"
        path.write_text("- item1\n- item2\n", encoding="utf-8")
        loader = ConfigLoader(path)
        with pytest.raises(ConfigParseError, match="YAML mapping"):
            loader.load()


class TestJsonLoading:
    """Tests for JSON configuration loading."""

    def test_load_valid_json(self, sample_json_file):
        loader = ConfigLoader(sample_json_file)
        config = loader.load()
        assert config.server.bind_host == "127.0.0.1"
        assert config.server.bind_port == 9090

    def test_load_json_syntax_error(self, tmp_dir):
        path = tmp_dir / "bad.json"
        path.write_text("{invalid json}", encoding="utf-8")
        loader = ConfigLoader(path)
        with pytest.raises(ConfigParseError, match="json"):
            loader.load()

    def test_load_json_non_object(self, tmp_dir):
        path = tmp_dir / "array.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        loader = ConfigLoader(path)
        with pytest.raises(ConfigParseError, match="JSON object"):
            loader.load()


class TestTomlLoading:
    """Tests for TOML configuration loading."""

    def test_load_valid_toml(self, sample_toml_file):
        loader = ConfigLoader(sample_toml_file)
        config = loader.load()
        assert config.server.bind_host == "127.0.0.1"
        assert config.server.bind_port == 9090

    def test_load_toml_syntax_error(self, tmp_dir):
        path = tmp_dir / "bad.toml"
        path.write_text("[invalid\ntoml content", encoding="utf-8")
        loader = ConfigLoader(path)
        with pytest.raises(ConfigParseError, match="toml"):
            loader.load()


class TestFileNotFound:
    """Tests for missing configuration files."""

    def test_file_not_found(self, tmp_dir):
        path = tmp_dir / "nonexistent.yaml"
        loader = ConfigLoader(path)
        with pytest.raises(ConfigFileNotFoundError):
            loader.load()

    def test_file_not_found_has_path(self, tmp_dir):
        path = tmp_dir / "nonexistent.yaml"
        loader = ConfigLoader(path)
        try:
            loader.load()
        except ConfigFileNotFoundError as exc:
            assert exc.file_path == path
            assert "nonexistent.yaml" in str(exc)


class TestLoadRaw:
    """Tests for load_raw() method."""

    def test_load_raw_returns_dict(self, sample_yaml_file):
        loader = ConfigLoader(sample_yaml_file)
        raw = loader.load_raw()
        assert isinstance(raw, dict)
        assert "server" in raw
        assert raw["server"]["bind_port"] == 9090

    def test_load_raw_file_not_found(self, tmp_dir):
        path = tmp_dir / "missing.yaml"
        loader = ConfigLoader(path)
        with pytest.raises(ConfigFileNotFoundError):
            loader.load_raw()


class TestMinimalConfig:
    """Tests for minimal configuration with defaults."""

    def test_minimal_yaml(self, minimal_yaml_file):
        loader = ConfigLoader(minimal_yaml_file)
        config = loader.load()
        assert config.server.bind_port == 8080
        assert config.server.bind_host == "0.0.0.0"  # default
        assert config.logging.level == "info"  # default
        assert len(config.routes) == 1
