# Milestone 3: Extended Coverage (P2) — Tasks 28–41

> ← [Milestone 2](04-milestone-2-core.md) | [README](README.md) | [Milestone 4](06-milestone-4-ship.md) →
>
> Rounds out complete API coverage. SDK + CLI combined in each task. API specs in [02-api-reference.md](02-api-reference.md). Workflow plugin architecture in [07-appendices.md](07-appendices.md#appendix-c-example-workflow-reference).

> Rounds out complete API coverage. SDK + CLI in each task.

---

### Task 28: Project files — SDK + CLI
- [ ] **P2** | M | Deps: 2, 5, 8
- 6 methods. See [Project Files API](#api-category-project-files-6-methods). CLI: `kanboard project-file list|get|upload|download|remove|remove-all`. Base64 encode/decode transparently.

### Task 29: Task files — SDK + CLI
- [ ] **P2** | M | Deps: 2, 5, 8
- 6 methods. See [Task Files API](#api-category-task-files-6-methods). CLI: `kanboard task-file list|get|upload|download|remove|remove-all`.

### Task 30: Project metadata — SDK + CLI
- [ ] **P2** | S | Deps: 2, 8
- 4 methods. See [Project Metadata API](#api-category-project-metadata-4-methods). CLI: `kanboard project-meta list|get|set|remove`.

### Task 31: Task metadata — SDK + CLI
- [ ] **P2** | S | Deps: 2, 8
- 4 methods. See [Task Metadata API](#api-category-task-metadata-4-methods). CLI: `kanboard task-meta list|get|set|remove`.

### Task 32: Project permissions — SDK + CLI
- [ ] **P2** | M | Deps: 2, 5, 8, 18
- 9 methods. See [Project Permissions API](#api-category-project-permissions-9-methods). CLI: `kanboard project-access list|assignable|add-user|add-group|remove-user|remove-group|set-user-role|set-group-role|user-role`.

### Task 33: Groups — SDK + CLI
- [ ] **P2** | S | Deps: 2, 5, 8
- 5 methods. See [Groups API](#api-category-groups-5-methods). CLI: `kanboard group list|get|create|update|remove`.

### Task 34: Group members — SDK + CLI
- [ ] **P2** | S | Deps: 2, 5, 8, 33
- 5 methods. See [Group Members API](#api-category-group-members-5-methods). CLI: `kanboard group member list|groups|add|remove|check`.

### Task 35: External task links — SDK + CLI
- [ ] **P2** | M | Deps: 2, 5, 8
- 7 methods. See [External Task Links API](#api-category-external-task-links-7-methods). CLI: `kanboard external-link types|dependencies|list|get|create|update|remove`.

### Task 36: Automatic actions — SDK + CLI
- [ ] **P2** | M | Deps: 2, 5, 8
- 6 methods. See [Automatic Actions API](#api-category-automatic-actions-6-methods). CLI: `kanboard action list|available|events|compatible-events|create|remove`.

### Task 37: Subtask time tracking — SDK + CLI
- [ ] **P2** | S | Deps: 2, 8, 17
- 4 methods. See [Subtask Time Tracking API](#api-category-subtask-time-tracking-4-methods). CLI: `kanboard timer status|start|stop|spent`.

### Task 38: Current user ("Me") — SDK + CLI
- [ ] **P2** | M | Deps: 2, 5, 8
- 7 methods. See [Current User API](#api-category-current-user--me-7-methods). CLI: `kanboard me [dashboard|activity|projects|overdue|create-project]`. **Note:** Requires User API auth — raise `KanboardAuthError` with clear message until Task 46.

### Task 39: Application info — SDK + CLI
- [ ] **P2** | S | Deps: 2, 8
- 7 methods. See [Application API](#api-category-application-7-methods). CLI: `kanboard app version|timezone|colors|default-color|roles`.

### Task 40: Workflow plugin architecture
- [ ] **P2** | L | Deps: 2, 8

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

### Task 41: Example workflow — separate repository
- [ ] **P2** | L | Deps: 6, 7, 40

Build a reference workflow plugin in a **separate repository** that demonstrates the full workflow system (Task 40). This serves as a template for users building their own workflows. The workflow should exercise: reading workflow-specific config from `[workflows.<name>]`, registering Click subcommands, and using the `KanboardClient` SDK for task creation and project management.

---

