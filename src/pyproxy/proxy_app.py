"""Main PyProxy Application Orchestrator.

Integrates TCPServer, ConfigLoader, Router, LoadBalancer, ProxyEngine,
WebSocketProxy, HealthChecker, MiddlewarePipeline, and Logging into a
unified, production-grade reverse proxy application.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from pyproxy.config import ConfigLoader, ConfigWatcher, ProxyConfig
from pyproxy.core import Container
from pyproxy.exceptions import PyProxyError
from pyproxy.health import HealthChecker
from pyproxy.load_balancer import LoadBalancer
from pyproxy.logging import setup_logging
from pyproxy.middleware import MiddlewarePipeline
from pyproxy.protocol import HTTPParser, HTTPRequest, HTTPResponse, HTTPResponseBuilder
from pyproxy.proxy.engine import ProxyEngine
from pyproxy.routing import Router
from pyproxy.server import Connection, TCPServer
from pyproxy.ssl import TLSContextFactory
from pyproxy.upstream import UpstreamConnectionPool, UpstreamTarget
from pyproxy.websocket import WebSocketProxy

logger = logging.getLogger("pyproxy.app")


class Proxy:
    """Production-grade asyncio reverse proxy server orchestrator.

    Example::

        from pyproxy import Proxy

        proxy = Proxy(config_path="config.yaml")
        proxy.run()
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        config: ProxyConfig | None = None,
    ) -> None:
        """Initialize Proxy application.

        Args:
            config_path: Path to configuration file (YAML/JSON/TOML).
            config: Explicit ProxyConfig model (overrides config_path).

        Raises:
            ConfigError: If configuration cannot be loaded or validated.
        """
        if config is not None:
            self.config: ProxyConfig = config
            self.config_path: Path | None = Path(config_path) if config_path else None
        elif config_path is not None:
            self.config_path = Path(config_path)
            loader = ConfigLoader(self.config_path)
            self.config = loader.load()
        else:
            self.config_path = None
            self.config = ProxyConfig()

        # 1. Setup logging system
        setup_logging(self.config.logging)

        # 2. Dependency Injection Container
        self.container: Container = Container()
        self.container.register_instance(ProxyConfig, self.config)

        # 3. Component initialization
        self.router: Router = Router()
        self.router.load_from_config(self.config.routes)

        self.connection_pool: UpstreamConnectionPool = UpstreamConnectionPool()
        self.load_balancer: LoadBalancer = LoadBalancer()
        self.proxy_engine: ProxyEngine = ProxyEngine(connection_pool=self.connection_pool)
        self.websocket_proxy: WebSocketProxy = WebSocketProxy()
        self.health_checker: HealthChecker = HealthChecker()
        self.middleware_pipeline: MiddlewarePipeline = MiddlewarePipeline()

        self.tcp_server: TCPServer | None = None
        self.config_watcher: ConfigWatcher | None = None

        logger.info("PyProxy engine initialized successfully")

    async def _handle_connection(self, client_conn: Connection) -> None:
        """Process incoming client connection lifecycle.

        Args:
            client_conn: Active client Connection object.
        """
        while not client_conn.is_closed and not self.tcp_server.shutdown_handler.is_shutting_down:  # type: ignore[union-attr]
            try:
                # 1. Parse HTTP request line & headers
                request: HTTPRequest = await HTTPParser.parse_request(
                    connection=client_conn,
                    read_timeout=self.config.server.read_timeout,
                )

                # 2. Run Pre-Request Middleware Pipeline
                middleware_result = await self.middleware_pipeline.execute_request(request)
                if isinstance(middleware_result, HTTPResponse):
                    # Short-circuit response from middleware
                    await HTTPResponseBuilder.send_response(
                        connection=client_conn,
                        response=middleware_result,
                        write_timeout=self.config.server.write_timeout,
                    )
                    if not request.is_keep_alive:
                        break
                    continue

                # 3. Match Route
                route_rule = self.router.match(request)

                # 4. Extract or build UpstreamTarget pool for route
                target_configs = route_rule.upstream_config.targets
                if not target_configs:
                    response_error = HTTPResponse.create_error(502, "No upstream targets configured for route")
                    await HTTPResponseBuilder.send_response(client_conn, response_error)
                    break

                targets = [UpstreamTarget.from_config(cfg) for cfg in target_configs]

                # 5. Load balance selection
                selected_target = self.load_balancer.select_target(
                    targets=targets,
                    request=request,
                    client_ip=client_conn.client_host,
                )

                # 6. WebSocket upgrade handling
                if request.is_websocket_upgrade:
                    upstream_conn = await self.connection_pool.acquire(selected_target)
                    await self.websocket_proxy.proxy_websocket(client_conn, request, upstream_conn)
                    break

                # 7. Proxy request to upstream & stream response back
                await self.proxy_engine.forward(
                    client_conn=client_conn,
                    request=request,
                    route_rule=route_rule,
                    target=selected_target,
                )

                # Record success for passive health check
                self.health_checker.record_passive_success(selected_target)

                if not request.is_keep_alive:
                    break

            except PyProxyError as exception:
                logger.warning("Proxy request error: %s", exception.detail)
                error_response = HTTPResponse.create_error(
                    status_code=502 if "UPSTREAM" in exception.error_code else 400,
                    detail=exception.detail,
                )
                try:
                    await HTTPResponseBuilder.send_response(client_conn, error_response)
                except Exception:
                    pass
                break
            except Exception as exception:
                logger.error("Unexpected proxy error: %s", exception, exc_info=True)
                break

    async def start(self) -> None:
        """Start the reverse proxy server async engine."""
        # Setup TLS context if enabled
        ssl_context = None
        if self.config.tls.enabled:
            ssl_context = TLSContextFactory.create_server_context(self.config.tls)

        self.tcp_server = TCPServer(
            config=self.config.server,
            connection_handler=self._handle_connection,
        )

        # Start hot-reload watcher if config file exists
        if self.config_path and self.config_path.exists():
            self.config_watcher = ConfigWatcher(
                file_path=self.config_path,
                on_reload=self._on_config_reload,
            )
            self.config_watcher.start_background()

        logger.info("PyProxy starting on %s:%d", self.config.server.bind_host, self.config.server.bind_port)
        await self.tcp_server.start()

    def _on_config_reload(self, new_config: ProxyConfig) -> None:
        """Callback triggered on config file hot reload."""
        logger.info("Applying reloaded configuration")
        self.config = new_config
        self.router.load_from_config(new_config.routes)

    async def stop(self) -> None:
        """Stop the reverse proxy server."""
        if self.config_watcher:
            await self.config_watcher.stop()
        if self.tcp_server:
            await self.tcp_server.stop()
        await self.connection_pool.close_all()
        logger.info("PyProxy shut down successfully")

    def run(self) -> None:
        """Run the PyProxy server synchronously (blocking)."""
        async def main_runner():
            await self.start()
            if self.tcp_server:
                await self.tcp_server.serve_forever()

        try:
            asyncio.run(main_runner())
        except (KeyboardInterrupt, SystemExit):
            logger.info("PyProxy execution terminated by user")
