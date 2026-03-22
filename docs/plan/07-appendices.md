# Appendices

> ← [Milestone 4](06-milestone-4-ship.md) | [README](README.md)

---

## Appendix A: Dependency Graph

```
Task 1 (scaffolding) ──────────────────────────┐
Task 3 (exceptions) ───> Task 2 (transport) ───┤
Task 4 (config) ────────────────────────────────┤
Task 5 (models) ────────────────────────────────┤
                                                │
                    ┌───────────────────────────┤
                    v                           v
            Tasks 6-7 (SDK:             Task 8 (CLI skeleton)
            tasks, projects)            Task 9 (formatters)
                    │                           │
                    └──────────┬────────────────┘
                               v
                        Task 10 (CLI: task +
                        project commands)
                               │
                    ┌──────────┴──────────────────────┐
                    v                                  v
            Tasks 11-20 (SDK:                   Tasks 21-26 (CLI:
            all remaining                       commands for M2
            resources)                          modules)
                    │                                  │
                    └──────────┬───────────────────────┘
                               v
                        Task 27 (M2 tests)
                               │
                    ┌──────────┴──────────────────────┐
                    v                                  v
            Tasks 28-39 (SDK+CLI:               Task 40 (workflow
            extended resources)                 plugin system)
                    │                                  │
                    │                                  v
                    │                           Task 41 (example
                    │                           workflow — separate repo)
                    └──────────┬───────────────────────┘
                               v
                        Tasks 42-48 (ship it)
```

---

## Appendix B: API Coverage Matrix

| # | Category | Methods | SDK Task | CLI Task | Pri |
|---|---|---|---|---|---|
| 1 | Application | 7 | 39 | 39 | P2 |
| 2 | Projects | 14 | 7 | 10 | P0 |
| 3 | Board | 1 | 11 | 21 | P1 |
| 4 | Tasks | 14 | 6 | 10 | P0 |
| 5 | Columns | 6 | 12 | 21 | P1 |
| 6 | Swimlanes | 11 | 13 | 21 | P1 |
| 7 | Categories | 5 | 15 | 23 | P1 |
| 8 | Comments | 5 | 14 | 22 | P1 |
| 9 | Current User | 7 | 38 | 38 | P2 |
| 10 | Subtasks | 5 | 17 | 24 | P1 |
| 11 | Time Tracking | 4 | 37 | 37 | P2 |
| 12 | Users | 10 | 18 | 25 | P1 |
| 13 | Tags | 7 | 16 | 23 | P1 |
| 14 | Link Types | 7 | 19 | 26 | P1 |
| 15 | Task Links | 5 | 20 | 26 | P1 |
| 16 | External Links | 7 | 35 | 35 | P2 |
| 17 | Groups | 5 | 33 | 33 | P2 |
| 18 | Group Members | 5 | 34 | 34 | P2 |
| 19 | Actions | 6 | 36 | 36 | P2 |
| 20 | Project Files | 6 | 28 | 28 | P2 |
| 21 | Task Files | 6 | 29 | 29 | P2 |
| 22 | Project Meta | 4 | 30 | 30 | P2 |
| 23 | Task Meta | 4 | 31 | 31 | P2 |
| 24 | Permissions | 9 | 32 | 32 | P2 |
| | **Total** | **158** | | | |

---

## Appendix C: Example Workflow Reference

Task 41 describes building a sample workflow plugin in a **separate repository** to serve as a reference implementation for the workflow system (Task 40). The specification for that workflow is maintained in its own repo and is not part of the `kanboard-cli` project.

A workflow plugin is any Python file or package dropped into `~/.config/kanboard/workflows/` that contains a `BaseWorkflow` subclass. It can:

- Register custom CLI subcommands (e.g., `kanboard myworkflow run`)
- Read its own config section from `[workflows.<name>]` in `config.toml`
- Use the full `KanboardClient` SDK to interact with Kanboard
- Call external APIs or perform any custom logic

See [Task 40 in Milestone 3](05-milestone-3-extended.md#task-40-workflow-plugin-architecture) for the `BaseWorkflow` ABC and discovery mechanism.
