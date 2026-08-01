"""Unique identifier generation for request tracing.

Provides UUID-based identifier generation for request IDs and
correlation IDs. Uses UUID v4 (random) for broad compatibility.

Why UUID v4 instead of UUID v7?
- UUID v7 (time-sortable) is ideal but requires Python 3.14+ for stdlib
  support. We use UUID v4 for now and will migrate to v7 when the
  minimum Python version is raised.
"""

from __future__ import annotations

import uuid


def generate_request_id() -> str:
    """Generate a unique request identifier.

    Each inbound request receives a unique ID for tracing through
    the proxy pipeline and into upstream services.

    Returns:
        A hyphenated UUID v4 string (e.g., ``"550e8400-e29b-41d4-a716-446655440000"``).
    """
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """Generate a unique correlation identifier.

    Correlation IDs link related requests across distributed systems.
    If an incoming request already carries a correlation ID (e.g., via
    ``X-Correlation-ID`` header), that value should be used instead
    of generating a new one.

    Returns:
        A hyphenated UUID v4 string.
    """
    return str(uuid.uuid4())
