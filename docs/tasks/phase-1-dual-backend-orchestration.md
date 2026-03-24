# Phase 1: Dual-Backend Orchestration — Plugin API Integration (Tasks 63–78)

> ← [Phase 0](phase-0-cross-project-orchestration.md) | [Design Spec](../design/cross-project-orchestration.md) →
>
> Extends the portfolio and milestone system to support **two interchangeable
> backends** — the existing local-file store and a new Kanboard Plugin API
> backend — selectable via configuration. Introduces SDK resource modules for
> the [Kanboard Portfolio Plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management)'s
> 28 JSON-RPC endpoints, a backend abstraction layer, configuration-driven
> backend selection, and bidirectional migration tooling.
>
> **Pre-requisite reading:**
> - [docs/design/cross-project-orchestration.md](../design/cross-project-orchestration.md) — §3.3 (plugin API), §3.4 (CLI/SDK integration), §3.5 (Phase 1 roadmap)
> - [docs/tasks/phase-0-cross-project-orchestration.md](phase-0-cross-project-orchestration.md) — the local-file backend being preserved
> - [Kanboard Portfolio Plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management) — `Plugin.php` for full API surface

---

## Overview

| Metric | Value |
|---|---|
| **Total tasks** | 16 (Tasks 63–78) |
| **Estimated effort** | 2–3 weeks |
| **New SDK resource modules** | 2 (`resources/portfolios.py`, `resources/milestones.py`) |
| **New abstraction layer** | 1 (`orchestration/backend.py`) |
| **New CLI subcommand** | `kanboard portfolio migrate` (4 sub-operations) |
| **Plugin API methods to wrap** | 28 across 6 categories |
| **Backward compatibility** | Full — local backend remains the default; no existing behavior changes |
| **Plugin dependency** | Backend B requires [kanboard-plugin-portfolio-management](https://github.com/geekmuse/kanboard-plugin-portfolio-management) installed on the Kanboard server |

---

## Motivation

Phase 0 delivered a working portfolio/milestone system using local JSON storage
and Kanboard metadata as a persistence layer. This works well for single-user
CLI workflows, but has inherent limitations:

1. **No server-side persistence** — portfolio definitions exist only on the
   user's machine; other Kanboard users cannot see them.
2. **N+1 API overhead** — aggregation requires fetching each project and task
   individually because the local store has no server-side query capability.
3. **No referential integrity** — if a project or task is deleted in Kanboard,
   the local store holds stale references until the next manual sync.
4. **No Kanboard UI integration** — the portfolio/milestone concepts are
   invisible in the web interface.

The [Kanboard Portfolio Plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management)
solves all four by adding server-side database tables, 28 JSON-RPC endpoints,
and web UI views. This phase integrates the CLI with that plugin while
**preserving the local backend as the default** for users without the plugin.

---

## Architecture Decisions

| # | Decision | Rationale |
|---|---|---|
| ADR-21 | **Backend abstraction via protocol class** (`PortfolioBackend`) in `orchestration/backend.py` | Allows `PortfolioManager` and CLI commands to operate identically regardless of storage backend. Uses `typing.Protocol` (structural subtyping) — no ABC inheritance required of backends. |
| ADR-22 | **`local` backend is the default** — `portfolio_backend = "local"` when unspecified | Zero-breaking-change guarantee for existing users. Plugin backend is opt-in. |
| ADR-23 | **Backend selection via existing layered config** (TOML profile → env → CLI flag) | Consistent with ADR-06. Adds one new config key (`portfolio_backend`) and one new CLI flag (`--portfolio-backend`) to the existing resolution chain. |
| ADR-24 | **Plugin detection via `getPortfolio` probe** — not `getVersion` string parsing | Calling a plugin-specific method is authoritative (method-not-found error = plugin absent). Version parsing is fragile. |
| ADR-25 | **SDK resource modules for plugin API live in `resources/`**, not `orchestration/` | Plugin API endpoints are 1:1 JSON-RPC method wrappers — same pattern as all other resource modules. Orchestration modules compose higher-level logic on top. |
| ADR-26 | **Migration is a dedicated `portfolio migrate` subcommand** | Bidirectional data transfer is a distinct, infrequent operation that warrants its own command with `--dry-run`, progress reporting, and conflict-resolution flags — not implicit backend-switching behavior. |
| ADR-27 | **Bidirectional migration: local→remote and remote→local** | Users may move to the plugin, or may need to extract data from a shared Kanboard into local development. Both directions must be supported. |

---

## Backend Abstraction Design

### Protocol Class

```python
# src/kanboard/orchestration/backend.py

from typing import Protocol

class PortfolioBackend(Protocol):
    """Structural interface for portfolio/milestone storage backends."""

    # Portfolio CRUD
    def list_portfolios(self) -> list[Portfolio]: ...
    def get_portfolio(self, name: str) -> Portfolio: ...
    def create_portfolio(self, name: str, description: str = "",
                         project_ids: list[int] | None = None) -> Portfolio: ...
    def update_portfolio(self, name: str, **kwargs) -> Portfolio: ...
    def remove_portfolio(self, name: str) -> bool: ...

    # Project membership
    def add_project(self, portfolio_name: str, project_id: int) -> Portfolio: ...
    def remove_project(self, portfolio_name: str, project_id: int) -> Portfolio: ...

    # Milestone CRUD
    def add_milestone(self, portfolio_name: str, milestone_name: str,
                      target_date: datetime | None = None) -> Milestone: ...
    def update_milestone(self, portfolio_name: str, milestone_name: str,
                         **kwargs) -> Milestone: ...
    def remove_milestone(self, portfolio_name: str, milestone_name: str) -> bool: ...

    # Task membership
    def add_task_to_milestone(self, portfolio_name: str, milestone_name: str,
                              task_id: int, critical: bool = False) -> Milestone: ...
    def remove_task_from_milestone(self, portfolio_name: str, milestone_name: str,
                                   task_id: int) -> Milestone: ...
```

### Backend Implementations

| Method | `LocalPortfolioStore` (Backend A) | `RemotePortfolioBackend` (Backend B) |
|---|---|---|
| `list_portfolios` | Read `portfolios.json` | `getAllPortfolios()` |
| `get_portfolio` | Lookup by name in JSON | `getPortfolioByName(name)` |
| `create_portfolio` | Append to JSON, atomic write | `createPortfolio(name, description)` + `addProjectToPortfolio()` per project |
| `update_portfolio` | Mutate in-memory, write JSON | `updatePortfolio(portfolio_id, ...)` |
| `remove_portfolio` | Filter from JSON, write | `removePortfolio(portfolio_id)` |
| `add_project` | Append to `project_ids`, write | `addProjectToPortfolio(portfolio_id, project_id)` |
| `remove_project` | Filter from `project_ids`, write | `removeProjectFromPortfolio(portfolio_id, project_id)` |
| `add_milestone` | Append to portfolio's milestones | `createMilestone(portfolio_id, name, ...)` |
| `update_milestone` | Mutate in-memory, write | `updateMilestone(milestone_id, ...)` |
| `remove_milestone` | Filter from milestones, write | `removeMilestone(milestone_id)` |
| `add_task_to_milestone` | Append to `task_ids` / `critical_task_ids` | `addTaskToMilestone(milestone_id, task_id, is_critical)` |
| `remove_task_from_milestone` | Filter from `task_ids` | `removeTaskFromMilestone(milestone_id, task_id)` |

### Backend Factory

```python
# src/kanboard/orchestration/backend.py

def create_backend(backend_type: str, client: KanboardClient | None = None,
                   store_path: Path | None = None) -> PortfolioBackend:
    """Create a backend instance based on the configured type.

    Args:
        backend_type: ``"local"`` or ``"remote"``.
        client: Required for ``"remote"`` backend.
        store_path: Optional override for local store file path.

    Raises:
        KanboardConfigError: On invalid backend_type or missing client.
    """
```

---

## Plugin API Mapping

### API Categories and SDK Resource Methods

The plugin exposes 28 JSON-RPC methods. Two new SDK resource modules will wrap them following the established resource pattern (`_client.call("methodName", ...)`, typed returns, standard exception handling).

#### `PortfoliosResource` — `src/kanboard/resources/portfolios.py` (13 methods)

| Plugin API Method | SDK Method | Params | Returns |
|---|---|---|---|
| `createPortfolio` | `create_portfolio(name, **kwargs)` | `name` (str, **req**), `description` (str, opt), `owner_id` (int, opt) | `int` portfolio_id or raise `KanboardAPIError` |
| `getPortfolio` | `get_portfolio(portfolio_id)` | `portfolio_id` (int, **req**) | `PluginPortfolio` or raise `KanboardNotFoundError` |
| `getPortfolioByName` | `get_portfolio_by_name(name)` | `name` (str, **req**) | `PluginPortfolio` or raise `KanboardNotFoundError` |
| `getAllPortfolios` | `get_all_portfolios()` | none | `list[PluginPortfolio]` |
| `updatePortfolio` | `update_portfolio(portfolio_id, **kwargs)` | `portfolio_id` (int, **req**), `name`/`description`/`owner_id`/`is_active` (opt) | `bool` or raise `KanboardAPIError` |
| `removePortfolio` | `remove_portfolio(portfolio_id)` | `portfolio_id` (int, **req**) | `bool` |
| `addProjectToPortfolio` | `add_project_to_portfolio(portfolio_id, project_id, **kwargs)` | `portfolio_id` (int, **req**), `project_id` (int, **req**), `position` (int, opt) | `bool` or raise `KanboardAPIError` |
| `removeProjectFromPortfolio` | `remove_project_from_portfolio(portfolio_id, project_id)` | `portfolio_id` (int, **req**), `project_id` (int, **req**) | `bool` |
| `getPortfolioProjects` | `get_portfolio_projects(portfolio_id)` | `portfolio_id` (int, **req**) | `list[dict]` (project data with position) |
| `getProjectPortfolios` | `get_project_portfolios(project_id)` | `project_id` (int, **req**) | `list[PluginPortfolio]` |
| `getPortfolioTasks` | `get_portfolio_tasks(portfolio_id, **kwargs)` | `portfolio_id` (int, **req**), `status_id`/`assignee_id`/`project_id`/`milestone_id`/`sort`/`direction`/`limit`/`offset` (opt) | `list[dict]` (enriched task data) |
| `getPortfolioTaskCount` | `get_portfolio_task_count(portfolio_id, **kwargs)` | `portfolio_id` (int, **req**), `status_id` (int, opt) | `dict` with count data |
| `getPortfolioOverview` | `get_portfolio_overview(portfolio_id)` | `portfolio_id` (int, **req**) | `dict` with overview data |

#### `MilestonesResource` — `src/kanboard/resources/milestones.py` (10 methods)

| Plugin API Method | SDK Method | Params | Returns |
|---|---|---|---|
| `createMilestone` | `create_milestone(portfolio_id, name, **kwargs)` | `portfolio_id` (int, **req**), `name` (str, **req**), `description`/`target_date`/`color_id`/`owner_id` (opt) | `int` milestone_id or raise `KanboardAPIError` |
| `getMilestone` | `get_milestone(milestone_id)` | `milestone_id` (int, **req**) | `PluginMilestone` or raise `KanboardNotFoundError` |
| `getPortfolioMilestones` | `get_portfolio_milestones(portfolio_id)` | `portfolio_id` (int, **req**) | `list[PluginMilestone]` |
| `updateMilestone` | `update_milestone(milestone_id, **kwargs)` | `milestone_id` (int, **req**), `name`/`description`/`target_date`/`color_id`/`owner_id`/`status` (opt) | `bool` or raise `KanboardAPIError` |
| `removeMilestone` | `remove_milestone(milestone_id)` | `milestone_id` (int, **req**) | `bool` |
| `addTaskToMilestone` | `add_task_to_milestone(milestone_id, task_id, **kwargs)` | `milestone_id` (int, **req**), `task_id` (int, **req**), `is_critical` (int, opt), `position` (int, opt) | `bool` or raise `KanboardAPIError` |
| `removeTaskFromMilestone` | `remove_task_from_milestone(milestone_id, task_id)` | `milestone_id` (int, **req**), `task_id` (int, **req**) | `bool` |
| `getMilestoneTasks` | `get_milestone_tasks(milestone_id)` | `milestone_id` (int, **req**) | `list[dict]` (task data with `is_critical`, `position`) |
| `getTaskMilestones` | `get_task_milestones(task_id)` | `task_id` (int, **req**) | `list[PluginMilestone]` |
| `getMilestoneProgress` | `get_milestone_progress(milestone_id)` | `milestone_id` (int, **req**) | `PluginMilestoneProgress` |

#### Dependency Queries (5 methods) — added to `PortfoliosResource`

| Plugin API Method | SDK Method | Params | Returns |
|---|---|---|---|
| `getPortfolioDependencies` | `get_portfolio_dependencies(portfolio_id, **kwargs)` | `portfolio_id` (int, **req**), `cross_project_only` (bool, opt) | `list[dict]` |
| `getBlockedTasks` | `get_blocked_tasks(portfolio_id)` | `portfolio_id` (int, **req**) | `list[dict]` |
| `getBlockingTasks` | `get_blocking_tasks(portfolio_id)` | `portfolio_id` (int, **req**) | `list[dict]` |
| `getPortfolioCriticalPath` | `get_portfolio_critical_path(portfolio_id)` | `portfolio_id` (int, **req**) | `list[dict]` |
| `getPortfolioDependencyGraph` | `get_portfolio_dependency_graph(portfolio_id, **kwargs)` | `portfolio_id` (int, **req**), `cross_project_only` (bool, opt) | `dict` (nodes + edges) |

### New SDK Models

The plugin backend requires distinct model classes from the Phase 0 orchestration models because plugin API responses include server-assigned fields (`id`, `portfolio_id`, `status`, `color_id`, `owner_id`) that don't exist in the local store. These follow the standard `from_api()` resource model pattern (ADR-05).

```python
# Added to src/kanboard/models.py

@dataclasses.dataclass
class PluginPortfolio:
    """Server-side portfolio entity from the Kanboard Portfolio plugin."""
    id: int
    name: str
    description: str
    owner_id: int
    is_active: int
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_api(cls, data: dict) -> Self: ...

@dataclasses.dataclass
class PluginMilestone:
    """Server-side milestone entity from the Kanboard Portfolio plugin."""
    id: int
    portfolio_id: int
    name: str
    description: str
    target_date: datetime | None
    status: int
    color_id: str
    owner_id: int
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_api(cls, data: dict) -> Self: ...

@dataclasses.dataclass
class PluginMilestoneProgress:
    """Server-computed milestone progress from the Kanboard Portfolio plugin."""
    milestone_id: int
    total: int
    completed: int
    percent: float
    is_at_risk: bool
    is_overdue: bool

    @classmethod
    def from_api(cls, data: dict) -> Self: ...
```

### Functional Asymmetries Between Backends

| Feature | Local Backend | Remote Backend | Handling |
|---|---|---|---|
| Portfolio lookup | By name (string) | By ID (integer) or name | Remote backend's `get_portfolio(name)` calls `getPortfolioByName` internally |
| Server-assigned IDs | N/A — names are identifiers | `portfolio.id`, `milestone.id` | Remote backend maps name-based protocol methods to ID-based API calls |
| `position` on project membership | Not tracked | `portfolio_has_projects.position` | Passed as `0` (default) during migration; optionally exposed later |
| `color_id` on milestones | Not tracked | `milestones.color_id` (default: `"blue"`) | Set to `"blue"` during migration |
| `status` on milestones | Not tracked | `milestones.status` (1=active, 0=closed) | Set to `1` during migration |
| `owner_id` on portfolios/milestones | Not tracked | Server field | Set to `0` during migration (Kanboard interprets as current user) |
| `sync_metadata` | Writes `kanboard_cli:` keys to Kanboard metadata | N/A — plugin has its own DB tables | Remote backend's `sync_metadata()` is a no-op (data is already server-side) |
| `getPortfolioTasks` | N+1 API calls per project | Single server-side query with filters | Remote backend benefits from server-side pagination, sorting, filtering |
| `getMilestoneProgress` | Client-side computation from individual task fetches | Single server-side computation | Remote backend returns `PluginMilestoneProgress.from_api()` directly |
| Dependency queries | Client-side graph traversal via `DependencyAnalyzer` | Server-side SQL queries via plugin | Remote backend delegates to plugin's `getPortfolioDependencies`, `getBlockedTasks`, `getCriticalPath` etc. |
| Offline operation | Fully functional | Fails with `KanboardConnectionError` | See "Offline/Degraded Mode" section below |

---

## Configuration Specification

### New Configuration Key: `portfolio_backend`

| Layer | Key / Variable / Flag | Values | Default |
|---|---|---|---|
| **TOML profile** | `portfolio_backend` | `"local"` \| `"remote"` | `"local"` |
| **Environment variable** | `KANBOARD_PORTFOLIO_BACKEND` | `local` \| `remote` | — (falls through to profile/default) |
| **CLI flag** | `--portfolio-backend` | `local` \| `remote` | — (falls through to env/profile/default) |

**Resolution order** (consistent with ADR-06): TOML profile → env var → CLI flag (highest priority).

### TOML Configuration Examples

```toml
# Explicit local backend (same as default — useful for documentation)
[profiles.default]
url = "https://kanboard.example.com/jsonrpc.php"
token = "my-token"
portfolio_backend = "local"

# Plugin backend — requires plugin installed on server
[profiles.work]
url = "https://kanboard.work.com/jsonrpc.php"
token = "work-token"
portfolio_backend = "remote"
```

### KanboardConfig Changes

Add `portfolio_backend` to the `KanboardConfig` dataclass:

```python
@dataclass(frozen=True)
class KanboardConfig:
    url: str
    token: str
    profile: str
    output_format: str
    auth_mode: str
    username: str
    password: str
    portfolio_backend: str   # NEW: "local" (default) or "remote"
```

Resolution in `KanboardConfig.resolve()`:
```python
portfolio_backend = (
    cli_portfolio_backend
    or os.environ.get("KANBOARD_PORTFOLIO_BACKEND")
    or profile_data.get("portfolio_backend")
    or "local"
)
```

### Validation Behavior

| Scenario | Behavior |
|---|---|
| `portfolio_backend` not set anywhere | Default to `"local"` — no error |
| `portfolio_backend = "remote"` but plugin not installed | `KanboardAPIError` with message: "Portfolio plugin not detected on server. Install kanboard-plugin-portfolio-management or use `--portfolio-backend local`." Detected via ADR-24 probe on first remote operation. |
| `portfolio_backend` set to invalid value (not `local`/`remote`) | `KanboardConfigError`: "Invalid portfolio_backend '{value}'; must be 'local' or 'remote'." Raised during `KanboardConfig.resolve()`. |
| `portfolio_backend = "remote"` with `auth_mode = "app"` | Valid — plugin API uses the same JSON-RPC auth as all other endpoints |
| `portfolio_backend = "remote"` and server unreachable | `KanboardConnectionError` — same as any other API call failure |

---

## CLI Interface Changes

### Global Option Addition

```python
# In src/kanboard_cli/main.py — added to the root cli group
@click.option("--portfolio-backend", type=click.Choice(["local", "remote"]),
              default=None, help="Portfolio storage backend: local file or Kanboard plugin API.")
```

### Backend Resolution in CLI Commands

Portfolio and milestone commands resolve the backend via the `AppContext`:

```python
# In commands/portfolio.py and commands/milestone.py
def _get_backend(ctx: click.Context) -> PortfolioBackend:
    app: AppContext = ctx.obj
    return create_backend(
        backend_type=app.config.portfolio_backend,
        client=app.client,
    )
```

### Existing Command Behavior

All existing `portfolio` and `milestone` subcommands continue to work unchanged. The backend is resolved transparently — no new arguments or options on individual subcommands (other than the global `--portfolio-backend`).

| Command | Local Backend Behavior (unchanged) | Remote Backend Behavior (new) |
|---|---|---|
| `portfolio list` | Read `portfolios.json` | `getAllPortfolios()` |
| `portfolio show <name>` | Local store + live API enrichment | `getPortfolioByName()` + `getPortfolioOverview()` |
| `portfolio create <name>` | Write to `portfolios.json` | `createPortfolio()` |
| `portfolio remove <name>` | Remove from `portfolios.json` | `getPortfolioByName()` → `removePortfolio(id)` |
| `portfolio tasks <name>` | N+1 `getAllTasks` per project | `getPortfolioTasks()` (single server query) |
| `portfolio sync <name>` | Push `kanboard_cli:` metadata keys | No-op (data is server-side); prints informational message |
| `portfolio dependencies <name>` | Client-side `DependencyAnalyzer` | `getPortfolioDependencies()` (server-side query) |
| `portfolio blocked <name>` | Client-side `DependencyAnalyzer.get_blocked_tasks()` | `getBlockedTasks()` |
| `portfolio blocking <name>` | Client-side `DependencyAnalyzer.get_blocking_tasks()` | `getBlockingTasks()` |
| `portfolio critical-path <name>` | Client-side Kahn's algorithm | `getPortfolioCriticalPath()` |
| `milestone list <portfolio>` | Read from local store | `getPortfolioByName()` → `getPortfolioMilestones()` |
| `milestone show <portfolio> <ms>` | Local store + live API | `getMilestone()` + `getMilestoneTasks()` |
| `milestone create ...` | Write to local store | `getPortfolioByName()` → `createMilestone()` |
| `milestone progress <portfolio>` | Client-side computation | `getMilestoneProgress()` per milestone |

---

## Migration Subcommand Design

### Placement Decision

The migration command is placed as `kanboard portfolio migrate` — a subcommand of the existing `portfolio` group. This is consistent with the project's convention of grouping related operations under a single resource command (`portfolio`). Migration is inherently a portfolio-level operation.

Alternatives considered and rejected:
- **Top-level `kanboard migrate`**: Too generic; the migration is specific to portfolio/milestone data, not general Kanboard data.
- **`kanboard portfolio export` / `kanboard portfolio import`**: Export/import implies file I/O. The local→remote direction is a push to an API, not a file export.
- **Separate `kanboard portfolio-migrate` group**: Over-engineering for 2 subcommands.

### Subcommand Interface

```
kanboard portfolio migrate local-to-remote <portfolio_name>
    [--all]                     # Migrate all portfolios instead of one
    [--dry-run]                 # Preview changes without executing
    [--on-conflict skip|overwrite|fail]  # Conflict resolution (default: fail)
    [--yes]                     # Skip confirmation prompt

kanboard portfolio migrate remote-to-local <portfolio_name>
    [--all]                     # Migrate all portfolios
    [--dry-run]                 # Preview changes without executing
    [--on-conflict skip|overwrite|fail]  # Conflict resolution (default: fail)
    [--yes]                     # Skip confirmation prompt

kanboard portfolio migrate status
    # Show current backend config and data counts on each side

kanboard portfolio migrate diff <portfolio_name>
    [--all]                     # Diff all portfolios
    # Compare local and remote state, show differences
```

### Migration Flow: `local-to-remote`

1. **Read** portfolio from `LocalPortfolioStore`.
2. **Probe** plugin availability (ADR-24).
3. **Check** if a portfolio with the same name exists on the server.
   - If exists and `--on-conflict fail` → error and abort.
   - If exists and `--on-conflict skip` → skip this portfolio, continue to next if `--all`.
   - If exists and `--on-conflict overwrite` → `removePortfolio()` then recreate.
4. **Create** portfolio via `createPortfolio(name, description)`.
5. **Add projects** via `addProjectToPortfolio()` for each `project_id`.
6. **Create milestones** via `createMilestone()` for each milestone.
7. **Add tasks** via `addTaskToMilestone()` for each task in each milestone (with `is_critical` flag).
8. **Report** summary: `Migrated portfolio "X": 3 projects, 2 milestones, 12 tasks`.

### Migration Flow: `remote-to-local`

1. **Fetch** portfolio from plugin API via `getPortfolioByName(name)`.
2. **Fetch** portfolio projects via `getPortfolioProjects(portfolio_id)`.
3. **Fetch** milestones via `getPortfolioMilestones(portfolio_id)`.
4. **Fetch** milestone tasks via `getMilestoneTasks(milestone_id)` for each.
5. **Check** if portfolio exists in local store.
   - Conflict resolution same as `local-to-remote`.
6. **Write** to `LocalPortfolioStore` via `create_portfolio()`, `add_milestone()`, `add_task_to_milestone()`.
7. **Report** summary.

### Cross-Cutting Migration Concerns

| Concern | Design |
|---|---|
| **Idempotency** | `--on-conflict skip` makes repeated runs safe. `overwrite` ensures convergence. |
| **Dry run** | `--dry-run` prints all operations that *would* be performed (creates, adds, etc.) without executing any API calls or file writes. Uses `click.echo()` for each planned operation. |
| **Partial failure** | Each portfolio is migrated independently. On failure, the error is logged and the next portfolio is attempted (when `--all`). A summary at the end lists succeeded/failed. No automatic rollback — manual cleanup via `remove` commands. |
| **Progress reporting** | For `--all` with many portfolios: print `[1/5] Migrating "Platform Launch"...` progress lines. |
| **Rollback** | Not implemented. Migration operations are individually reversible via standard `remove` commands. Documenting this is sufficient for Phase 1. |
| **Data loss prevention** | `--on-conflict fail` is the default. Users must explicitly opt into `overwrite`. The `--yes` flag is required for non-interactive overwrite. |

### `migrate status` Output Example

```
Portfolio Backend Configuration
  Active backend: local
  Config source:  profile "default" (config.toml)

Local Store (~/.config/kanboard/portfolios.json)
  Portfolios: 3
  Total milestones: 7
  Total task assignments: 42

Remote (https://kanboard.example.com/jsonrpc.php)
  Plugin detected: ✓ kanboard-plugin-portfolio-management
  Portfolios: 2
  Total milestones: 5
  Total task assignments: 31
```

### `migrate diff` Output Example

```
Portfolio: "Platform Launch"
  Local: 3 projects, 2 milestones, 12 tasks
  Remote: 3 projects, 2 milestones, 14 tasks

  Milestones:
    "Beta Release" — identical (6 tasks each)
    "GA Launch" — local: 6 tasks, remote: 8 tasks
      + Task #101 (remote only)
      + Task #105 (remote only)
```

---

## Cross-Cutting Concerns

### Authentication and Credentials

The plugin API uses the same JSON-RPC authentication as all other Kanboard endpoints — no additional credentials are needed. Both `auth_mode = "app"` (API token) and `auth_mode = "user"` (username/password) work. No new secrets to manage.

The plugin's API access map restricts mutating operations (`createPortfolio`, `updatePortfolio`, etc.) to `APP_MANAGER` role. Read operations are available to `APP_USER`. The CLI should surface `KanboardAuthError` with a clear message when a user lacks sufficient permissions.

### Error Handling

| Error Type | Local Backend | Remote Backend |
|---|---|---|
| File not found | `portfolios.json` missing → empty list (graceful) | N/A |
| Malformed data | `KanboardConfigError` on bad JSON / schema mismatch | `KanboardResponseError` on malformed API response |
| Resource not found | `KanboardConfigError("Portfolio 'X' not found")` | `KanboardNotFoundError` (null API response) |
| Write failure | `OSError` on atomic write → propagated with context | `KanboardAPIError` on `False` return |
| Network failure | N/A | `KanboardConnectionError` (httpx timeout/connect error) |
| Auth failure | N/A | `KanboardAuthError` (HTTP 401/403) |
| Plugin not installed | N/A | `KanboardAPIError` (JSON-RPC method-not-found) → wrapped as `KanboardConfigError` with install instructions |
| Concurrent modification | Last-write-wins (atomic file replace) | Server handles via DB transactions |

### Offline / Degraded Mode

When `portfolio_backend = "remote"` and the Kanboard server is unreachable:

- All portfolio/milestone commands will raise `KanboardConnectionError` — same as any other API command.
- **No automatic fallback to local.** This is intentional (ADR-22): implicit fallback creates confusion about which backend was actually used. Users who need offline access should configure `portfolio_backend = "local"` in a separate profile.
- **Recommendation for users:** Create a `local` profile for offline use and a `remote` profile for server-connected work. Use `--profile` or `KANBOARD_PROFILE` to switch:

  ```bash
  # Online — use plugin backend
  kanboard --profile work portfolio list

  # Offline — use local backend
  kanboard --profile local portfolio list
  ```

### Logging and Observability

- All backend operations log at `DEBUG` level: method name, arguments, and response summary.
- Plugin detection probe logs at `INFO`: "Probing for Portfolio plugin... detected (v1.17.0)" or "...not detected".
- Migration operations log at `INFO`: each step (create, add-project, add-milestone, add-task).
- Backend selection logs at `DEBUG` during CLI startup: "Portfolio backend: local (from config.toml profile 'default')".

### Testing Strategy

| Test Type | Scope | Backend | Approach |
|---|---|---|---|
| **Unit — SDK resources** | `resources/portfolios.py`, `resources/milestones.py` | Remote | `pytest-httpx` mocking, same pattern as all other resource tests |
| **Unit — backend abstraction** | `orchestration/backend.py` | Both | Test `create_backend()` factory, protocol conformance |
| **Unit — remote backend adapter** | `RemotePortfolioBackend` class | Remote | Mock `PortfoliosResource` + `MilestonesResource` |
| **Unit — local backend** | `LocalPortfolioStore` | Local | Existing tests (unchanged) |
| **Unit — migration logic** | Migration functions | Both | Mock both backends, test conflict resolution, dry-run, error handling |
| **CLI — backend selection** | `--portfolio-backend` flag, env var | Both | `CliRunner` with mocked backends |
| **CLI — migration commands** | `portfolio migrate *` | Both | `CliRunner` with mocked API and local store |
| **CLI — existing commands** | All `portfolio` + `milestone` subcommands | Both | Verify identical output regardless of backend (modulo server-only fields) |
| **Integration** | Full lifecycle | Remote | Docker Kanboard with plugin installed; CRUD → verify via API |

**Coverage targets:**
- `resources/portfolios.py` — ≥90% (consistent with all resource modules)
- `resources/milestones.py` — ≥90%
- `orchestration/backend.py` — ≥95%
- Migration logic — ≥90%

### Backward Compatibility

| Concern | Guarantee |
|---|---|
| Default behavior | Unchanged — `portfolio_backend` defaults to `"local"` |
| Existing config files | Valid without modification — new key is optional |
| Existing CLI invocations | All commands work identically without `--portfolio-backend` flag |
| Local store file format | Schema version 1 unchanged |
| `LocalPortfolioStore` API | All public methods preserved; class now additionally satisfies `PortfolioBackend` protocol |
| `PortfolioManager` API | Constructor signature unchanged; internally resolves backend from config when not explicitly provided |
| `DependencyAnalyzer` API | Unchanged — still used for local backend graph analysis; remote backend delegates to plugin |
| SDK public exports | All existing exports preserved; new exports added (`PortfoliosResource`, `MilestonesResource`, `PluginPortfolio`, `PluginMilestone`, `PluginMilestoneProgress`) |

### Deprecation Considerations

None. The local backend is not being deprecated. It serves a distinct and permanent use case (single-user CLI workflows, offline operation, environments without the plugin). Both backends will be maintained indefinitely.

---

## Tasks

### Task 63: Plugin SDK models — `PluginPortfolio`, `PluginMilestone`, `PluginMilestoneProgress`

- [ ] **Priority:** P0 — all plugin resource modules depend on these
- **Complexity:** S
- **Dependencies:** None

Add 3 new dataclasses to `src/kanboard/models.py` with `from_api()` classmethods. These are distinct from the Phase 0 orchestration models — they represent server-side entities with `id`, `portfolio_id`, `status`, `color_id`, `owner_id` fields.

**Done when:** Models importable from `kanboard`, unit tests with sample API payloads, `ruff check . && ruff format --check . && pytest` passes.

---

### Task 64: Portfolios resource module — SDK

- [ ] **Priority:** P0 — remote backend depends on this
- **Complexity:** L
- **Dependencies:** Task 63

Implement `src/kanboard/resources/portfolios.py` — `PortfoliosResource` with all 13 methods (6 portfolio CRUD + 4 project membership + 3 task queries). Follow the established resource pattern. Wire into `KanboardClient.portfolios`.

**Done when:** All 13 methods callable, typed returns, unit tests with `pytest-httpx`, ≥90% coverage.

---

### Task 65: Milestones resource module — SDK

- [ ] **Priority:** P0 — remote backend depends on this
- **Complexity:** L
- **Dependencies:** Task 63

Implement `src/kanboard/resources/milestones.py` — `MilestonesResource` with all 10 methods (5 milestone CRUD + 5 task membership). Wire into `KanboardClient.milestones`.

**Done when:** All 10 methods callable, typed returns, unit tests with `pytest-httpx`, ≥90% coverage.

---

### Task 66: Dependency query methods on PortfoliosResource

- [ ] **Priority:** P1 — enhances remote backend
- **Complexity:** M
- **Dependencies:** Task 64

Add 5 dependency query methods to `PortfoliosResource`: `get_portfolio_dependencies`, `get_blocked_tasks`, `get_blocking_tasks`, `get_portfolio_critical_path`, `get_portfolio_dependency_graph`. These wrap the plugin's server-side SQL queries.

**Done when:** All 5 methods callable, unit tests, coverage maintained.

---

### Task 67: Backend protocol and factory — `orchestration/backend.py`

- [ ] **Priority:** P0 — all dual-backend wiring depends on this
- **Complexity:** M
- **Dependencies:** Tasks 64, 65

Create `src/kanboard/orchestration/backend.py` with:
- `PortfolioBackend` protocol class defining the 12-method interface.
- `RemotePortfolioBackend` class wrapping `PortfoliosResource` + `MilestonesResource` to satisfy the protocol.
- `create_backend()` factory function.
- Verify `LocalPortfolioStore` already satisfies the protocol (it should without modification).

**Done when:** Both backends satisfy the protocol, factory creates correct backend by type string, unit tests verify protocol conformance and factory behavior, ≥95% coverage on `backend.py`.

---

### Task 68: Configuration extension — `portfolio_backend`

- [ ] **Priority:** P0 — CLI backend selection depends on this
- **Complexity:** S
- **Dependencies:** None (independent of backend implementation)

Extend `KanboardConfig`:
- Add `portfolio_backend: str` field (default: `"local"`).
- Add `KANBOARD_PORTFOLIO_BACKEND` env var support.
- Add `portfolio_backend` TOML profile key support.
- Validate value is `"local"` or `"remote"` during `resolve()`.

**Done when:** Config resolution works at all 3 layers, validation raises `KanboardConfigError` on invalid values, existing config tests still pass, new unit tests for the field.

---

### Task 69: CLI global option — `--portfolio-backend`

- [ ] **Priority:** P0 — CLI backend selection
- **Complexity:** S
- **Dependencies:** Task 68

Add `--portfolio-backend` Click option to the root `cli` group in `main.py`. Pass through to `KanboardConfig.resolve()`. Update `AppContext` if needed.

**Done when:** `kanboard --portfolio-backend remote portfolio list` routes to remote backend. CLI tests with `CliRunner` verify both values. `--help` shows the option.

---

### Task 70: Wire backend into portfolio CLI commands

- [ ] **Priority:** P0 — makes dual-backend functional
- **Complexity:** M
- **Dependencies:** Tasks 67, 69

Refactor `src/kanboard_cli/commands/portfolio.py` to resolve the backend via `create_backend()` instead of directly instantiating `LocalPortfolioStore`. All 12 subcommands must work transparently with either backend.

**Done when:** All existing `portfolio` CLI tests still pass (local backend). New tests verify remote backend routing. No behavioral regressions.

---

### Task 71: Wire backend into milestone CLI commands

- [ ] **Priority:** P0 — makes dual-backend functional
- **Complexity:** M
- **Dependencies:** Tasks 67, 69

Refactor `src/kanboard_cli/commands/milestone.py` to resolve the backend via `create_backend()`. All 7 subcommands must work transparently with either backend.

**Done when:** All existing `milestone` CLI tests still pass. New tests verify remote backend routing.

---

### Task 72: Plugin detection probe

- [ ] **Priority:** P1 — UX improvement for remote backend
- **Complexity:** S
- **Dependencies:** Task 64

Implement ADR-24: on first remote backend operation, call `getPortfolio(portfolio_id=0)` (or similar) and catch the JSON-RPC method-not-found error to detect whether the plugin is installed. Cache the result for the session. Surface a clear `KanboardConfigError` with installation instructions when the plugin is not detected.

**Done when:** Detection works, result is cached, clear error message, unit tests mock both detected/not-detected scenarios.

---

### Task 73: Migration subcommand — `portfolio migrate`

- [ ] **Priority:** P1 — enables backend transitions
- **Complexity:** XL
- **Dependencies:** Tasks 67, 70, 71

Implement `kanboard portfolio migrate` with 4 sub-operations:
- `local-to-remote <name> [--all] [--dry-run] [--on-conflict skip|overwrite|fail] [--yes]`
- `remote-to-local <name> [--all] [--dry-run] [--on-conflict skip|overwrite|fail] [--yes]`
- `status` — show backend config and data counts
- `diff <name> [--all]` — compare local and remote state

**Done when:** All 4 sub-operations implemented, `--dry-run` works, conflict resolution works, progress reporting for `--all`, partial failure handling, CLI tests with CliRunner.

---

### Task 74: Unit tests — plugin SDK resources

- [ ] **Priority:** P0 — quality gate
- **Complexity:** L
- **Dependencies:** Tasks 64, 65, 66

Unit tests for `PortfoliosResource` and `MilestonesResource` with `pytest-httpx`. One test file per resource module. ≥90% coverage on each.

**Done when:** All methods tested (success + error paths), coverage meets target, `ruff check . && pytest` passes.

---

### Task 75: Unit tests — backend abstraction and remote adapter

- [ ] **Priority:** P0 — quality gate
- **Complexity:** M
- **Dependencies:** Task 67

Unit tests for `orchestration/backend.py`: protocol conformance for both backends, factory behavior, `RemotePortfolioBackend` method delegation. ≥95% coverage.

**Done when:** All paths tested, coverage meets target.

---

### Task 76: CLI tests — backend selection and migration

- [ ] **Priority:** P0 — quality gate
- **Complexity:** L
- **Dependencies:** Tasks 70, 71, 73

CLI tests verifying:
- `--portfolio-backend` flag routes correctly.
- All `portfolio` and `milestone` subcommands work with both backends.
- Migration subcommands: `local-to-remote`, `remote-to-local`, `status`, `diff`.
- `--dry-run`, `--on-conflict`, `--yes` flag behavior.

**Done when:** Comprehensive CliRunner tests, all 4 output formats on list commands.

---

### Task 77: Integration tests — plugin backend

- [ ] **Priority:** P2 — validates real plugin interaction
- **Complexity:** L
- **Dependencies:** Tasks 64, 65, 66, 73

Integration tests against Docker Kanboard with the portfolio plugin installed. Full CRUD lifecycle for portfolios and milestones via the remote backend. Migration round-trip test (local→remote→local).

**Implementation note:** Requires extending `docker-compose.test.yml` to install the plugin into the Kanboard container.

**Done when:** Integration tests pass against live plugin, lifecycle tests cover CRUD for portfolios, milestones, and task membership.

---

### Task 78: Documentation — dual-backend orchestration

- [ ] **Priority:** P1 — required before merge/release
- **Complexity:** M
- **Dependencies:** All previous Phase 1 tasks

Update the following files:
- `docs/configuration.md` — add `portfolio_backend` config key, env var, CLI flag.
- `docs/cli-reference.md` — add `portfolio migrate` subcommand group, update `portfolio` and `milestone` with backend selection notes.
- `docs/sdk-guide.md` — add `PortfoliosResource` and `MilestonesResource` sections, backend selection via SDK.
- `CLAUDE.md` — add `portfolio_backend` config key, plugin resource modules, `PluginPortfolio`/`PluginMilestone` models, `orchestration/backend.py`.
- `AGENTS.md` — update directory structure with new resource modules.
- `README.md` — update orchestration section to mention dual-backend and plugin integration.

**Done when:** All files updated, no placeholder content, `ruff check . && pytest` passes.

---

## Dependency Graph

```
Task 63 (plugin models)
  ├──> Task 64 (PortfoliosResource)
  │      ├──> Task 66 (dependency query methods)
  │      ├──> Task 67 (backend protocol + factory)
  │      │      ├──> Task 70 (wire portfolio CLI)
  │      │      ├──> Task 71 (wire milestone CLI)
  │      │      ├──> Task 73 (migration subcommand)
  │      │      │      └──> Task 76 (CLI tests — migration)
  │      │      └──> Task 75 (unit tests — backend)
  │      ├──> Task 72 (plugin detection)
  │      └──> Task 74 (unit tests — resources)
  └──> Task 65 (MilestonesResource)
         ├──> Task 67 (backend protocol + factory)
         └──> Task 74 (unit tests — resources)

Task 68 (config extension) ──> Task 69 (CLI global option)
                                  ├──> Task 70 (wire portfolio CLI)
                                  └──> Task 71 (wire milestone CLI)

Task 77 (integration tests) depends on: 64, 65, 66, 73
Task 78 (documentation) depends on: all prior tasks
```

## Implementation Order (Suggested)

1. **Task 63** — Plugin SDK models (foundation)
2. **Tasks 64–65** — SDK resource modules (parallelizable)
3. **Task 66** — Dependency query methods on PortfoliosResource
4. **Task 68** — Configuration extension (independent, parallelizable with 64–66)
5. **Task 67** — Backend protocol and factory (needs 64, 65)
6. **Task 69** — CLI global option (needs 68)
7. **Tasks 70–71** — Wire backend into CLI commands (parallelizable, need 67 + 69)
8. **Task 72** — Plugin detection probe (needs 64)
9. **Task 73** — Migration subcommand (needs 67, 70, 71)
10. **Tasks 74–76** — Test suites (can start alongside implementation)
11. **Task 77** — Integration tests (needs Docker + plugin)
12. **Task 78** — Documentation (last)

---

## Open Questions

1. **Plugin version compatibility:** Should the SDK enforce a minimum plugin version? The `getPluginVersion()` API could be probed, but adds complexity. **Recommendation:** Defer to Phase 2 — document the compatible plugin version in docs instead.

2. **Server-side pagination for `getPortfolioTasks`:** The plugin supports `limit`/`offset` pagination. Should the CLI expose `--page`/`--limit` options on `portfolio tasks`? **Recommendation:** Add `--limit` (default 50) in this phase; full pagination UX in Phase 2.

3. **Concurrent backend access:** If two users both use `portfolio_backend = "remote"`, the plugin handles concurrency via DB transactions. If one user uses `local` and another uses `remote`, the data diverges. **Recommendation:** Document that `portfolio migrate sync` should be run periodically to reconcile. Real-time sync is a Phase 2+ feature.

4. **Milestone `status` and `color_id` fields:** The local backend doesn't track these. Should they be added to the local `Milestone` model for round-trip fidelity? **Recommendation:** Yes — add optional fields with defaults (`status=1`, `color_id="blue"`) to preserve data during remote→local migration. Non-breaking change to schema version 1 (new keys with defaults).
