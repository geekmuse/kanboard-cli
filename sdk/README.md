# kanboard-sdk

> Python SDK for the [Kanboard](https://kanboard.org/) JSON-RPC API — typed models, structured exceptions, and complete coverage of all 158 API methods.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/geekmuse/kanboard-cli/blob/main/LICENSE)
<!-- [![PyPI version](https://img.shields.io/pypi/v/kanboard-sdk.svg)](https://pypi.org/project/kanboard-sdk/) -->

## Installation

```bash
pip install kanboard-sdk
```

## Quick Start

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
```

## Features

- **Complete API coverage** — All 158 Kanboard JSON-RPC methods across 24 resource categories
- **Typed models** — Dataclass response models with `from_api()` factory methods that handle Kanboard's type inconsistencies
- **Structured exceptions** — `KanboardAuthError`, `KanboardNotFoundError`, `KanboardAPIError`, etc. with rich context
- **Resource-based access** — `client.tasks`, `client.projects`, `client.columns`, etc.
- **Context manager** — `KanboardClient` supports `with` statements for clean resource management
- **Batch calls** — `client.batch()` for sending multiple JSON-RPC requests in one HTTP round-trip
- **Cross-project orchestration** — Portfolio management, milestones, dependency analysis, and critical-path computation via `kanboard.orchestration`
- **Minimal dependencies** — Only `httpx`

## Resource Categories

| Accessor | Methods | Description |
|---|---|---|
| `client.tasks` | 14 | Task CRUD, search, move, duplicate |
| `client.projects` | 14 | Project CRUD, enable/disable, activity |
| `client.board` | 1 | Full board view (columns → swimlanes → tasks) |
| `client.columns` | 6 | Column management and positioning |
| `client.swimlanes` | 11 | Swimlane management |
| `client.comments` | 5 | Task comments |
| `client.categories` | 5 | Project categories |
| `client.tags` | 7 | Global and project tags |
| `client.subtasks` | 5 | Subtask management |
| `client.users` | 10 | User administration |
| `client.links` | 7 | Link type definitions |
| `client.task_links` | 5 | Internal task-to-task links |
| `client.external_task_links` | 7 | External URL links on tasks |
| `client.groups` | 5 | Group management |
| `client.group_members` | 5 | Group membership |
| `client.actions` | 6 | Automatic action configuration |
| `client.project_files` | 6 | Project file attachments |
| `client.task_files` | 6 | Task file attachments |
| `client.project_metadata` | 4 | Project key-value metadata |
| `client.task_metadata` | 4 | Task key-value metadata |
| `client.project_permissions` | 9 | Project user/group permissions |
| `client.subtask_time_tracking` | 4 | Subtask time tracking |
| `client.me` | 7 | Current user (requires user auth) |
| `client.application` | 7 | Application info (version, colors, roles) |
| `client.portfolios` | 18 | Portfolio plugin — portfolio CRUD, project membership, dependency queries *(requires plugin)* |
| `client.milestones` | 10 | Portfolio plugin — milestone CRUD, task membership, progress *(requires plugin)* |

## Exception Hierarchy

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

## Configuration

`KanboardClient` accepts URL and token directly, or use `KanboardConfig.resolve()` for layered config resolution (TOML file → environment variables → explicit args):

```python
from kanboard import KanboardClient, KanboardConfig

# Direct
client = KanboardClient(url="...", token="...")

# From config file / env vars
config = KanboardConfig.resolve()
client = KanboardClient(url=config.url, token=config.token)
```

### Environment Variables

| Variable | Purpose |
|---|---|
| `KANBOARD_URL` | JSON-RPC endpoint |
| `KANBOARD_TOKEN` | API token |
| `KANBOARD_PROFILE` | Active config profile |
| `KANBOARD_OUTPUT_FORMAT` | Default output format |
| `KANBOARD_AUTH_MODE` | `app` (token) or `user` (username/password) |
| `KANBOARD_USERNAME` | Username (user auth mode) |
| `KANBOARD_PASSWORD` | Password (user auth mode) |
| `KANBOARD_PORTFOLIO_BACKEND` | `local` (JSON file) or `remote` (plugin API) |

### Portfolio Backend (Orchestration)

The orchestration layer (`PortfolioManager`, `DependencyAnalyzer`) supports two storage backends. Select via `KanboardConfig` or the `create_backend()` factory:

```python
from kanboard import KanboardClient, KanboardConfig, create_backend
from kanboard.orchestration import PortfolioManager

config = KanboardConfig.resolve()  # reads portfolio_backend from env/config file

with KanboardClient(url=config.url, token=config.token) as kb:
    backend = create_backend(config.portfolio_backend, client=kb)
    manager = PortfolioManager(kb, backend)
    tasks = manager.get_portfolio_tasks("My Portfolio")
```

- **`"local"`** (default) — data stored in `~/.config/kanboard/portfolios.json`; no plugin required; machine-local only
- **`"remote"`** — data stored server-side via the [Kanboard Portfolio plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management); shared across all users

## CLI Companion

For a full command-line interface built on this SDK, install [`kanboard-cli`](https://github.com/geekmuse/kanboard-cli):

```bash
pip install kanboard-cli
```

## Documentation

- **[SDK Guide](https://github.com/geekmuse/kanboard-cli/blob/main/docs/sdk-guide.md)** — Full usage guide with examples for every resource
- **[Configuration](https://github.com/geekmuse/kanboard-cli/blob/main/docs/configuration.md)** — Config file, env vars, and profiles
- **[API Reference](https://github.com/geekmuse/kanboard-cli/blob/main/docs/plan/02-api-reference.md)** — Complete Kanboard JSON-RPC method signatures

## License

[MIT](https://github.com/geekmuse/kanboard-cli/blob/main/LICENSE)
