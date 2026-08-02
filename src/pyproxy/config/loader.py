"""Configuration file loader with multi-format support.

Loads configuration from YAML, JSON, or TOML files, applies environment
variable overrides, and produces a validated :class:`ProxyConfig` instance.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml

from pyproxy.config.env import apply_environment_overrides
from pyproxy.config.models import ProxyConfig
from pyproxy.exceptions.config import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)

# Mapping of file extensions to their format identifiers
_FORMAT_MAP: dict[str, str] = {
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
}


class ConfigLoader:
    """Loads, parses, and validates configuration files.

    Supports YAML, JSON, and TOML formats. The format is detected automatically
    from the file extension. After parsing, environment variable overrides
    (``PYPROXY_*``) are applied before the final validation pass.

    Example::

        loader = ConfigLoader(Path("config.yaml"))
        config = loader.load()
        print(config.server.bind_port)
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize the ConfigLoader.

        Args:
            file_path: Path to the configuration file.

        Raises:
            ConfigFileNotFoundError: If the file does not exist.
            ConfigValidationError: If the file extension is not supported.
        """
        self._file_path: Path = file_path
        self._format: str = self._detect_format()

    @property
    def file_path(self) -> Path:
        """The configuration file path.

        Returns:
            The path that was provided at construction.
        """
        return self._file_path

    @property
    def file_format(self) -> str:
        """The detected configuration file format.

        Returns:
            One of ``"yaml"``, ``"json"``, or ``"toml"``.
        """
        return self._format

    def _detect_format(self) -> str:
        """Detect the configuration file format from its extension.

        Returns:
            The format identifier string.

        Raises:
            ConfigValidationError: If the file extension is not supported.
        """
        suffix = self._file_path.suffix.lower()
        file_format = _FORMAT_MAP.get(suffix)
        if file_format is None:
            supported = ", ".join(sorted(_FORMAT_MAP.keys()))
            raise ConfigValidationError(
                field="config_file",
                value=str(self._file_path),
                reason=f"Unsupported file extension '{suffix}'. Supported: {supported}",
            )
        return file_format

    def load(self) -> ProxyConfig:
        """Load, parse, validate, and return the configuration.

        This method:
        1. Reads the file from disk.
        2. Parses it according to the detected format.
        3. Applies environment variable overrides.
        4. Constructs and validates the ``ProxyConfig`` model.

        Returns:
            A fully validated, immutable ProxyConfig instance.

        Raises:
            ConfigFileNotFoundError: If the file does not exist.
            ConfigParseError: If the file content is malformed.
            ConfigValidationError: If configuration values fail validation.
        """
        raw_data = self._read_file()
        parsed_data = self._parse(raw_data)
        overridden_data = apply_environment_overrides(parsed_data)
        return ProxyConfig.from_dict(overridden_data)

    def load_raw(self) -> dict[str, Any]:
        """Load and parse the configuration file without validation.

        Useful for the ``validate`` CLI command to report all validation
        errors at once rather than failing on the first.

        Returns:
            The raw parsed dictionary with environment overrides applied.

        Raises:
            ConfigFileNotFoundError: If the file does not exist.
            ConfigParseError: If the file content is malformed.
        """
        raw_data = self._read_file()
        parsed_data = self._parse(raw_data)
        return apply_environment_overrides(parsed_data)

    def _read_file(self) -> str | bytes:
        """Read the configuration file from disk.

        Returns:
            File contents as a string (YAML/JSON) or bytes (TOML).

        Raises:
            ConfigFileNotFoundError: If the file does not exist.
        """
        if not self._file_path.exists():
            raise ConfigFileNotFoundError(self._file_path)

        if self._format == "toml":
            return self._file_path.read_bytes()
        return self._file_path.read_text(encoding="utf-8")

    def _parse(self, raw_data: str | bytes) -> dict[str, Any]:
        """Parse raw file contents into a dictionary.

        Args:
            raw_data: The raw file contents.

        Returns:
            The parsed configuration dictionary.

        Raises:
            ConfigParseError: If the content cannot be parsed.
        """
        parsers = {
            "yaml": self._parse_yaml,
            "json": self._parse_json,
            "toml": self._parse_toml,
        }
        return parsers[self._format](raw_data)

    def _parse_yaml(self, raw_data: str | bytes) -> dict[str, Any]:
        """Parse YAML content.

        Args:
            raw_data: Raw YAML string.

        Returns:
            Parsed dictionary.

        Raises:
            ConfigParseError: On YAML syntax errors.
        """
        try:
            result = yaml.safe_load(raw_data)
        except yaml.YAMLError as exc:
            raise ConfigParseError(
                file_path=self._file_path,
                file_format="yaml",
                cause=str(exc),
            ) from exc

        if result is None:
            return {}
        if not isinstance(result, dict):
            raise ConfigParseError(
                file_path=self._file_path,
                file_format="yaml",
                cause="Configuration file must contain a YAML mapping at the top level",
            )
        return result  # type: ignore[no-any-return]

    def _parse_json(self, raw_data: str | bytes) -> dict[str, Any]:
        """Parse JSON content.

        Args:
            raw_data: Raw JSON string.

        Returns:
            Parsed dictionary.

        Raises:
            ConfigParseError: On JSON syntax errors.
        """
        try:
            result = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            raise ConfigParseError(
                file_path=self._file_path,
                file_format="json",
                cause=str(exc),
            ) from exc

        if not isinstance(result, dict):
            raise ConfigParseError(
                file_path=self._file_path,
                file_format="json",
                cause="Configuration file must contain a JSON object at the top level",
            )
        return result  # type: ignore[no-any-return]

    def _parse_toml(self, raw_data: str | bytes) -> dict[str, Any]:
        """Parse TOML content.

        Args:
            raw_data: Raw TOML bytes.

        Returns:
            Parsed dictionary.

        Raises:
            ConfigParseError: On TOML syntax errors.
        """
        if isinstance(raw_data, str):
            raw_data = raw_data.encode()

        try:
            result = tomllib.loads(raw_data.decode("utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ConfigParseError(
                file_path=self._file_path,
                file_format="toml",
                cause=str(exc),
            ) from exc

        return result  # type: ignore[no-any-return]
