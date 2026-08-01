"""Unit tests for MemoryCache and CacheManager."""

from __future__ import annotations

import pytest

from pyproxy.cache import CacheManager, MemoryCache
from pyproxy.protocol import HTTPRequest, HTTPResponse, Headers


class TestMemoryCache:
    """Tests for MemoryCache backend."""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = MemoryCache()
        await cache.set("k1", b"hello world", ttl_seconds=60)
        val = await cache.get("k1")
        assert val == b"hello world"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        cache = MemoryCache()
        assert await cache.get("missing") is None


class TestCacheManager:
    """Tests for CacheManager conditional requests."""

    def test_etag_304_match(self):
        manager = CacheManager()
        req = HTTPRequest(method="GET", headers=Headers({"If-None-Match": '"abc12345"'}))
        resp = HTTPResponse(status_code=200, headers=Headers({"ETag": '"abc12345"'}), body=b"data")

        res_304 = manager.process_conditional_request(req, resp)
        assert res_304.status_code == 304
        assert res_304.body == b""
