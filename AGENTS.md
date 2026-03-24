# kanboard-cli

Python SDK (`import kanboard`) and Click-based CLI (`kanboard`) providing complete coverage of all 158 Kanboard JSON-RPC API methods, with a plugin system for user-defined workflows.

## Commands

After ANY code change, run:
```bash
ruff check . && ruff format --check . && pytest
```

Individual commands:
- `pytest` — Run unit and CLI tests
- `ruff check .` — Lint code
- `ruff format .` — Format code
- `pip install -e ".[dev]"` — Install with dev dependencies

## Conventions

1. **src/ layout** — SDK is `src/kanboard/`, CLI is `src/kanboard_cli/`. Never mix them.
2. **pytest + pytest-httpx** for unit tests; Click `CliRunner` for CLI tests.
3. **Python 3.11+** — Use `tomllib`, `Self`, `StrEnum`, `|` union types. No backports.
4. **snake_case SDK methods** mapped from Kanboard's `camelCase` API (e.g., `createTask` → `create_task`).
5. **Full type hints** on all public methods. Return typed dataclass models, not raw dicts.
6. **Destructive CLI commands** (`remove`, `disable`, etc.) require `--yes` confirmation flag.
7. **One resource module per API category** in `src/kanboard/resources/` — follow the pattern in `tasks.py`.
8. **Strict ruff rules** — all ruff checks must pass.
9. **Docstrings on all public methods** — concise, describes params and return.
10. **≥90% test coverage** target on `src/kanboard/resources/`.

## Resource Pattern

Every SDK resource module follows this pattern:
```python
class FooResource:
    def __init__(self, client): self._client = client

    def get_foo(self, foo_id: int) -> Foo:
        result = self._client.call("getFoo", foo_id=foo_id)
        if result is None: raise KanboardNotFoundError("Foo", foo_id)
        return Foo.from_api(result)
```

- `False` from API → raise `KanboardAPIError`
- `None` from API → raise `KanboardNotFoundError`
- Empty list results → handle `False`/`None` as `[]`

## Directory Structure

```
src/
├── kanboard/                # SDK package (import kanboard)
│   ├── __init__.py          # Public API: KanboardClient, exceptions, models, orchestration
│   ├── client.py            # JSON-RPC transport (call, batch)
│   ├── config.py            # Layered config resolution (incl. portfolio_backend field)
│   ├── exceptions.py        # Typed exception hierarchy
│   ├── models.py            # Dataclass models (resources use from_api(); orchestration models do not)
│   │                        # Plugin models: PluginPortfolio, PluginMilestone, PluginMilestoneProgress
│   ├── resources/           # 26 modules, one per API category
│   │   ├── portfolios.py    # PortfoliosResource — 18 plugin API methods (13 CRUD + 5 dependency queries)
│   │   ├── milestones.py    # MilestonesResource — 10 plugin API methods
│   │   └── [24 other modules]
│   └── orchestration/       # Cross-project orchestration (opt-in subpackage, NOT a resource)
│       ├── __init__.py      # Exports: DependencyAnalyzer, LocalPortfolioStore, PortfolioManager,
│       │                    #          PortfolioBackend, RemotePortfolioBackend, create_backend
│       ├── portfolio.py     # PortfolioManager — multi-project aggregation, milestone progress
│       ├── dependencies.py  # DependencyAnalyzer — graph traversal, critical path
│       ├── store.py         # LocalPortfolioStore — JSON persistence
│       └── backend.py       # PortfolioBackend Protocol, RemotePortfolioBackend adapter, create_backend()
└── kanboard_cli/            # CLI package
    ├── main.py              # Click root group, global options (incl. --portfolio-backend)
    ├── formatters.py        # table/json/csv/quiet renderers
    ├── renderers.py         # ASCII dependency graph, progress bars, portfolio summary
    ├── workflow_loader.py   # Plugin discovery
    ├── commands/            # One module per CLI command group
    │   ├── portfolio.py     # 12 CRUD/query subcommands + migrate group (status/diff/local-to-remote/remote-to-local)
    │   └── milestone.py     # 7 subcommands for cross-project milestone management
    └── workflows/base.py    # BaseWorkflow ABC
tests/
├── unit/                    # Mocked httpx tests
│   ├── resources/           # One test file per resource module (incl. test_portfolios.py, test_milestones.py)
│   └── orchestration/       # Orchestration unit tests (conftest + test_store, test_portfolio, test_dependencies, test_backend)
├── cli/                     # CliRunner output tests
└── integration/             # Docker lifecycle tests (incl. test_plugin_backend.py)
```

## Testing

- Unit tests use `pytest-httpx` to mock HTTP; one test file per resource module in `tests/unit/resources/`
- CLI tests use Click `CliRunner`; verify all 4 output formats (table, json, csv, quiet)
- Integration tests run against Docker `kanboard/kanboard:latest` via `docker-compose.test.yml`
- Test files mirror source structure: `src/kanboard/resources/tasks.py` → `tests/unit/resources/test_tasks.py`

## Key References

- `docs/plan/01-architecture.md` — ADRs 1–15, directory structure, config schema
- `docs/plan/02-api-reference.md` — All 158 JSON-RPC method signatures
- `docs/plan/03-milestone-1-foundation.md` through `06-milestone-4-ship.md` — Implementation tasks
- `docs/design/cross-project-orchestration.md` — Orchestration research, architecture, Phase 0/1 roadmap
- `docs/design/phase-0-cross-project-orchestration.md` — Phase 0 detailed design
- `docs/tasks/` — Per-task implementation notes for the orchestration phase
- `CLAUDE.md` — Concise AI context (tech stack, gotchas, commands, orchestration metadata keys)
