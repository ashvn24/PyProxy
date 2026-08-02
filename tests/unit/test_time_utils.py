"""Tests for time utility functions."""

from __future__ import annotations

from datetime import UTC, datetime

from pyproxy.utils.time import (
    format_duration_human,
    format_duration_ms,
    monotonic_ns,
    utc_now,
)


class TestMonotonicNs:
    def test_returns_int(self):
        result = monotonic_ns()
        assert isinstance(result, int)

    def test_monotonically_increasing(self):
        t1 = monotonic_ns()
        t2 = monotonic_ns()
        assert t2 >= t1


class TestUtcNow:
    def test_returns_datetime(self):
        result = utc_now()
        assert isinstance(result, datetime)

    def test_timezone_aware(self):
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == UTC


class TestFormatDurationMs:
    def test_zero(self):
        assert format_duration_ms(0) == 0.0

    def test_one_ms(self):
        assert format_duration_ms(1_000_000) == 1.0

    def test_fractional(self):
        assert format_duration_ms(1_500_000) == 1.5

    def test_rounding(self):
        result = format_duration_ms(1_234_567)
        assert result == 1.235


class TestFormatDurationHuman:
    def test_nanoseconds(self):
        assert format_duration_human(500) == "500ns"

    def test_microseconds(self):
        result = format_duration_human(1_500)
        assert "µs" in result

    def test_milliseconds(self):
        result = format_duration_human(1_500_000)
        assert "ms" in result

    def test_seconds(self):
        result = format_duration_human(2_500_000_000)
        assert "s" in result
        assert "2.50" in result
