"""Unit tests for MiddlewarePipeline and BaseMiddleware."""

from __future__ import annotations

import pytest

from pyproxy.middleware import BaseMiddleware, MiddlewarePipeline
from pyproxy.protocol import HTTPRequest, HTTPResponse


class CustomHeaderMiddleware(BaseMiddleware):
    async def process_request(self, request: HTTPRequest) -> HTTPRequest | None:
        request.headers.set("X-Custom-Req", "1")
        return request

    async def process_response(self, request: HTTPRequest, response: HTTPResponse) -> HTTPResponse:
        response.headers.set("X-Custom-Resp", "1")
        return response


class ShortCircuitMiddleware(BaseMiddleware):
    async def process_request(self, request: HTTPRequest) -> HTTPResponse | None:
        if request.path == "/blocked":
            return HTTPResponse.create_error(403, "Access Denied")
        return None


class TestMiddlewarePipeline:
    """Tests for MiddlewarePipeline execution."""

    @pytest.mark.asyncio
    async def test_normal_pipeline_flow(self):
        pipeline = MiddlewarePipeline()
        pipeline.add_middleware(CustomHeaderMiddleware())

        req = HTTPRequest(path="/test")
        res_req = await pipeline.execute_request(req)
        assert isinstance(res_req, HTTPRequest)
        assert res_req.headers.get("X-Custom-Req") == "1"

        resp = HTTPResponse(status_code=200)
        res_resp = await pipeline.execute_response(res_req, resp)
        assert res_resp.headers.get("X-Custom-Resp") == "1"

    @pytest.mark.asyncio
    async def test_short_circuit_flow(self):
        pipeline = MiddlewarePipeline()
        pipeline.add_middleware(ShortCircuitMiddleware())

        req = HTTPRequest(path="/blocked")
        result = await pipeline.execute_request(req)
        assert isinstance(result, HTTPResponse)
        assert result.status_code == 403
