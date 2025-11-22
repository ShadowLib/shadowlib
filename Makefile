.PHONY: help install test lint format check clean build

help:
	@echo "ShadowLib Development Commands:"
	@echo ""
	@echo "  make install       Install package and dev dependencies"
	@echo "  make test          Run tests with pytest"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code with ruff"
	@echo "  make naming        Check naming conventions"
	@echo "  make verify        Verify package setup"
	@echo "  make check         Run all checks (lint + naming + tests)"
	@echo "  make clean         Remove build artifacts and cache"
	@echo "  make build         Build distribution packages"
	@echo ""

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

test-cov:
	pytest --cov=shadowlib --cov-report=html --cov-report=term

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

naming:
	python3 scripts/check_naming.py

verify:
	python3 scripts/verify_setup.py

check: lint naming test
	@echo "✅ All checks passed!"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

.DEFAULT_GOAL := help
