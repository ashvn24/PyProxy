"""Unit tests for IPFilter, RateLimiter, and CORSMiddleware."""

from __future__ import annotations

import pytest

from pyproxy.protocol import HTTPRequest, HTTPResponse, Headers
from pyproxy.security import CORSMiddleware, IPFilter, RateLimiter


class TestIPFilter:
    """Tests for IPFilter allowlist and denylist."""

    def test_denylist_blocks_ip(self):
        f = IPFilter(denylist=["192.168.1.100", "10.0.0.0/8"])
        assert f.is_allowed("192.168.1.100") is False
        assert f.is_allowed("10.0.1.5") is False
        assert f.is_allowed("172.16.0.1") is True

    def test_allowlist_permits_only_listed(self):
        f = IPFilter(allowlist=["127.0.0.1"])
        assert f.is_allowed("127.0.0.1") is True
        assert f.is_allowed("192.168.1.1") is False


class TestRateLimiter:
    """Tests for RateLimiter token bucket."""

    @pytest.mark.asyncio
    async def test_burst_capacity(self):
        limiter = RateLimiter(requests_per_second=1.0, burst=2)
        assert await limiter.is_allowed("client1") is True
        assert await limiter.is_allowed("client1") is True
        assert await limiter.is_allowed("client1") is False


class TestCORSMiddleware:
    """Tests for CORSMiddleware."""

    @pytest.mark.asyncio
    async def test_preflight_options(self):
        cors = CORSMiddleware()
        req = HTTPRequest(
            method="OPTIONS",
            headers=Headers({
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            }),
        )

        res = await cors.process_request(req)
        assert isinstance(res, HTTPResponse)
        assert res.status_code == 204
        assert res.headers.get("Access-Control-Allow-Origin") == "*"
