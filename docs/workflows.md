# Workflow Plugin Development Guide

> Step-by-step guide to creating, configuring, and distributing `kanboard-cli` workflow plugins.

---

## Table of Contents

- [Overview](#overview)
- [BaseWorkflow ABC Reference](#baseworkflow-abc-reference)
  - [Abstract Properties](#abstract-properties)
  - [Abstract Methods](#abstract-methods)
  - [Concrete Methods](#concrete-methods)
- [Creating a Workflow Plugin](#creating-a-workflow-plugin)
  - [Step 1 — Create the plugin file](#step-1--create-the-plugin-file)
  - [Step 2 — Subclass BaseWorkflow](#step-2--subclass-baseworkflow)
  - [Step 3 — Implement register_commands](#step-3--implement-register_commands)
  - [Step 4 — Add config (optional)](#step-4--add-config-optional)
  - [Step 5 — Verify discovery](#step-5--verify-discovery)
- [Workflow Config Section](#workflow-config-section)
- [Discovery Mechanism](#discovery-mechanism)
  - [Scan Directory](#scan-directory)
  - [Discovery Algorithm](#discovery-algorithm)
  - [Loading via importlib](#loading-via-importlib)
  - [Class Inspection](#class-inspection)
- [Full Example — Sprint Close Workflow](#full-example--sprint-close-workflow)
- [Multi-command Workflow Groups](#multi-command-workflow-groups)
- [Error Handling and Logging](#error-handling-and-logging)
- [Workflow Testing](#workflow-testing)

---

## Overview

The `kanboard-cli` workflow plugin system lets you extend the CLI with custom commands that use the full Kanboard SDK. Plugins are plain Python files dropped into `~/.config/kanboard/workflows/`. They are discovered automatically on every CLI invocation.

**Use cases:**

- Automate multi-step Kanboard workflows (e.g. sprint close, board cleanup, task triage)
- Build organisation-specific CLI commands on top of the Kanboard API
- Wrap batch operations that span multiple resource types

---

## BaseWorkflow ABC Reference

All workflow plugins must subclass `BaseWorkflow` from `kanboard_cli.workflows.base`.

```python
from kanboard_cli.workflows.base import BaseWorkflow
```

### Abstract Properties

Both properties **must** be implemented by concrete subclasses:

#### `name` → `str`

```python
@property
@abstractmethod
def name(self) -> str: ...
```

A short, unique identifier for the workflow. Used as the CLI command name and as the key in the `[workflows]` config section.

- **Must be a valid Click command name** (lowercase, hyphens OK, no spaces)
- **Must be unique** across all installed workflow plugins

**Examples:** `"sprint-close"`, `"board-cleanup"`, `"triage"`

---

#### `description` → `str`

```python
@property
@abstractmethod
def description(self) -> str: ...
```

A one-line human-readable summary shown in `kanboard workflow list` output and in `--help` text.

**Examples:** `"Close the current sprint and archive completed tasks"`, `"Triage unassigned tasks in inbox project"`

---

### Abstract Methods

#### `register_commands(cli: click.Group) → None`

```python
@abstractmethod
def register_commands(self, cli: click.Group) -> None: ...
```

Called by the CLI loader to attach this workflow's Click commands to the root CLI group.

| Parameter | Type          | Description                            |
|-----------|---------------|----------------------------------------|
| `cli`     | `click.Group` | The root Click group (`kanboard` CLI)  |

Inside this method, decorate your Click commands and add them to `cli`:

```python
def register_commands(self, cli: click.Group) -> None:
    @cli.command("my-workflow")
    @click.pass_context
    def run(ctx: click.Context) -> None:
        """One-line description shown in --help."""
        client = ctx.obj.client
        # Use the SDK here
        ...
```

---

### Concrete Methods

#### `get_config() → dict[str, Any]`

```python
def get_config(self) -> dict[str, Any]:
```

Reads the `[workflows.<name>]` section from `~/.config/kanboard/config.toml` and returns its contents as a plain dictionary. Returns `{}` when the section is absent.

```python
def register_commands(self, cli: click.Group) -> None:
    workflow_self = self

    @cli.command("sprint-close")
    @click.pass_context
    def run(ctx: click.Context) -> None:
        """Close the current sprint."""
        cfg = workflow_self.get_config()
        project_id = cfg.get("target_project", 1)
        ...
```

---

## Creating a Workflow Plugin

### Step 1 — Create the plugin file

Create a Python file in the workflows directory:

```bash
mkdir -p ~/.config/kanboard/workflows
touch ~/.config/kanboard/workflows/my_workflow.py
```

> **Naming:** The file name becomes part of the module name (`kanboard_workflows.my_workflow`). Use lowercase with underscores. Files starting with `_` are ignored by the loader.

---

### Step 2 — Subclass BaseWorkflow

```python
# ~/.config/kanboard/workflows/my_workflow.py
from __future__ import annotations

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
        ...
```

---

### Step 3 — Implement register_commands

Use `@cli.command()` to attach one or more commands to the root CLI group:

```python
def register_commands(self, cli: click.Group) -> None:
    @cli.command("my-workflow")
    @click.argument("project_id", type=int)
    @click.option("--dry-run", is_flag=True, help="Print actions without executing")
    @click.pass_context
    def run(ctx: click.Context, project_id: int, dry_run: bool) -> None:
        """Run my custom workflow on PROJECT_ID."""
        client = ctx.obj.client          # KanboardClient
        output_fmt = ctx.obj.output      # "table" | "json" | "csv" | "quiet"

        tasks = client.tasks.get_all_tasks(project_id, status_id=1)
        click.echo(f"Found {len(tasks)} open tasks in project {project_id}")

        if not dry_run:
            for task in tasks:
                # ... do something
                pass
```

**Accessing the SDK:**

The `ctx.obj` object is an `AppContext` instance with two attributes:

| Attribute | Type              | Description                                          |
|-----------|-------------------|------------------------------------------------------|
| `client`  | `KanboardClient`  | Authenticated SDK client (or `None` if config failed)|
| `output`  | `str`             | Active output format (`"table"`, `"json"`, etc.)     |
| `config`  | `KanboardConfig`  | Resolved configuration (or `None` if config failed)  |

Always check `ctx.obj.client is not None` or let Click's exception handling surface the config error.

---

### Step 4 — Add config (optional)

If your workflow needs configuration, add a `[workflows.<name>]` section to `~/.config/kanboard/config.toml`:

```toml
[workflows.my-workflow]
target_project = 42
notify_slack   = true
```

Then read it with `self.get_config()`:

```python
cfg = self.get_config()
project_id = cfg.get("target_project", 1)
```

---

### Step 5 — Verify discovery

```bash
kanboard workflow list
```

Your workflow should appear in the list. If it doesn't, run with `--verbose` to see load errors:

```bash
kanboard --verbose workflow list
```

---

## Workflow Config Section

Each workflow plugin can define its own named section under `[workflows]` in `~/.config/kanboard/config.toml`. The section key **must match** the workflow's `name` property exactly.

```toml
[workflows.sprint-close]
target_project = 42
sprint_tag     = "active-sprint"
done_column    = "Done"
archive        = true
```

`BaseWorkflow.get_config()` reads this section and returns the dictionary:

```python
# Inside a workflow command handler:
cfg = workflow_self.get_config()
# cfg == {"target_project": 42, "sprint_tag": "active-sprint", ...}
```

`get_config()` always returns a `dict` — it returns `{}` (empty dict) when the section is absent, so `.get("key", default)` patterns are always safe.

---

## Discovery Mechanism

### Scan Directory

The loader scans `~/.config/kanboard/workflows/` on every CLI invocation. This path is also available as a constant:

```python
from kanboard.config import WORKFLOW_DIR
# WORKFLOW_DIR == Path.home() / ".config" / "kanboard" / "workflows"
```

You can also pass a custom directory to `discover_workflows()` for testing.

---

### Discovery Algorithm

The loader (`kanboard_cli.workflow_loader.discover_workflows`) iterates over the scan directory in sorted order and loads:

1. **`.py` files** — any file matching `*.py` that does **not** start with `_`
2. **Packages** — any subdirectory containing an `__init__.py`

Entries starting with `_` (e.g. `_helpers.py`) are skipped, allowing shared helper modules.

```
~/.config/kanboard/workflows/
├── sprint_close.py          # ✅ loaded
├── board_cleanup.py         # ✅ loaded
├── _utils.py                # ⏭ skipped (starts with _)
└── my_package/
    ├── __init__.py          # ✅ loaded (package)
    └── helpers.py           # not loaded directly (package entry is __init__.py)
```

---

### Loading via importlib

Each discovered file is loaded using `importlib.util.spec_from_file_location` under the namespace `kanboard_workflows.<stem>`. Failed loads log a warning and are silently skipped — they do not crash the CLI.

```python
spec = importlib.util.spec_from_file_location("kanboard_workflows.sprint_close", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

---

### Class Inspection

After loading, the module is inspected for concrete `BaseWorkflow` subclasses using `inspect.getmembers`. The loader:

1. Finds all classes that are a subclass of `BaseWorkflow`
2. Skips `BaseWorkflow` itself
3. Skips abstract classes (`inspect.isabstract()`)
4. Instantiates each concrete class with `obj()`

Failed instantiations log a warning and are skipped.

The final list of workflow instances is sorted alphabetically by `name`.

---

## Full Example — Sprint Close Workflow

```python
# ~/.config/kanboard/workflows/sprint_close.py
"""Sprint close workflow — archives Done tasks and resets the sprint tag."""

from __future__ import annotations

import click

from kanboard_cli.workflows.base import BaseWorkflow


class SprintCloseWorkflow(BaseWorkflow):
    """Close the current sprint, archive completed tasks, and reset sprint tags."""

    @property
    def name(self) -> str:
        return "sprint-close"

    @property
    def description(self) -> str:
        return "Close the current sprint and archive completed tasks"

    def register_commands(self, cli: click.Group) -> None:
        workflow_self = self

        @cli.command("sprint-close")
        @click.option("--dry-run", is_flag=True, help="Preview actions without making changes")
        @click.pass_context
        def sprint_close(ctx: click.Context, dry_run: bool) -> None:
            """Close the current sprint and archive completed tasks."""
            cfg = workflow_self.get_config()
            project_id: int = cfg.get("target_project", 1)
            done_column_name: str = cfg.get("done_column", "Done")

            client = ctx.obj.client

            # Find the "Done" column
            columns = client.columns.get_columns(project_id)
            done_col = next(
                (c for c in columns if c.title.lower() == done_column_name.lower()),
                None,
            )
            if done_col is None:
                raise click.ClickException(
                    f"Column '{done_column_name}' not found in project {project_id}"
                )

            # Get all tasks in Done column
            board = client.board.get_board(project_id)
            done_tasks = [
                task
                for col in board
                if col.get("id") == done_col.id
                for task in col.get("tasks", [])
            ]

            click.echo(
                f"{'[DRY RUN] ' if dry_run else ''}Found {len(done_tasks)} "
                f"completed tasks in '{done_column_name}'"
            )

            if not dry_run:
                for task in done_tasks:
                    client.tasks.close_task(task["id"])
                    click.echo(f"  ✓ Closed task #{task['id']}: {task['title']}")

            click.echo("Sprint closed." if not dry_run else "Dry run complete — no changes made.")
```

**Config (`~/.config/kanboard/config.toml`):**

```toml
[workflows.sprint-close]
target_project = 42
done_column    = "Done"
```

**Usage:**

```bash
kanboard sprint-close --dry-run    # preview
kanboard sprint-close              # execute
```

---

## Multi-command Workflow Groups

Workflows can register a Click group with multiple subcommands:

```python
def register_commands(self, cli: click.Group) -> None:
    @cli.group("triage")
    def triage_group() -> None:
        """Task triage commands."""

    @triage_group.command("list")
    @click.argument("project_id", type=int)
    @click.pass_context
    def triage_list(ctx: click.Context, project_id: int) -> None:
        """List unassigned tasks for triage."""
        client = ctx.obj.client
        tasks = client.tasks.get_all_tasks(project_id, status_id=1)
        unassigned = [t for t in tasks if not t.assignee_id]
        click.echo(f"{len(unassigned)} unassigned tasks need triage")

    @triage_group.command("assign")
    @click.argument("task_id", type=int)
    @click.argument("user_id", type=int)
    @click.pass_context
    def triage_assign(ctx: click.Context, task_id: int, user_id: int) -> None:
        """Assign TASK_ID to USER_ID."""
        client = ctx.obj.client
        client.tasks.update_task(task_id, owner_id=user_id)
        click.echo(f"Task #{task_id} assigned to user {user_id}")
```

Usage:

```bash
kanboard triage list 42
kanboard triage assign 17 3
```

---

## Error Handling and Logging

Use Click's `ClickException` for user-facing errors:

```python
from kanboard.exceptions import KanboardAPIError

try:
    tasks = client.tasks.get_all_tasks(project_id, status_id=1)
except KanboardAPIError as exc:
    raise click.ClickException(str(exc)) from exc
```

For debug logging, use Python's standard `logging` module:

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Loading config for workflow '%s'", self.name)
```

Debug messages are visible when the user passes `--verbose`.

---

## Workflow Testing

Test your workflow using Click's `CliRunner` with a mocked `KanboardClient`:

```python
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_sprint_close_dry_run(runner):
    mock_client = MagicMock()
    mock_client.columns.get_columns.return_value = [
        MagicMock(id=5, title="Done")
    ]
    mock_client.board.get_board.return_value = [
        {"id": 5, "tasks": [{"id": 10, "title": "Fix bug"}]}
    ]

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=MagicMock(
            url="http://localhost/jsonrpc.php",
            token="token",
            profile="default",
            output_format="table",
            auth_mode="app",
            username=None,
            password=None,
        )),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["sprint-close", "--dry-run"])
        assert result.exit_code == 0
        assert "1 completed tasks" in result.output
        assert "Dry run complete" in result.output
        mock_client.tasks.close_task.assert_not_called()
```
