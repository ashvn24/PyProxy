"""Configuration-related exceptions.

These exceptions are raised during configuration file loading, parsing,
validation, and environment variable processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyproxy.exceptions.base import PyProxyError


class ConfigError(PyProxyError):
    """Base exception for all configuration errors.

    Attributes:
        error_code: Defaults to ``"CONFIG_ERROR"``.
    """

    def __init__(
        self,
        detail: str,
        *,
        error_code: str = "CONFIG_ERROR",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a ConfigError.

        Args:
            detail: Human-readable error description.
            error_code: Machine-readable error code.
            context: Additional diagnostic key-value pairs.
        """
        super().__init__(detail, error_code=error_code, context=context)


class ConfigFileNotFoundError(ConfigError):
    """Raised when the specified configuration file does not exist.

    Attributes:
        file_path: The path that was not found.
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize a ConfigFileNotFoundError.

        Args:
            file_path: The configuration file path that was not found.
        """
        self.file_path: Path = file_path
        super().__init__(
            f"Configuration file not found: {file_path}",
            error_code="CONFIG_FILE_NOT_FOUND",
            context={"file_path": str(file_path)},
        )


class ConfigValidationError(ConfigError):
    """Raised when configuration values fail validation.

    Attributes:
        field: The configuration field that failed validation.
        value: The invalid value that was provided.
        reason: Explanation of why the value is invalid.
    """

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
    ) -> None:
        """Initialize a ConfigValidationError.

        Args:
            field: The configuration field name (dot-separated path).
            value: The invalid value.
            reason: Why the value is invalid.
        """
        self.field: str = field
        self.value: Any = value
        self.reason: str = reason
        super().__init__(
            f"Invalid configuration for '{field}': {reason}",
            error_code="CONFIG_VALIDATION_ERROR",
            context={
                "field": field,
                "value": repr(value),
                "reason": reason,
            },
        )


class ConfigParseError(ConfigError):
    """Raised when a configuration file cannot be parsed.

    Attributes:
        file_path: The path of the file that failed parsing.
        file_format: The expected format (yaml, json, toml).
    """

    def __init__(
        self,
        file_path: Path,
        file_format: str,
        cause: str,
    ) -> None:
        """Initialize a ConfigParseError.

        Args:
            file_path: The path of the unparseable file.
            file_format: The expected file format.
            cause: Description of the parse failure.
        """
        self.file_path: Path = file_path
        self.file_format: str = file_format
        super().__init__(
            f"Failed to parse {file_format.upper()} configuration: {cause}",
            error_code="CONFIG_PARSE_ERROR",
            context={
                "file_path": str(file_path),
                "file_format": file_format,
                "cause": cause,
            },
        )
