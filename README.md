# kanboard-cli

> A Python SDK and CLI for the [Kanboard](https://kanboard.org/) JSON-RPC API — complete coverage of all 158 API methods, a plugin system for custom workflows, and a first-class developer experience.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
<!-- [![PyPI version](https://img.shields.io/pypi/v/kanboard-cli.svg)](https://pypi.org/project/kanboard-cli/) -->

**Documentation:**
[CLI Reference](docs/cli-reference.md) •
[SDK Guide](docs/sdk-guide.md) •
[Configuration](docs/configuration.md) •
[Workflows](docs/workflows.md) •
[Contributing](CONTRIBUTING.md)

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
- **Cross-project orchestration** — Portfolio management, cross-project milestones, dependency analysis, and critical-path computation as a client-side meta-construct (no server plugin required)

## Cross-Project Orchestration

kanboard-cli ships a **Phase 0 orchestration layer** that treats multiple Kanboard projects as a unified portfolio — using only the existing Kanboard API (task links, metadata) as a persistence layer with no server-side plugin required.

### What it enables

| Capability | Description |
|---|---|
| **Portfolio management** | Group multiple projects into a named portfolio stored locally in `~/.config/kanboard/portfolios.json` |
| **Cross-project milestones** | Define milestones that span tasks from multiple projects; track percent-complete and at-risk status |
| **Dependency analysis** | Discover cross-project `blocks`/`is blocked by` relationships; detect blocked and blocking tasks |
| **Critical path** | Compute the longest dependency chain (topological sort) across all portfolio tasks |
| **Metadata sync** | Push portfolio and milestone membership into Kanboard project/task metadata using the `kanboard_cli:` key prefix |

### Quick example

```bash
# Create a portfolio grouping two projects
kanboard portfolio create "Platform Launch" --description "Q3 release"
kanboard portfolio add-project "Platform Launch" 1
kanboard portfolio add-project "Platform Launch" 2

# Create a milestone spanning both projects
kanboard milestone create "Platform Launch" "Beta Release" --target-date 2026-06-30
kanboard milestone add-task "Platform Launch" "Beta Release" 42
kanboard milestone add-task "Platform Launch" "Beta Release" 99 --critical

# Check progress and risks
kanboard milestone progress "Platform Launch"
kanboard portfolio show "Platform Launch"

# Visualise cross-project dependencies
kanboard portfolio dependencies "Platform Launch"
kanboard portfolio blocked "Platform Launch"
kanboard portfolio critical-path "Platform Launch"
```

### SDK example

```python
from kanboard import KanboardClient
from kanboard.orchestration import PortfolioManager, DependencyAnalyzer, LocalPortfolioStore

with KanboardClient(url=URL, token=TOKEN) as kb:
    store = LocalPortfolioStore()
    manager = PortfolioManager(kb, store)
    analyzer = DependencyAnalyzer(kb)

    # Aggregate tasks across all portfolio projects
    tasks = manager.get_portfolio_tasks("Platform Launch")

    # Find blocked cross-project tasks
    edges = analyzer.get_dependency_edges(tasks, cross_project_only=True)
    blocked = analyzer.get_blocked_tasks(tasks)

    # Compute critical path
    critical = analyzer.get_critical_path(tasks)
```

### Server-side visualization (optional)

For in-browser Kanboard UI features — including interactive dependency graphs, multi-project Gantt timelines, portfolio dashboards, and board-level blocking indicators — see the companion **[Kanboard Portfolio plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management)**.

The CLI's `portfolio` and `milestone` commands work independently of the plugin, but the plugin provides the visual layer within Kanboard's web interface.

See **[docs/sdk-guide.md#cross-project-orchestration](docs/sdk-guide.md#cross-project-orchestration)** and **[docs/cli-reference.md#portfolio](docs/cli-reference.md#portfolio)** for full reference documentation.

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
git clone https://github.com/geekmuse/kanboard-cli.git
cd kanboard-cli
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

For the full SDK guide including all resource examples, exception handling, and batch usage, see **[docs/sdk-guide.md](docs/sdk-guide.md)**.

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
| `kanboard portfolio` | Portfolio management + dependency analysis (cross-project orchestration) |
| `kanboard milestone` | Cross-project milestone tracking         |

Use `kanboard <command> --help` for detailed usage of any command.

For the full command reference, see **[docs/cli-reference.md](docs/cli-reference.md)**.

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
│   │   ├── resources/              # One module per API category (24 modules)
│   │   └── orchestration/          # Cross-project orchestration (opt-in)
│   │       ├── __init__.py         # Exports: PortfolioManager, DependencyAnalyzer, LocalPortfolioStore
│   │       ├── portfolio.py        # PortfolioManager — multi-project aggregation
│   │       ├── dependencies.py     # DependencyAnalyzer — graph traversal, critical path
│   │       └── store.py            # LocalPortfolioStore — JSON persistence
│   └── kanboard_cli/               # CLI package
│       ├── main.py                 # Click app root, global options
│       ├── formatters.py           # Table / JSON / CSV / quiet renderers
│       ├── renderers.py            # ASCII dependency graph, progress bar renderers
│       ├── workflow_loader.py      # Plugin discovery and loading
│       ├── commands/               # One module per CLI command group
│       └── workflows/
│           └── base.py             # BaseWorkflow ABC
├── tests/
│   ├── unit/                       # Mocked httpx tests
│   │   └── orchestration/          # Orchestration unit tests
│   ├── integration/                # Docker-based lifecycle tests
│   └── cli/                        # CliRunner output tests
├── docs/
│   ├── plan/                       # Architecture and build plan
│   ├── design/                     # Design documents and research
│   └── tasks/                      # Per-task implementation notes
├── pyproject.toml
├── Makefile
├── LICENSE
└── CHANGELOG.md
```

## Development

### Setup

```bash
git clone https://github.com/geekmuse/kanboard-cli.git
cd kanboard-cli
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
