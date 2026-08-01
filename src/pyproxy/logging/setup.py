"""Logging system setup and configuration.

Configures Python's stdlib logging with appropriate handlers, formatters,
and log levels based on the :class:`LoggingConfig`. Supports both JSON
and text output formats, file rotation, and separate access/error loggers.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from pyproxy.config.models import LoggingConfig
from pyproxy.logging.formatter import JSONFormatter, TextFormatter

# Well-known logger names used throughout PyProxy
LOGGER_ROOT = "pyproxy"
LOGGER_ACCESS = "pyproxy.access"
LOGGER_ERROR = "pyproxy.error"
LOGGER_SERVER = "pyproxy.server"
LOGGER_CONFIG = "pyproxy.config"

_LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def setup_logging(config: LoggingConfig) -> None:
    """Configure the logging system based on the provided configuration.

    Sets up:
    - Root ``pyproxy`` logger with console output.
    - Access logger (``pyproxy.access``) with optional file handler.
    - Error logger (``pyproxy.error``) with optional file handler.

    All handlers use the format specified in the config (JSON or text).
    File handlers use :class:`RotatingFileHandler` for automatic rotation.

    This function is idempotent — calling it multiple times replaces
    existing handlers rather than adding duplicates.

    Args:
        config: The logging configuration to apply.
    """
    log_level = _LOG_LEVEL_MAP.get(config.level, logging.INFO)

    # Select formatter based on config
    formatter: logging.Formatter
    if config.format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Configure the root pyproxy logger
    root_logger = logging.getLogger(LOGGER_ROOT)
    root_logger.setLevel(log_level)
    _clear_handlers(root_logger)

    # Console handler (stdout for INFO and below, stderr for WARNING and above)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(_MaxLevelFilter(logging.INFO))
    root_logger.addHandler(stdout_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    # Access logger — separate from main logger to allow independent configuration
    access_logger = logging.getLogger(LOGGER_ACCESS)
    access_logger.setLevel(log_level)
    access_logger.propagate = False
    _clear_handlers(access_logger)

    if config.access_log:
        access_console = logging.StreamHandler(sys.stdout)
        access_console.setLevel(log_level)
        access_console.setFormatter(formatter)
        access_logger.addHandler(access_console)

        if config.access_log_path:
            access_file = _create_rotating_handler(
                config.access_log_path,
                config.max_file_size_bytes,
                config.backup_count,
                formatter,
            )
            access_logger.addHandler(access_file)

    # Error logger — for error-level entries with optional file output
    error_logger = logging.getLogger(LOGGER_ERROR)
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False
    _clear_handlers(error_logger)

    error_console = logging.StreamHandler(sys.stderr)
    error_console.setLevel(logging.ERROR)
    error_console.setFormatter(formatter)
    error_logger.addHandler(error_console)

    if config.error_log_path:
        error_file = _create_rotating_handler(
            config.error_log_path,
            config.max_file_size_bytes,
            config.backup_count,
            formatter,
        )
        error_logger.addHandler(error_file)


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the ``pyproxy`` namespace.

    Ensures all loggers are children of the root ``pyproxy`` logger, which
    means they inherit its handlers and level configuration.

    Args:
        name: Logger name. Will be prefixed with ``pyproxy.`` if not already.

    Returns:
        A configured Logger instance.
    """
    if not name.startswith("pyproxy."):
        name = f"pyproxy.{name}"
    return logging.getLogger(name)


def _clear_handlers(logger: logging.Logger) -> None:
    """Remove all existing handlers from a logger.

    Args:
        logger: The logger to clear handlers from.
    """
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def _create_rotating_handler(
    file_path: str,
    max_bytes: int,
    backup_count: int,
    formatter: logging.Formatter,
) -> RotatingFileHandler:
    """Create a rotating file handler with the specified parameters.

    Args:
        file_path: Path to the log file.
        max_bytes: Maximum file size before rotation.
        backup_count: Number of backup files to keep.
        formatter: The formatter to use for log entries.

    Returns:
        A configured RotatingFileHandler instance.
    """
    handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


class _MaxLevelFilter(logging.Filter):
    """Filter that only allows log records at or below a maximum level.

    Used to prevent WARNING+ messages from appearing on stdout
    (they go to stderr instead).
    """

    def __init__(self, max_level: int) -> None:
        """Initialize the filter.

        Args:
            max_level: Maximum log level to allow through this filter.
        """
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Determine if the record should be allowed through.

        Args:
            record: The log record to filter.

        Returns:
            True if the record level is at or below the maximum.
        """
        return record.levelno <= self._max_level
