.PHONY: install lint format test coverage clean test-integration \
        bump-cli-patch bump-cli-minor bump-cli-major bump-cli-version \
        bump-sdk-patch bump-sdk-minor bump-sdk-major bump-sdk-version \
        build-sdk build-cli build help

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install SDK (editable) + CLI (editable) with dev dependencies
	pip install -e sdk/
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
# Build
# ---------------------------------------------------------------------------

build-sdk:  ## Build kanboard-sdk wheel and sdist
	cd sdk && hatch build

build-cli:  ## Build kanboard-cli wheel and sdist
	hatch build

build: build-sdk build-cli  ## Build both packages

# ---------------------------------------------------------------------------
# Version management (scripts/bump_version.py — stdlib only, no extra deps)
# ---------------------------------------------------------------------------

bump-sdk-patch:  ## Bump SDK patch version (also updates CLI dep)
	python scripts/bump_version.py sdk patch

bump-sdk-minor:  ## Bump SDK minor version (also updates CLI dep)
	python scripts/bump_version.py sdk minor

bump-sdk-major:  ## Bump SDK major version (also updates CLI dep)
	python scripts/bump_version.py sdk major

bump-sdk-version:  ## Bump SDK to specific version: make bump-sdk-version VERSION=x.y.z
	@test -n "$(VERSION)" || (echo "Usage: make bump-sdk-version VERSION=x.y.z" && exit 1)
	python scripts/bump_version.py sdk $(VERSION)

bump-cli-patch:  ## Bump CLI patch version
	python scripts/bump_version.py cli patch

bump-cli-minor:  ## Bump CLI minor version
	python scripts/bump_version.py cli minor

bump-cli-major:  ## Bump CLI major version
	python scripts/bump_version.py cli major

bump-cli-version:  ## Bump CLI to specific version: make bump-cli-version VERSION=x.y.z
	@test -n "$(VERSION)" || (echo "Usage: make bump-cli-version VERSION=x.y.z" && exit 1)
	python scripts/bump_version.py cli $(VERSION)
