# Milestone 2: Core Coverage (P1) — Tasks 11–27

> ← [Milestone 1](03-milestone-1-foundation.md) | [README](README.md) | [Milestone 3](05-milestone-3-extended.md) →
>
> Each SDK task follows the pattern established in [Task 6](03-milestone-1-foundation.md#task-6-tasks-resource-module--sdk). Each CLI task follows [Task 10](03-milestone-1-foundation.md#task-10-task--project-cli-commands). All API method specs are in [02-api-reference.md](02-api-reference.md).

> Each SDK task follows Task 6's pattern. Each CLI task follows Task 10's pattern.

---

### Task 11: Board resource — SDK
- [ ] **P1** | M | Deps: 2, 5
- 1 method: `get_board(project_id)`. See [Board API](#api-category-board-1-method). Complex nested response.

### Task 12: Columns resource — SDK
- [ ] **P1** | M | Deps: 2, 5
- 6 methods. See [Columns API](#api-category-columns-6-methods). Wire to `KanboardClient.columns`.

### Task 13: Swimlanes resource — SDK
- [ ] **P1** | M | Deps: 2, 5
- 11 methods. See [Swimlanes API](#api-category-swimlanes-11-methods). Wire to `KanboardClient.swimlanes`.

### Task 14: Comments resource — SDK
- [ ] **P1** | S | Deps: 2, 5
- 5 methods. See [Comments API](#api-category-comments-5-methods). Wire to `KanboardClient.comments`.

### Task 15: Categories resource — SDK
- [ ] **P1** | S | Deps: 2, 5
- 5 methods. See [Categories API](#api-category-categories-5-methods). Wire to `KanboardClient.categories`.

### Task 16: Tags resource — SDK
- [ ] **P1** | S | Deps: 2, 5
- 7 methods. See [Tags API](#api-category-tags-7-methods). Wire to `KanboardClient.tags`.

### Task 17: Subtasks resource — SDK
- [ ] **P1** | S | Deps: 2, 5
- 5 methods. See [Subtasks API](#api-category-subtasks-5-methods). Wire to `KanboardClient.subtasks`.

### Task 18: Users resource — SDK
- [ ] **P1** | M | Deps: 2, 5
- 10 methods. See [Users API](#api-category-users-10-methods). Wire to `KanboardClient.users`.

### Task 19: Link types resource — SDK
- [ ] **P1** | S | Deps: 2, 5
- 7 methods. See [Link Types API](#api-category-link-types-7-methods). Wire to `KanboardClient.links`.

### Task 20: Internal task links resource — SDK
- [ ] **P1** | S | Deps: 2, 5, 19
- 5 methods. See [Internal Task Links API](#api-category-internal-task-links-5-methods). Wire to `KanboardClient.task_links`.

### Task 21: Board + Column + Swimlane CLI commands
- [ ] **P1** | L | Deps: 8, 9, 11, 12, 13

```
kanboard board show <project_id>
kanboard column list|get|add|update|remove|move
kanboard swimlane list [--all]|get|get-by-name|add|update|remove|enable|disable|move
```

### Task 22: Comment CLI commands
- [ ] **P1** | S | Deps: 8, 9, 14

```
kanboard comment list <task_id> | get <id> | add <task_id> <content> --user-id | update <id> <content> | remove <id> [--yes]
```

### Task 23: Category + Tag CLI commands
- [ ] **P1** | M | Deps: 8, 9, 15, 16

```
kanboard category list|get|create|update|remove
kanboard tag list [--project-id]|create|update|remove|set <project_id> <task_id> <tags>...|get <task_id>
```

### Task 24: Subtask CLI commands
- [ ] **P1** | S | Deps: 8, 9, 17

```
kanboard subtask list|get|create|update|remove
```

### Task 25: User CLI commands
- [ ] **P1** | M | Deps: 8, 9, 18

```
kanboard user list|get|get-by-name|create|update|remove [--yes]|enable|disable|is-active
```
Password prompt via `click.prompt(hide_input=True)` when not provided.

### Task 26: Link CLI commands
- [ ] **P1** | M | Deps: 8, 9, 19, 20

```
kanboard link list|get|get-by-label|create|update|remove
kanboard task-link list|get|create|update|remove
```

### Task 27: Unit + CLI tests for Milestone 2
- [ ] **P1** | L | Deps: 11-26

Unit tests for all resource modules with mocked httpx. CLI output tests via CliRunner across all 4 formats. Error path tests. Target >=90% coverage on `src/kanboard/resources/`.

---

