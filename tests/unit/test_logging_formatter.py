"""Tests for the JSON log formatter."""

from __future__ import annotations

import logging

import orjson
import pytest

from pyproxy.logging.context import RequestContext
from pyproxy.logging.formatter import JSONFormatter, TextFormatter


@pytest.fixture
def json_formatter():
    return JSONFormatter()


@pytest.fixture
def text_formatter():
    return TextFormatter()


@pytest.fixture
def log_record():
    """Create a basic log record for testing."""
    record = logging.LogRecord(
        name="pyproxy.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    return record


class TestJSONFormatter:
    """Tests for JSONFormatter output."""

    def test_valid_json_output(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert isinstance(parsed, dict)

    def test_required_fields(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed

    def test_level_lowercase(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert parsed["level"] == "info"

    def test_logger_name(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert parsed["logger"] == "pyproxy.test"

    def test_message_content(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert parsed["message"] == "Test message"

    def test_timestamp_iso_format(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        # ISO 8601 format should contain 'T' and timezone info
        assert "T" in parsed["timestamp"]

    def test_request_id_from_context(self, json_formatter, log_record):
        with RequestContext(request_id="test-req-123"):
            output = json_formatter.format(log_record)
            parsed = orjson.loads(output)
            assert parsed["request_id"] == "test-req-123"

    def test_correlation_id_from_context(self, json_formatter, log_record):
        with RequestContext(correlation_id="test-corr-456"):
            output = json_formatter.format(log_record)
            parsed = orjson.loads(output)
            assert parsed["correlation_id"] == "test-corr-456"

    def test_no_context_no_ids(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert "request_id" not in parsed
        assert "correlation_id" not in parsed

    def test_extra_fields(self, json_formatter):
        record = logging.LogRecord(
            name="pyproxy.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="With extras",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"  # type: ignore[attr-defined]
        output = json_formatter.format(record)
        parsed = orjson.loads(output)
        assert parsed["custom_field"] == "custom_value"

    def test_source_for_warnings(self, json_formatter):
        record = logging.LogRecord(
            name="pyproxy.test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=99,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        output = json_formatter.format(record)
        parsed = orjson.loads(output)
        assert "source" in parsed
        assert parsed["source"]["line"] == 99

    def test_no_source_for_info(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        parsed = orjson.loads(output)
        assert "source" not in parsed

    def test_exception_info(self, json_formatter):
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="pyproxy.test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            output = json_formatter.format(record)
            parsed = orjson.loads(output)
            assert "exception" in parsed
            assert parsed["exception"]["type"] == "ValueError"
            assert "test error" in parsed["exception"]["message"]

    def test_single_line_output(self, json_formatter, log_record):
        output = json_formatter.format(log_record)
        assert "\n" not in output


class TestTextFormatter:
    """Tests for TextFormatter output."""

    def test_contains_level(self, text_formatter, log_record):
        output = text_formatter.format(log_record)
        assert "INFO" in output

    def test_contains_message(self, text_formatter, log_record):
        output = text_formatter.format(log_record)
        assert "Test message" in output

    def test_contains_logger(self, text_formatter, log_record):
        output = text_formatter.format(log_record)
        assert "pyproxy.test" in output

    def test_request_id_in_text(self, text_formatter, log_record):
        with RequestContext(request_id="abc12345-full-id"):
            output = text_formatter.format(log_record)
            assert "req=abc12345" in output
