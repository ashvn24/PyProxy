.DEFAULT_GOAL := help
.PHONY: help install-dev lint format typecheck test coverage clean build publish

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev: ## Install package in editable mode with all dev dependencies
	pip install -e ".[dev,test,docs]"
	pre-commit install

lint: ## Run linter (ruff check + format check)
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Auto-format code
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck: ## Run static type checker (mypy)
	mypy src/

test: ## Run tests
	pytest tests/ -v

coverage: ## Run tests with coverage report
	pytest tests/ --cov=pyproxy --cov-report=term-missing --cov-report=html --cov-fail-under=95

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf .tox/ .mypy_cache/ .pytest_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

build: clean ## Build distribution packages
	python -m build

publish: build ## Publish to PyPI (requires credentials)
	python -m twine upload dist/*

check-all: lint typecheck test ## Run all checks (lint + typecheck + test)
