.PHONY: install lint format test coverage clean

install:  ## Install package with dev dependencies
	pip install -e '.[dev]'

lint:  ## Run ruff linter
	ruff check .

format:  ## Run ruff formatter
	ruff format .

test:  ## Run unit and CLI tests
	pytest

coverage:  ## Run tests with coverage report
	coverage run -m pytest tests/unit tests/cli
	coverage report
	coverage html

clean:  ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf htmlcov/ .coverage

test-integration:  ## Run integration tests (requires Docker)
	pytest tests/integration/ -v
