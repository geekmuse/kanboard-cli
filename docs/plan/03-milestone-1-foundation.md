# Milestone 1: Foundation (P0) — Tasks 1–10

> ← [API Reference](02-api-reference.md) | [README](README.md) | [Milestone 2](04-milestone-2-core.md) →

> Everything here unblocks all subsequent work.

---

### Task 1: Project scaffolding and packaging setup

- [ ] **Priority:** P0 — without this, nothing is installable or testable
- **Complexity:** M

Create the full project skeleton. `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "kanboard-cli"
version = "0.1.0"
description = "Python SDK and CLI for the Kanboard JSON-RPC API"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
dependencies = ["httpx>=0.27", "click>=8.1", "rich>=13.0", "tomli-w>=1.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-httpx>=0.30", "ruff>=0.4", "coverage>=7.0"]

[project.scripts]
kanboard = "kanboard_cli.main:cli"

[tool.hatch.build.targets.wheel]
packages = ["src/kanboard", "src/kanboard_cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py311"
src = ["src"]
```

**Done when:** `pip install -e ".[dev]"` succeeds, `ruff check .` passes, `pytest` discovers tests. `.gitignore`, `LICENSE` (MIT), `Makefile` (install/lint/test/coverage targets), all directories and `__init__.py` files created per Target Directory Structure.

---

### Task 2: JSON-RPC transport layer

- [ ] **Priority:** P0 — every SDK method depends on this
- **Complexity:** L
- **Dependencies:** Task 3

Build `src/kanboard/client.py`. Key design:

```python
class KanboardClient:
    JSONRPC_VERSION = "2.0"

    def __init__(self, url: str, token: str, *, timeout: float = 30.0):
        self._url = url
        self._auth = ("jsonrpc", token)
        self._http = httpx.Client(timeout=timeout)
        # Resource accessors added by Tasks 6+ (e.g., self.tasks = TasksResource(self))

    def call(self, method: str, **params) -> Any:
        """Single JSON-RPC call. Returns parsed 'result' value."""
        # Build payload, POST, parse response, handle errors

    def batch(self, calls: list[tuple[str, dict]]) -> list[Any]:
        """Batch JSON-RPC call. Returns list of results."""

    def close(self): ...
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
```

Resource modules attach as: `self.tasks = TasksResource(self)` where each resource calls `self._client.call("methodName", **params)`.

**Done when:** `call()` and `batch()` work; JSON-RPC errors raise `KanboardAPIError`; HTTP 401/403 raise `KanboardAuthError`; connection failures raise `KanboardConnectionError`; malformed responses raise `KanboardResponseError`; DEBUG logging for request/response; unit tests with `pytest-httpx` covering all paths.

---

### Task 3: Exception hierarchy

- [ ] **Priority:** P0 — transport layer and all resources depend on this
- **Complexity:** S

Create `src/kanboard/exceptions.py`:

```python
KanboardError (base)
├── KanboardConfigError(message, field)
├── KanboardConnectionError(message, url, cause)
├── KanboardAuthError(message, http_status)
├── KanboardAPIError(message, method, code)
│   ├── KanboardNotFoundError(resource, identifier)
│   └── KanboardValidationError
└── KanboardResponseError(message, raw_body)
```

**Done when:** All exceptions importable from `kanboard`, each carries structured context, `str()` produces human-readable message, unit tests verify construction.

---

### Task 4: Configuration system

- [ ] **Priority:** P0 — CLI and client instantiation depend on this
- **Complexity:** M

Build `src/kanboard/config.py`. See [Configuration Schema](#configuration-schema) for full spec.

```python
@dataclass(frozen=True)
class KanboardConfig:
    url: str
    token: str
    profile: str
    output_format: str

    @classmethod
    def resolve(cls, cli_url=None, cli_token=None, cli_profile=None, cli_output=None) -> "KanboardConfig":
        # 1. Load ~/.config/kanboard/config.toml via tomllib
        # 2. Determine profile (CLI > env KANBOARD_PROFILE > file default)
        # 3. Resolve each field: CLI > env > file
        # 4. Validate required fields, raise KanboardConfigError if missing

    @staticmethod
    def get_workflow_config(name: str) -> dict:
        """Load [workflows.<name>] section from config file."""
```

Export constants: `CONFIG_DIR`, `CONFIG_FILE`, `WORKFLOW_DIR` (all under `~/.config/kanboard/`).

**Done when:** Layered resolution works correctly, missing values raise actionable errors, unit tests cover each layer and override.

---

### Task 5: SDK response models

- [ ] **Priority:** P0 — typed returns for all resource methods
- **Complexity:** L

Create `src/kanboard/models.py` with dataclasses. Each model has `@classmethod from_api(cls, data: dict)` that uses `.get()` with defaults and coerces types.

**Models:** `Task`, `Project`, `Column`, `Swimlane`, `Comment`, `Subtask`, `User`, `Category`, `Tag`, `Link`, `TaskLink`, `ExternalTaskLink`, `Group`, `ProjectFile`, `TaskFile`, `Action`.

**Helpers:**

```python
def _parse_date(value) -> datetime | None:
    # Handle None, "", "0", 0, unix timestamps, "YYYY-MM-DD HH:MM", "YYYY-MM-DD"

def _int(value) -> int:
    # Coerce to int; Kanboard sometimes returns "0" as string
```

**Done when:** All models cover fields from API `get*` responses, `from_api()` handles Kanboard's type inconsistencies, importable from `kanboard`, unit tests with sample payloads.

**Risks:** API response shapes aren't formally documented as schemas — fields may need adjustment when integration tests run.

---

### Task 6: Tasks resource module — SDK

- [ ] **Priority:** P0 — validates the resource-module pattern all others copy
- **Complexity:** L
- **Dependencies:** Tasks 2, 3, 5

Implement `src/kanboard/resources/tasks.py` — all 14 methods from [API Category: Tasks](#api-category-tasks-14-methods). Wire into `KanboardClient.tasks`.

**Pattern:**

```python
class TasksResource:
    def __init__(self, client): self._client = client

    def create_task(self, title: str, project_id: int, **kwargs) -> int:
        result = self._client.call("createTask", title=title, project_id=project_id, **kwargs)
        if result is False: raise KanboardAPIError(...)
        return int(result)

    def get_task(self, task_id: int) -> Task:
        result = self._client.call("getTask", task_id=task_id)
        if result is None: raise KanboardNotFoundError("Task", task_id)
        return Task.from_api(result)

    def get_all_tasks(self, project_id: int, status_id: int = 1) -> list[Task]:
        result = self._client.call("getAllTasks", project_id=project_id, status_id=status_id)
        return [Task.from_api(t) for t in (result or [])]

    # ... remaining 11 methods follow same patterns
```

**Done when:** All 14 methods callable, all optional params supported as kwargs, typed model returns, `KanboardNotFoundError` on null, unit tests for every method.

---

### Task 7: Projects resource module — SDK

- [ ] **Priority:** P0 — projects are the container for everything
- **Complexity:** L
- **Dependencies:** Tasks 2, 3, 5

Implement `src/kanboard/resources/projects.py` — all 14 methods from [API Category: Projects](#api-category-projects-14-methods). Wire into `KanboardClient.projects`. Follow Task 6 pattern exactly.

---

### Task 8: Click application skeleton and command groups

- [ ] **Priority:** P0 — the CLI is the primary user interface
- **Complexity:** M
- **Dependencies:** Tasks 1, 4

Build `src/kanboard_cli/main.py`:

```python
@click.group()
@click.option("--url", envvar="KANBOARD_URL")
@click.option("--token", envvar="KANBOARD_API_TOKEN")
@click.option("--profile", envvar="KANBOARD_PROFILE", default=None)
@click.option("--output", "-o", type=click.Choice(["table","json","csv","quiet"]), default=None)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def cli(ctx, url, token, profile, output, verbose):
    # Resolve config, create KanboardClient, store in ctx.obj
    # Allow config-less commands (e.g., config init) by catching KanboardConfigError
```

Register stub command groups for all resources. Auto-discover and register workflow commands via `workflow_loader.py`.

**Done when:** `kanboard --help` shows all groups, global options inherited, config resolution wired, stubs for all command groups registered.

---

### Task 9: Output formatters

- [ ] **Priority:** P0 — every CLI command needs output rendering
- **Complexity:** M
- **Dependencies:** Task 8

Build `src/kanboard_cli/formatters.py`:

```python
def format_output(data, *, format="table", columns=None):
    # Normalize to list of dicts (handle dataclasses via asdict)
    # table: rich.table.Table with colored headers, auto-width
    # json: json.dumps indent=2 (single object if one result, array if many)
    # csv: csv.DictWriter with proper escaping
    # quiet: print only 'id' field, one per line

def format_success(message: str, format="table"):
    # json mode: {"status": "ok", "message": ...}
    # other modes: "checkmark {message}"
```

**Done when:** All 4 formats produce correct output, unit tests verify each.

---

### Task 10: Task + Project CLI commands

- [ ] **Priority:** P0 — proves the full stack end-to-end
- **Complexity:** XL
- **Dependencies:** Tasks 6, 7, 8, 9

**Task commands:**
```
kanboard task list <project_id> [--status active|inactive]
kanboard task get <task_id>
kanboard task create <project_id> <title> [--owner-id] [--column-id] [--swimlane-id] [--due DATE] [--description] [--color] [--category-id] [--score] [--priority] [--reference] [--tag TAG]...
kanboard task update <task_id> [--title] [--color] [--due] [--description] [--owner-id] [--category-id] [--score] [--priority] [--reference] [--tag TAG]...
kanboard task close <task_id>
kanboard task open <task_id>
kanboard task remove <task_id> [--yes]
kanboard task search <project_id> <query>
kanboard task move <task_id> --project-id --column-id --position --swimlane-id
kanboard task move-to-project <task_id> <project_id> [--swimlane-id] [--column-id] [--category-id] [--owner-id]
kanboard task duplicate <task_id> <project_id> [--swimlane-id] [--column-id]
kanboard task overdue [--project-id P]
```

**Project commands:**
```
kanboard project list
kanboard project get <project_id>
kanboard project create <name> [--description] [--owner-id] [--identifier] [--start-date] [--end-date]
kanboard project update <project_id> [--name] [--description] [--owner-id] [--identifier]
kanboard project remove <project_id> [--yes]
kanboard project enable <project_id>
kanboard project disable <project_id>
kanboard project activity <project_id>
```

Destructive commands require `--yes` confirmation. All 4 output formats on every command. CLI tests with CliRunner.

---

