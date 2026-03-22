# Contributing to kanboard-cli

Thank you for your interest in contributing to **kanboard-cli**! This guide covers everything you need to get started — from development setup through submitting a pull request.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style and Conventions](#code-style-and-conventions)
  - [Formatting and Linting](#formatting-and-linting)
  - [Type Hints](#type-hints)
  - [Docstrings](#docstrings)
  - [Naming Conventions](#naming-conventions)
- [Testing Guide](#testing-guide)
  - [Unit Tests](#unit-tests)
  - [CLI Tests](#cli-tests)
  - [Integration Tests](#integration-tests)
  - [Running Tests](#running-tests)
  - [Coverage Requirements](#coverage-requirements)
- [Adding a New SDK Resource](#adding-a-new-sdk-resource)
- [Adding a New CLI Command](#adding-a-new-cli-command)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## Development Setup

### Prerequisites

- Python 3.11 or 3.12
- Git
- Docker (for integration tests only — optional for most contributions)

### 1. Fork and clone

```bash
git clone https://github.com/geekmuse/kanboard-cli.git
cd kanboard-cli
```

### 2. Install in editable mode with dev dependencies

```bash
pip install -e ".[dev]"
# or
make install
```

This installs all runtime dependencies (`httpx`, `click`, `rich`, `tomli-w`) plus development tools (`pytest`, `pytest-httpx`, `ruff`, `coverage`).

### 3. Verify your setup

```bash
make lint     # ruff check — should print nothing
make test     # pytest — all tests should pass
kanboard --version
```

### 4. (Optional) Set up a pre-commit hook

A pre-commit hook is already configured at `.git/hooks/pre-commit` and runs lint → format → test → build in sequence before every commit. Make sure it is executable:

```bash
chmod +x .git/hooks/pre-commit
```

---

## Project Structure

```
kanboard-cli/
├── src/
│   ├── kanboard/                   # SDK package (import kanboard)
│   │   ├── __init__.py             # Public API surface
│   │   ├── client.py               # JSON-RPC transport layer
│   │   ├── config.py               # Layered configuration resolution
│   │   ├── exceptions.py           # Typed exception hierarchy
│   │   ├── models.py               # Dataclass response models
│   │   └── resources/              # One module per API category (24 modules)
│   └── kanboard_cli/               # CLI package
│       ├── main.py                 # Click app root, global options, AppContext
│       ├── formatters.py           # Table / JSON / CSV / quiet renderers
│       ├── workflow_loader.py      # Plugin discovery and loading
│       ├── commands/               # One module per CLI command group
│       └── workflows/
│           └── base.py             # BaseWorkflow ABC
├── tests/
│   ├── unit/                       # Mocked httpx tests for the SDK
│   │   └── resources/              # One test file per resource module
│   ├── cli/                        # CliRunner output tests
│   └── integration/                # Docker-based lifecycle tests
├── docs/                           # Reference documentation
├── scripts/                        # Development utility scripts
├── .github/workflows/              # CI/CD pipelines
├── pyproject.toml                  # Project metadata, deps, ruff, pytest config
└── Makefile                        # Developer shortcuts
```

---

## Code Style and Conventions

### Formatting and Linting

All code is formatted and linted with **[ruff](https://docs.astral.sh/ruff/)** in strict mode.

```bash
make lint       # ruff check . (errors block commit)
make format     # ruff format . (auto-fix formatting)
```

Key rules enabled (see `[tool.ruff.lint]` in `pyproject.toml`):

| Rule set | Coverage                                    |
|----------|---------------------------------------------|
| `E`, `W` | pycodestyle errors and warnings             |
| `F`      | pyflakes (unused imports, undefined names)  |
| `I`      | isort (import ordering)                     |
| `B`      | flake8-bugbear (common bugs and bad patterns)|
| `UP`     | pyupgrade (modern Python syntax)            |
| `N`      | pep8-naming (class, function, variable names)|
| `D`      | pydocstyle (docstring conventions)          |
| `ANN`    | flake8-annotations (type hint enforcement)  |

**Run ruff auto-fix** before committing:

```bash
ruff check --fix .
ruff format .
```

---

### Type Hints

- All public SDK methods and CLI helpers **must** be fully type-hinted.
- Use Python 3.11+ union syntax: `str | None` (not `Optional[str]`).
- Use `Self` from `typing` for builder/fluent return types.
- Use `StrEnum` for string enumerations.
- Annotate return types on every public function, including those returning `None`.

```python
# ✅ Correct
def get_task(self, task_id: int) -> Task:
    ...

def delete_task(self, task_id: int) -> None:
    ...

# ❌ Avoid
def get_task(self, task_id):
    ...
```

---

### Docstrings

All public modules, classes, and methods **must** have docstrings. Use **Google style**:

```python
def create_task(self, title: str, project_id: int, color_id: str = "green") -> int:
    """Create a new task in the specified project.

    Args:
        title: The task title.
        project_id: ID of the project to create the task in.
        color_id: Task color identifier (default: ``"green"``).

    Returns:
        The ID of the newly created task.

    Raises:
        KanboardAPIError: If the API returns an error response.
        KanboardNotFoundError: If the project does not exist.
    """
```

- One-line docstrings are acceptable for simple getters/properties.
- Always document `Args`, `Returns`, and `Raises` for methods with non-trivial behavior.
- Module-level docstrings should describe the module's purpose in 1–3 sentences.

---

### Naming Conventions

| Context                          | Convention          | Example                          |
|----------------------------------|---------------------|----------------------------------|
| SDK resource methods             | `snake_case`        | `get_all_tasks`, `create_project`|
| Kanboard JSON-RPC methods        | `camelCase`         | `getAllTasks`, `createProject`   |
| Dataclass model fields           | `snake_case`        | `task_id`, `project_id`          |
| CLI command names                | `kebab-case`        | `task list`, `project create`    |
| Environment variables            | `SCREAMING_SNAKE`   | `KANBOARD_URL`, `KANBOARD_TOKEN` |
| Private helpers                  | `_leading_underscore` | `_require_user_auth`           |

SDK methods use `snake_case` that maps directly from the Kanboard `camelCase` API name:

```python
# Kanboard API: createTask  →  SDK: create_task
# Kanboard API: getAllTasks →  SDK: get_all_tasks
```

---

## Testing Guide

### Unit Tests

Unit tests live in `tests/unit/`. They test SDK resource methods in isolation using `pytest-httpx` to mock HTTP responses — no running Kanboard instance required.

**Pattern:**

```python
# tests/unit/resources/test_tasks.py
import pytest
from pytest_httpx import HTTPXMock

from kanboard import KanboardClient
from kanboard.exceptions import KanboardNotFoundError


def test_get_task_returns_model(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "id": 42,
                "title": "Fix login bug",
                "project_id": 1,
                # ... other fields
            },
        }
    )
    client = KanboardClient(url="http://localhost/jsonrpc.php", token="token")
    task = client.tasks.get_task(42)
    assert task.id == 42
    assert task.title == "Fix login bug"


def test_get_task_raises_not_found(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"jsonrpc": "2.0", "id": 1, "result": None})
    client = KanboardClient(url="http://localhost/jsonrpc.php", token="token")
    with pytest.raises(KanboardNotFoundError):
        client.tasks.get_task(999)
```

**One test file per resource module** in `tests/unit/resources/`.

---

### CLI Tests

CLI tests live in `tests/cli/`. They use Click's `CliRunner` with a mocked `KanboardClient` to test command output in all four formats.

**Pattern:**

```python
# tests/cli/test_task.py
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_client():
    return MagicMock()


def invoke(runner, mock_client, args):
    """Invoke the CLI with a mocked config and client."""
    with (
        patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            return_value=MagicMock(
                url="http://localhost/jsonrpc.php",
                token="token",
                profile="default",
                output_format="table",
                auth_mode="app",
                username=None,
                password=None,
            ),
        ),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args)


def test_task_list_table(runner, mock_client):
    from kanboard.models import Task
    mock_client.tasks.get_all_tasks.return_value = [
        Task(id=1, title="Fix bug", project_id=1)
    ]
    result = invoke(runner, mock_client, ["task", "list", "1"])
    assert result.exit_code == 0
    assert "Fix bug" in result.output


def test_task_list_json(runner, mock_client):
    import json
    from kanboard.models import Task
    mock_client.tasks.get_all_tasks.return_value = [
        Task(id=1, title="Fix bug", project_id=1)
    ]
    result = invoke(runner, mock_client, ["task", "list", "1", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 1
```

**Key patching points:**

- `kanboard_cli.main.KanboardConfig.resolve` — inject a mock config
- `kanboard_cli.main.KanboardClient` — inject a mock client
- `kanboard_cli.commands.<module>.CONFIG_FILE` — patch file paths for config commands

---

### Integration Tests

Integration tests live in `tests/integration/`. They run against a real Kanboard instance in Docker and are marked with `@pytest.mark.integration`.

**Prerequisites:**

- Docker installed and running
- `docker-compose.test.yml` in the project root

**Running integration tests:**

```bash
make test-integration
# or
pytest tests/integration/ -v
```

**Writing integration tests:**

```python
# tests/integration/test_my_feature.py
import pytest

pytestmark = pytest.mark.integration


def test_my_feature(kanboard_client, cleanup_project_ids):
    """Test description."""
    # Create a project (will be cleaned up automatically)
    project_id = kanboard_client.projects.create_project(name="Test Project")
    cleanup_project_ids.append(project_id)

    # Test your feature
    project = kanboard_client.projects.get_project_by_id(project_id)
    assert project.name == "Test Project"
```

**Available fixtures** (defined in `tests/integration/conftest.py`):

| Fixture                | Scope    | Purpose                                      |
|------------------------|----------|----------------------------------------------|
| `kanboard_client`      | session  | `KanboardClient` connected to Docker instance|
| `kanboard_url`         | session  | URL of the Docker Kanboard instance          |
| `cleanup_project_ids`  | function | List of project IDs to remove after test     |
| `cleanup_task_ids`     | function | List of task IDs to remove after test        |
| `cleanup_user_ids`     | function | List of user IDs to remove after test        |
| `cleanup_group_ids`    | function | List of group IDs to remove after test       |
| `cleanup_link_ids`     | function | List of link type IDs to remove after test   |
| `integration_project`  | function | Pre-created project with auto-cleanup        |
| `integration_task`     | function | Pre-created task (needs `integration_project`)|

Integration tests are skipped automatically when Docker is unavailable.

---

### Running Tests

```bash
# All unit + CLI tests (fast, no Docker required)
make test
# or
pytest

# With coverage report
make coverage

# Integration tests only (requires Docker)
make test-integration

# Specific test file
pytest tests/unit/resources/test_tasks.py -v

# Specific test by name
pytest -k "test_create_task" -v

# Run with output on failure
pytest -s
```

---

### Coverage Requirements

The target coverage for `src/kanboard/resources/` is **≥ 90%**. CI enforces this via `[tool.coverage.report] fail_under = 90` in `pyproject.toml`.

Check coverage locally:

```bash
make coverage       # runs unit + CLI tests, shows HTML + terminal report
coverage report     # terminal-only report after running coverage run
```

---

## Adding a New SDK Resource

1. **Create the resource module** at `src/kanboard/resources/<category>.py`

   Follow the pattern of existing modules (e.g. `tasks.py`, `projects.py`):
   - Inherit from `BaseResource` (or the relevant mixin)
   - One method per Kanboard API method, using `snake_case` names
   - All parameters fully type-hinted
   - All methods have docstrings
   - Return typed dataclass models from `kanboard.models`

2. **Add model classes** to `src/kanboard/models.py` if needed

3. **Register the resource** on `KanboardClient` in `src/kanboard/client.py`

4. **Export** the new resource class from `src/kanboard/__init__.py`

5. **Write unit tests** in `tests/unit/resources/test_<category>.py`

6. **Write integration tests** in `tests/integration/test_<category>.py` (optional but encouraged)

---

## Adding a New CLI Command

1. **Create the command module** at `src/kanboard_cli/commands/<resource>.py`

   Follow the pattern of existing modules (e.g. `task.py`, `project.py`):
   - Define a Click group with `@click.group()`
   - One `@<group>.command()` per operation
   - Use `@click.pass_context` and `ctx.obj` to access the client
   - Use `format_output()` / `format_success()` from `kanboard_cli.formatters`
   - Destructive commands (delete, remove) must have `--yes` confirmation

2. **Register the command group** in `src/kanboard_cli/main.py`:
   ```python
   from kanboard_cli.commands.my_resource import my_resource
   cli.add_command(my_resource)
   ```

3. **Write CLI tests** in `tests/cli/test_<resource>.py`

4. **Document the commands** in `docs/cli-reference.md`

---

## Commit Message Conventions

This project uses **[Conventional Commits](https://www.conventionalcommits.org/)**:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

### Types

| Type       | Use for                                                        |
|------------|----------------------------------------------------------------|
| `feat`     | New feature or capability                                      |
| `fix`      | Bug fix                                                        |
| `docs`     | Documentation changes only                                     |
| `test`     | Adding or updating tests (no production code changes)          |
| `refactor` | Code change that neither fixes a bug nor adds a feature        |
| `chore`    | Build process, dependency updates, CI changes                  |
| `perf`     | Performance improvements                                       |
| `style`    | Formatting/style changes (whitespace, missing semicolons, etc.)|

### Scope (optional)

Use the resource or area being changed:

```
feat(tasks): add duplicate_task_to_project method
fix(config): handle missing config file gracefully
docs(sdk): add batch API example
test(integration): add user lifecycle tests
chore(ci): add Python 3.12 to test matrix
```

### Examples

```
feat: [US-003] - User API authentication support

feat(tasks): add get_overdue_tasks resource method

fix(config): token masking crashes for tokens < 4 chars

docs: add configuration reference and workflows guide

test(cli): add snapshot tests for all output formats

chore: bump ruff to 0.6.0
```

---

## Pull Request Process

1. **Branch** from `main` using a descriptive name:
   ```bash
   git checkout -b feat/add-gantt-export
   git checkout -b fix/token-masking-short-tokens
   ```

2. **Keep changes focused** — one logical change per PR. Separate refactors from features.

3. **Ensure all checks pass** before pushing:
   ```bash
   make lint && make test
   ```

4. **Write a clear PR description** covering:
   - What the change does
   - Why it is needed
   - How to test it manually
   - Any breaking changes

5. **Link related issues** in the PR body: `Closes #42`

6. **Respond to review feedback** promptly. Address all comments before requesting re-review.

7. PRs are merged via **squash merge** to keep the commit history clean.

---

## Reporting Issues

Please use [GitHub Issues](https://github.com/geekmuse/kanboard-cli/issues) to report bugs or request features.

**Bug reports should include:**

- `kanboard --version` output
- Python version (`python --version`)
- Kanboard server version (from `kanboard config test` or server admin panel)
- The full command you ran (with `--verbose` output if relevant)
- Expected vs actual behavior
- Traceback (if applicable)

**Feature requests should include:**

- Use case / motivation
- Proposed API or CLI interface (if you have one in mind)
- Any relevant Kanboard API documentation links
