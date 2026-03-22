# Milestone 4: Ship It (P3) — Tasks 42–48

> ← [Milestone 3](05-milestone-3-extended.md) | [README](README.md) | [Appendices](07-appendices.md) →

---

### Task 42: Integration test suite
- [ ] **P3** | XL | Deps: All SDK/CLI tasks

`docker-compose.test.yml` with `kanboard/kanboard:latest`. Pytest fixtures for lifecycle. CRUD lifecycle tests for every resource. Idempotent. `make test-integration`.

### Task 43: CLI output tests
- [ ] **P3** | M | Deps: 8, 9, 10

Snapshot tests via CliRunner with mocked SDK. All 4 formats, error cases, empty results, edge cases.

### Task 44: README and documentation
- [ ] **P3** | L | Deps: All feature tasks

Installation, quick start, full CLI reference, SDK usage guide, configuration reference, workflow development guide, contributing guide.

### Task 45: PyPI packaging and CI/CD
- [ ] **P3** | M | Deps: 1, 42

Finalize `pyproject.toml` metadata. GitHub Actions: lint -> test -> build -> publish on tag. `kanboard --version`.

### Task 46: User API authentication
- [ ] **P3** | M | Deps: 2, 4, 38

Config: `auth_mode = "user"`, `username`, `password`/`token`. CLI: `--auth-mode user`. Enables "Me" procedures.

### Task 47: Shell completions
- [ ] **P3** | S | Deps: 8

`kanboard completion bash|zsh|fish|install`. Click's built-in `shell_complete`.

### Task 48: Config management CLI
- [ ] **P3** | M | Deps: 4, 8, 39

`kanboard config init|show|path|profiles|test`. Init uses `tomli_w`. Show masks tokens. Test calls `getVersion`.

---

