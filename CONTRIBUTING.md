# Contributing to PyProxy

Thank you for your interest in contributing to PyProxy! This document provides
guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.13+
- Git

### Getting Started

1. **Fork and clone** the repository:

   ```bash
   git clone https://github.com/YOUR_USERNAME/pyproxy.git
   cd pyproxy
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. **Install in development mode**:

   ```bash
   pip install -e ".[dev,test,docs]"
   ```

4. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

## Development Workflow

### Code Style

- We use **Ruff** for linting and formatting (replaces Black + Flake8 + isort).
- We use **Mypy** in strict mode for static type checking.
- Line length: 99 characters.
- All public functions must have type hints and Google-style docstrings.

```bash
# Format code
make format

# Check linting
make lint

# Run type checker
make typecheck
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/unit/test_config_models.py -v

# Run tests matching a pattern
pytest -k "test_config" -v
```

### All Checks

```bash
# Run lint + typecheck + tests in one command
make check-all

# Or use tox for isolated environments
tox
```

## Pull Request Process

1. **Create a feature branch** from `main`:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines.

3. **Add tests** for any new functionality. We require >95% code coverage.

4. **Run all checks** before committing:

   ```bash
   make check-all
   ```

5. **Write meaningful commit messages** following
   [Conventional Commits](https://www.conventionalcommits.org/):

   ```
   feat: add weighted round-robin load balancer
   fix: handle connection reset in upstream pool
   docs: update configuration reference
   test: add integration tests for TLS termination
   refactor: extract header parsing into separate module
   ```

6. **Open a Pull Request** against `main` with:
   - A clear description of the changes.
   - Reference to any related issues.
   - Screenshots or logs if applicable.

## Architecture Guidelines

- Follow **SOLID principles** and **Clean Architecture**.
- Prefer **composition over inheritance**.
- Use **dependency injection** via the `Container` class.
- Every module must have a clear, single responsibility.
- Avoid unnecessary abstractions — keep it simple.
- All I/O must be asynchronous (`async/await`).

## Reporting Issues

- Use [GitHub Issues](https://github.com/pyproxy/pyproxy/issues) to report bugs.
- Include Python version, OS, and steps to reproduce.
- For security issues, email security@pyproxy.dev instead of opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.
