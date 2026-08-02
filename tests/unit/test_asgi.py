"""Unit tests for PyProxy ASGI & FastAPI Gateway integration."""

from __future__ import annotations

import pytest

from pyproxy.asgi import PyProxyGateway, PyProxyRouter
from pyproxy.auth import AuthMiddleware
from pyproxy.middleware import BaseMiddleware
from pyproxy.protocol import HTTPRequest, HTTPResponse


class CustomAuthPlugin(BaseMiddleware):
    """Example custom JWT / auth plugin."""

    async def process_request(self, request: HTTPRequest) -> HTTPRequest | HTTPResponse | None:
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr != "Bearer secret-jwt-token":
            return HTTPResponse.create_error(401, "Invalid JWT Token")
        return None


class TestPyProxyGateway:
    """Tests for PyProxyGateway ASGI 3.0 middleware."""

    def test_init_with_dict_routes(self):
        gateway = PyProxyGateway(
            routes=[
                {"path": "/api", "target": "http://127.0.0.1:8001"},
                {"path": "/users", "target": "http://127.0.0.1:8002", "strip_prefix": True},
            ]
        )
        assert len(gateway.router.routes) == 2

    def test_add_route(self):
        gateway = PyProxyGateway()
        gateway.add_route("/service", "http://localhost:9000", methods={"GET", "POST"})
        assert len(gateway.router.routes) == 1
        rule = gateway.router.routes[0]
        assert rule.path_pattern == "/service"
        assert getattr(rule, "_target_host") == "localhost"
        assert getattr(rule, "_target_port") == 9000

    def test_domain_target_urls(self):
        gateway = PyProxyGateway()
        gateway.add_route("/users", "https://api.users-service.com")
        gateway.add_route("/payments", "payments.company.org")

        rule1 = gateway.router.routes[0]
        assert getattr(rule1, "_target_host") == "api.users-service.com"
        assert getattr(rule1, "_target_port") == 443
        assert getattr(rule1, "_target_ssl") is True

        rule2 = gateway.router.routes[1]
        assert getattr(rule2, "_target_host") == "payments.company.org"
        assert getattr(rule2, "_target_port") == 80
        assert getattr(rule2, "_target_ssl") is False

    def test_plugin_registration(self):
        gateway = PyProxyGateway(
            auth=AuthMiddleware(valid_api_keys={"my-api-key"}),
            rate_limit=60,
            enable_caching=True,
        )
        assert len(gateway.middleware_pipeline._middlewares) == 3

    @pytest.mark.asyncio
    async def test_auth_plugin_short_circuit_401(self):
        sent_messages = []

        async def dummy_send(msg):
            sent_messages.append(msg)

        async def dummy_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        gateway = PyProxyGateway(
            routes=[{"path": "/api", "target": "http://127.0.0.1:8001"}],
            auth=AuthMiddleware(valid_api_keys={"valid-key"}),
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [(b"x-api-key", b"invalid-key")],
        }

        await gateway(scope, dummy_receive, dummy_send)
        assert len(sent_messages) == 2
        assert sent_messages[0]["type"] == "http.response.start"
        assert sent_messages[0]["status"] == 401

    @pytest.mark.asyncio
    async def test_custom_jwt_plugin(self):
        sent_messages = []

        async def dummy_send(msg):
            sent_messages.append(msg)

        async def dummy_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        gateway = PyProxyGateway(
            routes=[{"path": "/api", "target": "http://127.0.0.1:8001"}],
            middlewares=[CustomAuthPlugin()],
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/protected",
            "headers": [(b"authorization", b"Bearer wrong-token")],
        }

        await gateway(scope, dummy_receive, dummy_send)
        assert len(sent_messages) == 2
        assert sent_messages[0]["status"] == 401
        assert b"Invalid JWT Token" in sent_messages[1]["body"]

    @pytest.mark.asyncio
    async def test_unhandled_scope_type_delegates_to_app(self):
        called = False

        async def dummy_app(scope, receive, send):
            nonlocal called
            called = True

        gateway = PyProxyGateway(app=dummy_app)
        await gateway({"type": "lifespan"}, None, None)
        assert called is True

    @pytest.mark.asyncio
    async def test_unmatched_route_delegates_to_app(self):
        called = False

        async def dummy_app(scope, receive, send):
            nonlocal called
            called = True

        gateway = PyProxyGateway(
            app=dummy_app,
            routes=[{"path": "/api", "target": "http://127.0.0.1:8001"}],
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
        }

        await gateway(scope, None, None)
        assert called is True

    @pytest.mark.asyncio
    async def test_unmatched_route_no_app_returns_404(self):
        sent_messages = []

        async def dummy_send(msg):
            sent_messages.append(msg)

        gateway = PyProxyGateway(routes=[{"path": "/api", "target": "http://127.0.0.1:8001"}])

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/unmatched",
            "headers": [],
        }

        await gateway(scope, None, dummy_send)
        assert len(sent_messages) == 2
        assert sent_messages[0]["type"] == "http.response.start"
        assert sent_messages[0]["status"] == 404


class TestPyProxyRouter:
    """Tests for PyProxyRouter helper."""

    def test_router_add_route(self):
        router = PyProxyRouter()
        router.add_route("/orders", target="http://orders-service:8080")
        assert len(router.gateway.router.routes) == 1
        rule = router.gateway.router.routes[0]
        assert getattr(rule, "_target_host") == "orders-service"
