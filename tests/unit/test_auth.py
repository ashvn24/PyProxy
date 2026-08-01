"""Unit tests for AuthMiddleware."""

from __future__ import annotations

import base64
import pytest

from pyproxy.auth import AuthMiddleware
from pyproxy.protocol import HTTPRequest, HTTPResponse, Headers


class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    @pytest.mark.asyncio
    async def test_api_key_valid(self):
        auth = AuthMiddleware(valid_api_keys={"key123"})
        req = HTTPRequest(headers=Headers({"X-API-Key": "key123"}))

        result = await auth.process_request(req)
        assert result is None

    @pytest.mark.asyncio
    async def test_api_key_invalid(self):
        auth = AuthMiddleware(valid_api_keys={"key123"})
        req = HTTPRequest(headers=Headers({"X-API-Key": "wrong"}))

        result = await auth.process_request(req)
        assert isinstance(result, HTTPResponse)
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_basic_auth_valid(self):
        auth = AuthMiddleware(basic_credentials={"admin": "secret"})
        creds = base64.b64encode(b"admin:secret").decode("ascii")
        req = HTTPRequest(headers=Headers({"Authorization": f"Basic {creds}"}))

        result = await auth.process_request(req)
        assert result is None
