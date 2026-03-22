# kanboard-cli — Complete Build Plan

> **A reusable Python SDK (`import kanboard`) + Click-based CLI (`kanboard-cli`), publishable to PyPI and GitHub, with complete Kanboard JSON-RPC API coverage and a plugin system for user-defined workflows.**
>
> This plan is self-contained. It includes all architecture decisions, API specifications, code patterns, and context needed to execute every task from an empty repository.

---

## Documents

| File | Contents |
|---|---|
| [01-architecture.md](01-architecture.md) | ADRs, directory structure, configuration schema |
| [02-api-reference.md](02-api-reference.md) | Complete Kanboard JSON-RPC API spec (all 158 methods) |
| [03-milestone-1-foundation.md](03-milestone-1-foundation.md) | Tasks 1–10 (P0): scaffolding, transport, exceptions, config, models, task/project SDK+CLI ✅ |
| [04-milestone-2-core.md](04-milestone-2-core.md) | Tasks 11–27 (P1): board, columns, swimlanes, comments, categories, tags, subtasks, users, links, CLI commands, tests ✅ |
| [05-milestone-3-extended.md](05-milestone-3-extended.md) | Tasks 28–41 (P2): files, metadata, permissions, groups, actions, time tracking, me, application, workflow system ✅ |
| [06-milestone-4-ship.md](06-milestone-4-ship.md) | Tasks 42–48 (P3): integration tests, docs, PyPI, user auth, completions, config CLI |
| [07-appendices.md](07-appendices.md) | Dependency graph, API coverage matrix, example workflow reference |

---

## Overview

| Metric | Value |
|---|---|
| **Total tasks** | 48 |
| **P0 — Critical / Foundational** | 10 ✅ |
| **P1 — High** | 17 ✅ |
| **P2 — Medium** | 14 (13 ✅, 1 out-of-scope*) |
| **P3 — Nice-to-have / Polish** | 7 |
| **Kanboard API methods covered** | 158 across 24 categories |
| **Tests passing** | 1753 |
| **Resource test coverage** | 100% (852 stmts, 0 missed) |

\* Task 41 (example workflow) is in a separate repository per ADR-11.

## High-Level Roadmap

```
Milestone 1: Foundation          ████████████████████  Tasks 1–10  (P0) ✅
Milestone 2: Core Coverage       ████████████████████  Tasks 11–27 (P1) ✅
Milestone 3: Extended Coverage   ████████████████████  Tasks 28–41 (P2) ✅
Milestone 4: Ship It             ░░░░░░░░░░░░░░░░░░░░  Tasks 42–48 (P3)
```
