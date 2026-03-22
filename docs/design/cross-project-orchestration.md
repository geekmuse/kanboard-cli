# Cross-Project Orchestration for Kanboard

## Research Findings & CLI/SDK Design

**Date:** 2026-03-22
**Author:** kanboard-cli team
**Status:** Proposal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Findings](#2-research-findings)
   - [2.1 Existing Kanboard Capabilities](#21-existing-kanboard-capabilities-already-cross-project)
   - [2.2 Existing Plugins](#22-existing-plugins-evaluated)
   - [2.3 Approaches with Existing Functionality](#23-approaches-with-existing-functionality)
   - [2.4 Community Discussions](#24-community-discussions--feature-requests)
   - [2.5 Third-Party Tools](#25-third-party-tools--middleware)
   - [2.6 Gap Analysis](#26-gap-analysis)
3. [Solution Architecture](#3-solution-architecture)
   - [3.1 Two-Layer Approach](#31-two-layer-approach)
   - [3.2 Problem Statement & User Stories](#32-problem-statement--user-stories)
   - [3.3 The Kanboard Portfolio Plugin (External Dependency)](#33-the-kanboard-portfolio-plugin-external-dependency)
   - [3.4 CLI/SDK Integration](#34-clisdk-integration)
   - [3.5 Implementation Roadmap](#35-implementation-roadmap)
4. [Appendix: Existing Cross-Project Link Verification](#appendix-existing-cross-project-link-verification)

---

## 1. Executive Summary

**The good news:** Kanboard's internal task link system (`task_has_links` table) is **already cross-project by design**. Tasks are referenced by global ID, not scoped to a project. You can link Task #42 in "Product Alpha" to Task #99 in "Marketing Site" using the existing `blocks`/`is blocked by` relationship — right now, via the API or the UI.

**The bad news:** While the *data model* supports cross-project links, Kanboard provides **zero cross-project visualization, aggregation, or coordination tooling**. There is no way to:
- See a unified view of tasks across multiple projects
- Visualize cross-project dependency chains
- Define or track milestones that span projects
- Get a "portfolio" or "program" level perspective

**Our recommendation:** Build a two-layer solution:

1. **A Kanboard PHP plugin ("Portfolio")** — a separate project — that adds server-side data model extensions (portfolios, cross-project milestones, dependency metadata), new views (unified board, timeline, dependency graph), and new API endpoints.

2. **A CLI/SDK companion layer** in this project (`kanboard-cli`) that provides cross-project orchestration both as a standalone CLI capability (Phase 0, no plugin required) and as a typed client for the plugin's API endpoints (Phase 1+).

No existing plugin or third-party tool adequately solves this problem. The closest candidates (Bigboard, Gantt, Milestone, Relation Graph) each address a fragment but none provide the integrated portfolio management experience required.

---

## 2. Research Findings

### 2.1 Existing Kanboard Capabilities (Already Cross-Project)

#### Internal Task Links — The Hidden Cross-Project Feature

The `task_has_links` table schema reveals that task links are **globally scoped**:

```sql
CREATE TABLE task_has_links (
    id INTEGER PRIMARY KEY,
    link_id INTEGER NOT NULL,       -- references links(id) — relationship type
    task_id INTEGER NOT NULL,       -- references tasks(id) — ANY task, any project
    opposite_task_id INTEGER NOT NULL, -- references tasks(id) — ANY task, any project
    FOREIGN KEY(link_id) REFERENCES links(id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(opposite_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
```

**Built-in link types** (relevant to cross-project dependencies):

| Link ID | Label | Opposite |
|---------|-------|----------|
| 2 | blocks | is blocked by |
| 3 | is blocked by | blocks |
| 6 | is a child of | is a parent of |
| 7 | is a parent of | is a child of |
| 8 | targets milestone | is a milestone of |
| 9 | is a milestone of | targets milestone |

**Key finding:** You can already call `createTaskLink(task_id=42, opposite_task_id=99, link_id=2)` where task 42 is in Project A and task 99 is in Project B. The link type "blocks" creates a cross-project dependency. This works in the UI too — the task detail page shows links to tasks in other projects.

**What's missing is entirely on the visualization/aggregation side.**

#### Automatic Actions — Limited Cross-Project Potential

Two built-in automatic actions work cross-project:
- **"Duplicate the task to another project"** — on task close, copies task to a target project
- **"Move the task to another project"** — on column change, moves task to a target project

These are coarse-grained (whole-task operations) and don't support conditional logic, dependency-aware triggering, or sequencing.

#### Webhooks — External Orchestration Hook

Kanboard fires webhooks for all task lifecycle events including:
- `task.close`, `task.open`, `task.create`
- `task.move.column`, `task.move.project`
- `task_internal_link.create_update`, `task_internal_link.delete`

A webhook receiver could implement cross-project orchestration logic externally, but this requires deploying and maintaining a separate service.

#### Project Metadata — Extensible Key-Value Store

The `project_metadata` and `task_metadata` APIs provide arbitrary key-value storage on projects and tasks. This could store portfolio membership, milestone assignments, or dependency metadata without schema changes — though querying is limited to per-entity lookups (no cross-entity queries).

### 2.2 Existing Plugins Evaluated

#### Bigboard (BlueTeck) — ★★☆☆☆ for our use case

- **What it does:** Displays multiple project boards side-by-side in a single view. Each project renders its own board columns and swimlanes.
- **Repository:** https://github.com/BlueTeck/kanboard_plugin_bigboard
- **Status:** Maintenance mode ("no significant feature development"). Last meaningful update ~2020.
- **Relevance:** Provides a *visual* aggregation of multiple boards, but:
  - No dependency visualization between projects
  - No filtering, searching, or sorting across projects
  - No milestone or timeline view
  - It's literally just multiple boards rendered on one page
  - Cannot show dependency relationships between tasks in different project columns
- **Verdict:** Useful for a quick glance at multiple boards, but does not solve cross-project coordination.

#### Gantt (Official Kanboard Plugin) — ★★☆☆☆ for our use case

- **What it does:** Adds Gantt chart views at the project level (task timelines by date_started/date_due) and a project-level Gantt showing project date ranges.
- **Repository:** https://github.com/kanboard/plugin-gantt
- **Status:** Official plugin, v1.0.6, requires Kanboard > 1.2.3. Maintained.
- **Relevance:**
  - The *project-level* Gantt shows all projects on a timeline — useful for seeing project date ranges overlap
  - The *task-level* Gantt is scoped to a single project — doesn't show cross-project dependencies
  - No dependency arrows or critical path visualization
  - No interactive drag-and-drop scheduling
- **Verdict:** Partially useful for seeing project-level timelines, but lacks cross-project task-level Gantt with dependency arrows.

#### Milestone Plugin (oliviermaridat) — ★★★☆☆ for our use case

- **What it does:** Uses the built-in "is a milestone of" / "targets milestone" link types to create a milestone section on task detail pages. Shows all tasks linked to a "milestone task" with their status.
- **Repository:** https://github.com/oliviermaridat/kanboard-milestone-plugin
- **Status:** v1.1.2, last update ~2020. Works with Kanboard >= 1.0.37.
- **Relevance:**
  - Leverages the existing cross-project link capability — milestone tasks can link to tasks in other projects
  - Shows milestone progress (completed vs. total linked tasks)
  - Integrates with the Gantt plugin for date inference
  - **Key limitation:** Milestones are individual tasks, not first-class entities. No global milestone dashboard. No portfolio-level milestone timeline. Requires navigating to each milestone task individually.
- **Verdict:** Best existing building block. Proves the data model works. But needs a portfolio-level aggregation layer on top.

#### Relation Graph (BlueTeck) — ★★☆☆☆ for our use case

- **What it does:** Renders a force-directed graph visualization of task relationships (internal links) using a JavaScript graph library.
- **Repository:** https://github.com/BlueTeck/kanboard_plugin_relationgraph
- **Status:** Maintenance mode. Requires Kanboard >= 1.2.10.
- **Relevance:**
  - Shows task link relationships as a graph — including cross-project links if they exist
  - Scoped to a single task's relationship neighborhood
  - No project-level or portfolio-level graph
  - No dependency chain / critical path analysis
  - Limited to visualization; no interaction or status-aware rendering
- **Verdict:** Demonstrates that graph visualization of task relationships is feasible in Kanboard's plugin system. Could inform our dependency graph design.

#### Other Plugins Reviewed (Not Relevant)

| Plugin | Why Not |
|--------|---------|
| **Glancer** (aljawaid) | Dashboard widgets for project summaries — single-project scoped |
| **Global Search** (kenlog) | Text search across projects — useful but not dependency-aware |
| **MetaMagik** (creecros) | Enhanced metadata UI — could complement but doesn't solve core problem |
| **Metadata** (BlueTeck) | Custom fields on tasks/projects — data storage only |
| **ProjectReports** (noclickhouse) | Project-level reporting — single-project scoped |
| **Creecros Filter Pack** | Enhanced task filtering — single-project scoped |
| **TableView** (greyaz) | Alternative list view — single-project scoped |
| **StarredProjects** (biblibre) | Bookmark favourite projects — organizational only |

### 2.3 Approaches with Existing Functionality

#### Approach A: Cross-Project Links + Metadata Convention (API-Driven)

**How it works:**
1. Use `createTaskLink` with `link_id=2` (blocks) to create cross-project dependency links
2. Store portfolio membership in project metadata: `saveProjectMetadata(project_id, {"portfolio": "Launch-Q2-2026"})`
3. Store milestone assignments in task metadata: `saveTaskMetadata(task_id, {"milestone": "v2.0-launch", "milestone_target_date": "2026-06-01"})`
4. Build a Python CLI tool (using our SDK) that queries all projects in a portfolio, fetches all tasks, resolves all cross-project links, and renders unified views

**Pros:**
- Zero Kanboard modifications needed
- Works today with our existing SDK
- Full control over visualization (CLI tables, exported HTML/JSON)
- Can implement sophisticated logic (critical path, dependency chains)

**Cons:**
- No in-browser Kanboard UI — everything is CLI/external
- Requires many API calls to assemble cross-project views (N+1 problem: list projects, then fetch all tasks per project, then fetch all links per task)
- Metadata conventions are fragile (no schema validation, no referential integrity)
- Other Kanboard users who don't use the CLI won't see the portfolio views

**Viability:** ★★★★☆ — Pragmatic starting point. Best approach for immediate relief before a plugin is built.

#### Approach B: Webhook-Driven Orchestration Service

**How it works:**
1. Deploy a webhook receiver (Python FastAPI or similar)
2. Configure Kanboard to send all events to the receiver
3. The receiver maintains a cross-project dependency graph in a local database
4. When a task is closed/moved, the receiver checks if it unblocks tasks in other projects and takes action (updates status, sends notifications, creates comments)

**Pros:**
- Real-time reactive orchestration
- Can implement complex business logic (cascading unblocks, auto-assignment)
- Decoupled from Kanboard's plugin architecture

**Cons:**
- Requires deploying and maintaining a separate service
- Webhook receiver must respond in <1 second (Kanboard's synchronous webhook limitation)
- No UI integration in Kanboard
- State synchronization challenges if the service goes down

**Viability:** ★★★☆☆ — Good for automation/enforcement, but doesn't solve the visualization need.

#### Approach C: "Master Project" with Sub-Task Linking

**How it works:**
1. Create a dedicated "Portfolio: Q2 Launch" project
2. Create milestone tasks in this project: "Product A v2.0 Released", "Marketing Site Live", etc.
3. Link milestone tasks to actual tasks in product/marketing projects using "is a milestone of"
4. Use the Milestone plugin to see progress on each milestone task
5. Use the Gantt plugin on the portfolio project for a timeline view

**Pros:**
- Uses existing plugins (Milestone + Gantt)
- Some visualization in Kanboard's UI
- Milestones are visible to all Kanboard users

**Cons:**
- Manual maintenance burden — milestone links must be kept in sync
- No automatic dependency enforcement
- Gantt shows only the milestone tasks' dates, not the dependent tasks
- Still no unified task list across projects
- The "portfolio project" doesn't have real columns/swimlanes relevant to the work

**Viability:** ★★★☆☆ — Reasonable low-effort workaround with significant manual overhead.

### 2.4 Community Discussions & Feature Requests

Kanboard's GitHub issues and forum discussions reveal this is a **frequently requested capability** with no official solution:

1. **Multi-project Gantt / portfolio view** — Repeatedly requested in GitHub issues. The official position is that Kanboard is intentionally a "minimalist" tool and portfolio management is out of scope for core.

2. **Cross-project dependencies** — Users have noted that internal task links work cross-project but there's no visibility into this. Feature requests for "dependency-aware column restrictions" (can't move task to Done if it's blocked by an open task in another project) have not been implemented.

3. **Dashboard improvements** — The built-in dashboard (`getMyDashboard`) shows tasks assigned to the current user across projects, which is the closest thing to a cross-project view. It shows tasks, subtasks, and project activity but not dependency relationships.

4. **General consensus:** Users who need portfolio management typically either (a) use a separate tool on top of Kanboard, (b) collapse into a single project with tags, or (c) accept the limitation. There is no established community solution.

### 2.5 Third-Party Tools / Middleware

| Tool | Approach | Relevance |
|------|----------|-----------|
| **Planka** | Alternative to Kanboard with multi-board support | Replacement, not integration |
| **Vikunja** | Alternative with namespace/project hierarchy | Replacement, not integration |
| **Taiga** | Agile PM with epics spanning projects | Replacement, not integration |
| **Custom Grafana dashboard** | Query Kanboard's database directly, build cross-project dashboards | Read-only visualization; requires direct DB access |
| **n8n / Zapier** | Workflow automation connecting Kanboard webhooks to actions | Orchestration only, no visualization |
| **Our SDK/CLI** | Python SDK with full API coverage | Best foundation for building the solution |

**No third-party tool was found that provides a portfolio management layer specifically designed to sit on top of Kanboard.**

### 2.6 Gap Analysis

| Requirement | Existing Coverage | Gap |
|------------|------------------|-----|
| Cross-project task dependencies (data) | ✅ Built-in task links work cross-project | None — works today |
| Cross-project dependency visualization | ❌ No unified graph or dependency chain view | **Critical gap** |
| Unified multi-project task view | ❌ Only per-user dashboard (own tasks) | **Critical gap** |
| Cross-project milestones (data) | 🟡 Milestone plugin uses task links | Limited — no portfolio-level aggregation |
| Cross-project milestone dashboard | ❌ No portfolio-level milestone view | **Critical gap** |
| Cross-project Gantt/timeline | 🟡 Project-level Gantt exists | No task-level cross-project Gantt |
| Dependency enforcement | ❌ No blocking/gating based on dependencies | **Significant gap** |
| Cross-project notifications | ❌ No dependency-aware notifications | **Moderate gap** |
| Portfolio/program grouping | ❌ No concept of project groups | **Critical gap** |

---

## 3. Solution Architecture

### 3.1 Two-Layer Approach

The solution is split across two projects:

| Layer | Project | Language | Responsibility |
|-------|---------|----------|----------------|
| **Server-side plugin** | `kanboard-plugin-portfolio` (separate repo) | PHP | Database tables, JSON-RPC API endpoints, Kanboard UI views (dashboards, graphs, board indicators), event listeners, automatic actions |
| **CLI/SDK client** | `kanboard-cli` (this repo) | Python | CLI-side orchestration (Phase 0 — no plugin), typed SDK resource modules for the plugin API (Phase 1+), CLI commands for portfolio/milestone/dependency workflows |

**Key principle:** The CLI provides cross-project orchestration value **independently** of the plugin (Phase 0), and gains additional capabilities when the plugin is installed (Phase 1+). The plugin is an external dependency, not something built or maintained within this project.

### 3.2 Problem Statement & User Stories

#### Problem Statement

A product company managing multiple software products and a marketing/site project in Kanboard has no way to visualize, track, or enforce the cross-project dependencies that are fundamental to coordinated launches. While Kanboard's data model supports cross-project task links, the lack of portfolio-level views, milestone aggregation, and dependency visualization forces users into inadequate workarounds.

#### User Stories

**US-1: Portfolio Definition**
> As a project manager, I want to group related Kanboard projects into a "portfolio" (e.g., "Q2 2026 Launch") so that I can manage them as a coordinated program.

**US-2: Unified Task View**
> As a project manager, I want to see a single list/table of all tasks across all projects in a portfolio, filterable by project, status, assignee, tag, and date, so that I can identify bottlenecks and make resource allocation decisions.

**US-3: Cross-Project Dependency Declaration**
> As a developer, I want to declare that "Task #42: Publish Product Page" in the Site Project is blocked by "Task #15: Finalize Product Branding" in Product A, so that the dependency is formally tracked.

**US-4: Dependency Chain Visualization**
> As a project manager, I want to see a visual graph of all cross-project dependencies in my portfolio, with color-coded status indicators (open/blocked/completed), so that I can identify the critical path to launch.

**US-5: Cross-Project Milestones**
> As a project manager, I want to define milestones like "Product A v2.0 Feature Complete" that aggregate tasks from multiple projects, with a progress percentage and target date, so that I can track convergence toward key dates.

**US-6: Milestone Dashboard**
> As a stakeholder, I want to see a dashboard of all portfolio milestones with progress bars, target dates, and at-risk indicators, so that I can quickly assess program health.

**US-7: Dependency-Aware Notifications**
> As a developer, I want to be notified when a task that blocks my work in another project is completed, so that I know I can begin my dependent task.

**US-8: Cross-Project Timeline**
> As a project manager, I want to see a Gantt-style timeline showing tasks from multiple projects with dependency arrows between them, so that I can plan sequencing and identify scheduling conflicts.

**US-9: Blocking Indicators on Board**
> As a developer, when viewing any project board, I want to see visual indicators on tasks that are blocked by tasks in other projects (and which project/task is blocking), so that I understand external dependencies without leaving my board.

**US-10: API Access**
> As an automation engineer, I want API endpoints for all portfolio features so that I can build CLI tools, reports, and integrations using our Python SDK.

#### User Story Coverage by Layer

| User Story | Phase 0 (CLI-only) | Phase 1+ (CLI + Plugin) |
|------------|---------------------|--------------------------|
| US-1 Portfolio Definition | ✅ Local JSON store + metadata sync | ✅ Server-side portfolio entities via plugin API |
| US-2 Unified Task View | ✅ CLI table output | ✅ CLI + Kanboard web UI |
| US-3 Dependency Declaration | ✅ Uses existing `task-link` commands | ✅ Same (built-in Kanboard feature) |
| US-4 Dependency Visualization | 🟡 ASCII graph in CLI | ✅ Interactive D3.js graph in Kanboard UI |
| US-5 Milestones | ✅ Local milestone definitions | ✅ Server-side milestone entities |
| US-6 Milestone Dashboard | 🟡 CLI progress bars | ✅ Web dashboard with progress bars |
| US-7 Notifications | ❌ Not feasible CLI-only | ✅ Plugin event listeners + automatic actions |
| US-8 Timeline | ❌ Not feasible CLI-only | ✅ Plugin Gantt timeline view |
| US-9 Board Indicators | ❌ Not feasible CLI-only | ✅ Plugin template hooks on board cards |
| US-10 API Access | ✅ Python orchestration classes | ✅ Plugin JSON-RPC endpoints + SDK resource modules |

### 3.3 The Kanboard Portfolio Plugin (External Dependency)

The Kanboard Portfolio plugin is a **separate PHP project** maintained in its own repository. It is not built, tested, or shipped as part of `kanboard-cli`.

> **Plugin specification:** See `/tmp/kanboard-portfolio-plugin-spec.md` for the complete
> implementation specification (2,400+ lines covering data model, all 28 API endpoints,
> controllers, templates, events, security, and testing strategy).

#### What the Plugin Provides

| Capability | Details |
|-----------|---------|
| **Database tables** | 4 new tables: `portfolios`, `portfolio_has_projects`, `milestones`, `milestone_has_tasks` |
| **JSON-RPC API** | 28 new methods across 6 categories (portfolio CRUD, project membership, milestone CRUD, milestone-task membership, dependency queries, unified task queries) |
| **Web UI** | Portfolio dashboard, unified task list, aggregate board, D3.js dependency graph, Gantt timeline, milestone management views |
| **Template hooks** | Board task blocking indicators, task detail milestone/dependency sections, dashboard sidebar, project sidebar |
| **Event system** | Listens to `task.close`/`task.open`/`task_internal_link.*`; fires `portfolio.dependency.resolved` |
| **Automatic actions** | "Notify on dependency resolved", "Comment on dependency resolved" |
| **Search filter** | `portfolio:` keyword in Kanboard's task search |

#### How This Project Relates to the Plugin

| Concern | Who Owns It |
|---------|------------|
| Plugin PHP code, schema, templates, JS assets | `kanboard-plugin-portfolio` repo |
| Plugin installation, packaging, Kanboard directory listing | `kanboard-plugin-portfolio` repo |
| Python SDK resource modules that call the plugin's API | **This project** (`kanboard-cli`) |
| CLI commands that wrap the plugin's API | **This project** (`kanboard-cli`) |
| CLI-only orchestration (Phase 0, no plugin) | **This project** (`kanboard-cli`) |
| Plugin specification document | Authored here, delivered to the plugin project |

#### Plugin API Summary (for SDK integration)

The plugin exposes 28 JSON-RPC methods. The CLI/SDK needs typed wrappers for all of them:

**Portfolio CRUD (6):** `createPortfolio`, `getPortfolio`, `getPortfolioByName`, `getAllPortfolios`, `updatePortfolio`, `removePortfolio`

**Portfolio ↔ Project Membership (4):** `addProjectToPortfolio`, `removeProjectFromPortfolio`, `getPortfolioProjects`, `getProjectPortfolios`

**Milestone CRUD (5):** `createMilestone`, `getMilestone`, `getPortfolioMilestones`, `updateMilestone`, `removeMilestone`

**Milestone ↔ Task Membership (5):** `addTaskToMilestone`, `removeTaskFromMilestone`, `getMilestoneTasks`, `getTaskMilestones`, `getMilestoneProgress`

**Dependency Queries (5):** `getPortfolioDependencies`, `getBlockedTasks`, `getBlockingTasks`, `getPortfolioCriticalPath`, `getPortfolioDependencyGraph`

**Unified Task Queries (3):** `getPortfolioTasks`, `getPortfolioTaskCount`, `getPortfolioOverview`

### 3.4 CLI/SDK Integration

#### New SDK Resource Modules (Phase 1+ — requires plugin)

```python
# src/kanboard/resources/portfolios.py
class PortfoliosResource:
    """Kanboard Portfolio Plugin API resource.
    Requires the Portfolio plugin to be installed on the Kanboard server.
    """
    def create_portfolio(self, name: str, **kwargs) -> int: ...
    def get_portfolio(self, portfolio_id: int) -> Portfolio: ...
    def get_all_portfolios(self) -> list[Portfolio]: ...
    def add_project_to_portfolio(self, portfolio_id: int, project_id: int, **kwargs) -> bool: ...
    def get_portfolio_dependencies(self, portfolio_id: int, cross_project_only: bool = True) -> list[dict]: ...
    def get_portfolio_critical_path(self, portfolio_id: int) -> list[dict]: ...
    def get_blocked_tasks(self, portfolio_id: int) -> list[dict]: ...
    # ... (all 28 methods)

# src/kanboard/resources/milestones.py
class MilestonesResource:
    """Kanboard Portfolio Plugin — Milestone management."""
    def create_milestone(self, portfolio_id: int, name: str, **kwargs) -> int: ...
    def get_milestone(self, milestone_id: int) -> Milestone: ...
    def get_portfolio_milestones(self, portfolio_id: int) -> list[Milestone]: ...
    def add_task_to_milestone(self, milestone_id: int, task_id: int, **kwargs) -> bool: ...
    def get_milestone_progress(self, milestone_id: int) -> MilestoneProgress: ...
    # ...
```

#### New Models

```python
@dataclasses.dataclass
class Portfolio:
    id: int
    name: str
    description: str
    owner_id: int
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_api(cls, data: dict) -> Self: ...

@dataclasses.dataclass
class Milestone:
    id: int
    portfolio_id: int
    name: str
    description: str
    target_date: datetime | None
    status: int
    color_id: str
    owner_id: int
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_api(cls, data: dict) -> Self: ...

@dataclasses.dataclass
class MilestoneProgress:
    milestone_id: int
    total: int
    completed: int
    percent: float
    is_at_risk: bool
    is_overdue: bool

    @classmethod
    def from_api(cls, data: dict) -> Self: ...
```

#### CLI Commands

```
kanboard portfolio list                              # List all portfolios
kanboard portfolio show <id>                         # Portfolio dashboard
kanboard portfolio create --name "Q2 Launch"         # Create portfolio
kanboard portfolio add-project <id> --project <pid>  # Add project
kanboard portfolio tasks <id> [--status active]      # Unified task list
kanboard portfolio dependencies <id>                  # Show dependency graph (ASCII)
kanboard portfolio critical-path <id>                 # Show critical path
kanboard portfolio blocked <id>                       # List blocked tasks

kanboard milestone list --portfolio <id>              # List milestones
kanboard milestone show <id>                          # Milestone detail + progress
kanboard milestone create --portfolio <id> --name "v2.0 Feature Complete"
kanboard milestone add-task <id> --task <tid>         # Add task to milestone
kanboard milestone progress <id>                      # Progress report
```

#### CLI Workflow Example

```bash
# Create a portfolio for the Q2 launch
$ kanboard portfolio create --name "Q2 2026 Launch" --description "Coordinated product launch"
Portfolio created: ID 1

# Add projects
$ kanboard portfolio add-project 1 --project 3   # Product A
$ kanboard portfolio add-project 1 --project 5   # Product B
$ kanboard portfolio add-project 1 --project 8   # Site Project

# Create cross-project dependencies (using existing task link API)
$ kanboard task-link create --task 42 --opposite-task 15 --link-type "is blocked by"
Task link created: Task #42 (Site) is blocked by Task #15 (Product A)

# Create a milestone
$ kanboard milestone create --portfolio 1 --name "Product Pages Live" \
    --target-date "2026-06-15"
Milestone created: ID 1

# Add tasks to milestone
$ kanboard milestone add-task 1 --task 15   # Product A: Finalize branding
$ kanboard milestone add-task 1 --task 42   # Site: Publish product page
$ kanboard milestone add-task 1 --task 55   # Site: Landing page

# View portfolio overview
$ kanboard portfolio show 1

  Portfolio: Q2 2026 Launch
  Projects: Product A, Product B, Site Project
  Active Tasks: 47 | Blocked: 12 | Milestones: 3

  Milestones:
    ████████░░  Product Pages Live (72%) - Target: Jun 15
    ████░░░░░░  Blog Series Launch (35%) - Target: Jun 22
    ██░░░░░░░░  Onboarding v2 (18%) - Target: Jul 01

# View blocked tasks
$ kanboard portfolio blocked 1

  BLOCKED TASKS (12)
  ─────────────────────────────────────────────────
  #42  Publish product page     [Site]      Blocked by: #15 (Product A) ⬤ OPEN
  #88  Blog post sequence       [Site]      Blocked by: #67 (Product B) ⬤ OPEN
  #91  Onboarding deep link     [Product A] Blocked by: #55 (Site)      ⬤ OPEN
  ...

# View critical path
$ kanboard portfolio critical-path 1

  CRITICAL PATH (longest dependency chain)
  ─────────────────────────────────────────────────
  1. #15  Finalize branding     [Product A]  ⬤ OPEN     Est: May 20
  2. #42  Publish product page  [Site]       🔴 BLOCKED  Est: May 30
  3. #88  Blog post sequence    [Site]       🔴 BLOCKED  Est: Jun 10
  4. #95  Social campaign       [Site]       🔴 BLOCKED  Est: Jun 15

  Critical path length: 4 tasks, ~26 days
  Bottleneck: Task #15 blocks 3 downstream tasks
```

### 3.5 Implementation Roadmap

#### Phase 0: CLI-Only Orchestration (this project)

> **Task list:** [docs/tasks/phase-0-cross-project-orchestration.md](../tasks/phase-0-cross-project-orchestration.md) — Tasks 49–62

**No plugin required.** Build cross-project orchestration as a CLI-side meta-construct using the existing Kanboard API:

- `src/kanboard/orchestration/` subpackage with `PortfolioManager`, `DependencyAnalyzer`, `LocalPortfolioStore`
- Portfolio/milestone definitions stored locally (`~/.config/kanboard/portfolios.json`) with metadata sync to Kanboard
- Cross-project dependencies via existing `task_has_links` (blocks/is blocked by)
- CLI commands: `kanboard portfolio`, `kanboard milestone`
- ASCII dependency graph renderer, critical path calculator

**Limitation:** No Kanboard UI integration. Metadata-based storage has no referential integrity. N+1 API calls for aggregation.

#### Phase 1: Plugin SDK Integration (this project — requires plugin)

> **Depends on:** The Kanboard Portfolio plugin being implemented and installed on the target Kanboard instance.

Once the plugin is available, this project adds:

- SDK resource modules (`src/kanboard/resources/portfolios.py`, `milestones.py`) wrapping the plugin's 28 JSON-RPC endpoints
- Typed dataclass models (`Portfolio`, `Milestone`, `MilestoneProgress`) with `from_api()` factories
- CLI commands rewritten to call the plugin API instead of the local-store/metadata approach
- Detection logic: CLI commands auto-detect whether the plugin is installed (by calling `getPortfolio` and checking for a JSON-RPC method-not-found error) and fall back to Phase 0 behavior if not

**Value:** Proper data model with referential integrity. Server-side queries (no N+1). CLI and Kanboard UI share the same data.

#### Phase 2+: Advanced CLI Features (this project)

Future CLI enhancements that build on the plugin's API:

- Export portfolio reports (HTML, PDF)
- Automated portfolio health checks (CI-friendly exit codes)
- Dependency change detection (diff between runs)
- Integration with workflow plugins for automated cross-project orchestration

---

## Appendix: Existing Cross-Project Link Verification

To verify that cross-project task links work today with our SDK:

```python
from kanboard import KanboardClient

client = KanboardClient("https://kanboard.example.com/jsonrpc.php", token="...")

# Create tasks in different projects
task_a = client.tasks.create_task(title="Finalize branding", project_id=3)   # Product A
task_b = client.tasks.create_task(title="Publish product page", project_id=8) # Site Project

# Get the "blocks" link type ID
blocks_link = client.links.get_link_by_label("blocks")

# Create cross-project dependency
link_id = client.task_links.create_task_link(
    task_id=task_a,
    opposite_task_id=task_b,
    link_id=blocks_link.id,
)

# Verify: task_b now shows "is blocked by" task_a
links = client.task_links.get_all_task_links(task_id=task_b)
for link in links:
    print(f"Task #{link.task_id} {link.label} Task #{link.opposite_task_id}")
    # Output: "Task #task_b is blocked by Task #task_a"
```

This works today. The portfolio plugin adds the orchestration layer on top.
