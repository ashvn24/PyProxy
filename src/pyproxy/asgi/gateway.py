"""PyProxy ASGI Gateway Integration for FastAPI and Starlette.

Provides PyProxyGateway ASGI 3.0 middleware/application to mount PyProxy as a
centralized microservice reverse proxy gateway inside FastAPI applications with
full plugin support (JWT/Auth, Rate Limiting, Caching, and Custom Middlewares).
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Any, Awaitable, Callable, Sequence

from pyproxy.config.models import CacheConfig, RateLimiterConfig, RouteConfig, UpstreamConfig, UpstreamTargetConfig
from pyproxy.middleware.pipeline import BaseMiddleware, MiddlewarePipeline
from pyproxy.protocol.headers import Headers
from pyproxy.protocol.request import HTTPRequest
from pyproxy.protocol.response import HTTPResponse
from pyproxy.routing.router import Router
from pyproxy.routing.rule import RouteMatchType, RouteRule

logger = logging.getLogger("pyproxy.asgi")

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class PyProxyGateway:
    """ASGI 3.0 Middleware / Application Gateway with full Plugin Support.

    Allows mounting PyProxy as a reverse proxy gateway directly inside FastAPI,
    Starlette, or any ASGI 3.0 application with built-in or custom plugins
    (JWT/Auth, Rate Limiting, Caching, and custom Middlewares).

    Example::

        from fastapi import FastAPI
        from pyproxy.asgi import PyProxyGateway
        from pyproxy.auth import AuthMiddleware

        app = FastAPI(title="Central Microservice Gateway")
        app.add_middleware(
            PyProxyGateway,
            routes=[
                {"path": "/users", "target": "http://127.0.0.1:8001"},
                {"path": "/orders", "target": "http://127.0.0.1:8002"},
            ],
            auth=AuthMiddleware(valid_api_keys={"secret-key-123"}),
            rate_limit=100,
            enable_caching=True,
        )
    """

    def __init__(
        self,
        app: Any | None = None,
        routes: list[dict[str, Any] | RouteConfig] | None = None,
        enable_caching: bool = False,
        rate_limit: int | None = None,
        auth: Any | None = None,
        enable_cors: bool = False,
        cors: Any | None = None,
        middlewares: Sequence[BaseMiddleware] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize PyProxyGateway.

        Args:
            app: Optional inner ASGI application (e.g., FastAPI app).
            routes: Initial list of route configurations or dictionaries.
            enable_caching: Enable in-memory response caching plugin.
            rate_limit: Configurable rate limit per IP (requests per minute).
            auth: AuthMiddleware instance or dict configuration for API Key / Basic / JWT.
            enable_cors: Enable CORS preflight and headers plugin.
            cors: Custom CORSMiddleware instance or dict configuration.
            middlewares: Custom list of BaseMiddleware instances to run in pipeline.
            timeout: Upstream connection/read timeout in seconds.
        """
        self.app = app
        self.router = Router()
        self.timeout = timeout
        self.enable_caching = enable_caching
        self.rate_limit = rate_limit

        # Initialize Middleware Pipeline with plugins
        self.middleware_pipeline = MiddlewarePipeline()

        if middlewares:
            for mw in middlewares:
                self.middleware_pipeline.add_middleware(mw)

        if enable_cors or cors:
            from pyproxy.security.cors import CORSMiddleware
            if isinstance(cors, CORSMiddleware):
                self.middleware_pipeline.add_middleware(cors)
            elif isinstance(cors, dict):
                self.middleware_pipeline.add_middleware(CORSMiddleware(**cors))
            else:
                self.middleware_pipeline.add_middleware(CORSMiddleware())

        if auth is not None:
            if isinstance(auth, BaseMiddleware):
                self.middleware_pipeline.add_middleware(auth)
            elif isinstance(auth, dict):
                from pyproxy.auth import AuthMiddleware
                self.middleware_pipeline.add_middleware(AuthMiddleware(**auth))

        if rate_limit is not None:
            from pyproxy.security.middleware import RateLimiterMiddleware
            self.middleware_pipeline.add_middleware(
                RateLimiterMiddleware(RateLimiterConfig(enabled=True, rate=float(rate_limit), burst=15))
            )

        if enable_caching:
            from pyproxy.cache import CacheMiddleware
            self.middleware_pipeline.add_middleware(
                CacheMiddleware(CacheConfig(enabled=True))
            )

        if routes:
            for route in routes:
                if isinstance(route, dict):
                    self.add_route(
                        path=route.get("path", "/"),
                        target=route.get("target", "http://127.0.0.1:8000"),
                        strip_prefix=route.get("strip_prefix", False),
                        methods=route.get("methods"),
                    )
                elif isinstance(route, RouteConfig):
                    self.router.add_route(RouteRule.from_config(route))

    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """Register a custom middleware plugin to the gateway pipeline.

        Args:
            middleware: BaseMiddleware subclass instance.
        """
        self.middleware_pipeline.add_middleware(middleware)

    def add_route(
        self,
        path: str,
        target: str,
        strip_prefix: bool = False,
        methods: set[str] | list[str] | None = None,
    ) -> None:
        """Add a route to the proxy gateway.

        Args:
            path: Path prefix to match (e.g. "/api/v1").
            target: Upstream target URL (e.g. "http://127.0.0.1:8001").
            strip_prefix: Whether to strip matched path prefix when forwarding.
            methods: List or set of HTTP methods to allow.
        """
        if "://" not in target:
            target = f"http://{target}"

        parsed = urllib.parse.urlparse(target)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ssl_enabled = parsed.scheme == "https"
        target_path_prefix = parsed.path.rstrip("/")

        target_cfg = UpstreamTargetConfig(host=host, port=port, weight=1)
        upstream_cfg = UpstreamConfig(
            targets=(target_cfg,),
        )

        rule = RouteRule(
            path_pattern=path,
            match_type=RouteMatchType.PREFIX,
            methods=set(methods) if methods else None,
            strip_prefix=strip_prefix,
            upstream_config=upstream_cfg,
        )
        rule._target_url = target  # type: ignore[attr-defined]
        rule._target_host = host  # type: ignore[attr-defined]
        rule._target_port = port  # type: ignore[attr-defined]
        rule._target_ssl = ssl_enabled  # type: ignore[attr-defined]
        rule._target_path_prefix = target_path_prefix  # type: ignore[attr-defined]

        self.router.add_route(rule)
        logger.info("Added ASGI proxy route: %s -> %s", path, target)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI 3.0 interface entrypoint.

        Args:
            scope: ASGI scope dictionary.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] != "http":
            if self.app is not None:
                await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        method = scope.get("method", "GET").upper()

        matching_rule: RouteRule | None = None
        for rule in self.router.routes:
            if rule.methods and method not in rule.methods:
                continue
            if rule.match_type == RouteMatchType.PREFIX:
                if path == rule.path_pattern or path.startswith(rule.path_pattern.rstrip("/") + "/"):
                    matching_rule = rule
                    break
            elif rule.match_type == RouteMatchType.EXACT:
                if path == rule.path_pattern:
                    matching_rule = rule
                    break

        if matching_rule is None:
            if self.app is not None:
                await self.app(scope, receive, send)
            else:
                await self._send_404(send)
            return

        await self._proxy_http_request(matching_rule, scope, receive, send)

    async def _proxy_http_request(
        self,
        rule: RouteRule,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Forward ASGI HTTP request to upstream target and stream response back."""
        target_host = getattr(rule, "_target_host", None)
        target_port = getattr(rule, "_target_port", None)
        target_ssl = getattr(rule, "_target_ssl", False)
        target_path_prefix = getattr(rule, "_target_path_prefix", "")

        if (target_host is None or target_port is None) and rule.upstream_config and rule.upstream_config.targets:
            target_cfg = rule.upstream_config.targets[0]
            target_host = target_cfg.host
            target_port = target_cfg.port

        if not target_host:
            target_host = "127.0.0.1"
        if not target_port:
            target_port = 8000

        path = scope.get("path", "/")
        if rule.strip_prefix and path.startswith(rule.path_pattern):
            forward_path = path[len(rule.path_pattern) :]
            if not forward_path.startswith("/"):
                forward_path = "/" + forward_path
        else:
            forward_path = path

        if target_path_prefix:
            forward_path = target_path_prefix.rstrip("/") + forward_path

        query_string = scope.get("query_string", b"").decode("latin-1")

        # Read request body from receive()
        body_chunks: list[bytes] = []
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break

        request_body = b"".join(body_chunks)
        method = scope.get("method", "GET")

        # Build PyProxy HTTPRequest for Middleware Pipeline execution
        headers_model = Headers()
        headers_dict: dict[str, str] = {}
        for raw_name, raw_value in scope.get("headers", []):
            name_str = raw_name.decode("latin-1")
            val_str = raw_value.decode("latin-1")
            headers_model.set(name_str, val_str)
            if name_str.lower() != "host":
                headers_dict[name_str.lower()] = val_str

        client = scope.get("client")
        client_ip = client[0] if client else "127.0.0.1"
        if not headers_model.get("X-Forwarded-For"):
            headers_model.set("X-Forwarded-For", client_ip)

        http_request = HTTPRequest(
            method=method,
            path=path,
            target=path + (f"?{query_string}" if query_string else ""),
            query_string=query_string,
            headers=headers_model,
            body=request_body,
        )

        # Run Pre-Request Middleware Pipeline (Auth, Rate Limit, Cache, Custom Plugins)
        middleware_result = await self.middleware_pipeline.execute_request(http_request)
        if isinstance(middleware_result, HTTPResponse):
            await self._send_http_response(middleware_result, send)
            return

        headers_dict["host"] = f"{target_host}:{target_port}" if target_port not in (80, 443) else target_host
        headers_dict["x-forwarded-for"] = client_ip
        headers_dict["x-forwarded-proto"] = scope.get("scheme", "http")
        headers_dict["via"] = "1.1 PyProxy/0.2.0"

        if query_string:
            forward_path = f"{forward_path}?{query_string}"

        response_started = False
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=target_host,
                    port=target_port,
                    ssl=target_ssl,
                ),
                timeout=self.timeout,
            )

            req_lines = [f"{method} {forward_path} HTTP/1.1"]
            for h_name, h_val in headers_dict.items():
                req_lines.append(f"{h_name.title()}: {h_val}")
            if request_body and "content-length" not in headers_dict:
                req_lines.append(f"Content-Length: {len(request_body)}")
            req_lines.append("")
            req_lines.append("")

            req_bytes = "\r\n".join(req_lines).encode("latin-1") + request_body
            writer.write(req_bytes)
            await writer.drain()

            status_line = await reader.readline()
            if not status_line:
                await self._send_502(send)
                writer.close()
                await writer.wait_closed()
                return

            parts = status_line.decode("latin-1").split(" ", 2)
            status_code = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 502

            resp_headers: list[tuple[bytes, bytes]] = []
            resp_headers_model = Headers()
            content_length: int | None = None

            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                h_line = line.decode("latin-1").strip()
                if ":" in h_line:
                    k, v = h_line.split(":", 1)
                    k_str = k.strip().lower()
                    v_str = v.strip()
                    if k_str == "content-length":
                        content_length = int(v_str)
                    resp_headers.append((k_str.encode("latin-1"), v_str.encode("latin-1")))
                    resp_headers_model.set(k_str, v_str)

            response_started = True
            await send({
                "type": "http.response.start",
                "status": status_code,
                "headers": resp_headers,
            })

            resp_chunks: list[bytes] = []
            if content_length is not None:
                remaining = content_length
                while remaining > 0:
                    chunk = await reader.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    resp_chunks.append(chunk)
                    await send({
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    })
            else:
                while True:
                    chunk = await reader.read(65536)
                    if not chunk:
                        break
                    resp_chunks.append(chunk)
                    await send({
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    })

            await send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            })

            # Run Post-Response Middleware Pipeline
            full_resp_body = b"".join(resp_chunks)
            http_response = HTTPResponse(
                status_code=status_code,
                headers=resp_headers_model,
                body=full_resp_body,
            )
            await self.middleware_pipeline.execute_response(http_request, http_response)

            writer.close()
            await writer.wait_closed()

        except Exception as exc:
            logger.error("ASGI Proxy error: %s", exc)
            if not response_started:
                await self._send_502(send)

    async def _send_http_response(self, response: HTTPResponse, send: Send) -> None:
        """Send a PyProxy HTTPResponse object through ASGI send."""
        raw_headers: list[tuple[bytes, bytes]] = [
            (k.encode("latin-1"), v.encode("latin-1")) for k, v in response.headers.items()
        ]
        body_bytes = response.body if isinstance(response.body, bytes) else response.body.encode("utf-8")
        if "content-length" not in response.headers:
            raw_headers.append((b"content-length", str(len(body_bytes)).encode("latin-1")))

        await send({
            "type": "http.response.start",
            "status": response.status_code,
            "headers": raw_headers,
        })
        await send({
            "type": "http.response.body",
            "body": body_bytes,
            "more_body": False,
        })

    async def _send_404(self, send: Send) -> None:
        """Send standard 404 response to client."""
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"error": "Not Found", "message": "No matching PyProxy route"}',
            "more_body": False,
        })

    async def _send_502(self, send: Send) -> None:
        """Send standard 502 Bad Gateway response to client."""
        await send({
            "type": "http.response.start",
            "status": 502,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"error": "Bad Gateway", "message": "PyProxy upstream target unreachable"}',
            "more_body": False,
        })
