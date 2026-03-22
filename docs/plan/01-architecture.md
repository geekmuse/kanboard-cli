# Architecture & Configuration

> Binding decisions, project structure, and configuration schema. Referenced by all task files.

---

## Architecture Decisions Record

| # | Decision | Rationale |
|---|---|---|
| ADR-01 | **Python 3.11+** minimum | `tomllib` in stdlib, modern typing features (`Self`, `StrEnum`, `ExceptionGroup`) |
| ADR-02 | **`httpx`** for HTTP (sync client, async-ready) | Drop-in replacement for `requests` with native async path for future expansion |
| ADR-03 | **Click** for CLI framework | Mature, decorator-based, excellent subcommand support, built-in shell completion |
| ADR-04 | **`rich`** for table output | Colored, auto-width tables; future TUI potential |
| ADR-05 | **Typed exceptions** (`KanboardAuthError`, `KanboardNotFoundError`, etc.) | Clear programmatic error handling for SDK consumers |
| ADR-06 | **Layered config**: config file < env vars < CLI flags | Maximum flexibility; config file uses TOML (`tomllib` for read, `tomli_w` for write) |
| ADR-07 | **Named profiles** in config file | Support multiple Kanboard instances (e.g., production vs dev) |
| ADR-08 | **Application API auth** only at launch (jsonrpc user + global token) | User API auth (username + password/PAT) deferred to Task 46 |
| ADR-09 | **`kanboard`** = importable SDK namespace; **`kanboard_cli`** = CLI entry point | Clean separation: library consumers import `kanboard`, CLI users run `kanboard` command |
| ADR-10 | **Directory-based workflow discovery** at `~/.config/kanboard/workflows/` | Users drop `.py` files into a known path; no entry_points complexity |
| ADR-11 | **Zero bundled workflows** — all workflows live in separate repos or user directories | The main project ships no domain-specific code |
| ADR-12 | **Four output formats**: table (default), JSON, CSV, quiet/ID-only | Covers human use, scripting, and piping |
| ADR-13 | **Clean break** from any prior codebase | No backward compatibility obligations |
| ADR-14 | **`src/` layout** for packaging | Prevents accidental imports of uninstalled code |
| ADR-15 | **Unit tests + integration tests + CLI output tests** | Unit: mocked httpx; integration: Docker Kanboard; CLI: Click CliRunner |

---

## Target Directory Structure

```
kanboard-cli/
├── src/
│   ├── kanboard/                          # SDK package (`import kanboard`)
│   │   ├── __init__.py                    # Public API: KanboardClient, exceptions, models
│   │   ├── client.py                      # JSON-RPC transport layer
│   │   ├── config.py                      # Config resolution (file < env < args)
│   │   ├── exceptions.py                  # Typed exception hierarchy
│   │   ├── models.py                      # Dataclasses for API response objects
│   │   └── resources/                     # One module per API category
│   │       ├── __init__.py
│   │       ├── tasks.py                   # 14 methods
│   │       ├── projects.py                # 14 methods
│   │       ├── board.py                   # 1 method
│   │       ├── columns.py                 # 6 methods
│   │       ├── swimlanes.py               # 11 methods
│   │       ├── categories.py              # 5 methods
│   │       ├── comments.py                # 5 methods
│   │       ├── subtasks.py                # 5 methods
│   │       ├── subtask_time_tracking.py   # 4 methods
│   │       ├── users.py                   # 10 methods
│   │       ├── me.py                      # 7 methods
│   │       ├── tags.py                    # 7 methods
│   │       ├── links.py                   # 7 methods
│   │       ├── task_links.py              # 5 methods
│   │       ├── external_task_links.py     # 7 methods
│   │       ├── groups.py                  # 5 methods
│   │       ├── group_members.py           # 5 methods
│   │       ├── actions.py                 # 6 methods
│   │       ├── project_files.py           # 6 methods
│   │       ├── task_files.py              # 6 methods
│   │       ├── project_metadata.py        # 4 methods
│   │       ├── task_metadata.py           # 4 methods
│   │       ├── project_permissions.py     # 9 methods
│   │       └── application.py             # 7 methods
│   └── kanboard_cli/                      # CLI package
│       ├── __init__.py
│       ├── main.py                        # Click app root, global options
│       ├── formatters.py                  # Table / JSON / CSV / quiet renderers
│       ├── workflow_loader.py             # Discovers & loads user workflows
│       ├── commands/                      # One module per CLI command group
│       │   └── (task.py, project.py, board.py, column.py, swimlane.py,
│       │       category.py, comment.py, subtask.py, timer.py, user.py,
│       │       me.py, tag.py, link.py, task_link.py, external_link.py,
│       │       group.py, action.py, project_file.py, task_file.py,
│       │       project_meta.py, task_meta.py, project_access.py,
│       │       app_info.py, config_cmd.py, workflow.py)
│       └── workflows/
│           ├── __init__.py
│           └── base.py                    # BaseWorkflow ABC
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_client.py
│   │   ├── test_config.py
│   │   ├── test_exceptions.py
│   │   ├── test_models.py
│   │   └── resources/  (one test file per resource module)
│   ├── integration/
│   │   └── (Docker-based lifecycle tests)
│   └── cli/
│       └── (CliRunner-based output tests)
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── Makefile
└── docker-compose.test.yml
```

---

## Configuration Schema

### Config file: `~/.config/kanboard/config.toml`

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

### Environment variables (override config file)

| Variable | Maps to |
|---|---|
| `KANBOARD_URL` | `profiles.<active>.url` |
| `KANBOARD_API_TOKEN` | `profiles.<active>.token` |
| `KANBOARD_PROFILE` | `settings.default_profile` |
| `KANBOARD_OUTPUT` | `settings.output_format` |

### CLI flags (override everything)

| Flag | Purpose |
|---|---|
| `--url URL` | Kanboard JSON-RPC endpoint |
| `--token TOKEN` | API token |
| `--profile NAME` | Config profile to use |
| `--output FORMAT` | Output format: table, json, csv, quiet |
| `--verbose` | Enable debug logging |

### Resolution order: config file → env vars → CLI flags

### Workflow file location: `~/.config/kanboard/workflows/`
