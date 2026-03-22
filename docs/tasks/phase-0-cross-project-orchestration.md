# Phase 0: Cross-Project Orchestration — CLI-Only (Tasks 49–62)

> ← [Design Spec](../design/cross-project-orchestration.md) | [Milestone 4](../plan/06-milestone-4-ship.md) →
>
> Builds cross-project portfolio management, milestone tracking, and dependency
> analysis as a **CLI-side meta-construct** — no Kanboard plugin required.
> Uses the existing Kanboard API (task links, task metadata, project metadata)
> as the persistence layer, with orchestration logic living entirely in our
> Python SDK and CLI.
>
> **Pre-requisite reading:** [docs/design/cross-project-orchestration.md](../design/cross-project-orchestration.md)
> — especially §2.1 (existing cross-project capabilities), §2.3 Approach A,
> and §3.4–§3.5 (CLI/SDK integration, implementation roadmap).

---

## Overview

| Metric | Value |
|---|---|
| **Total tasks** | 14 (Tasks 49–62) |
| **Estimated effort** | 1–2 weeks |
| **New SDK modules** | 2 (`orchestration/portfolio.py`, `orchestration/dependencies.py`) |
| **New CLI command groups** | 2 (`portfolio`, `milestone`) |
| **New models** | 3 (`Portfolio`, `Milestone`, `DependencyEdge`) |
| **Kanboard modifications** | None — uses existing API only |
| **Plugin dependency** | None for core features; Kanboard Portfolio plugin URL required before doc updates (see Task 62 pre-flight) |

## Architecture Decisions

| # | Decision | Rationale |
|---|---|---|
| ADR-16 | **Orchestration logic in `src/kanboard/orchestration/`** — new subpackage, not `resources/` | Resources are 1:1 with Kanboard JSON-RPC methods. Orchestration modules compose multiple resource calls and add client-side logic (graph traversal, progress calculation). Separating them preserves the clean resource pattern. |
| ADR-17 | **Portfolio/milestone state stored in Kanboard metadata** — project metadata for portfolio membership, task metadata for milestone membership | Uses the existing API (no plugin). Trade-off: no referential integrity, no server-side queries across entities. Acceptable for Phase 0; Phase 1 plugin replaces with proper tables. |
| ADR-18 | **Cross-project dependencies use existing `task_has_links`** — no new storage | Kanboard's internal task links already work cross-project (task IDs are global). The "blocks"/"is blocked by" link types (IDs 2/3) express dependencies natively. |
| ADR-19 | **Local JSON cache file for portfolio definitions** — `~/.config/kanboard/portfolios.json` | Metadata API has no cross-entity query capability (can't say "find all projects with metadata key X"). Portfolio definitions (name → project IDs, milestone definitions) are stored locally with metadata used as a synchronization marker. |
| ADR-20 | **Orchestration module returns typed dataclasses, not raw dicts** | Consistent with SDK conventions (ADR-05). Orchestration models live in `models.py` alongside existing models. |

## Metadata Conventions

These key names are reserved by the orchestration layer. All values are JSON-encoded strings.

| Scope | Metadata Key | Value | Example |
|-------|-------------|-------|---------|
| Project | `kanboard_cli:portfolio` | JSON list of portfolio names this project belongs to | `'["Q2 Launch", "Annual Roadmap"]'` |
| Task | `kanboard_cli:milestones` | JSON list of `{portfolio, milestone}` dicts | `'[{"portfolio": "Q2 Launch", "milestone": "v2.0 Feature Complete"}]'` |
| Task | `kanboard_cli:milestone_critical` | JSON list of milestone names where this task is on critical path | `'["v2.0 Feature Complete"]'` |

All metadata keys are prefixed with `kanboard_cli:` to avoid collisions with user metadata or other tools.

## Local Portfolio Store

`~/.config/kanboard/portfolios.json` — canonical source for portfolio definitions:

```json
{
  "version": 1,
  "portfolios": [
    {
      "name": "Q2 2026 Launch",
      "description": "Coordinated product and marketing launch",
      "project_ids": [3, 5, 8],
      "milestones": [
        {
          "name": "v2.0 Feature Complete",
          "target_date": "2026-06-01",
          "task_ids": [15, 42, 55],
          "critical_task_ids": [15]
        }
      ],
      "created_at": "2026-03-22T10:00:00",
      "updated_at": "2026-03-22T10:00:00"
    }
  ]
}
```

A `portfolio sync` command pushes this state to Kanboard metadata (marking projects and tasks) and pulls any changes made via the Kanboard UI (e.g., tasks closed, links added).

---

## Tasks

### Task 49: Orchestration subpackage scaffolding

- [ ] **Priority:** P0 — all other Phase 0 tasks depend on this
- **Complexity:** S
- **Dependencies:** None (existing project structure)

Create the `src/kanboard/orchestration/` subpackage with:

```
src/kanboard/orchestration/
├── __init__.py          # Public API re-exports
├── portfolio.py         # PortfolioManager — CRUD + sync for portfolios
├── dependencies.py      # DependencyAnalyzer — graph traversal, critical path
└── store.py             # LocalPortfolioStore — JSON file I/O
```

**`__init__.py` exports:**
```python
from kanboard.orchestration.portfolio import PortfolioManager
from kanboard.orchestration.dependencies import DependencyAnalyzer
from kanboard.orchestration.store import LocalPortfolioStore
```

**Done when:**
- Package is importable: `from kanboard.orchestration import PortfolioManager`
- All three modules exist with stub classes
- `ruff check . && ruff format --check .` passes
- Smoke-test import in `tests/test_smoke.py` updated

**Implementation notes:**
- Do NOT add orchestration to `KanboardClient` as an attribute (unlike resources). Orchestration classes are instantiated separately, accepting a `KanboardClient` as a constructor argument. This keeps the client clean and makes orchestration opt-in.
- `__init__.py` should also export `__all__` for explicit public API.

---

### Task 50: Orchestration data models

- [ ] **Priority:** P0 — all orchestration logic and CLI commands depend on these
- **Complexity:** S
- **Dependencies:** Task 49

Add the following dataclasses to `src/kanboard/models.py`:

```python
@dataclasses.dataclass
class Portfolio:
    """A named group of Kanboard projects managed as a coordinated program."""
    name: str
    description: str
    project_ids: list[int]
    milestones: list[Milestone]
    created_at: datetime | None
    updated_at: datetime | None

@dataclasses.dataclass
class Milestone:
    """A cross-project milestone within a portfolio."""
    name: str
    portfolio_name: str
    target_date: datetime | None
    task_ids: list[int]
    critical_task_ids: list[int]

@dataclasses.dataclass
class MilestoneProgress:
    """Computed progress for a milestone."""
    milestone_name: str
    portfolio_name: str
    target_date: datetime | None
    total: int
    completed: int
    percent: float
    is_at_risk: bool
    is_overdue: bool
    blocked_task_ids: list[int]

@dataclasses.dataclass
class DependencyEdge:
    """A single dependency relationship between two tasks, possibly cross-project."""
    task_id: int
    task_title: str
    task_project_id: int
    task_project_name: str
    opposite_task_id: int
    opposite_task_title: str
    opposite_task_project_id: int
    opposite_task_project_name: str
    link_label: str
    is_cross_project: bool
    is_resolved: bool          # True if blocking task is closed
```

**Done when:**
- All three dataclasses added to `models.py`
- Each has `__post_init__` or factory as needed (no `from_api` needed — these are constructed client-side)
- Existing model tests still pass
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- These models do NOT have `from_api()` class methods because they are composed client-side from multiple API responses, not deserialized from a single API response. This is a deliberate departure from the resource model pattern.
- `Portfolio` and `Milestone` are mutable (no `frozen=True`) because they are edited locally before syncing.
- `MilestoneProgress` and `DependencyEdge` are computed/read-only and could be frozen, but keeping them mutable is simpler and consistent.
- Add these to `kanboard/__init__.py` public exports and `kanboard/models.py` `__all__`.

---

### Task 51: Local portfolio store — JSON persistence

- [ ] **Priority:** P0 — portfolio CRUD and sync depend on this
- **Complexity:** M
- **Dependencies:** Tasks 49, 50

Implement `src/kanboard/orchestration/store.py`:

```python
class LocalPortfolioStore:
    """Manages portfolio definitions in a local JSON file.

    Default path: ~/.config/kanboard/portfolios.json
    """

    def __init__(self, path: Path | None = None) -> None: ...

    def load(self) -> list[Portfolio]: ...
    def save(self, portfolios: list[Portfolio]) -> None: ...

    def get_portfolio(self, name: str) -> Portfolio: ...
    def create_portfolio(self, name: str, description: str = "",
                         project_ids: list[int] | None = None) -> Portfolio: ...
    def update_portfolio(self, name: str, **kwargs) -> Portfolio: ...
    def remove_portfolio(self, name: str) -> bool: ...

    def add_project(self, portfolio_name: str, project_id: int) -> Portfolio: ...
    def remove_project(self, portfolio_name: str, project_id: int) -> Portfolio: ...

    def add_milestone(self, portfolio_name: str, milestone: Milestone) -> Portfolio: ...
    def update_milestone(self, portfolio_name: str, milestone_name: str,
                         **kwargs) -> Milestone: ...
    def remove_milestone(self, portfolio_name: str, milestone_name: str) -> bool: ...

    def add_task_to_milestone(self, portfolio_name: str, milestone_name: str,
                              task_id: int, critical: bool = False) -> Milestone: ...
    def remove_task_from_milestone(self, portfolio_name: str, milestone_name: str,
                                   task_id: int) -> Milestone: ...
```

**File format:** Version 1 schema as defined in the Metadata Conventions section above.

**Done when:**
- All CRUD methods implemented and tested
- File created automatically on first write (parent dirs via `Path.mkdir(parents=True, exist_ok=True)`)
- Atomic write (write to temp file, then rename) to prevent corruption
- Raises `KanboardConfigError` on malformed JSON or schema version mismatch
- Unit tests in `tests/unit/orchestration/test_store.py` using `tmp_path` fixture (no real filesystem)
- ≥95% coverage on `store.py`
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Use `json` stdlib for serialization. No external dependencies.
- `datetime` fields serialized as ISO-8601 strings, deserialized with `datetime.fromisoformat()`.
- Portfolio names are case-sensitive and unique. Raise `ValueError` on duplicate create.
- Milestone names are unique within a portfolio.
- Default path uses `kanboard.config.CONFIG_DIR` constant for consistency.

---

### Task 52: Portfolio manager — multi-project aggregation

- [ ] **Priority:** P0 — all portfolio CLI commands and dependency analysis depend on this
- **Complexity:** L
- **Dependencies:** Tasks 49, 50, 51

Implement `src/kanboard/orchestration/portfolio.py`:

```python
class PortfolioManager:
    """Orchestrates cross-project operations using the Kanboard API.

    Composes KanboardClient resource calls to aggregate data across
    multiple projects within a portfolio.
    """

    def __init__(self, client: KanboardClient, store: LocalPortfolioStore) -> None: ...

    # --- Portfolio queries ---
    def get_portfolio_projects(self, portfolio_name: str) -> list[Project]: ...
    def get_portfolio_tasks(self, portfolio_name: str,
                            status: int = 1,
                            assignee_id: int | None = None,
                            project_id: int | None = None) -> list[Task]: ...

    # --- Milestone progress ---
    def get_milestone_progress(self, portfolio_name: str,
                               milestone_name: str) -> MilestoneProgress: ...
    def get_all_milestone_progress(self, portfolio_name: str) -> list[MilestoneProgress]: ...

    # --- Sync ---
    def sync_metadata(self, portfolio_name: str) -> dict[str, int]: ...
        """Push portfolio/milestone membership to Kanboard metadata.

        Returns dict with counts: {"projects_synced", "tasks_synced"}.
        """
```

**Aggregation strategy:**
1. `get_portfolio_tasks` iterates portfolio project IDs, calls `client.tasks.get_all_tasks(project_id, status)` for each, optionally filters by assignee.
2. `get_milestone_progress` fetches each task in the milestone via `client.tasks.get_task(task_id)`, counts closed vs. total, computes percent. Checks for overdue (target_date < now and not 100%). At-risk defined as: target_date within 7 days and percent < 80%.
3. `sync_metadata` writes `kanboard_cli:portfolio` to each project's metadata and `kanboard_cli:milestones` to each task's metadata.

**Done when:**
- All methods implemented
- Handles missing projects/tasks gracefully (project deleted from Kanboard but still in portfolio → logged warning, skipped)
- Unit tests in `tests/unit/orchestration/test_portfolio.py` mocking `KanboardClient` with `pytest-httpx`
- ≥90% coverage on `portfolio.py`
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Accept that this is N+1 API calls by design. Phase 1 plugin will solve this server-side. For Phase 0, this is the pragmatic trade-off documented in ADR-17.
- Use `client.tasks.get_all_tasks(project_id, status_id=1)` to fetch active tasks. The `status_id` parameter is required (not optional) per the Kanboard API.
- For progress calculation: a task is "completed" if `is_active == 0` (closed). Use `_int(task_data.get("is_active"))` to check.
- `Project` and `Task` models already exist in `models.py` — reuse them.

---

### Task 53: Dependency analyzer — graph traversal and critical path

- [ ] **Priority:** P0 — dependency CLI commands depend on this
- **Complexity:** L
- **Dependencies:** Tasks 49, 50, 52

Implement `src/kanboard/orchestration/dependencies.py`:

```python
class DependencyAnalyzer:
    """Analyzes task dependency graphs across projects in a portfolio.

    Uses existing Kanboard internal task links (blocks/is blocked by)
    to build and traverse a directed dependency graph.
    """

    def __init__(self, client: KanboardClient) -> None: ...

    def get_dependency_edges(self, tasks: list[Task],
                             cross_project_only: bool = False) -> list[DependencyEdge]: ...
        """Build the list of dependency edges for the given tasks.

        Fetches all task links for each task, filters to "blocks"/"is blocked by"
        relationships, enriches with project names, and returns DependencyEdge list.
        """

    def get_blocked_tasks(self, tasks: list[Task]) -> list[tuple[Task, list[DependencyEdge]]]: ...
        """Return tasks that have unresolved (open) blockers."""

    def get_blocking_tasks(self, tasks: list[Task]) -> list[tuple[Task, list[DependencyEdge]]]: ...
        """Return open tasks that are blocking other tasks."""

    def get_critical_path(self, tasks: list[Task]) -> list[Task]: ...
        """Compute the critical path — the longest dependency chain.

        Uses topological sort on the dependency graph and finds the
        longest path through unresolved dependencies.
        """

    def get_dependency_graph(self, tasks: list[Task],
                             cross_project_only: bool = False) -> dict: ...
        """Return a graph structure suitable for rendering.

        Returns: {"nodes": [...], "edges": [...]} where nodes are tasks
        and edges are DependencyEdge dicts.
        """
```

**Algorithm notes:**
- Build adjacency list from task links: for each task, call `client.task_links.get_all_task_links(task_id)`, filter to link IDs 2 and 3 ("blocks" and "is blocked by").
- Critical path: topological sort (Kahn's algorithm), then longest-path on the DAG. If cycles detected (shouldn't happen with blocks/blocked-by, but defensive), log warning and return partial result.
- Cross-project filter: include edge only if `task.project_id != opposite_task.project_id`.
- Task enrichment: need to fetch each linked task to get its title, project_id, and status. Cache fetched tasks in a `dict[int, Task]` to avoid redundant API calls.

**Done when:**
- All methods implemented
- Critical path algorithm correct for: linear chain, diamond dependency, multiple independent chains, empty graph, single task with no deps
- Unit tests in `tests/unit/orchestration/test_dependencies.py` — mock `KanboardClient` with pre-built task/link fixtures
- ≥90% coverage on `dependencies.py`
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- The "blocks" link type has `link_id=2`; "is blocked by" has `link_id=3`. Fetch link types once via `client.links.get_all_links()` and cache. Don't hardcode IDs — look up by label for robustness.
- `getAllTaskLinks` returns links from the perspective of the queried task. If task A blocks task B and you query task A's links, you get `{link_id: 2, opposite_task_id: B}`. If you query task B's links, you get `{link_id: 3, opposite_task_id: A}`. Deduplicate edges accordingly.
- For the critical path, only consider unresolved (open) tasks. Closed tasks are "done" edges in the graph.

---

### Task 54: ASCII dependency graph renderer

- [ ] **Priority:** P1 — enhances CLI output but not blocking for core functionality
- **Complexity:** M
- **Dependencies:** Task 53

Implement dependency graph rendering for the CLI in `src/kanboard_cli/renderers.py`:

```python
def render_dependency_graph(edges: list[DependencyEdge],
                            nodes: list[Task],
                            cross_project_only: bool = False,
                            use_color: bool = True) -> str:
    """Render a text-based dependency graph.

    Groups nodes by project, shows blocking arrows between them,
    and uses ANSI colors for status (green=resolved, red=blocked, yellow=open).
    """

def render_critical_path(tasks: list[Task], edges: list[DependencyEdge]) -> str:
    """Render the critical path as a numbered sequential list."""

def render_milestone_progress(progress: MilestoneProgress,
                               use_color: bool = True) -> str:
    """Render a single milestone progress bar.

    Example: ████████░░ v2.0 Feature Complete (72%) - Target: Jun 01
    """

def render_portfolio_summary(portfolio: Portfolio,
                              milestones: list[MilestoneProgress],
                              task_count: int,
                              blocked_count: int) -> str:
    """Render the portfolio dashboard summary."""
```

**Done when:**
- All four renderers produce readable, well-formatted output
- Color support can be disabled (for piping, CI, quiet mode)
- Progress bars use Unicode block characters (`█`, `░`)
- Unit tests verify output structure (not exact character-by-character — test for key strings and formatting patterns)
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Use `rich.console.Console` for colored output (consistent with existing CLI).
- The dependency graph renderer doesn't need to be a full graph layout engine — a simple text list grouped by project with arrow annotations is sufficient for Phase 0. Example:

```
Product A
  #15 Finalize branding       ⬤ OPEN      ── blocks ──> #42 (Site Project)
  #22 API v2                   ✅ DONE      ── blocks ──> #55 (Site Project)

Product B
  #67 Feature integration      ⬤ OPEN      ── blocks ──> #88 (Site Project)

Site Project
  #42 Publish product page     🔴 BLOCKED   ◄── blocked by #15 (Product A)
  #55 Landing page             ⬤ READY      (dependency resolved)
  #88 Blog post sequence       🔴 BLOCKED   ◄── blocked by #67 (Product B)
```

- Progress bar width: 20 characters. Fill = `round(percent / 5)` blocks.
- At-risk indicator: `⚠️` prefix. Overdue: `🔴 OVERDUE` suffix.

---

### Task 55: Portfolio CLI command group — CRUD

- [ ] **Priority:** P0 — primary user interface for portfolio management
- **Complexity:** L
- **Dependencies:** Tasks 51, 52

Create `src/kanboard_cli/commands/portfolio.py`:

```
kanboard portfolio list                                    # List all portfolios
kanboard portfolio show <name>                             # Portfolio overview + milestones
kanboard portfolio create <name> [--description TEXT]      # Create portfolio
kanboard portfolio remove <name> --yes                     # Remove portfolio (destructive)
kanboard portfolio add-project <name> <project_id>         # Add project to portfolio
kanboard portfolio remove-project <name> <project_id> --yes  # Remove project
kanboard portfolio tasks <name> [--status active|closed]   # Unified task list
    [--project PROJECT_ID] [--assignee USER_ID]
kanboard portfolio sync <name>                             # Sync metadata to Kanboard
```

**Subcommand details:**

| Command | Action | Output |
|---------|--------|--------|
| `list` | Read local store, display all portfolios | Table: name, description, project count, milestone count |
| `show` | Read store + fetch live data from API | Dashboard: portfolio summary + milestone progress bars + at-risk items |
| `create` | Create in local store | Success message with name |
| `remove` | Remove from local store + clean metadata (best-effort) | Success message. Requires `--yes`. |
| `add-project` | Add project ID to portfolio in local store. Validates project exists via API. | Success message. |
| `remove-project` | Remove project from portfolio. Requires `--yes`. | Success message. |
| `tasks` | Aggregate tasks via `PortfolioManager.get_portfolio_tasks()` | Table: id, title, project_name, column_title, assignee, due_date, priority. All 4 output formats. |
| `sync` | Push metadata to Kanboard | Summary: "Synced 3 projects, 12 tasks" |

**Done when:**
- All 8 subcommands implemented
- `portfolio show` displays milestone progress bars and at-risk items using renderers from Task 54
- `portfolio tasks` supports all 4 output formats (table, json, csv, quiet)
- `portfolio remove` and `remove-project` require `--yes` flag
- Helpful error messages when portfolio not found, project doesn't exist, etc.
- CLI tests in `tests/cli/test_portfolio.py` using `CliRunner` — test all subcommands with mocked client
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Register in `src/kanboard_cli/main.py`: `cli.add_command(portfolio)`.
- `portfolio show` combines local store data with live API data. If API is unreachable, show cached data with a warning.
- `portfolio tasks` output table should include a `project` column showing the project name (not ID) — requires fetching project details. Cache project lookups for the portfolio.
- `portfolio create` takes `name` as a positional argument (Click `@click.argument`), not `--name`.
- Validate that `project_id` exists by calling `client.projects.get_project_by_id(project_id)` before adding.

---

### Task 56: Milestone CLI command group

- [ ] **Priority:** P0 — primary interface for milestone management
- **Complexity:** M
- **Dependencies:** Tasks 51, 52, 55

Create `src/kanboard_cli/commands/milestone.py`:

```
kanboard milestone list <portfolio_name>                   # List milestones in portfolio
kanboard milestone show <portfolio_name> <milestone_name>  # Milestone detail + task list
kanboard milestone create <portfolio_name> <milestone_name>  # Create milestone
    [--target-date YYYY-MM-DD] [--description TEXT]
kanboard milestone remove <portfolio_name> <milestone_name> --yes
kanboard milestone add-task <portfolio_name> <milestone_name> <task_id>
    [--critical]
kanboard milestone remove-task <portfolio_name> <milestone_name> <task_id> --yes
kanboard milestone progress <portfolio_name> [<milestone_name>]  # Progress report
```

**Subcommand details:**

| Command | Action | Output |
|---------|--------|--------|
| `list` | List milestones in portfolio from local store | Table: name, target_date, task_count, critical_count |
| `show` | Fetch live task data, compute progress | Detail: progress bar, task list with status, blockers |
| `create` | Add milestone to portfolio in local store | Success message |
| `remove` | Remove milestone + clean task metadata | Success message. Requires `--yes`. |
| `add-task` | Add task ID to milestone. Validates task exists and belongs to a portfolio project. | Success message. `--critical` marks as critical path. |
| `remove-task` | Remove task from milestone. Requires `--yes`. | Success message. |
| `progress` | Compute and display milestone progress | If milestone specified: single progress detail. If omitted: all milestones in portfolio. |

**Done when:**
- All 7 subcommands implemented
- `milestone show` displays task list with status indicators and blocking info
- `milestone progress` renders progress bars (single or all)
- `milestone remove` and `remove-task` require `--yes` flag
- CLI tests in `tests/cli/test_milestone.py`
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Register in `main.py`: `cli.add_command(milestone)`.
- `add-task` validation: fetch the task via API, verify `task.project_id` is in the portfolio's project list. Error if not.
- `progress` uses `PortfolioManager.get_milestone_progress()` or `get_all_milestone_progress()`.
- Date parsing: accept `YYYY-MM-DD` format, convert to `datetime` on store.

---

### Task 57: Dependency CLI commands

- [ ] **Priority:** P0 — primary interface for cross-project dependency visibility
- **Complexity:** M
- **Dependencies:** Tasks 53, 54, 55

Add dependency subcommands to the `portfolio` command group (not a separate top-level group):

```
kanboard portfolio dependencies <name>                     # Show dependency graph
    [--cross-project-only] [--format graph|table|json]
kanboard portfolio blocked <name>                          # List blocked tasks
kanboard portfolio blocking <name>                         # List blocking tasks
kanboard portfolio critical-path <name>                    # Show critical path
```

**Subcommand details:**

| Command | Action | Output |
|---------|--------|--------|
| `dependencies` | Build full dependency graph for portfolio | `graph`: ASCII graph (default). `table`: flat table of edges. `json`: structured JSON. |
| `blocked` | List tasks with unresolved cross-project blockers | Table: task_id, title, project, blocked_by_task, blocked_by_project. All 4 output formats. |
| `blocking` | List open tasks that block tasks in other projects | Table: task_id, title, project, blocks_task, blocks_project. All 4 output formats. |
| `critical-path` | Compute and display the longest dependency chain | Numbered list with estimated sequence and bottleneck identification. |

**Done when:**
- All 4 subcommands implemented
- `dependencies` defaults to ASCII graph view, supports `--format` override
- `blocked` and `blocking` support all 4 output formats
- `critical-path` identifies and highlights the bottleneck task
- CLI tests in `tests/cli/test_portfolio.py` (extend existing file)
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- `dependencies` fetches all tasks in portfolio via `PortfolioManager.get_portfolio_tasks()`, then passes to `DependencyAnalyzer.get_dependency_edges()`.
- `--cross-project-only` is a common filter — default False for `dependencies`, implicit True for `blocked`/`blocking`.
- `critical-path` output should identify the bottleneck: the single task whose completion would unblock the most downstream tasks.

---

### Task 58: Unit tests — orchestration modules

- [ ] **Priority:** P0 — quality gate
- **Complexity:** L
- **Dependencies:** Tasks 51, 52, 53

Create comprehensive unit tests for all orchestration modules:

```
tests/unit/orchestration/
├── __init__.py
├── conftest.py              # Shared fixtures: mock client, sample portfolios
├── test_store.py            # LocalPortfolioStore tests
├── test_portfolio.py        # PortfolioManager tests
└── test_dependencies.py     # DependencyAnalyzer tests
```

**Coverage targets:**

| Module | Target | Key scenarios |
|--------|--------|---------------|
| `store.py` | ≥95% | Create/read/update/delete portfolios, milestones, tasks. Atomic write. Schema validation. Missing file. Duplicate names. |
| `portfolio.py` | ≥90% | Multi-project task aggregation. Milestone progress computation (0%, 50%, 100%). At-risk/overdue detection. Missing projects. API errors. Sync metadata. |
| `dependencies.py` | ≥90% | Linear chain. Diamond graph. No dependencies. Cross-project filter. Critical path (single chain, parallel chains, empty). Cycle detection. Resolved vs unresolved edges. |

**Test fixtures (in `conftest.py`):**
- `sample_portfolio` — Portfolio with 3 projects, 2 milestones
- `mock_tasks` — 10 tasks across 3 projects with various statuses
- `mock_task_links` — Cross-project blocking relationships forming a known graph
- `mock_link_types` — Standard Kanboard link types (blocks, is blocked by, etc.)

**Done when:**
- All test files created with comprehensive test cases
- `pytest tests/unit/orchestration/ -v` passes
- Coverage meets targets
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Mock `KanboardClient` at the httpx level using `pytest-httpx` (consistent with existing test patterns).
- For `test_dependencies.py`, construct specific graph topologies as test fixtures and verify critical path output matches expected sequences.
- For `test_store.py`, use `tmp_path` pytest fixture to create isolated temp directories — don't touch real `~/.config/kanboard/`.
- For `test_portfolio.py`, mock the client to return pre-defined tasks/projects — verify aggregation and progress computation logic.

---

### Task 59: CLI tests — portfolio and milestone commands

- [ ] **Priority:** P0 — quality gate
- **Complexity:** L
- **Dependencies:** Tasks 55, 56, 57

Create CLI output tests for all portfolio and milestone commands:

```
tests/cli/
├── test_portfolio.py        # Portfolio command tests
└── test_milestone.py        # Milestone command tests
```

**Test coverage:**
- Every subcommand tested with `CliRunner`
- All 4 output formats tested for list/table commands (table, json, csv, quiet)
- Error cases: portfolio not found, project doesn't exist, milestone not found
- Destructive commands: verify `--yes` is required, verify rejection without it
- `portfolio show` — verify milestone progress bars appear in output
- `portfolio dependencies` — verify graph output contains expected task references
- `portfolio blocked` — verify blocked task listing

**Done when:**
- All CLI commands have at least 2 tests each (success + error case)
- List commands tested with all 4 output formats
- `pytest tests/cli/test_portfolio.py tests/cli/test_milestone.py -v` passes
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- Mock the `KanboardClient` at the `AppContext` level (same pattern as existing CLI tests).
- For `portfolio show`, mock both the local store and the API client.
- Use `CliRunner(mix_stderr=False)` to separate stdout and stderr for assertion.
- Test that `--yes` flag is respected on destructive commands by invoking without it and checking for the abort/error.

---

### Task 60: Integration with existing `task-link` commands

- [ ] **Priority:** P1 — convenience enhancement
- **Complexity:** S
- **Dependencies:** Tasks 52, 53

Enhance the existing `task-link create` command to optionally display cross-project context:

1. After creating a task link, if the two tasks belong to different projects, print an informational message:
   ```
   ✓ Task link created (ID: 5)
   ℹ Cross-project dependency: Task #42 (Site Project) is blocked by Task #15 (Product A)
   ```

2. Add a new `task-link list` enhancement: `--with-project` flag that enriches each link with the opposite task's project name (requires additional API call per link).

**Done when:**
- `task-link create` shows cross-project info when applicable
- `task-link list --with-project` adds `opposite_project` column
- Existing tests still pass (backward-compatible change)
- New tests for the enhancements
- `ruff check . && ruff format --check . && pytest` passes

**Implementation notes:**
- The cross-project detection requires fetching both tasks to compare `project_id` values. Only do this when the link is successfully created (don't add latency to the error path).
- The `--with-project` flag on `list` makes additional API calls — document that it's slower for tasks with many links.

---

### Task 61: Export orchestration `__init__.py` and wire CLI

- [ ] **Priority:** P0 — final integration
- **Complexity:** S
- **Dependencies:** Tasks 55, 56, 57

Final wiring:

1. Update `src/kanboard/__init__.py` to export orchestration classes:
   ```python
   from kanboard.orchestration import PortfolioManager, DependencyAnalyzer, LocalPortfolioStore
   ```

2. Update `src/kanboard_cli/main.py` to register portfolio and milestone commands:
   ```python
   from kanboard_cli.commands.portfolio import portfolio
   from kanboard_cli.commands.milestone import milestone

   cli.add_command(portfolio)
   cli.add_command(milestone)
   ```

3. Verify end-to-end: `kanboard portfolio --help` and `kanboard milestone --help` produce correct help text.

4. Run full test suite: `ruff check . && ruff format --check . && pytest`

**Done when:**
- `kanboard portfolio --help` shows all subcommands
- `kanboard milestone --help` shows all subcommands
- `from kanboard import PortfolioManager, DependencyAnalyzer` works
- Full test suite passes
- `ruff check . && ruff format --check . && pytest` passes

---

### Task 62: Documentation updates

- [ ] **Priority:** P1 — required before merge/release
- **Complexity:** M
- **Dependencies:** All previous Phase 0 tasks (49–61)

#### ⚠️ PRE-FLIGHT CHECK

> **Before starting this task, the project owner MUST provide the URL for the
> Kanboard Portfolio plugin** (the server-side PHP plugin that provides
> visualization/aggregation features described in the design spec's Phase 1+).
>
> **Action required:** Confirm the plugin URL is provided and set it as
> `PORTFOLIO_PLUGIN_URL` in the instructions below. If the URL is not yet
> available, this task MUST be deferred — do NOT write placeholder URLs or
> leave TODO markers in published documentation.
>
> **How to verify:** The implementer must ask the project owner for the plugin
> URL before writing any documentation content. The URL must:
> - Be a valid, accessible URL (GitHub repo, plugin page, etc.)
> - Point to the actual Kanboard Portfolio plugin (not a placeholder)
> - Be confirmed by the project owner as the canonical reference

Once the plugin URL (`PORTFOLIO_PLUGIN_URL`) is confirmed, update the following files:

#### 1. `README.md`

Add a new section **after** "Key Features" and **before** "Prerequisites":

```markdown
## Cross-Project Orchestration

kanboard-cli includes built-in **cross-project orchestration** — the ability to
manage portfolios of related Kanboard projects, track milestones that span
projects, analyze cross-project task dependencies, and identify critical paths
across your entire program.

This is implemented as a **CLI-side meta-construct** that composes existing
Kanboard API capabilities (internal task links, metadata) into higher-level
portfolio management features. No server-side modifications are required for
core functionality.

### What's included in the CLI

- **Portfolio management** — group projects into named portfolios
- **Cross-project milestones** — define milestones spanning multiple projects
  with target dates and progress tracking
- **Dependency analysis** — visualize cross-project task dependencies, identify
  blocked tasks, and compute critical paths
- **Unified task views** — list and filter tasks across all projects in a
  portfolio from a single command

### Server-side visualization (optional)

For in-browser Kanboard UI features — including interactive dependency graphs,
multi-project Gantt timelines, portfolio dashboards, and board-level blocking
indicators — see the companion **[Kanboard Portfolio plugin](PORTFOLIO_PLUGIN_URL)**.

The CLI's `portfolio` and `milestone` commands work independently of the plugin,
but the plugin provides the visual layer within Kanboard's web interface.
```

Also add `portfolio` and `milestone` to the CLI command examples section.

#### 2. `docs/cli-reference.md`

Add two new command group sections:

- **`portfolio`** — with all subcommands documented: `list`, `show`, `create`,
  `remove`, `add-project`, `remove-project`, `tasks`, `sync`, `dependencies`,
  `blocked`, `blocking`, `critical-path`
- **`milestone`** — with all subcommands: `list`, `show`, `create`, `remove`,
  `add-task`, `remove-task`, `progress`

Include usage examples for the most common workflows:
- Creating a portfolio and adding projects
- Creating milestones and adding tasks
- Viewing cross-project dependencies
- Checking blocked tasks and critical path

#### 3. `docs/sdk-guide.md`

Add a new section **"Cross-Project Orchestration"** covering:

- `PortfolioManager` usage
- `DependencyAnalyzer` usage
- `LocalPortfolioStore` usage
- Example: creating a portfolio, adding projects, computing milestone progress
- Example: analyzing cross-project dependencies and critical path
- Note explaining the relationship to the Kanboard Portfolio plugin:

```markdown
> **Note:** The orchestration classes work with standard Kanboard instances —
> no server-side plugin is required. For additional server-side features
> (UI dashboards, dependency graphs, board indicators), see the
> [Kanboard Portfolio plugin](PORTFOLIO_PLUGIN_URL).
```

#### 4. `CLAUDE.md`

Update with:
- New architecture section mentioning `src/kanboard/orchestration/` subpackage
- Note that orchestration modules are NOT resources (composed, not 1:1 with API)
- Portfolio store path: `~/.config/kanboard/portfolios.json`
- Metadata key prefix convention: `kanboard_cli:`
- Reference to `docs/design/cross-project-orchestration.md`

#### 5. `AGENTS.md`

Update:
- Add `orchestration/` to the Directory Structure section
- Add `docs/tasks/` and `docs/design/` to the Key References section
- Note convention that orchestration tests live in `tests/unit/orchestration/`

#### 6. `docs/design/cross-project-orchestration.md`

Update the Phase 0 section to mark it as "in progress" or "complete" (depending on status), and add a link to the plugin URL in the Phase 1 section:

```markdown
> **Kanboard Portfolio Plugin:** [PORTFOLIO_PLUGIN_URL](PORTFOLIO_PLUGIN_URL)
```

**Done when:**
- All 6 files updated with accurate, non-placeholder content
- Plugin URL appears correctly in all locations (README, sdk-guide, design doc)
- No TODO markers or placeholder URLs remain in any documentation
- Documentation accurately describes what the CLI provides vs. what requires the plugin
- `ruff check . && ruff format --check . && pytest` passes (docs don't break anything)

**Implementation notes:**
- The distinction between "CLI meta-construct" and "plugin-provided features" must be crystal clear in all documentation. Users should understand that:
  1. The CLI's portfolio/milestone commands work with any Kanboard instance
  2. Cross-project task links are a built-in Kanboard feature (not ours)
  3. The CLI adds the orchestration/aggregation/analysis layer
  4. The Kanboard Portfolio plugin adds server-side UI features (dashboards, graphs, board indicators)
- Do NOT overstate what the CLI provides — it does not modify the Kanboard UI, it does not add board indicators, it does not provide Gantt charts. Those are plugin features.
- Use consistent terminology: "cross-project orchestration" for the overall capability, "portfolio" for the grouping concept, "milestone" for cross-project milestones, "dependency analysis" for the graph/critical-path features.

---

## Dependency Graph

```
Task 49 (scaffolding)
  ├──> Task 50 (models)
  │      ├──> Task 51 (store)
  │      │      ├──> Task 52 (portfolio manager)
  │      │      │      ├──> Task 55 (portfolio CLI)
  │      │      │      │      ├──> Task 57 (dependency CLI)
  │      │      │      │      ├──> Task 59 (CLI tests)
  │      │      │      │      └──> Task 61 (wiring)
  │      │      │      ├──> Task 56 (milestone CLI)
  │      │      │      │      ├──> Task 59 (CLI tests)
  │      │      │      │      └──> Task 61 (wiring)
  │      │      │      └──> Task 58 (unit tests)
  │      │      └──> Task 58 (unit tests)
  │      └──> Task 53 (dependency analyzer)
  │             ├──> Task 54 (ASCII renderer)
  │             │      └──> Task 57 (dependency CLI)
  │             ├──> Task 57 (dependency CLI)
  │             └──> Task 58 (unit tests)
  └──> Task 60 (task-link enhancements)

Task 61 (wiring) ──> Task 62 (documentation)
```

## Implementation Order (Suggested)

1. **Tasks 49–50** — Scaffolding and models (foundation)
2. **Task 51** — Local store (enables all CRUD)
3. **Tasks 52–53** — Portfolio manager + dependency analyzer (core logic, parallelizable)
4. **Task 54** — ASCII renderers (needed by CLI)
5. **Tasks 55–57** — CLI commands (portfolio, milestone, dependencies — parallelizable)
6. **Task 58** — Unit tests (can start alongside 52–57)
7. **Task 59** — CLI tests (after CLI commands complete)
8. **Task 60** — Task-link enhancements (independent, can be done anytime after 53)
9. **Task 61** — Final wiring and integration verification
10. **Task 62** — Documentation (last — requires plugin URL pre-flight)
