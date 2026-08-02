# PyProxy

[![CI](https://github.com/ashvn24/PyProxy/actions/workflows/ci.yml/badge.svg)](https://github.com/ashvn24/PyProxy/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ashvn24/PyProxy/branch/main/graph/badge.svg)](https://codecov.io/gh/ashvn24/PyProxy)
[![PyPI version](https://badge.fury.io/py/python-pyproxy.svg)](https://pypi.org/project/python-pyproxy/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A modern, production-grade reverse proxy built entirely in Python on asyncio.**

PyProxy is a high-performance reverse proxy and load balancer designed for
modern infrastructure. It implements its own HTTP request lifecycle from the
ground up — no frameworks, no shortcuts.

## Features

- **Async-native** — Built on Python's `asyncio` with optional `uvloop` acceleration
- **Full HTTP/1.1** — Streaming, chunked encoding, keep-alive, persistent connections
- **Load Balancing** — Round Robin, Weighted RR, Least Connections, IP Hash, and more
- **Health Checking** — Active and passive checks with automatic recovery and circuit breaker
- **TLS Termination** — Certificate loading, SNI, mutual TLS, OCSP stapling
- **WebSocket Proxy** — Full upgrade, ping/pong, streaming, reconnect
- **Middleware Pipeline** — Extensible before/after request hooks
- **Caching** — In-memory and Redis with Cache-Control, ETag, conditional requests
- **Compression** — gzip and Brotli with content negotiation
- **Authentication** — JWT, Basic Auth, API Keys, OAuth hooks
- **Security** — Rate limiting, IP allow/deny lists, CORS, CSRF, header sanitization
- **Observability** — Prometheus metrics, structured JSON logging, request tracing
- **Hot Reload** — Configuration changes applied without restart
- **CLI** — `pyproxy start`, `validate`, `reload`, `benchmark`, and more

## Quick Start

### Installation

```bash
pip install python-pyproxy
```

### FastAPI / ASGI Gateway Integration (v0.2.0)

Mount PyProxy as a centralized microservice gateway directly inside FastAPI or Starlette with full plugin support (Auth, JWT, Rate Limiting, Caching):

```python
from fastapi import FastAPI
from pyproxy.asgi import PyProxyGateway
from pyproxy.auth import AuthMiddleware

app = FastAPI(title="Central Microservice Gateway")

# Mount PyProxy as ASGI Gateway middleware
app.add_middleware(
    PyProxyGateway,
    routes=[
        {"path": "/users", "target": "http://127.0.0.1:8001"},
        {"path": "/orders", "target": "http://127.0.0.1:8002", "strip_prefix": True},
    ],
    auth=AuthMiddleware(valid_api_keys={"secret-key-123"}),
    rate_limit=100, # Rate limiting (100 req/min per IP)
    enable_caching=True, # Response TTL caching
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "gateway": "PyProxy v0.2.0"}
```

### YAML / CLI Proxy Server Quick Start

Create a `config.yaml`:

```yaml
server:
  bind_host: "0.0.0.0"
  bind_port: 8080

routes:
  - path: "/api"
    upstream:
      targets:
        - host: "127.0.0.1"
          port: 3000
```

Start via CLI or Python:

```bash
pyproxy start config.yaml
```

```python
from pyproxy import Proxy

proxy = Proxy(config_path="config.yaml")
proxy.run()
```

#### Advanced FastAPI Gateway & Plugin Configuration

```python
from fastapi import FastAPI
from pyproxy.asgi import PyProxyGateway
from pyproxy.auth import AuthMiddleware
from pyproxy.middleware import BaseMiddleware
from pyproxy.protocol import HTTPRequest, HTTPResponse

# Custom JWT Authentication Plugin
class JWTAuthPlugin(BaseMiddleware):
    async def process_request(self, request: HTTPRequest) -> HTTPRequest | HTTPResponse | None:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != "secret-jwt-token":
            return HTTPResponse.create_error(401, "Invalid JWT Token") # Short-circuit
        return None

app = FastAPI(title="Central Microservice Gateway")

# Mount PyProxy as ASGI middleware with full Plugin pipeline
app.add_middleware(
    PyProxyGateway,
    routes=[
        {"path": "/users", "target": "http://127.0.0.1:8001"},
        {"path": "/orders", "target": "http://127.0.0.1:8002"},
    ],
    middlewares=[JWTAuthPlugin()], # Custom JWT Auth plugin
    auth=AuthMiddleware(valid_api_keys={"my-key"}), # API Key Auth plugin
    rate_limit=60, # Rate limiting plugin (60 req/min per IP)
    enable_caching=True, # In-memory TTL caching plugin
)
```

#### FastAPI Gateway Plugin Usage Guide

| Plugin | When to Use | How to Use |
| :--- | :--- | :--- |
| **JWT / OAuth** | Protect backend microservices behind FastAPI with token verification. | Subclass `BaseMiddleware`, override `process_request()`, pass to `middlewares=[...]`. |
| **API Keys & Basic Auth** | Service-to-service auth or developer API endpoints. | Pass `auth=AuthMiddleware(valid_api_keys={...})` into `PyProxyGateway`. |
| **Rate Limiting** | Prevent API abuse and DDoS attacks per client IP. | Set `rate_limit=60` (requests per minute per IP) in `PyProxyGateway`. |
| **In-Memory Caching** | Deliver sub-millisecond responses for read-heavy GET routes. | Set `enable_caching=True` in `PyProxyGateway`. |
| **Audit & Header Hooks** | Inject correlation IDs (`X-Correlation-ID`) or response signatures. | Subclass `BaseMiddleware`, override `process_request()` / `process_response()`. |

## Configuration

PyProxy supports YAML, JSON, and TOML configuration files. Environment variables
can override any setting using the `PYPROXY_` prefix:

```bash
# Override bind port
export PYPROXY_SERVER__BIND_PORT=9090

# Override log level
export PYPROXY_LOGGING__LEVEL=debug
```

See [examples/](examples/) for annotated configuration examples.

## Development

```bash
# Clone and install
git clone https://github.com/ashvn24/PyProxy.git
cd PyProxy
pip install -e ".[dev,test]"

# Run checks
make lint        # Ruff linting
make typecheck   # Mypy strict mode
make test        # Pytest
make coverage    # Coverage report
make check-all   # All of the above
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full developer guide.

## Architecture

PyProxy follows Clean Architecture with clear module boundaries:

| Module | Responsibility |
|--------|---------------|
| `server` | Low-level asyncio TCP server, connection lifecycle |
| `routing` | Route matching (prefix, regex, host, wildcard) |
| `proxy` | Reverse proxy engine, header rewriting, streaming |
| `upstream` | Upstream connection pooling and management |
| `load_balancer` | Load balancing strategies |
| `health` | Health checking and circuit breaker |
| `middleware` | Extensible middleware pipeline |
| `config` | Configuration loading, validation, hot reload |
| `ssl` | TLS termination, certificate management |
| `websocket` | WebSocket proxy with upgrade handling |
| `cache` | Response caching (memory, Redis) |
| `compression` | gzip/Brotli response compression |
| `auth` | Authentication (JWT, Basic, API Key) |
| `security` | Rate limiting, CORS, IP filtering |
| `metrics` | Prometheus metrics collection |
| `logging` | Structured JSON logging with context |

## License

MIT — see [LICENSE](LICENSE) for details.
