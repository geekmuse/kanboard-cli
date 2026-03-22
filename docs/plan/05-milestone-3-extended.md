# Milestone 3: Extended Coverage (P2) — Tasks 28–41 ✅

> ← [Milestone 2](04-milestone-2-core.md) | [README](README.md) | [Milestone 4](06-milestone-4-ship.md) →
>
> Rounds out complete API coverage. SDK + CLI combined in each task. API specs in [02-api-reference.md](02-api-reference.md). Workflow plugin architecture in [07-appendices.md](07-appendices.md#appendix-c-example-workflow-reference).

> **Status: COMPLETE** — All 14 tasks implemented, 1753 tests passing (100% coverage on `src/kanboard/resources/`, 852 stmts, 0 missed), ruff clean.

---

### Task 28: Project files — SDK + CLI ✅
- [x] **P2** | M | Deps: 2, 5, 8
- 6 methods. See [Project Files API](02-api-reference.md#api-category-project-files-6-methods). CLI: `kanboard project-file list|get|upload|download|remove|remove-all`. Base64 encode/decode transparently.

**Implementation notes:**
- Rich table truncates long cell values in narrow terminals — use prefix checks (e.g. `"rep"`) in table output assertions, not full string matches.
- `--output` is a reserved param name for Click in the `download` command; use `output_path` as the Python variable name.
- `ProjectFile` and `TaskFile` dataclasses already pre-defined in `models.py` — no model work needed.
- 31 SDK unit tests + 27 CLI tests (58 total).

### Task 29: Task files — SDK + CLI ✅
- [x] **P2** | M | Deps: 2, 5, 8
- 6 methods. See [Task Files API](02-api-reference.md#api-category-task-files-6-methods). CLI: `kanboard task-file list|get|upload|download|remove|remove-all`.

**Implementation notes:**
- Task file API signatures differ from project files: `get_task_file(file_id)` and `download_task_file(file_id)` take only `file_id` (no project_id), while `create_task_file` takes both `project_id` and `task_id`.
- Import ordering in `client.py` must be alphabetical by module path — `task_files` goes after `tags` and before `task_links`.
- 31 SDK unit tests + 27 CLI tests (58 total).

### Task 30: Project metadata — SDK + CLI ✅
- [x] **P2** | S | Deps: 2, 8
- 4 methods. See [Project Metadata API](02-api-reference.md#api-category-project-metadata-4-methods). CLI: `kanboard project-meta list|get|set|remove`.

**Implementation notes:**
- Metadata APIs return plain dicts/strings, not dataclass models — format list output as `[{"key": k, "value": v}]` dicts for `format_output`.
- `get_*_by_name` methods: `not result` fails to catch `False` because `False == 0` in Python — use explicit `result is None or result is False` guard.
- Ruff `RUF002` flags en-dash characters in docstrings — always use plain hyphen-minus.
- 24 SDK unit tests + 20 CLI tests (44 total).

### Task 31: Task metadata — SDK + CLI ✅
- [x] **P2** | S | Deps: 2, 8
- 4 methods. See [Task Metadata API](02-api-reference.md#api-category-task-metadata-4-methods). CLI: `kanboard task-meta list|get|set|remove`.

**Implementation notes:**
- Handles Kanboard quirk where `getTaskMetadata` returns `[]` (empty list) instead of `{}` on empty — added `isinstance(result, list)` guard.
- Task metadata follows identical pattern to project metadata — only differs in parameter names (`task_id` vs `project_id`).
- 26 SDK unit tests + 20 CLI tests (46 total).

### Task 32: Project permissions — SDK + CLI ✅
- [x] **P2** | M | Deps: 2, 5, 8, 18
- 9 methods. See [Project Permissions API](02-api-reference.md#api-category-project-permissions-9-methods). CLI: `kanboard project-access list|assignable|add-user|add-group|remove-user|remove-group|set-user-role|set-group-role|user-role`.

**Implementation notes:**
- Split into SDK (US-005) and CLI (US-006) due to being the largest resource module (9 methods).
- Permission APIs return dicts mapping user/group IDs (as strings) to usernames — no dataclass models needed.
- `get_project_user_role` returns a role string — uses same `result is None or result is False or result == ""` guard as metadata-by-name methods.
- For `add-user`/`add-group` with optional `--role`, build kwargs dict conditionally rather than always passing `role=None`.
- The `user-role` query command formats as `{"user_id": str(user_id), "role": role}` for consistent output across formats.
- 47 SDK unit tests + 45 CLI tests (92 total).

### Task 33: Groups — SDK + CLI ✅
- [x] **P2** | S | Deps: 2, 5, 8
- 5 methods. See [Groups API](02-api-reference.md#api-category-groups-5-methods). CLI: `kanboard group list|get|create|update|remove`.

**Implementation notes:**
- Groups resource is simple with only 3 fields (`id`, `name`, `external_id`) — straightforward dataclass mapping.
- `update_group` raises `KanboardAPIError` on False (mutation); `remove_group` just returns bool.
- Single-item JSON output from `format_output` returns a plain dict, not a list wrapping one element.
- 32 SDK unit tests + 24 CLI tests (56 total).

### Task 34: Group members — SDK + CLI ✅
- [x] **P2** | S | Deps: 2, 5, 8, 33
- 5 methods. See [Group Members API](02-api-reference.md#api-category-group-members-5-methods). CLI: `kanboard group member list|groups|add|remove|check`.

**Implementation notes:**
- Group members is a sub-group of the group CLI command — use `@group.group("member")` to nest a Click group under an existing group.
- `get_group_members` returns `list[User]` while `get_member_groups` returns `list[Group]` — need both model types imported.
- `is_group_member` check formats as `{"group_id": ..., "user_id": ..., "is_member": ...}` dict for consistent output.
- 28 SDK unit tests + 25 CLI tests (53 total).

### Task 35: External task links — SDK + CLI ✅
- [x] **P2** | M | Deps: 2, 5, 8
- 7 methods. See [External Task Links API](02-api-reference.md#api-category-external-task-links-7-methods). CLI: `kanboard external-link types|dependencies|list|get|create|update|remove`.

**Implementation notes:**
- External task link APIs use `providerName` (camelCase) as the param name for `getExternalTaskLinkProviderDependencies` — SDK translates via kwargs.
- `get_external_task_link_types` and `get_external_task_link_provider_dependencies` return plain dicts — format as `[{"key": k, "label": v}]` for table output.
- Network failure tests must use `httpx_mock.add_exception(httpx_lib.ConnectError("refused"))` pattern — pytest-httpx asserts all requests are expected.
- 34 SDK unit tests + 33 CLI tests (67 total).

### Task 36: Automatic actions — SDK + CLI ✅
- [x] **P2** | M | Deps: 2, 5, 8
- 6 methods. See [Automatic Actions API](02-api-reference.md#api-category-automatic-actions-6-methods). CLI: `kanboard action list|available|events|compatible-events|create|remove`.

**Implementation notes:**
- Mix of return types: `get_available_actions` and `get_available_action_events` return dicts, `get_compatible_action_events` returns a list, `get_actions` returns `list[Action]`, `create_action` returns int, `remove_action` returns bool.
- `get_compatible_action_events` may return either a list or a dict from the API — use `list()` to handle both (dict yields keys).
- The `--param`/`-p` repeatable option with `multiple=True` is used for key=value pairs — parse with `split("=", 1)`.
- Ruff `D301` requires `r"""` prefix for docstrings containing backslashes (e.g. `\\TaskClose` in examples).
- 30 SDK unit tests + 28 CLI tests (58 total).

### Task 37: Subtask time tracking — SDK + CLI ✅
- [x] **P2** | S | Deps: 2, 8, 17
- 4 methods. See [Subtask Time Tracking API](02-api-reference.md#api-category-subtask-time-tracking-4-methods). CLI: `kanboard timer status|start|stop|spent`.

**Implementation notes:**
- Simple resource (4 methods, no dataclass models) — returns bool and float primitives.
- `set_subtask_start_time` and `set_subtask_end_time` raise `KanboardAPIError` on False (mutation pattern); `has_subtask_timer` and `get_subtask_time_spent` are query methods returning falsy defaults.
- `get_subtask_time_spent` returns `0.0` (not `0`) — use `float(result)` conversion.
- CLI commands output simple status/query data formatted as `[{"key": ..., "value": ...}]` for `format_output` consistency.
- 26 SDK unit tests + 23 CLI tests (49 total).

### Task 38: Current user ("Me") — SDK + CLI ✅
- [x] **P2** | M | Deps: 2, 5, 8
- 7 methods. See [Current User API](02-api-reference.md#api-category-current-user--me-7-methods). CLI: `kanboard me [dashboard|activity|projects|overdue|create-project]`. **Note:** Requires User API auth — all 7 methods raise `KanboardAuthError` with clear message until Task 46 is implemented.

**Implementation notes:**
- All 7 methods unconditionally raise `KanboardAuthError` — no HTTP calls are made until User API auth (Task 46) is implemented.
- Uses `invoke_without_command=True` so bare `kanboard me` shows current user info.
- `KanboardAuthError` supports optional `http_status` param, but for pre-emptive auth errors (before HTTP calls), omit it.
- Resource methods that unconditionally raise don't need pytest-httpx mocking.
- When ClickException is raised, `--output` format does not change the error display — Click handles errors independently.
- 12 SDK unit tests + 12 CLI tests (24 total).

### Task 39: Application info — SDK + CLI ✅
- [x] **P2** | S | Deps: 2, 8
- 7 methods. See [Application API](02-api-reference.md#api-category-application-7-methods). CLI: `kanboard app version|timezone|colors|default-color|roles`.

**Implementation notes:**
- Entirely read-only resource (no mutations) — all methods return str or dict with falsy-default guards, no `KanboardAPIError` raises needed.
- The `roles` CLI command combines two API calls (`getApplicationRoles` + `getProjectRoles`) into one table with a `scope` column.
- The `colors` command formats dict values using `str(v)` since colour definitions can be nested dicts.
- 32 SDK unit tests + 28 CLI tests (60 total).

### Task 40: Workflow plugin architecture ✅
- [x] **P2** | L | Deps: 2, 8

**`src/kanboard_cli/workflows/base.py`:**
```python
class BaseWorkflow(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def description(self) -> str: ...
    @abstractmethod
    def register_commands(self, cli: click.Group) -> None: ...
    def get_config(self) -> dict:
        return KanboardConfig.get_workflow_config(self.name)
```

**`src/kanboard_cli/workflow_loader.py`:**
- Scan `~/.config/kanboard/workflows/` for `.py` files and packages (dirs with `__init__.py`)
- `importlib.util` to load modules, inspect for `BaseWorkflow` subclasses
- Instantiate and return discovered workflows
- `main.py` calls `workflow.register_commands(cli)` for each

CLI: `kanboard workflow list` shows discovered workflows.

**Done when:** A `.py` file dropped into `~/.config/kanboard/workflows/` with a `BaseWorkflow` subclass auto-registers its commands on next `kanboard` invocation.

**Implementation notes:**
- `importlib.util.spec_from_file_location` can return `None` for invalid paths — always check before calling `exec_module`.
- `inspect.isabstract(obj)` reliably filters out ABC subclasses that haven't implemented all abstract methods.
- Workflow loader must register modules in `sys.modules` before `exec_module` to avoid circular import issues.
- Sorting discovered workflows by `wf.name` ensures deterministic ordering across platforms.
- The `workflow list` command uses deferred `discover_workflows()` import in the command handler (not at module load time) to avoid issues with test patching.
- 14 loader tests + 5 ABC tests + 7 CLI tests (26 total).

### Task 41: Example workflow — separate repository
- [ ] **P2** | L | Deps: 6, 7, 40

Build a reference workflow plugin in a **separate repository** that demonstrates the full workflow system (Task 40). This serves as a template for users building their own workflows. The workflow should exercise: reading workflow-specific config from `[workflows.<name>]`, registering Click subcommands, and using the `KanboardClient` SDK for task creation and project management.

**Note:** This task is out of scope for the `kanboard-cli` repository per ADR-11 (zero bundled workflows). The workflow plugin architecture (Task 40) is complete and ready for external workflow development.

---
