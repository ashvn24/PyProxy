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

### Configuration

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

logging:
  level: "info"
  format: "json"
```

### Start the Proxy

```bash
pyproxy start config.yaml
```

### Programmatic Usage

```python
from pyproxy import Proxy

proxy = Proxy(config_path="config.yaml")
proxy.run()
```

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
