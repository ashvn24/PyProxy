"""Utility functions for PyProxy.

Provides cross-cutting utility functions including unique identifier
generation, time helpers, and common formatting.

Example::

    from pyproxy.utils import generate_request_id, monotonic_ns

    request_id = generate_request_id()
    start = monotonic_ns()
"""

from __future__ import annotations

from pyproxy.utils.identifiers import generate_correlation_id, generate_request_id
from pyproxy.utils.time import (
    format_duration_human,
    format_duration_ms,
    monotonic_ns,
    utc_now,
)

__all__: list[str] = [
    "format_duration_human",
    "format_duration_ms",
    "generate_correlation_id",
    "generate_request_id",
    "monotonic_ns",
    "utc_now",
]
