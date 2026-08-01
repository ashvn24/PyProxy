"""Time utilities for centralized clock access.

Centralizes all time-related operations to:
1. Ensure consistent time sources across the codebase.
2. Enable test-time clock mocking without monkey-patching stdlib.
3. Provide convenient formatting helpers.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime


def monotonic_ns() -> int:
    """Get the current monotonic clock value in nanoseconds.

    Monotonic clocks are not affected by system clock adjustments
    (NTP, manual changes) and are the correct choice for measuring
    durations and enforcing timeouts.

    Returns:
        Monotonic time in nanoseconds.
    """
    return time.monotonic_ns()


def utc_now() -> datetime:
    """Get the current UTC datetime.

    Uses timezone-aware datetime with the UTC timezone. Prefer this
    over ``datetime.utcnow()`` (which returns naive datetimes and is
    deprecated in Python 3.12+).

    Returns:
        The current UTC datetime, timezone-aware.
    """
    return datetime.now(tz=UTC)


def format_duration_ms(duration_ns: int) -> float:
    """Convert a nanosecond duration to milliseconds.

    Args:
        duration_ns: Duration in nanoseconds.

    Returns:
        Duration in milliseconds, rounded to 3 decimal places.
    """
    return round(duration_ns / 1_000_000, 3)


def format_duration_human(duration_ns: int) -> str:
    """Format a nanosecond duration as a human-readable string.

    Automatically selects the best unit (ns, µs, ms, s) based on magnitude.

    Args:
        duration_ns: Duration in nanoseconds.

    Returns:
        A human-readable duration string (e.g., ``"1.234ms"``, ``"2.50s"``).
    """
    if duration_ns < 1_000:
        return f"{duration_ns}ns"
    if duration_ns < 1_000_000:
        return f"{duration_ns / 1_000:.2f}µs"
    if duration_ns < 1_000_000_000:
        return f"{duration_ns / 1_000_000:.2f}ms"
    return f"{duration_ns / 1_000_000_000:.2f}s"
