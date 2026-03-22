# kanboard-cli

> A Python SDK and CLI for the [Kanboard](https://kanboard.org/) JSON-RPC API — complete coverage of all 158 API methods, a plugin system for custom workflows, and a first-class developer experience.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
<!-- [![PyPI version](https://img.shields.io/pypi/v/kanboard-cli.svg)](https://pypi.org/project/kanboard-cli/) -->

---

## Overview

**kanboard-cli** provides two complementary interfaces for [Kanboard](https://kanboard.org/):

- **`kanboard` (SDK)** — An importable Python library (`import kanboard`) with typed models, structured exceptions, and resource-based access to the full Kanboard API.
- **`kanboard` (CLI)** — A Click-based command-line tool with rich table output, JSON/CSV/quiet modes, named configuration profiles, and a plugin system for user-defined workflows.

Both are distributed as a single `kanboard-cli` package installable from PyPI.

## Key Features

- **Complete API coverage** — All 158 Kanboard JSON-RPC methods across 24 resource categories
- **Typed Python SDK** — Dataclass models, structured exceptions, and IDE-friendly type hints
- **Powerful CLI** — Subcommand groups for every resource, four output formats, shell completions
- **Multiple output formats** — `table` (rich/colored), `json`, `csv`, `quiet` (IDs only)
- **Named profiles** — Manage multiple Kanboard instances (production, dev, staging) via TOML config
- **Layered configuration** — Config file → environment variables → CLI flags
- **Workflow plugins** — Drop `.py` files into `~/.config/kanboard/workflows/` to add custom CLI commands
- **Context manager support** — `KanboardClient` works with `with` statements for clean resource management

## Prerequisites

- **Python 3.11+** (required for `tomllib`, modern typing features)
- **A running Kanboard instance** with API access enabled
- **API token** from Kanboard Settings → API

## Installation

### From PyPI

```bash
pip install kanboard-cli
```

### From source (development)

```bash
git clone https://github.com/geekmuse/kanboard-cli-denuo.git
cd kanboard-cli-denuo
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure your connection

Create `~/.config/kanboard/config.toml`:

```toml
[profiles.default]
url = "https://kanboard.example.com/jsonrpc.php"
token = "your-api-token-here"

[settings]
default_profile = "default"
output_format = "table"
```

Or use environment variables:

```bash
export KANBOARD_URL="https://kanboard.example.com/jsonrpc.php"
export KANBOARD_API_TOKEN="your-api-token-here"
```

### 2. Use the CLI

```bash
# List all projects
kanboard project list

# Create a task
kanboard task create 1 "Fix login bug" --color red --priority 3

# Get task details as JSON
kanboard task get 42 --output json

# Search tasks
kanboard task search 1 "status:open assignee:me"

# View the board
kanboard board show 1

# List overdue tasks across all projects
kanboard task overdue
```

### 3. Use the SDK

```python
from kanboard import KanboardClient

with KanboardClient(url="https://kanboard.example.com/jsonrpc.php",
                     token="your-api-token") as kb:
    # Create a project
    project_id = kb.projects.create_project(name="My Project")

    # Create a task
    task_id = kb.tasks.create_task(
        title="Implement feature X",
        project_id=project_id,
        color_id="green",
        priority=2,
    )

    # Get all active tasks
    tasks = kb.tasks.get_all_tasks(project_id, status_id=1)
    for task in tasks:
        print(f"#{task.id} [{task.color_id}] {task.title}")

    # Work with columns, swimlanes, comments, tags, and more
    columns = kb.columns.get_columns(project_id)
    kb.comments.create_comment(task_id=task_id, user_id=1, content="Started work")
    kb.tags.set_task_tags(project_id, task_id, ["backend", "urgent"])
```

## Configuration

### Config File

Location: `~/.config/kanboard/config.toml`

```toml
[profiles.default]
url = "https://kanboard.example.com/jsonrpc.php"
token = "your-api-token-here"

[profiles.dev]
url = "http://localhost:8080/jsonrpc.php"
token = "dev-token"

[settings]
default_profile = "default"
output_format = "table"            # table | json | csv | quiet
```

### Environment Variables

| Variable               | Overrides                    |
|------------------------|------------------------------|
| `KANBOARD_URL`         | `profiles.<active>.url`      |
| `KANBOARD_API_TOKEN`   | `profiles.<active>.token`    |
| `KANBOARD_PROFILE`     | `settings.default_profile`   |
| `KANBOARD_OUTPUT`      | `settings.output_format`     |

### CLI Flags

| Flag              | Purpose                                         |
|-------------------|-------------------------------------------------|
| `--url URL`       | Kanboard JSON-RPC endpoint                      |
| `--token TOKEN`   | API token                                       |
| `--profile NAME`  | Config profile to use                           |
| `--output FORMAT` | Output format: `table`, `json`, `csv`, `quiet`  |
| `--verbose`       | Enable debug logging                            |

**Resolution order:** config file → environment variables → CLI flags (highest priority)

## CLI Reference

Every Kanboard resource has a corresponding command group:

| Command Group        | Description                              |
|----------------------|------------------------------------------|
| `kanboard task`      | Tasks: list, get, create, update, close, open, remove, search, move |
| `kanboard project`   | Projects: list, get, create, update, remove, enable, disable, activity |
| `kanboard board`     | Board view for a project                 |
| `kanboard column`    | Column management                        |
| `kanboard swimlane`  | Swimlane management                      |
| `kanboard comment`   | Task comments                            |
| `kanboard category`  | Project categories                       |
| `kanboard tag`       | Tags (global and per-project)            |
| `kanboard subtask`   | Subtask management                       |
| `kanboard timer`     | Subtask time tracking                    |
| `kanboard user`      | User administration                      |
| `kanboard me`        | Current user dashboard and activity      |
| `kanboard link`      | Link type definitions                    |
| `kanboard task-link` | Internal task-to-task links              |
| `kanboard external-link` | External task links                  |
| `kanboard group`     | Group management and membership          |
| `kanboard action`    | Automatic action configuration           |
| `kanboard project-file` | Project file attachments              |
| `kanboard task-file` | Task file attachments                    |
| `kanboard project-meta` | Project key-value metadata            |
| `kanboard task-meta` | Task key-value metadata                  |
| `kanboard project-access` | Project permissions (users/groups)  |
| `kanboard app`       | Application info (version, colors, roles)|
| `kanboard config`    | Configuration management                 |
| `kanboard workflow`  | List discovered workflow plugins         |
| `kanboard completion`| Shell completion (bash/zsh/fish)         |

Use `kanboard <command> --help` for detailed usage of any command.

## Output Formats

All list/get commands support four output formats via `--output` / `-o`:

```bash
# Rich colored table (default)
kanboard task list 1

# JSON (for scripting and piping)
kanboard task list 1 -o json

# CSV (for spreadsheets and data tools)
kanboard task list 1 -o csv

# Quiet / ID-only (for shell pipelines)
kanboard task list 1 -o quiet | xargs -I{} kanboard task close {}
```

## Workflows (Plugin System)

kanboard-cli supports user-defined workflow plugins for custom automation.

### Creating a workflow

1. Create a Python file in `~/.config/kanboard/workflows/`:

```python
# ~/.config/kanboard/workflows/my_workflow.py
import click
from kanboard_cli.workflows.base import BaseWorkflow

class MyWorkflow(BaseWorkflow):
    @property
    def name(self) -> str:
        return "my-workflow"

    @property
    def description(self) -> str:
        return "My custom automation workflow"

    def register_commands(self, cli: click.Group) -> None:
        @cli.command("my-workflow")
        @click.pass_context
        def run(ctx):
            """Run my custom workflow."""
            client = ctx.obj["client"]
            # Use the full SDK here
            tasks = client.tasks.get_all_tasks(project_id=1, status_id=1)
            click.echo(f"Found {len(tasks)} active tasks")
```

2. Optionally add config in `~/.config/kanboard/config.toml`:

```toml
[workflows.my-workflow]
target_project = 1
```

3. The workflow is automatically discovered on next CLI invocation:

```bash
kanboard workflow list       # See discovered workflows
kanboard my-workflow         # Run your workflow
```

See `docs/plan/05-milestone-3-extended.md` (Tasks 40–41) for full architecture details.

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
│       ├── main.py                 # Click app root, global options
│       ├── formatters.py           # Table / JSON / CSV / quiet renderers
│       ├── workflow_loader.py      # Plugin discovery and loading
│       ├── commands/               # One module per CLI command group
│       └── workflows/
│           └── base.py             # BaseWorkflow ABC
├── tests/
│   ├── unit/                       # Mocked httpx tests
│   ├── integration/                # Docker-based lifecycle tests
│   └── cli/                        # CliRunner output tests
├── docs/
│   └── plan/                       # Architecture and build plan
├── pyproject.toml
├── Makefile
├── LICENSE
└── CHANGELOG.md
```

## Development

### Setup

```bash
git clone https://github.com/geekmuse/kanboard-cli-denuo.git
cd kanboard-cli-denuo
pip install -e ".[dev]"
```

### Common Commands

```bash
make install          # Install in editable mode with dev dependencies
make lint             # Run ruff linter
make test             # Run unit and CLI tests
make test-integration # Run integration tests (requires Docker)
make coverage         # Run tests with coverage report
```

### Testing

- **Unit tests** — Mocked `httpx` via `pytest-httpx`; covers all SDK resource methods and exception paths
- **CLI tests** — Click `CliRunner`-based; verifies output across all four formats
- **Integration tests** — Docker-based (`docker-compose.test.yml`) with a live Kanboard instance; full CRUD lifecycle for every resource

### Dependencies

| Package       | Purpose                                   |
|---------------|-------------------------------------------|
| `httpx`       | HTTP client (JSON-RPC transport)          |
| `click`       | CLI framework                             |
| `rich`        | Colored table output                      |
| `tomli-w`     | TOML config writing                       |
| `pytest`      | Test framework (dev)                      |
| `pytest-httpx`| HTTP mocking for tests (dev)              |
| `ruff`        | Linter and formatter (dev)                |
| `coverage`    | Code coverage reporting (dev)             |

## Exception Hierarchy

The SDK provides structured exceptions for programmatic error handling:

```
KanboardError (base)
├── KanboardConfigError          # Missing/invalid configuration
├── KanboardConnectionError      # Network/connection failures
├── KanboardAuthError            # HTTP 401/403, invalid credentials
├── KanboardAPIError             # JSON-RPC error responses
│   ├── KanboardNotFoundError    # Resource not found (null response)
│   └── KanboardValidationError  # Invalid parameters
└── KanboardResponseError        # Malformed/unparseable responses
```

## License

[MIT](LICENSE)
