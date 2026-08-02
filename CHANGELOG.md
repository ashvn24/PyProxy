# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-03

### Added
- **FastAPI / ASGI Gateway Integration**: Mount PyProxy as an ASGI 3.0 middleware (`PyProxyGateway`) or router (`PyProxyRouter`) inside FastAPI/Starlette applications.
- **Middleware Plugin Pipeline**: Full support for custom `BaseMiddleware` plugins, `AuthMiddleware` (API keys, Basic Auth, custom JWT tokens), `RateLimiterMiddleware` (Token Bucket sliding window), and `CacheMiddleware` (In-memory TTL cache with 304 conditional responses).
- **Target URL Normalization**: Support for full domain target URLs (HTTPS on port 443, HTTP on port 80, SNI TLS handshakes, and host header rewriting).
- **Interactive Documentation**: Comprehensive FastAPI Gateway Getting Started guide, plugin examples, and usage tables in `docs.html` and `README.md`.

## [0.1.3] - 2026-08-01

### Added
- Project scaffolding with `src/` layout and modular architecture.
- Configuration system supporting YAML, JSON, and TOML with environment variable overrides.
- Hot-reload configuration watcher using `watchfiles`.
- Structured JSON logging with `orjson` and `contextvars`-based request/correlation IDs.
- Lightweight dependency injection container with transient, singleton, and scoped lifetimes.
- Custom exception hierarchy with structured error context.
- CLI entry point with `version` and `validate` subcommands.
- Full dev tooling: Ruff, Mypy, Pytest, pre-commit, tox, GitHub Actions CI.
