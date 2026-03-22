# Milestone 2: Core Coverage (P1) — Tasks 11–27 ✅

> ← [Milestone 1](03-milestone-1-foundation.md) | [README](README.md) | [Milestone 3](05-milestone-3-extended.md) →
>
> Each SDK task follows the pattern established in [Task 6](03-milestone-1-foundation.md#task-6-tasks-resource-module--sdk). Each CLI task follows [Task 10](03-milestone-1-foundation.md#task-10-task--project-cli-commands). All API method specs are in [02-api-reference.md](02-api-reference.md).

> **Status: COMPLETE** — All 17 tasks implemented, 1037 tests passing (100% coverage on `src/kanboard/resources/`), ruff clean.

---

### Task 11: Board resource — SDK ✅
- [x] **P1** | M | Deps: 2, 5
- 1 method: `get_board(project_id)`. See [Board API](02-api-reference.md#api-category-board-1-method). Complex nested response.

**Implementation notes:**
- `BoardResource.get_board` returns raw `list[dict]` (not dataclass models) due to deep nesting complexity — intentional per plan.
- Returns `[]` on empty/falsy response.
- 10 unit tests covering: success, multi-column, empty (False/None/[]), error paths, client accessor, importability.

### Task 12: Columns resource — SDK ✅
- [x] **P1** | M | Deps: 2, 5
- 6 methods. See [Columns API](02-api-reference.md#api-category-columns-6-methods). Wire to `KanboardClient.columns`.

**Implementation notes:**
- `update_column` raises `KanboardAPIError` on `False`; `remove_column` just returns `False` (no raise) — asymmetry is intentional.
- `add_column` uses `if not result` (catches `0` and `False`) to guard the int return.
- `KanboardNotFoundError` uses `resource=` and `identifier=` kwargs; `__str__` returns `"Not found: {resource} '{identifier}' does not exist"`.
- 27 unit tests.

### Task 13: Swimlanes resource — SDK ✅
- [x] **P1** | M | Deps: 2, 5
- 11 methods. See [Swimlanes API](02-api-reference.md#api-category-swimlanes-11-methods). Wire to `KanboardClient.swimlanes`.

**Implementation notes:**
- `update_swimlane` returns `bool(result)` without raising on `False` (unlike `update_column` which raises) — always verify per-method raise vs return-bool semantics.
- `get_swimlane_by_name` uses `identifier=name` (a string) in `KanboardNotFoundError`; ID-based lookups use `identifier=swimlane_id` (int).
- `getAllSwimlanes` (not `getSwimlanes`) is the correct Kanboard API method name — "All" prefix is used consistently for full list endpoints.
- 45 unit tests.

### Task 14: Comments resource — SDK ✅
- [x] **P1** | S | Deps: 2, 5
- 5 methods. See [Comments API](02-api-reference.md#api-category-comments-5-methods). Wire to `KanboardClient.comments`.

**Implementation notes:**
- `update_comment` raises `KanboardAPIError` on False — consistent with "update = must succeed" pattern.
- `remove_comment` returns `bool(result)` without raising — same pattern as other `remove_*` methods.
- Comment model has `comment` field (same name as class) holding the text body.
- 24 unit tests.

### Task 15: Categories resource — SDK ✅
- [x] **P1** | S | Deps: 2, 5
- 5 methods. See [Categories API](02-api-reference.md#api-category-categories-5-methods). Wire to `KanboardClient.categories`.

**Implementation notes:**
- `Category.from_api` maps: `id`, `name`, `project_id`, `color_id` — all string-encoded in API response, cast via `_int()` and `str()`.
- 25 unit tests.

### Task 16: Tags resource — SDK ✅
- [x] **P1** | S | Deps: 2, 5
- 7 methods. See [Tags API](02-api-reference.md#api-category-tags-7-methods). Wire to `KanboardClient.tags`.

**Implementation notes:**
- `get_all_tags()` takes NO arguments — project-agnostic endpoint returning all tags globally.
- `get_task_tags()` returns a `dict` (tag_id → tag_name), not a list of Tag models — unique return type.
- `set_task_tags()` returns `bool` without raising on False — replaces all existing tag assignments.
- 35 unit tests.

### Task 17: Subtasks resource — SDK ✅
- [x] **P1** | S | Deps: 2, 5
- 5 methods. See [Subtasks API](02-api-reference.md#api-category-subtasks-5-methods). Wire to `KanboardClient.subtasks`.

**Implementation notes:**
- `KanboardNotFoundError` requires a positional message argument as first param — `resource=` and `identifier=` are kwargs.
- `Subtask.from_api` maps: `id`, `title`, `task_id`, `user_id`, `status`, `time_estimated` (float), `time_spent` (float), `position`, `username`, `name`.
- 24 unit tests.

### Task 18: Users resource — SDK ✅
- [x] **P1** | M | Deps: 2, 5
- 10 methods. See [Users API](02-api-reference.md#api-category-users-10-methods). Wire to `KanboardClient.users`.

**Implementation notes:**
- `create_ldap_user` only takes `username` (no password) — reads from LDAP.
- `is_active_user` returns `bool` and does NOT raise on False — it's a query, not a command.
- `disable_user` and `enable_user` return `bool(result)` without raising — same passive-return pattern as `remove_*` methods.
- `get_user_by_name` uses `identifier=username` (string) in `KanboardNotFoundError`.
- 42 unit tests.

### Task 19: Link types resource — SDK ✅
- [x] **P1** | S | Deps: 2, 5
- 7 methods. See [Link Types API](02-api-reference.md#api-category-link-types-7-methods). Wire to `KanboardClient.links`.

**Implementation notes:**
- `Link` model fields: `id`, `label`, `opposite_id` — note `opposite_id` (not `opposite_link_id`) in the model.
- `get_link_by_label` and `get_link_by_id` both use `if not result` guard (catches both `False` and `None`).
- `get_opposite_link_id` and `create_link` also use `if not result` (catches `False` and `0`).
- 35 unit tests.

### Task 20: Internal task links resource — SDK ✅
- [x] **P1** | S | Deps: 2, 5, 19
- 5 methods. See [Internal Task Links API](02-api-reference.md#api-category-internal-task-links-5-methods). Wire to `KanboardClient.task_links`.

**Implementation notes:**
- `TaskLink` model fields: `id`, `task_id`, `opposite_task_id`, `link_id` — all int, all string-encoded in API response.
- `typing.Any` import not needed when no `**kwargs` methods — ruff F401 flags unused imports.
- 24 unit tests.

### Task 21: Board + Column + Swimlane CLI commands ✅
- [x] **P1** | L | Deps: 8, 9, 11, 12, 13

```
kanboard board show <project_id>
kanboard column list|get|add|update|remove|move
kanboard swimlane list [--all]|get|get-by-name|add|update|remove|enable|disable|move
```

**Implementation notes:**
- Split into two command modules: `commands/board.py` + `commands/column.py` (US-011) and `commands/swimlane.py` (US-012).
- `board show` uses `format_output(board_data, app.output, columns=_BOARD_COLUMNS)` for clean table output using only top-level column fields; JSON shows full nested structure.
- `swimlane list` uses `--all` flag to switch between `get_active_swimlanes` and `get_all_swimlanes`.
- `swimlane remove` takes both `project_id` AND `swimlane_id` as positional args (unlike `column remove` which only takes `column_id`).
- 7 board tests + 29 column tests + 40 swimlane tests.

### Task 22: Comment CLI commands ✅
- [x] **P1** | S | Deps: 8, 9, 14

```
kanboard comment list <task_id> | get <id> | add <task_id> <content> --user-id | update <id> <content> | remove <id> [--yes]
```

**Implementation notes:**
- `comment add` uses `--user-id` as a required option (not a positional arg).
- Table output wraps long comment text — use short fields like `username` or `id` for table test assertions.
- 22 CLI tests.

### Task 23: Category + Tag CLI commands ✅
- [x] **P1** | M | Deps: 8, 9, 15, 16

```
kanboard category list|get|create|update|remove
kanboard tag list [--project-id]|create|update|remove|set <project_id> <task_id> <tags>...|get <task_id>
```

**Implementation notes:**
- `tag list` uses `--project-id` optional option — when provided calls `get_tags_by_project(project_id)`, otherwise calls `get_all_tags()`.
- `tag get <task_id>` returns a `dict` (tag_id → tag_name) — `format_output` handles via `_normalize` wrapping.
- `tag set` uses `nargs=-1, required=True` for variadic `<tags>...` — Click enforces at least one value.
- `tag create` argument named `tag_name` in Click (not `tag`) to avoid shadowing the Click group name.
- `category update` SDK signature is `update_category(id, name, **kwargs)` — avoid keyword `id=` to prevent Python builtin shadowing.
- 23 category tests + 28 tag tests.

### Task 24: Subtask CLI commands ✅
- [x] **P1** | S | Deps: 8, 9, 17

```
kanboard subtask list|get|create|update|remove
```

**Implementation notes:**
- `subtask update` exposes both `subtask_id` and `task_id` as required positional arguments; all other fields are optional `--option` flags.
- Import sort order matters: ruff I001 flags unsorted imports in `main.py` — fix with `ruff check --fix`.
- 26 CLI tests.

### Task 25: User CLI commands ✅
- [x] **P1** | M | Deps: 8, 9, 18

```
kanboard user list|get|get-by-name|create|update|remove [--yes]|enable|disable|is-active
```
Password prompt via `click.prompt(hide_input=True)` when not provided.

**Implementation notes:**
- `click.prompt("Password", hide_input=True, confirmation_prompt=True)` prompts for password + confirmation; in tests supply `input="s3cret\ns3cret\n"` via CliRunner's `input=`.
- `user is-active` renders "active"/"inactive" status message via `format_success` — it's a query, not a command.
- `user update` passes `user_id` positionally (not `id=`) to avoid shadowing the Python builtin.
- 35 CLI tests.

### Task 26: Link CLI commands ✅
- [x] **P1** | M | Deps: 8, 9, 19, 20

```
kanboard link list|get|get-by-label|create|update|remove
kanboard task-link list|get|create|update|remove
```

**Implementation notes:**
- `link update` takes 3 positional args: `link_id`, `opposite_link_id`, `label` — all required.
- `task_link` Click group specifies `name="task-link"` to match the CLI hyphenated command name.
- `task-link update` takes 4 positional args matching the SDK `update_task_link` signature.
- `link create` uses `--opposite-label` (hyphenated) as Click option; mapped to `opposite_label` (underscored) Python param.
- 26 link tests + 21 task-link tests.

### Task 27: Unit + CLI tests for Milestone 2 ✅
- [x] **P1** | L | Deps: 11-26

Unit tests for all resource modules with mocked httpx. CLI output tests via CliRunner across all 4 formats. Error path tests. Target >=90% coverage on `src/kanboard/resources/`.

**Implementation notes:**
- Final coverage: 100% on `src/kanboard/resources/` (474 stmts, 0 missed).
- All 10 M2 resource test files had: `KanboardNotFoundError` on null, `KanboardAPIError` on False, empty-list returns.
- Created `tests/unit/resources/test_network_failures.py` — 21 tests adding explicit `KanboardConnectionError` tests for all 10 M2 resources using `httpx.ConnectError`, `httpx.ReadTimeout`, `httpx.ConnectTimeout` variants.
- All CLI groups confirmed to have: all 4 output formats, `--yes` destructive confirmation, and empty-list rendering tests.
- `KanboardConnectionError` propagates from `client.call()` through any resource method — one consolidated test file is a clean pattern for cross-cutting transport error coverage.
- 1037 tests total at milestone completion.

---
