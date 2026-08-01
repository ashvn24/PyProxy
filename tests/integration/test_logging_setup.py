"""Integration tests for the logging setup."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from pyproxy.config.models import LoggingConfig
from pyproxy.logging.context import RequestContext
from pyproxy.logging.setup import get_logger, setup_logging


class TestLoggingSetup:
    """Integration tests for the full logging pipeline."""

    def test_setup_creates_loggers(self):
        config = LoggingConfig(level="debug", format="json")
        setup_logging(config)

        logger = logging.getLogger("pyproxy")
        assert logger.level == logging.DEBUG

    def test_json_output_to_file(self, tmp_dir):
        log_file = tmp_dir / "test_access.log"
        config = LoggingConfig(
            level="info",
            format="json",
            access_log=True,
            access_log_path=str(log_file),
        )
        setup_logging(config)

        logger = logging.getLogger("pyproxy.access")
        logger.info("Test access log entry")

        # Force flush
        for handler in logger.handlers:
            handler.flush()

        content = log_file.read_text(encoding="utf-8")
        assert content.strip()  # Not empty

        # Each line should be valid JSON
        for line in content.strip().split("\n"):
            parsed = json.loads(line)
            assert "message" in parsed
            assert "timestamp" in parsed

    def test_error_log_to_file(self, tmp_dir):
        error_file = tmp_dir / "test_error.log"
        config = LoggingConfig(
            level="info",
            format="json",
            error_log_path=str(error_file),
        )
        setup_logging(config)

        logger = logging.getLogger("pyproxy.error")
        logger.error("Test error message")

        for handler in logger.handlers:
            handler.flush()

        content = error_file.read_text(encoding="utf-8")
        assert "Test error message" in content

    def test_get_logger_prefixes(self):
        logger = get_logger("my_module")
        assert logger.name == "pyproxy.my_module"

    def test_get_logger_already_prefixed(self):
        logger = get_logger("pyproxy.existing")
        assert logger.name == "pyproxy.existing"

    def test_context_in_log_output(self, tmp_dir):
        log_file = tmp_dir / "context_test.log"
        config = LoggingConfig(
            level="info",
            format="json",
            access_log=True,
            access_log_path=str(log_file),
        )
        setup_logging(config)

        logger = logging.getLogger("pyproxy.access")

        with RequestContext(request_id="ctx-test-123"):
            logger.info("Request with context")

        for handler in logger.handlers:
            handler.flush()

        content = log_file.read_text(encoding="utf-8")
        for line in content.strip().split("\n"):
            parsed = json.loads(line)
            if "Request with context" in parsed.get("message", ""):
                assert parsed.get("request_id") == "ctx-test-123"
                break
        else:
            pytest.fail("Log entry with context not found")

    def test_text_format_setup(self):
        config = LoggingConfig(level="info", format="text")
        setup_logging(config)
        logger = logging.getLogger("pyproxy")
        # Should not raise
        logger.info("Text format test")

    def test_idempotent_setup(self):
        """Calling setup_logging multiple times should not add duplicate handlers."""
        config = LoggingConfig(level="info", format="json")
        setup_logging(config)
        handler_count = len(logging.getLogger("pyproxy").handlers)
        setup_logging(config)
        assert len(logging.getLogger("pyproxy").handlers) == handler_count
