# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffolding with `src/` layout and modular architecture.
- Configuration system supporting YAML, JSON, and TOML with environment variable overrides.
- Hot-reload configuration watcher using `watchfiles`.
- Structured JSON logging with `orjson` and `contextvars`-based request/correlation IDs.
- Lightweight dependency injection container with transient, singleton, and scoped lifetimes.
- Custom exception hierarchy with structured error context.
- CLI entry point with `version` and `validate` subcommands.
- Full dev tooling: Ruff, Mypy, Pytest, pre-commit, tox, GitHub Actions CI.
