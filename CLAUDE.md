# CLAUDE.md — AI Assistant Context

## Project Summary

Python SDK (`import kanboard`) and Click-based CLI (`kanboard`) providing complete coverage of all 158 Kanboard JSON-RPC API methods, with a plugin system for user-defined workflows. Distributed as a single PyPI package `kanboard-cli`.

## Tech Stack

- **Language:** Python 3.11+ (required for `tomllib`, `Self`, `StrEnum`)
- **HTTP:** `httpx` (sync client; async-ready for future)
- **CLI:** `click` (decorator-based, subcommand groups)
- **Output:** `rich` (colored tables), plus JSON/CSV/quiet modes
- **Config:** TOML (`tomllib` stdlib for read, `tomli_w` for write)
- **Testing:** `pytest`, `pytest-httpx` (mocked HTTP), Click `CliRunner`
- **Linting:** `ruff`
- **Build:** `hatchling` backend, `src/` layout
- **Integration tests:** Docker (`kanboard/kanboard:latest`) via `docker-compose.test.yml`

## Architecture & Key Patterns

- **`src/` layout** — SDK is `src/kanboard/`, CLI is `src/kanboard_cli/`
- **Resource pattern** — Each API category is a module in `src/kanboard/resources/` (e.g., `tasks.py`, `projects.py`). Resources attach to `KanboardClient` as attributes (e.g., `client.tasks`, `client.projects`)
- **Resource methods** call `self._client.call("methodName", **params)` and return typed dataclass models
- **Return conventions:** `False` from API → raise `KanboardAPIError`; `None` → raise `KanboardNotFoundError`; lists handle `False`/`None` as empty `[]`
- **Models** — Dataclasses in `models.py` with `@classmethod from_api(cls, data: dict)` factory; use `.get()` with defaults to handle Kanboard's inconsistent types
- **Config resolution order:** config file (`~/.config/kanboard/config.toml`) → env vars (`KANBOARD_*`) → CLI flags
- **Named profiles** in config (`[profiles.default]`, `[profiles.dev]`)
- **Four output formats:** `table` (rich), `json`, `csv`, `quiet` (ID-only) — every CLI command supports all four
- **Workflow plugins:** User `.py` files in `~/.config/kanboard/workflows/` auto-discovered via `importlib.util`; must subclass `BaseWorkflow` ABC
- **Auth:** Application API only (username `jsonrpc`, global token). User API auth (for `getMe*` etc.) deferred — raise `KanboardAuthError` until implemented
- **JSON-RPC 2.0:** Single endpoint, HTTP Basic Auth, supports batch calls
- See `docs/plan/01-architecture.md` for all ADRs and directory structure

## File/Folder Structure

```
src/kanboard/                    # SDK (importable library)
  __init__.py                    # Public API: KanboardClient, exceptions, models
  client.py                      # JSON-RPC transport (call, batch, context manager)
  config.py                      # KanboardConfig dataclass with resolve() classmethod
  exceptions.py                  # Typed hierarchy (see below)
  models.py                      # Dataclasses: Task, Project, Column, Swimlane, etc.
  resources/                     # 24 modules, one per API category

src/kanboard_cli/                # CLI (Click application)
  main.py                        # Root click.Group, global options, config wiring
  formatters.py                  # format_output() and format_success()
  workflow_loader.py             # Plugin discovery from ~/.config/kanboard/workflows/
  commands/                      # One module per CLI command group
  workflows/base.py              # BaseWorkflow ABC

tests/unit/                      # Mocked httpx tests
tests/cli/                       # CliRunner output tests
tests/integration/               # Docker lifecycle tests
```

## Coding Conventions

- **Python 3.11+ features:** Use `tomllib`, `Self`, `StrEnum`, modern `|` union types
- **Method naming:** SDK methods use `snake_case` mapped from API's `camelCase` (e.g., `createTask` → `create_task`)
- **Required params:** Explicit positional/keyword args. Optional params: `**kwargs` passed through to RPC call
- **Type hints:** All public methods fully typed; return typed models, not raw dicts
- **Exceptions:** Always structured with context (`resource`, `identifier`, `method`, `code`, etc.)
- **CLI destructive commands:** Require `--yes` confirmation flag
- **CLI password input:** Use `click.prompt(hide_input=True)`
- **Dataclass models:** `frozen=True` where appropriate; `from_api()` handles type coercion
- **Helper functions:** `_parse_date()` for date parsing (handles None, "", "0", 0, timestamps, ISO strings); `_int()` for string-to-int coercion
- **Imports:** SDK public API re-exported from `kanboard.__init__`

## Exception Hierarchy

```
KanboardError
├── KanboardConfigError(message, field)
├── KanboardConnectionError(message, url, cause)
├── KanboardAuthError(message, http_status)
├── KanboardAPIError(message, method, code)
│   ├── KanboardNotFoundError(resource, identifier)
│   └── KanboardValidationError
└── KanboardResponseError(message, raw_body)
```

## Common Commands

```bash
pip install -e ".[dev]"    # Install editable with dev deps
make install               # Same via Makefile
make lint                  # ruff check .
make test                  # pytest (unit + CLI tests)
make test-integration      # pytest integration/ (needs Docker)
make coverage              # pytest with coverage
ruff check src/ tests/     # Lint
ruff format src/ tests/    # Format
```

## API Coverage

- 158 methods across 24 categories
- See `docs/plan/02-api-reference.md` for complete method signatures
- See `docs/plan/07-appendices.md` (Appendix B) for category → task mapping

## Key Config Paths

- Config file: `~/.config/kanboard/config.toml`
- Workflow plugins: `~/.config/kanboard/workflows/`
- Constants exported from `kanboard.config`: `CONFIG_DIR`, `CONFIG_FILE`, `WORKFLOW_DIR`

## Build Plan Reference

| Doc | Contents |
|---|---|
| `docs/plan/01-architecture.md` | ADRs, directory structure, config schema |
| `docs/plan/02-api-reference.md` | All 158 JSON-RPC method signatures |
| `docs/plan/03-milestone-1-foundation.md` | Tasks 1–10: scaffolding, transport, exceptions, config, models, task/project SDK+CLI |
| `docs/plan/04-milestone-2-core.md` | Tasks 11–27: board, columns, swimlanes, comments, categories, tags, subtasks, users, links |
| `docs/plan/05-milestone-3-extended.md` | Tasks 28–41: files, metadata, permissions, groups, actions, time tracking, workflows |
| `docs/plan/06-milestone-4-ship.md` | Tasks 42–48: integration tests, docs, PyPI, user auth, completions |
| `docs/plan/07-appendices.md` | Dependency graph, API coverage matrix |

## Critical Gotchas

- Kanboard API returns `False` for failures and `None`/`null` for not-found — these are semantically different
- Kanboard sometimes returns string `"0"` where `int` `0` is expected — always coerce with `_int()`
- Date fields can be `None`, `""`, `"0"`, `0`, Unix timestamps, or ISO strings — use `_parse_date()`
- `getMe*`/`getMy*` methods require User API auth, not Application API — raise `KanboardAuthError` until user auth is implemented
- `kanboard` is the importable SDK namespace; `kanboard_cli` is the CLI package — keep them strictly separate
- No backward compatibility obligations (ADR-13: clean break from any prior codebase)
- Zero bundled workflows (ADR-11) — all workflows live in user directories or separate repos
