# Cross-Project Orchestration for Kanboard

## Research Findings & Plugin Design Specification

**Date:** 2026-03-22
**Author:** kanboard-cli team
**Status:** Proposal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1: Research Findings](#2-phase-1-research-findings)
   - [2.1 Existing Kanboard Capabilities](#21-existing-kanboard-capabilities-already-cross-project)
   - [2.2 Existing Plugins](#22-existing-plugins-evaluated)
   - [2.3 Approaches with Existing Functionality](#23-approaches-with-existing-functionality)
   - [2.4 Community Discussions](#24-community-discussions--feature-requests)
   - [2.5 Third-Party Tools](#25-third-party-tools--middleware)
   - [2.6 Gap Analysis](#26-gap-analysis)
3. [Phase 2: Plugin Design — "Kanboard Portfolio"](#3-phase-2-plugin-design--kanboard-portfolio)
   - [3.1 Problem Statement & User Stories](#31-problem-statement--user-stories)
   - [3.2 Architecture Overview](#32-architecture-overview)
   - [3.3 Data Model](#33-data-model)
   - [3.4 Feature Specification](#34-feature-specification)
   - [3.5 API Endpoints](#35-api-endpoints-json-rpc)
   - [3.6 UI/UX Design](#36-uiux-design)
   - [3.7 SDK Integration](#37-integration-with-our-sdk)
   - [3.8 Implementation Phases](#38-implementation-phases)
   - [3.9 Risks, Constraints & Trade-offs](#39-risks-constraints--trade-offs)

---

## 1. Executive Summary

**The good news:** Kanboard's internal task link system (`task_has_links` table) is **already cross-project by design**. Tasks are referenced by global ID, not scoped to a project. You can link Task #42 in "Product Alpha" to Task #99 in "Marketing Site" using the existing `blocks`/`is blocked by` relationship — right now, via the API or the UI.

**The bad news:** While the *data model* supports cross-project links, Kanboard provides **zero cross-project visualization, aggregation, or coordination tooling**. There is no way to:
- See a unified view of tasks across multiple projects
- Visualize cross-project dependency chains
- Define or track milestones that span projects
- Get a "portfolio" or "program" level perspective

**Our recommendation:** Build a two-layer solution:

1. **A Kanboard PHP plugin ("Portfolio")** that adds server-side data model extensions (portfolios, cross-project milestones, dependency metadata), new views (unified board, timeline, dependency graph), and new API endpoints.

2. **A CLI/SDK companion layer** in our existing `kanboard-cli` project that extends the Python SDK with the plugin's API endpoints and adds CLI commands for cross-project orchestration workflows.

No existing plugin or third-party tool adequately solves this problem. The closest candidates (Bigboard, Gantt, Milestone, Relation Graph) each address a fragment but none provide the integrated portfolio management experience required.

---

## 2. Phase 1: Research Findings

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

## 3. Phase 2: Plugin Design — "Kanboard Portfolio"

### 3.1 Problem Statement & User Stories

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

### 3.2 Architecture Overview

The plugin follows Kanboard's standard plugin architecture and uses every major extension point:

```
plugins/Portfolio/
├── Plugin.php                    # Registration: hooks, events, routes, API, DI
├── Schema/
│   ├── Sqlite.php               # Database migrations (SQLite)
│   ├── Mysql.php                # Database migrations (MySQL/MariaDB)
│   └── Postgres.php             # Database migrations (PostgreSQL)
├── Model/
│   ├── PortfolioModel.php       # CRUD for portfolios
│   ├── PortfolioProjectModel.php # Portfolio ↔ project membership
│   ├── MilestoneModel.php       # Cross-project milestones
│   ├── MilestoneTaskModel.php   # Milestone ↔ task membership
│   ├── DependencyModel.php      # Cross-project dependency queries & graph
│   └── PortfolioQueryModel.php  # Unified cross-project task queries
├── Controller/
│   ├── PortfolioController.php  # Portfolio CRUD views
│   ├── PortfolioViewController.php  # Unified task list, timeline, graph
│   ├── MilestoneController.php  # Milestone management views
│   └── DependencyController.php # Dependency graph views
├── Action/
│   ├── NotifyOnDependencyResolved.php  # Automatic action
│   └── BlockColumnMoveIfDependency.php # Automatic action
├── Notification/
│   └── DependencyResolvedNotification.php
├── Formatter/
│   ├── PortfolioTaskListFormatter.php
│   └── PortfolioGanttFormatter.php
├── Filter/
│   └── TaskPortfolioFilter.php  # "portfolio:name" search filter
├── Template/
│   ├── portfolio/               # Portfolio views
│   ├── milestone/               # Milestone views
│   ├── dependency/              # Dependency views
│   └── widget/                  # Dashboard widgets, board indicators
├── Asset/
│   ├── js/
│   │   ├── dependency-graph.js  # D3.js force-directed graph
│   │   ├── portfolio-gantt.js   # Multi-project Gantt chart
│   │   └── milestone-progress.js
│   └── css/
│       └── portfolio.css
├── Locale/
│   └── en_US/
│       └── translations.php
└── Test/
```

#### Integration Points Used

| Kanboard Extension Point | How We Use It |
|--------------------------|---------------|
| **Schema Migrations** | 4 new tables: `portfolios`, `portfolio_has_projects`, `milestones`, `milestone_has_tasks` |
| **Custom Routes** | `/portfolio/:id`, `/portfolio/:id/timeline`, `/portfolio/:id/dependencies`, `/milestone/:id` |
| **API Methods** | ~20 new JSON-RPC methods for portfolio/milestone/dependency CRUD and queries |
| **Template Hooks** | Dashboard sidebar, dashboard show, board task footer, task detail sidebar, project header |
| **Event Listeners** | `task.close`, `task.open`, `task.move.column`, `task_internal_link.create_update` |
| **Automatic Actions** | 2 new actions: dependency-resolved notification, block-move-if-blocked |
| **Task Filters** | New `portfolio:` filter keyword in task search |
| **Reference Hooks** | `formatter:board:query` to inject blocking indicators into board rendering |
| **Asset Hooks** | JavaScript (D3.js for graphs, chart library for Gantt) and CSS |
| **DI Container** | Register all Model classes for application-wide access |

### 3.3 Data Model

#### New Tables

```sql
-- Portfolio: a named group of related projects
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    owner_id INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0,
    UNIQUE(name)
);

-- Portfolio ↔ Project membership (many-to-many)
CREATE TABLE portfolio_has_projects (
    portfolio_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,    -- display ordering
    added_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (portfolio_id, project_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Cross-project milestones (first-class entities, not tasks)
CREATE TABLE milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    target_date INTEGER DEFAULT 0,          -- Unix timestamp
    status INTEGER NOT NULL DEFAULT 1,      -- 1=active, 0=completed, 2=cancelled
    color_id TEXT DEFAULT 'blue',
    owner_id INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

-- Milestone ↔ Task membership (many-to-many, cross-project)
CREATE TABLE milestone_has_tasks (
    milestone_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,    -- sequencing within milestone
    is_critical INTEGER NOT NULL DEFAULT 0, -- marks task as critical path
    added_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (milestone_id, task_id),
    FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Indexes for query performance
CREATE INDEX idx_portfolio_projects_portfolio ON portfolio_has_projects(portfolio_id);
CREATE INDEX idx_portfolio_projects_project ON portfolio_has_projects(project_id);
CREATE INDEX idx_milestones_portfolio ON milestones(portfolio_id);
CREATE INDEX idx_milestone_tasks_milestone ON milestone_has_tasks(milestone_id);
CREATE INDEX idx_milestone_tasks_task ON milestone_has_tasks(task_id);
```

#### Relationship to Existing Tables

```
portfolios ──1:N──> portfolio_has_projects ──N:1──> projects (existing)
portfolios ──1:N──> milestones
milestones ──1:N──> milestone_has_tasks ──N:1──> tasks (existing)
tasks ──N:N──> tasks (via existing task_has_links — cross-project dependencies)
```

**Critical design decision:** We do NOT create a new dependency table. Cross-project dependencies use Kanboard's **existing `task_has_links` table** with the built-in "blocks"/"is blocked by" link types. The plugin adds *visualization and query capabilities* on top of existing data, not a parallel data store.

This means:
- Dependencies created via the standard Kanboard UI or API are automatically visible in portfolio views
- No data migration needed for existing cross-project links
- The plugin enhances rather than replaces core Kanboard functionality

#### Entity Relationship Diagram

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐
│  portfolios  │────>│ portfolio_has_projects│────>│   projects   │
│              │     │                      │     │  (existing)  │
│  id          │     │  portfolio_id (FK)   │     │              │
│  name        │     │  project_id (FK)     │     │  id          │
│  description │     │  position            │     │  name        │
│  owner_id    │     └──────────────────────┘     │  ...         │
│  is_active   │                                  └──────┬───────┘
│  created_at  │                                         │
│  updated_at  │                                         │
└──────┬───────┘                                         │
       │                                                 │
       │ 1:N                                             │ 1:N
       ▼                                                 ▼
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐
│  milestones  │────>│  milestone_has_tasks  │────>│    tasks     │
│              │     │                      │     │  (existing)  │
│  id          │     │  milestone_id (FK)   │     │              │
│  portfolio_id│     │  task_id (FK)        │     │  id          │
│  name        │     │  position            │     │  project_id  │
│  target_date │     │  is_critical         │     │  title       │
│  status      │     └──────────────────────┘     │  ...         │
│  color_id    │                                  └──────┬───────┘
│  owner_id    │                                         │
└──────────────┘                                         │ N:N
                                                         ▼
                                                  ┌──────────────┐
                                                  │task_has_links│
                                                  │  (existing)  │
                                                  │              │
                                                  │  id          │
                                                  │  link_id     │
                                                  │  task_id     │
                                                  │opposite_task_│
                                                  │  id          │
                                                  └──────────────┘
```

### 3.4 Feature Specification

#### 3.4.1 Portfolio Management

**Create/Edit/Delete Portfolios:**
- Global-level entity (not project-scoped)
- Only app-admin and app-manager roles can create portfolios
- A portfolio has a name, description, owner, and active/inactive status
- Projects can belong to multiple portfolios (a project might be in both "Q2 Launch" and "Annual Roadmap")

**Portfolio ↔ Project Membership:**
- Add/remove projects from a portfolio
- Reorder projects within a portfolio (display ordering)
- A project's membership in a portfolio does not affect its independent configuration

#### 3.4.2 Unified Multi-Project Task View

**Portfolio Task List:**
- Displays all tasks from all projects in the portfolio in a single sortable, filterable table
- Columns: Task ID, Title, Project, Column (status), Assignee, Due Date, Priority, Tags, Blocked By, Blocking
- Filters: by project, by status (active/closed), by assignee, by tag, by date range, by "has cross-project dependency", by milestone
- Sort: by due date, priority, project, creation date, last modified
- Pagination for large portfolios

**Portfolio Board View (Aggregate Kanban):**
- Displays an aggregate board where columns represent workflow stages (configurable mapping of per-project columns to portfolio-level stages)
- Each card shows the project badge, task title, assignee, and blocking indicators
- Swimlanes can be grouped by project or by milestone
- Cards with cross-project blockers show a red "blocked" indicator with the blocking task's project and title on hover

**Portfolio List View:**
- Simple card/tile view of all portfolios the user has access to
- Shows: portfolio name, project count, active task count, milestone progress summary, at-risk indicator

#### 3.4.3 Cross-Project Dependency Declaration & Visualization

**Dependency Declaration:**
- Uses existing `createTaskLink` API with "blocks"/"is blocked by" link types
- The plugin adds a **convenience UI** on the portfolio dependency view: select two tasks from different projects and declare a dependency
- No new data storage — leverages existing `task_has_links`

**Dependency Graph View:**
- Force-directed graph (D3.js) showing all tasks in the portfolio that have cross-project links
- Nodes = tasks, colored by project, sized by priority
- Edges = dependency arrows (blocking direction), colored by status:
  - 🔴 Red: Blocking task is open → downstream task is blocked
  - 🟢 Green: Blocking task is closed → dependency resolved
  - 🟡 Yellow: Blocking task is open but downstream task is not yet ready (no scheduling conflict)
- Click a node to navigate to the task detail page
- Hover for tooltip: task title, project, assignee, due date, status
- Filter by: project, milestone, status, critical path only

**Critical Path Analysis:**
- Compute the longest dependency chain in the portfolio
- Highlight critical path tasks in the graph and task list
- Show estimated completion date based on critical path + task dates

**Blocking Indicators on Project Boards:**
- Via `template:board:task:icons` hook: inject a small icon on board cards that have unresolved cross-project blockers
- Via `template:board:task:footer` hook: show "Blocked by: [Project X] Task #NN" text
- Tooltip on hover shows the full dependency chain

#### 3.4.4 Cross-Project Milestones

**Milestone CRUD:**
- Create milestones within a portfolio
- Set target date, description, color, owner
- Assign tasks from any project in the portfolio to the milestone
- Mark tasks as "critical" within a milestone

**Milestone Progress Tracking:**
- Progress = (closed tasks / total tasks) × 100
- Weighted progress option: weight by task complexity/score
- At-risk indicator: milestone is at risk if target date is approaching and progress < threshold
- Overdue indicator: target date has passed and milestone is not complete

**Milestone Dashboard:**
- Shows all milestones in a portfolio as horizontal progress bars
- Sorted by target date
- Color-coded by health: green (on track), yellow (at risk), red (overdue/blocked)
- Click to expand: shows all tasks in the milestone grouped by project, with status indicators
- Shows blockers: tasks in the milestone that are blocked by tasks outside the milestone

**Milestone Timeline:**
- Gantt-style view of milestones along a date axis
- Each milestone shows its target date and actual progress
- Task bars within each milestone row, colored by project
- Dependency arrows between tasks (including cross-project)

#### 3.4.5 Notifications and Automatic Actions

**New Event: `portfolio.dependency.resolved`**
- Fired when a task that blocks another task in a different project is closed
- Event data includes: resolved task, unblocked tasks, portfolio(s), milestone(s)

**New Automatic Action: "Notify on Cross-Project Dependency Resolved"**
- Trigger: `portfolio.dependency.resolved`
- Action: Send notification to the assignee of the unblocked task
- Parameters: notification channel (email, web, Slack via existing plugins)

**New Automatic Action: "Add Comment When Dependency Resolved"**
- Trigger: `portfolio.dependency.resolved`
- Action: Add an automated comment on the unblocked task: "✅ Dependency resolved: [Task #NN] in [Project X] has been completed. This task is no longer blocked."

**New Automatic Action: "Block Column Move If Dependency Unresolved"** (optional, may require core override)
- Trigger: `task.move.column`
- Action: Prevent moving a task to a "Done"-type column if it has unresolved "blocked by" dependencies
- Parameters: target column, dependency link types to check

#### 3.4.6 Portfolio Search Filter

**New filter keyword: `portfolio:`**
- Example: `portfolio:"Q2 Launch" status:open assignee:me`
- Returns tasks from all projects in the named portfolio matching the filter criteria
- Registered via `$this->container->extend('taskLexer', ...)` hook

### 3.5 API Endpoints (JSON-RPC)

All endpoints follow Kanboard's JSON-RPC 2.0 convention. Method names use `camelCase` to match Kanboard's API style.

#### Portfolio CRUD

| Method | Params | Returns |
|--------|--------|---------|
| `createPortfolio` | `name` (str, **req**), `description` (str, opt), `owner_id` (int, opt) | `int` portfolio_id or `false` |
| `getPortfolio` | `portfolio_id` (int, **req**) | portfolio dict or `null` |
| `getPortfolioByName` | `name` (str, **req**) | portfolio dict or `null` |
| `getAllPortfolios` | none | `list[dict]` |
| `updatePortfolio` | `portfolio_id` (int, **req**), `name` (str, opt), `description` (str, opt), `owner_id` (int, opt), `is_active` (int, opt) | `true` or `false` |
| `removePortfolio` | `portfolio_id` (int, **req**) | `true` or `false` |

#### Portfolio ↔ Project Membership

| Method | Params | Returns |
|--------|--------|---------|
| `addProjectToPortfolio` | `portfolio_id` (int, **req**), `project_id` (int, **req**), `position` (int, opt) | `true` or `false` |
| `removeProjectFromPortfolio` | `portfolio_id` (int, **req**), `project_id` (int, **req**) | `true` or `false` |
| `getPortfolioProjects` | `portfolio_id` (int, **req**) | `list[dict]` project dicts with position |
| `getProjectPortfolios` | `project_id` (int, **req**) | `list[dict]` portfolio dicts |

#### Milestone CRUD

| Method | Params | Returns |
|--------|--------|---------|
| `createMilestone` | `portfolio_id` (int, **req**), `name` (str, **req**), `description` (str, opt), `target_date` (str, opt), `color_id` (str, opt), `owner_id` (int, opt) | `int` milestone_id or `false` |
| `getMilestone` | `milestone_id` (int, **req**) | milestone dict or `null` |
| `getPortfolioMilestones` | `portfolio_id` (int, **req**) | `list[dict]` |
| `updateMilestone` | `milestone_id` (int, **req**), `name` (str, opt), `description` (str, opt), `target_date` (str, opt), `color_id` (str, opt), `owner_id` (int, opt), `status` (int, opt) | `true` or `false` |
| `removeMilestone` | `milestone_id` (int, **req**) | `true` or `false` |

#### Milestone ↔ Task Membership

| Method | Params | Returns |
|--------|--------|---------|
| `addTaskToMilestone` | `milestone_id` (int, **req**), `task_id` (int, **req**), `is_critical` (int, opt) | `true` or `false` |
| `removeTaskFromMilestone` | `milestone_id` (int, **req**), `task_id` (int, **req**) | `true` or `false` |
| `getMilestoneTasks` | `milestone_id` (int, **req**) | `list[dict]` task dicts with milestone metadata |
| `getTaskMilestones` | `task_id` (int, **req**) | `list[dict]` milestone dicts |
| `getMilestoneProgress` | `milestone_id` (int, **req**) | `dict` `{total, completed, percent, is_at_risk, is_overdue}` |

#### Cross-Project Dependency Queries

| Method | Params | Returns |
|--------|--------|---------|
| `getPortfolioDependencies` | `portfolio_id` (int, **req**), `cross_project_only` (bool, opt, default true) | `list[dict]` link dicts with full task+project info |
| `getPortfolioCriticalPath` | `portfolio_id` (int, **req**) | `list[dict]` ordered chain of tasks on critical path |
| `getBlockedTasks` | `portfolio_id` (int, **req**) | `list[dict]` tasks with unresolved blockers |
| `getBlockingTasks` | `portfolio_id` (int, **req**) | `list[dict]` open tasks that block other tasks |
| `getPortfolioDependencyGraph` | `portfolio_id` (int, **req**) | `dict` `{nodes: [...], edges: [...]}` for graph rendering |

#### Unified Task Queries

| Method | Params | Returns |
|--------|--------|---------|
| `getPortfolioTasks` | `portfolio_id` (int, **req**), `status_id` (int, opt), `assignee_id` (int, opt), `project_id` (int, opt), `milestone_id` (int, opt), `limit` (int, opt), `offset` (int, opt) | `list[dict]` |
| `getPortfolioTaskCount` | `portfolio_id` (int, **req**), `status_id` (int, opt) | `dict` `{total, active, closed, blocked}` |
| `getPortfolioOverview` | `portfolio_id` (int, **req**) | `dict` comprehensive portfolio stats |

### 3.6 UI/UX Design

#### Navigation & Entry Points

**Global Navigation (header):**
- New "Portfolios" link in the top navigation bar (via `template:header:creation-dropdown` hook for creating, and a custom menu entry)
- Route: `/portfolios` → list of all portfolios
- Route: `/portfolio/:id` → portfolio dashboard

**Dashboard Integration:**
- Via `template:dashboard:sidebar` hook: "My Portfolios" section in the dashboard sidebar
- Via `template:dashboard:show` hook: Portfolio summary widget showing at-risk milestones across all portfolios the user participates in

**Project-Level Integration:**
- Via `template:project:sidebar` hook: "Portfolios" link in project settings sidebar showing which portfolios this project belongs to
- Via `template:project:header:after` hook: Small badge indicating portfolio membership

**Task-Level Integration:**
- Via `template:task:sidebar:information` hook: "Milestones" section showing which milestones this task belongs to
- Via `template:task:show:before-internal-links` hook: "Cross-Project Dependencies" section with visual indicators
- Via `template:board:task:icons` hook: 🔴 blocked indicator, 🟢 blocking-resolved indicator
- Via `template:board:task:footer` hook: "Blocked by: [Project] #ID" text on board cards

#### View Hierarchy

```
/portfolios                          ← Portfolio list (all portfolios)
/portfolio/create                    ← Create new portfolio form
/portfolio/:id                       ← Portfolio dashboard (overview + milestones)
/portfolio/:id/tasks                 ← Unified task list (filterable table)
/portfolio/:id/board                 ← Aggregate Kanban board
/portfolio/:id/timeline              ← Multi-project Gantt timeline
/portfolio/:id/dependencies          ← Dependency graph (D3.js interactive)
/portfolio/:id/milestones            ← Milestone management list
/portfolio/:id/settings              ← Portfolio settings (members, projects)
/milestone/:id                       ← Milestone detail (tasks, progress)
```

#### Portfolio Dashboard (`/portfolio/:id`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Portfolio: Q2 2026 Launch                          [Settings]  │
│  3 projects · 47 active tasks · 12 blocked                     │
├──────────────────────────┬──────────────────────────────────────┤
│                          │                                      │
│  📊 Milestone Progress   │  📋 View Switcher                    │
│                          │  [Dashboard] [Tasks] [Board]         │
│  ████████░░ v2.0 Feat    │  [Timeline]  [Dependencies]          │
│  Complete (72%) - Jun 1  │                                      │
│                          │  ⚠️  At-Risk Items                   │
│  ████░░░░░░ Marketing    │                                      │
│  Site Launch (35%) Jun15 │  🔴 Task #42 "Publish product page"  │
│                          │     Blocked by #15 in Product A      │
│  ██░░░░░░░░ Onboarding   │     (14 days until milestone)        │
│  Flow v2 (18%) - Jul 1   │                                      │
│                          │  🟡 Task #88 "Blog post sequence"    │
│  📈 Project Health       │     Waiting on #67 in Product B      │
│                          │     (21 days until milestone)        │
│  Product A    ████ 80%   │                                      │
│  Product B    ██░░ 45%   │  📅 Upcoming Dates                   │
│  Site Project █░░░ 25%   │                                      │
│                          │  Jun 01 - v2.0 Feature Complete      │
│                          │  Jun 15 - Marketing Site Launch      │
│                          │  Jul 01 - Onboarding Flow v2         │
└──────────────────────────┴──────────────────────────────────────┘
```

#### Dependency Graph (`/portfolio/:id/dependencies`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Dependencies: Q2 2026 Launch                                   │
│  [All] [Cross-Project Only] [Critical Path] [Blocked Only]     │
│  Filter by project: [All ▼]  Filter by milestone: [All ▼]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│         Product A                Site Project                   │
│         ┌───────┐                ┌────────────┐                 │
│    ┌───>│ #15   │──── blocks ──>│   #42      │                 │
│    │    │Branding│               │Publish page│                 │
│    │    │ ⬤ OPEN │               │ 🔴 BLOCKED │                 │
│    │    └───────┘                └─────┬──────┘                 │
│    │                                   │                        │
│    │    Product B                      │ blocks                 │
│    │    ┌───────┐                      ▼                        │
│    │    │ #67   │               ┌────────────┐                  │
│    │    │Feature│── blocks ──> │   #88      │                  │
│    │    │ ⬤ OPEN │               │Blog series │                  │
│    │    └───────┘               │ 🔴 BLOCKED │                  │
│    │                            └────────────┘                  │
│    │                                                            │
│    │    ┌───────┐                ┌────────────┐                 │
│    └────│ #22   │──── blocks ──>│   #55      │                 │
│         │API v2 │               │Landing page│                  │
│         │ ✅ DONE│               │ ⬤ READY    │                  │
│         └───────┘               └────────────┘                  │
│                                                                 │
│  Legend: ⬤ Open  ✅ Done  🔴 Blocked  ── blocks ──>            │
│  Critical path highlighted in bold                              │
└─────────────────────────────────────────────────────────────────┘
```

#### Aggregate Board (`/portfolio/:id/board`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Board: Q2 2026 Launch                                          │
│  Group by: [Project ▼]  Filter: [____________]                 │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│   Backlog    │  In Progress │   Review     │     Done          │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ Product A    │              │              │                   │
│ ┌──────────┐│ ┌──────────┐ │              │ ┌───────────────┐ │
│ │#15 Brand │││ │#18 API   │ │              │ │#22 API v2    ✅│ │
│ │  @alice  │││ │  @bob    │ │              │ │  @bob         │ │
│ └──────────┘│ └──────────┘ │              │ └───────────────┘ │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ Product B    │              │              │                   │
│ ┌──────────┐│ ┌──────────┐ │              │                   │
│ │#67 Feat  │││ │#70 Tests │ │              │                   │
│ │  @carol  │││ │  @dave   │ │              │                   │
│ └──────────┘│ └──────────┘ │              │                   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ Site Project │              │              │                   │
│ ┌──────────┐│              │              │ ┌───────────────┐ │
│ │#42 Pub 🔴│││              │              │ │#55 Landing  ⬤│ │
│ │  @eve    │││              │              │ │  @eve         │ │
│ │Blocked by││              │              │ └───────────────┘ │
│ │ProdA #15 ││              │              │                   │
│ └──────────┘│              │              │                   │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

### 3.7 Integration with Our SDK

#### New Resource Module: `src/kanboard/resources/portfolios.py`

```python
"""Portfolio resource module — cross-project portfolio management for Kanboard."""

from __future__ import annotations
from typing import TYPE_CHECKING
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Portfolio, PortfolioProject, Milestone, MilestoneProgress

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class PortfoliosResource:
    """Kanboard Portfolio Plugin API resource.

    Requires the Portfolio plugin to be installed on the Kanboard server.
    """

    def __init__(self, client: KanboardClient) -> None:
        self._client = client

    def create_portfolio(self, name: str, **kwargs) -> int:
        """Create a new portfolio."""
        result = self._client.call("createPortfolio", name=name, **kwargs)
        if not result:
            raise KanboardAPIError(f"Failed to create portfolio '{name}'", method="createPortfolio")
        return int(result)

    def get_portfolio(self, portfolio_id: int) -> Portfolio:
        """Get a portfolio by ID."""
        result = self._client.call("getPortfolio", portfolio_id=portfolio_id)
        if result is None:
            raise KanboardNotFoundError("Portfolio", portfolio_id)
        return Portfolio.from_api(result)

    def get_all_portfolios(self) -> list[Portfolio]:
        """Get all portfolios."""
        result = self._client.call("getAllPortfolios")
        if not result:
            return []
        return [Portfolio.from_api(p) for p in result]

    def add_project_to_portfolio(self, portfolio_id: int, project_id: int, **kwargs) -> bool:
        """Add a project to a portfolio."""
        result = self._client.call(
            "addProjectToPortfolio", portfolio_id=portfolio_id, project_id=project_id, **kwargs
        )
        if not result:
            raise KanboardAPIError("Failed to add project to portfolio", method="addProjectToPortfolio")
        return True

    def get_portfolio_dependencies(self, portfolio_id: int, cross_project_only: bool = True) -> list[dict]:
        """Get all dependency links in a portfolio."""
        return self._client.call(
            "getPortfolioDependencies",
            portfolio_id=portfolio_id,
            cross_project_only=cross_project_only,
        ) or []

    def get_portfolio_critical_path(self, portfolio_id: int) -> list[dict]:
        """Get the critical path through the portfolio's dependency graph."""
        return self._client.call("getPortfolioCriticalPath", portfolio_id=portfolio_id) or []

    def get_blocked_tasks(self, portfolio_id: int) -> list[dict]:
        """Get all tasks blocked by unresolved cross-project dependencies."""
        return self._client.call("getBlockedTasks", portfolio_id=portfolio_id) or []

    # ... (similar methods for all API endpoints)
```

#### New Resource Module: `src/kanboard/resources/milestones.py`

```python
class MilestonesResource:
    """Kanboard Portfolio Plugin — Milestone management."""

    def create_milestone(self, portfolio_id: int, name: str, **kwargs) -> int: ...
    def get_milestone(self, milestone_id: int) -> Milestone: ...
    def get_portfolio_milestones(self, portfolio_id: int) -> list[Milestone]: ...
    def add_task_to_milestone(self, milestone_id: int, task_id: int, **kwargs) -> bool: ...
    def get_milestone_progress(self, milestone_id: int) -> MilestoneProgress: ...
    # ...
```

#### New Models in `src/kanboard/models.py`

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

#### New CLI Commands in `src/kanboard_cli/commands/`

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

### 3.8 Implementation Phases

#### Phase 0: Immediate CLI-Only Solution (1-2 weeks)

**No plugin required.** Build a cross-project orchestration tool using our existing SDK that:

1. Uses `task_metadata` to store portfolio/milestone membership as JSON
2. Uses existing `createTaskLink` for cross-project dependencies
3. Aggregates data from multiple projects via API calls
4. Renders unified views in the CLI (tables, ASCII dependency graphs)

**Deliverables:**
- New CLI commands: `portfolio`, `milestone`, `cross-deps`
- ASCII dependency graph renderer
- Critical path calculator (topological sort on dependency graph)
- Portfolio overview report

**Value:** Immediate relief for the stated problem. Establishes conventions for portfolio metadata that the plugin will later formalize.

**Limitation:** No Kanboard UI integration. Metadata-based storage has no referential integrity.

#### Phase 1: Plugin MVP — Data Model + API (2-3 weeks)

**Server-side plugin providing the data model and API endpoints.**

1. Schema migrations for `portfolios`, `portfolio_has_projects`, `milestones`, `milestone_has_tasks`
2. Model classes for all CRUD operations
3. All ~25 JSON-RPC API endpoints
4. Event listeners for `task.close` → check and fire `portfolio.dependency.resolved`
5. Basic PHP unit tests

**Deliverables:**
- `plugins/Portfolio/` with Schema, Model, Plugin.php
- SDK resource modules: `portfolios.py`, `milestones.py`
- Updated CLI commands that call plugin API instead of metadata hack
- Full test coverage for SDK and CLI

**Value:** Proper data model with referential integrity. API-first design enables both CLI and future UI.

#### Phase 2: Plugin UI — Views + Dashboard (3-4 weeks)

**Server-side views in Kanboard's UI.**

1. Portfolio list and dashboard views (Controller + Template)
2. Unified task list view with filtering/sorting
3. Milestone management views with progress bars
4. Template hooks for dashboard sidebar, project sidebar, task detail
5. Board card indicators for blocked tasks
6. CSS styling consistent with Kanboard's default theme

**Deliverables:**
- All Controller and Template files
- Template hook integrations (dashboard, board, task, project)
- Portfolio task filter (`portfolio:` keyword)
- Automatic actions: notification on dependency resolved

**Value:** Full Kanboard UI integration. Non-CLI users can access portfolio features.

#### Phase 3: Plugin Advanced — Visualizations (2-3 weeks)

**Interactive JavaScript visualizations.**

1. D3.js dependency graph with force-directed layout
2. Multi-project Gantt/timeline view (using a lightweight Gantt library or custom D3)
3. Interactive board view with cross-project drag support (if feasible)
4. Milestone progress charts
5. Critical path highlighting

**Deliverables:**
- `Asset/js/` graph and timeline components
- Dependency graph view with filtering, zooming, node click-through
- Timeline view with dependency arrows
- Milestone progress visualization

**Value:** The "wow factor" — visual dependency graphs and timelines that make cross-project relationships tangible.

#### Phase 4: Polish + Publish (1-2 weeks)

1. Performance optimization (query efficiency for large portfolios)
2. Localization (at minimum en_US, framework for additional languages)
3. Documentation (user guide, admin guide, API reference)
4. Plugin packaging for Kanboard's plugin directory
5. Integration tests against Docker Kanboard instance

### 3.9 Risks, Constraints & Trade-offs

#### Plugin Architecture Constraints

| Constraint | Impact | Mitigation |
|-----------|--------|------------|
| **No global menu hook** | Kanboard doesn't provide a clean hook to add top-level navigation items. The `template:header:creation-dropdown` hook adds to the "+" menu, not the main nav. | Use `template:layout:top` or `template:header:creation-dropdown` + a sidebar approach. Or override the header template. |
| **Template hooks are append-only** | Cannot insert content *between* existing elements, only before/after defined hook points. | Work within existing hook points. Use CSS for visual positioning if needed. |
| **No global task query** | Kanboard's core task queries are project-scoped. `getAllTasks` requires a `project_id`. | Our plugin models will build custom SQL queries using PicoDb (Kanboard's query builder) that join across projects. |
| **Single-page Kanban limitation** | Kanboard's board view is tightly coupled to a single project. Creating a true multi-project Kanban board requires significant custom rendering. | The portfolio board view will be a completely custom controller/template, not an extension of the existing board. |
| **JavaScript ecosystem** | Kanboard uses jQuery + vanilla JS. No modern framework (React, Vue). Complex visualizations must work within this context. | Use D3.js (framework-agnostic) for graphs. Keep JS dependencies minimal. Bundle with the plugin. |
| **Synchronous webhooks** | Kanboard's webhook calls are synchronous and must respond in <1 second. Complex dependency chain analysis might be slow. | Perform dependency analysis asynchronously via a background worker or pre-compute and cache dependency data in the database. |

#### Performance Risks

| Risk | Scenario | Mitigation |
|------|----------|------------|
| **N+1 query problem** | Portfolio with 10 projects × 100 tasks each = 1000+ tasks to fetch and analyze | Use batch SQL queries with JOINs across portfolio tables. Cache computed metrics (milestone progress, dependency graph) in portfolio metadata. |
| **Large dependency graphs** | 500+ tasks with complex interdependencies could make D3 graph unusable | Implement graph filtering (cross-project only, critical path, per-milestone). Paginate and virtualize. |
| **API response size** | `getPortfolioTasks` for a large portfolio could return massive payloads | Support `limit`/`offset` pagination in all list endpoints. |

#### Data Integrity Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Task deleted with milestone membership** | Orphaned references in `milestone_has_tasks` | `ON DELETE CASCADE` foreign keys handle this automatically. |
| **Project removed from portfolio** | Tasks from that project still in milestones | On project removal, also remove that project's tasks from portfolio milestones (cascade logic in model layer). |
| **Kanboard upgrade breaks plugin** | Schema migrations or hook changes in Kanboard core could break plugin | Pin `getCompatibleVersion()`. Test against each Kanboard release. Follow Kanboard's deprecation notices. |

#### Trade-offs

1. **Plugin vs. External Service:**
   We chose a Kanboard plugin over a standalone service because it provides native UI integration, uses the same database, and doesn't require deploying/maintaining a separate application. The trade-off is that we're constrained by Kanboard's plugin architecture and PHP ecosystem.

2. **New tables vs. Metadata-only:**
   We chose new database tables over using metadata key-value storage because proper tables provide referential integrity, efficient queries (JOINs, indexes), and type safety. The trade-off is that the plugin requires schema migrations and DB access.

3. **Reusing existing `task_has_links` vs. New dependency table:**
   We chose to reuse the existing link system because it means all dependencies created through any channel (UI, API, other plugins) are automatically visible in portfolio views. The trade-off is that we can't add metadata to dependencies (e.g., "expected resolution date") without a supplementary table.

4. **PHP plugin + Python SDK vs. Pure Python:**
   The Kanboard server is PHP; the plugin must be PHP. Our SDK and CLI are Python. This dual-language approach means developing and maintaining code in two languages. But this is inherent to extending a PHP application with a Python toolchain.

---

## Appendix A: Kanboard Plugin Architecture Quick Reference

### Extension Points Summary

| Category | Mechanism | Documentation |
|----------|-----------|---------------|
| Database | Schema migrations (`Schema/*.php`) | [docs/plugins/schema_migrations](https://docs.kanboard.org/v1/plugins/schema_migrations/) |
| API | `$this->api->getProcedureHandler()->withCallback()` | [docs/plugins/hooks](https://docs.kanboard.org/v1/plugins/hooks/) |
| Routes | `$this->route->addRoute()` | [docs/plugins/routes](https://docs.kanboard.org/v1/plugins/routes/) |
| UI Templates | `$this->template->hook->attach()` | [docs/plugins/hooks](https://docs.kanboard.org/v1/plugins/hooks/) |
| Events | `$this->on('event.name', $callback)` | [docs/plugins/events](https://docs.kanboard.org/v1/plugins/events/) |
| DI Container | `getClasses()` → auto-register models | [docs/plugins/registration](https://docs.kanboard.org/v1/plugins/registration/) |
| Auto Actions | `$this->actionManager->register()` | [docs/plugins/automatic_actions](https://docs.kanboard.org/v1/plugins/automatic_actions/) |
| Task Filters | `$this->container->extend('taskLexer', ...)` | [docs/plugins/hooks](https://docs.kanboard.org/v1/plugins/hooks/) |
| Assets | `template:layout:css` / `template:layout:js` hooks | [docs/plugins/hooks](https://docs.kanboard.org/v1/plugins/hooks/) |
| Overrides | `$this->template->setTemplateOverride()` | [docs/plugins/overrides](https://docs.kanboard.org/v1/plugins/overrides/) |

### Key Template Hooks for Portfolio Plugin

| Hook | Our Usage |
|------|-----------|
| `template:dashboard:sidebar` | "My Portfolios" sidebar section |
| `template:dashboard:show` | At-risk milestones widget |
| `template:board:task:icons` | 🔴 Blocked indicator on board cards |
| `template:board:task:footer` | "Blocked by: [Project] #ID" text |
| `template:task:show:before-internal-links` | Cross-project dependency section |
| `template:task:sidebar:information` | Milestone membership |
| `template:project:sidebar` | Portfolio membership link |
| `template:header:creation-dropdown` | "Create Portfolio" quick action |
| `template:layout:css` | Plugin stylesheet |
| `template:layout:js` | D3.js and plugin JavaScript |

## Appendix B: Existing Cross-Project Link Verification

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
