.PHONY: install lint format test coverage clean test-integration \
        bump-patch bump-minor bump-major bump-version help

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

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

# ---------------------------------------------------------------------------
# Version management (scripts/bump_version.py — stdlib only, no extra deps)
# ---------------------------------------------------------------------------

bump-patch:  ## Bump patch version (e.g. 0.4.0 → 0.4.1)
	python scripts/bump_version.py patch

bump-minor:  ## Bump minor version (e.g. 0.4.0 → 0.5.0)
	python scripts/bump_version.py minor

bump-major:  ## Bump major version (e.g. 0.4.0 → 1.0.0)
	python scripts/bump_version.py major

bump-version:  ## Bump to specific version: make bump-version VERSION=x.y.z
	@test -n "$(VERSION)" || (echo "Usage: make bump-version VERSION=x.y.z" && exit 1)
	python scripts/bump_version.py $(VERSION)
