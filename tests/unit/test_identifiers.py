"""Tests for unique identifier generation."""

from __future__ import annotations

import re

from pyproxy.utils.identifiers import generate_correlation_id, generate_request_id

# UUID v4 format: 8-4-4-4-12 hex digits
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestGenerateRequestId:
    """Tests for request ID generation."""

    def test_returns_string(self):
        result = generate_request_id()
        assert isinstance(result, str)

    def test_uuid_format(self):
        result = generate_request_id()
        assert _UUID_PATTERN.match(result), f"Not a valid UUID v4: {result}"

    def test_unique_ids(self):
        ids = {generate_request_id() for _ in range(1000)}
        assert len(ids) == 1000, "Generated IDs are not unique"

    def test_consistent_length(self):
        ids = [generate_request_id() for _ in range(100)]
        lengths = {len(id_) for id_ in ids}
        assert len(lengths) == 1, "UUID lengths should be consistent"
        assert 36 in lengths  # UUID string length with hyphens


class TestGenerateCorrelationId:
    """Tests for correlation ID generation."""

    def test_returns_string(self):
        result = generate_correlation_id()
        assert isinstance(result, str)

    def test_uuid_format(self):
        result = generate_correlation_id()
        assert _UUID_PATTERN.match(result), f"Not a valid UUID v4: {result}"

    def test_unique_from_request_id(self):
        req_id = generate_request_id()
        corr_id = generate_correlation_id()
        assert req_id != corr_id
