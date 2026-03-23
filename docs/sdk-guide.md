# SDK Usage Guide

The `kanboard` package provides a full-featured Python SDK for the
[Kanboard](https://kanboard.org/) JSON-RPC API.

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Client Initialization](#client-initialization)
  - [Application API Auth (default)](#application-api-auth-default)
  - [User API Auth](#user-api-auth)
  - [Context Manager](#context-manager)
  - [Manual Close](#manual-close)
- [Resource Categories](#resource-categories)
- [Resource Examples](#resource-examples)
  - [Projects](#projects)
  - [Tasks](#tasks)
  - [Columns](#columns)
  - [Swimlanes](#swimlanes)
  - [Comments](#comments)
  - [Tags](#tags)
  - [Users](#users)
  - [Subtasks](#subtasks)
  - [Categories](#categories)
  - [Board](#board)
  - [Groups and Group Members](#groups-and-group-members)
  - [Links and Task Links](#links-and-task-links)
  - [External Task Links](#external-task-links)
  - [Files (Project and Task)](#files-project-and-task)
  - [Metadata (Project and Task)](#metadata-project-and-task)
  - [Project Permissions](#project-permissions)
  - [Actions](#actions)
  - [Subtask Time Tracking](#subtask-time-tracking)
  - [Application Info](#application-info)
  - [Me (User API)](#me-user-api)
- [Exception Handling](#exception-handling)
- [Batch API](#batch-api)
- [Low-Level `call()`](#low-level-call)
- [Response Models](#response-models)
- [Cross-Project Orchestration](#cross-project-orchestration)
  - [Overview](#overview)
  - [LocalPortfolioStore](#localportfoliostore)
  - [PortfolioManager](#portfoliomanager)
  - [DependencyAnalyzer](#dependencyanalyzer)
  - [Orchestration Models](#orchestration-models)

---

## Installation

```bash
pip install kanboard-cli
```

The `kanboard` SDK module is part of the `kanboard-cli` package.

```python
from kanboard import KanboardClient
```

---

## Quick Start

```python
from kanboard import KanboardClient

with KanboardClient(
    url="https://kanboard.example.com/jsonrpc.php",
    token="your-api-token",
) as kb:
    # Create a project
    project_id = kb.projects.create_project("My Project")

    # Create a task
    task_id = kb.tasks.create_task(
        title="Implement feature X",
        project_id=project_id,
        color_id="green",
        priority=2,
    )

    # List all active tasks
    tasks = kb.tasks.get_all_tasks(project_id, status_id=1)
    for task in tasks:
        print(f"#{task.id} {task.title}")

    # Add a comment
    kb.comments.create_comment(task_id=task_id, user_id=1, content="Started work")

    # Apply tags
    kb.tags.set_task_tags(project_id, task_id, ["backend", "urgent"])
```

---

## Client Initialization

### Application API Auth (default)

Standard authentication using an API token. Suitable for machine clients and
automation scripts.

```python
from kanboard import KanboardClient

client = KanboardClient(
    url="https://kanboard.example.com/jsonrpc.php",
    token="your-api-token",
)
```

The token is available in Kanboard at **Settings → API**.

Optional parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str` | *(required)* | Kanboard JSON-RPC endpoint URL |
| `token` | `str` | `""` | API token for `app` auth mode |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `auth_mode` | `str` | `"app"` | Authentication mode (`"app"` or `"user"`) |
| `username` | `str \| None` | `None` | Username for `user` auth mode |
| `password` | `str \| None` | `None` | Password or personal access token for `user` auth mode |

### User API Auth

Required to access `me.*` endpoints. Uses HTTP Basic Auth with username and
password instead of the API token.

```python
from kanboard import KanboardClient

client = KanboardClient(
    url="https://kanboard.example.com/jsonrpc.php",
    auth_mode="user",
    username="admin",
    password="your-password",
)

# Now me.* endpoints are available
me = client.me.get_me()
print(me.name)
```

### Context Manager

The recommended approach. The underlying HTTP connection is automatically
closed when the `with` block exits, even if an exception is raised.

```python
from kanboard import KanboardClient

with KanboardClient(url="...", token="...") as kb:
    projects = kb.projects.get_all_projects()
    for p in projects:
        print(p.name)
# HTTP client closed automatically here
```

### Manual Close

When you manage the client lifetime yourself, call `close()` explicitly.

```python
client = KanboardClient(url="...", token="...")
try:
    tasks = client.tasks.get_all_tasks(1)
finally:
    client.close()
```

---

## Resource Categories

All resource methods are accessed through attributes of `KanboardClient`:

| Attribute | Resource Class | API Category |
|---|---|---|
| `kb.actions` | `ActionsResource` | Automatic actions |
| `kb.application` | `ApplicationResource` | Server info (version, timezone, colors, roles) |
| `kb.board` | `BoardResource` | Board layout |
| `kb.categories` | `CategoriesResource` | Task categories |
| `kb.columns` | `ColumnsResource` | Board columns |
| `kb.comments` | `CommentsResource` | Task comments |
| `kb.external_task_links` | `ExternalTaskLinksResource` | External (URL) task links |
| `kb.group_members` | `GroupMembersResource` | Group membership |
| `kb.groups` | `GroupsResource` | User groups |
| `kb.links` | `LinksResource` | Link type definitions |
| `kb.me` | `MeResource` | Authenticated user (requires user auth) |
| `kb.project_files` | `ProjectFilesResource` | Project file attachments |
| `kb.project_metadata` | `ProjectMetadataResource` | Project key-value metadata |
| `kb.project_permissions` | `ProjectPermissionsResource` | Project user/group access |
| `kb.projects` | `ProjectsResource` | Projects |
| `kb.subtask_time_tracking` | `SubtaskTimeTrackingResource` | Subtask timers |
| `kb.subtasks` | `SubtasksResource` | Subtasks |
| `kb.swimlanes` | `SwimlanesResource` | Board swimlanes |
| `kb.tags` | `TagsResource` | Tags |
| `kb.task_files` | `TaskFilesResource` | Task file attachments |
| `kb.task_links` | `TaskLinksResource` | Internal task-to-task links |
| `kb.task_metadata` | `TaskMetadataResource` | Task key-value metadata |
| `kb.tasks` | `TasksResource` | Tasks |
| `kb.users` | `UsersResource` | Users |

---

## Resource Examples

### Projects

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Create
    project_id = kb.projects.create_project(
        "My Project",
        description="A sample project",
        identifier="MYPROJ",
    )

    # Read
    project = kb.projects.get_project_by_id(project_id)
    print(project.name, project.identifier)

    all_projects = kb.projects.get_all_projects()

    # Update
    kb.projects.update_project(project_id, name="Renamed Project")

    # Enable / disable
    kb.projects.disable_project(project_id)
    kb.projects.enable_project(project_id)

    # Activity feed
    events = kb.projects.get_project_activity(project_id)
    for event in events[:5]:
        print(event)

    # Remove
    kb.projects.remove_project(project_id)
```

### Tasks

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Create
    task_id = kb.tasks.create_task(
        title="Fix login bug",
        project_id=1,
        color_id="red",
        priority=3,
        date_due="2025-12-31",
        tags=["bug", "auth"],
    )

    # Read
    task = kb.tasks.get_task(task_id)
    print(task.title, task.priority)

    active_tasks = kb.tasks.get_all_tasks(project_id=1, status_id=1)
    inactive_tasks = kb.tasks.get_all_tasks(project_id=1, status_id=0)

    # Search using Kanboard filter syntax
    results = kb.tasks.search_tasks(project_id=1, query="assignee:me status:open")

    # Update
    kb.tasks.update_task(task_id, title="Fixed login bug", priority=1)

    # Close and reopen
    kb.tasks.close_task(task_id)
    kb.tasks.open_task(task_id)

    # Move within project
    kb.tasks.move_task_position(
        project_id=1, task_id=task_id,
        column_id=3, position=1, swimlane_id=0,
    )

    # Move to another project
    kb.tasks.move_task_to_project(task_id, dest_project_id=2, column_id=1)

    # Duplicate to another project
    new_id = kb.tasks.duplicate_task_to_project(task_id, dest_project_id=2)

    # Overdue tasks
    overdue = kb.tasks.get_overdue_tasks()
    project_overdue = kb.tasks.get_overdue_tasks_by_project(project_id=1)

    # Remove
    kb.tasks.remove_task(task_id)
```

### Columns

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Add a column
    col_id = kb.columns.add_column(
        project_id=1,
        title="In Review",
        task_limit=5,
        description="Tasks waiting for review",
    )

    # Read
    columns = kb.columns.get_columns(project_id=1)
    column = kb.columns.get_column(col_id)

    # Update
    kb.columns.update_column(col_id, "Reviewed", task_limit=10)

    # Reorder (1-based, leftmost = 1)
    kb.columns.change_column_position(project_id=1, column_id=col_id, position=2)

    # Remove
    kb.columns.remove_column(col_id)
```

### Swimlanes

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Add a swimlane
    lane_id = kb.swimlanes.add_swimlane(
        project_id=1,
        name="High Priority",
        description="Critical work items",
    )

    # Read
    active = kb.swimlanes.get_active_swimlanes(project_id=1)
    all_lanes = kb.swimlanes.get_all_swimlanes(project_id=1)
    lane = kb.swimlanes.get_swimlane(lane_id)
    lane_by_name = kb.swimlanes.get_swimlane_by_name(project_id=1, name="High Priority")

    # Update
    kb.swimlanes.update_swimlane(project_id=1, swimlane_id=lane_id, name="Critical")

    # Enable / disable
    kb.swimlanes.disable_swimlane(project_id=1, swimlane_id=lane_id)
    kb.swimlanes.enable_swimlane(project_id=1, swimlane_id=lane_id)

    # Reorder (1-based, topmost = 1)
    kb.swimlanes.change_swimlane_position(project_id=1, swimlane_id=lane_id, position=1)

    # Remove
    kb.swimlanes.remove_swimlane(project_id=1, swimlane_id=lane_id)
```

### Comments

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Add a comment
    comment_id = kb.comments.create_comment(
        task_id=42,
        user_id=1,
        content="This looks good.",
    )

    # Read
    comment = kb.comments.get_comment(comment_id)
    all_comments = kb.comments.get_all_comments(task_id=42)

    # Update
    kb.comments.update_comment(comment_id, content="Revised review notes.")

    # Remove
    kb.comments.remove_comment(comment_id)
```

### Tags

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Create project-scoped tags
    tag_id = kb.tags.create_tag(project_id=1, tag_name="urgent", color_id="red")

    # Read
    all_tags = kb.tags.get_all_tags()
    project_tags = kb.tags.get_tags_by_project(project_id=1)

    # Assign tags to a task (replaces existing)
    kb.tags.set_task_tags(project_id=1, task_id=42, tags=["urgent", "backend"])

    # Get tags on a task (returns dict: tag_id → tag_name)
    task_tags = kb.tags.get_task_tags(task_id=42)
    print(list(task_tags.values()))  # ["urgent", "backend"]

    # Update tag name
    kb.tags.update_tag(tag_id, tag_name="critical")

    # Remove
    kb.tags.remove_tag(tag_id)
```

### Users

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Create
    user_id = kb.users.create_user(
        username="jdoe",
        password="s3cret",
        name="John Doe",
        email="jdoe@example.com",
        role="app-user",
    )

    # Read
    user = kb.users.get_user(user_id)
    user_by_name = kb.users.get_user_by_name("jdoe")
    all_users = kb.users.get_all_users()

    # Update
    kb.users.update_user(user_id, name="Jonathan Doe", email="jonathan@example.com")

    # Enable / disable
    kb.users.disable_user(user_id)
    kb.users.enable_user(user_id)
    active = kb.users.is_active_user(user_id)  # bool

    # Remove
    kb.users.remove_user(user_id)
```

### Subtasks

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Create
    subtask_id = kb.subtasks.create_subtask(
        task_id=42,
        title="Write unit tests",
        user_id=1,
        time_estimated=2.0,
        status=0,  # 0=todo, 1=in progress, 2=done
    )

    # Read
    subtask = kb.subtasks.get_subtask(subtask_id)
    all_subtasks = kb.subtasks.get_all_subtasks(task_id=42)

    # Update
    kb.subtasks.update_subtask(
        subtask_id=subtask_id,
        task_id=42,
        status=1,
        time_spent=0.5,
    )

    # Remove
    kb.subtasks.remove_subtask(subtask_id)
```

### Categories

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    cat_id = kb.categories.create_category(project_id=1, name="Frontend", color_id="blue")
    category = kb.categories.get_category(cat_id)
    all_cats = kb.categories.get_all_categories(project_id=1)
    kb.categories.update_category(cat_id, name="UI/UX")
    kb.categories.remove_category(cat_id)
```

### Board

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Returns a list of column dicts with nested swimlane/task structure
    board = kb.board.get_board(project_id=1)
    for column in board:
        print(column["title"], "—", len(column.get("swimlanes", [])), "swimlanes")
```

### Groups and Group Members

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Groups
    group_id = kb.groups.create_group("Developers")
    group = kb.groups.get_group(group_id)
    all_groups = kb.groups.get_all_groups()
    kb.groups.update_group(group_id, name="Engineering")

    # Members
    kb.group_members.add_group_member(group_id=group_id, user_id=3)
    members = kb.group_members.get_group_members(group_id)
    user_groups = kb.group_members.get_member_groups(user_id=3)
    is_member = kb.group_members.is_group_member(group_id=group_id, user_id=3)
    kb.group_members.remove_group_member(group_id=group_id, user_id=3)

    kb.groups.remove_group(group_id)
```

### Links and Task Links

Link types define the vocabulary for task relationships ("blocks",
"is blocked by", etc.).

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Create a bidirectional link type
    link_id = kb.links.create_link(
        label="blocks",
        opposite_label="is blocked by",
    )
    opposite_id = kb.links.get_opposite_link_id(link_id)

    # Look up
    link = kb.links.get_link_by_id(link_id)
    link_by_label = kb.links.get_link_by_label("blocks")
    all_links = kb.links.get_all_links()

    # Create a task-to-task link
    task_link_id = kb.task_links.create_task_link(
        task_id=10, opposite_task_id=20, link_id=link_id,
    )
    tl = kb.task_links.get_task_link_by_id(task_link_id)
    all_task_links = kb.task_links.get_all_task_links(task_id=10)

    kb.task_links.remove_task_link(task_link_id)
    kb.links.remove_link(link_id)
```

### External Task Links

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Discover available link types
    types = kb.external_task_links.get_external_task_link_types()

    # Add an external URL link
    ext_id = kb.external_task_links.create_external_task_link(
        task_id=42,
        url="https://github.com/org/repo/issues/10",
        dependency="related",
        type="weblink",
        title="GitHub issue #10",
    )

    ext_link = kb.external_task_links.get_external_task_link(ext_id)
    all_ext = kb.external_task_links.get_all_external_task_links(task_id=42)

    kb.external_task_links.update_external_task_link(
        ext_id, task_id=42, title="Updated title",
    )
    kb.external_task_links.remove_external_task_link(task_id=42, link_id=ext_id)
```

### Files (Project and Task)

Files are uploaded as base64-encoded blobs.

```python
import base64
from pathlib import Path

with KanboardClient(url=URL, token=TOKEN) as kb:
    # Project files
    content = base64.b64encode(Path("report.pdf").read_bytes()).decode()
    pf_id = kb.project_files.create_project_file(
        project_id=1,
        filename="report.pdf",
        blob=content,
    )
    pf = kb.project_files.get_project_file(pf_id)
    all_pf = kb.project_files.get_all_project_files(project_id=1)
    downloaded = kb.project_files.download_project_file(pf_id)  # base64 string
    kb.project_files.remove_project_file(pf_id)
    kb.project_files.remove_all_project_files(project_id=1)

    # Task files — same pattern
    tf_id = kb.task_files.create_task_file(
        project_id=1,
        task_id=42,
        filename="screenshot.png",
        blob=base64.b64encode(Path("screenshot.png").read_bytes()).decode(),
    )
    kb.task_files.remove_task_file(tf_id)
```

### Metadata (Project and Task)

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Project metadata
    kb.project_metadata.save_project_metadata(project_id=1, values={"sprint": "Sprint 5"})
    all_meta = kb.project_metadata.get_all_project_metadata(project_id=1)
    sprint = kb.project_metadata.get_project_metadata_by_name(project_id=1, name="sprint")
    kb.project_metadata.remove_project_metadata(project_id=1, name="sprint")

    # Task metadata — same pattern
    kb.task_metadata.save_task_metadata(task_id=42, values={"estimate": "8h"})
    task_meta = kb.task_metadata.get_all_task_metadata(task_id=42)
    kb.task_metadata.remove_task_metadata(task_id=42, name="estimate")
```

### Project Permissions

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Users
    kb.project_permissions.add_project_user(
        project_id=1, user_id=5, role="project-member",
    )
    users = kb.project_permissions.get_project_users(project_id=1)
    # users is dict[str, str]: {"5": "jdoe", ...}
    role = kb.project_permissions.get_project_user_role(project_id=1, user_id=5)
    kb.project_permissions.change_project_user_role(
        project_id=1, user_id=5, role="project-manager",
    )
    kb.project_permissions.remove_project_user(project_id=1, user_id=5)

    # Groups
    kb.project_permissions.add_project_group(
        project_id=1, group_id=2, role="project-viewer",
    )
    kb.project_permissions.change_project_group_role(
        project_id=1, group_id=2, role="project-member",
    )
    kb.project_permissions.remove_project_group(project_id=1, group_id=2)

    # Assignable users
    assignable = kb.project_permissions.get_assignable_users(project_id=1)
```

### Actions

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Discover available actions and events
    available = kb.actions.get_available_actions()
    # {"\\TaskClose": "Close the task", "\\TaskAssignUser": "Assign user", ...}

    events = kb.actions.get_available_action_events()
    # {"task.move.column": "Move a task to another column", ...}

    compatible = kb.actions.get_compatible_action_events("\\TaskClose")

    # Create: close a task when moved to the last column
    action_id = kb.actions.create_action(
        project_id=1,
        event_name="task.move.column",
        action_name="\\TaskClose",
        params={"column_id": "5"},  # param values must be strings
    )

    actions = kb.actions.get_actions(project_id=1)
    kb.actions.remove_action(action_id)
```

### Subtask Time Tracking

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    # Start a timer (user_id required when using user auth)
    kb.subtask_time_tracking.set_subtask_start_time(subtask_id=10, user_id=1)

    # Check status
    running = kb.subtask_time_tracking.has_subtask_timer(subtask_id=10, user_id=1)
    print("Timer running:", running)  # True

    # Stop
    kb.subtask_time_tracking.set_subtask_end_time(subtask_id=10, user_id=1)

    # Total hours spent
    hours = kb.subtask_time_tracking.get_subtask_time_spent(subtask_id=10, user_id=1)
    print(f"Time spent: {hours:.2f} hours")
```

### Application Info

```python
with KanboardClient(url=URL, token=TOKEN) as kb:
    version = kb.application.get_version()
    tz = kb.application.get_timezone()
    colors = kb.application.get_default_task_colors()
    default_color = kb.application.get_default_task_color()
    app_roles = kb.application.get_application_roles()
    project_roles = kb.application.get_project_roles()
```

### Me (User API)

The `me` resource requires `auth_mode="user"` with a username and password.

```python
from kanboard import KanboardClient

with KanboardClient(
    url="https://kanboard.example.com/jsonrpc.php",
    auth_mode="user",
    username="admin",
    password="your-password",
) as kb:
    # Current user profile
    me = kb.me.get_me()
    print(me.username, me.email)

    # Dashboard summary
    dashboard = kb.me.get_my_dashboard()

    # Activity stream
    activity = kb.me.get_my_activity_stream()

    # Projects the user is a member of
    my_projects = kb.me.get_my_projects()

    # Overdue tasks
    overdue = kb.me.get_my_overdue_tasks()

    # Create a private project
    project_id = kb.me.create_my_private_project("My Private Project")
```

---

## Exception Handling

The SDK provides a structured exception hierarchy. All exceptions inherit
from `KanboardError`, so you can catch them all with a single clause or
handle fine-grained sub-classes as needed.

```
KanboardError (base)
├── KanboardConfigError          # Missing/invalid configuration
├── KanboardConnectionError      # Network/connection failures
├── KanboardAuthError            # HTTP 401/403, wrong credentials or auth mode
├── KanboardAPIError             # JSON-RPC error responses
│   ├── KanboardNotFoundError    # Resource not found (API returned null)
│   └── KanboardValidationError  # Invalid parameters rejected by server
└── KanboardResponseError        # Malformed/unparseable server response
```

### Catch everything

```python
from kanboard import KanboardClient
from kanboard.exceptions import KanboardError

with KanboardClient(url=URL, token=TOKEN) as kb:
    try:
        task = kb.tasks.get_task(999)
    except KanboardError as exc:
        print(f"Kanboard error: {exc}")
```

### Handle specific error types

```python
from kanboard.exceptions import (
    KanboardNotFoundError,
    KanboardAuthError,
    KanboardConnectionError,
    KanboardAPIError,
)

with KanboardClient(url=URL, token=TOKEN) as kb:
    try:
        task = kb.tasks.get_task(task_id)
    except KanboardNotFoundError:
        print(f"Task {task_id} does not exist")
    except KanboardAuthError as exc:
        print(f"Authentication failed (HTTP {exc.http_status}): {exc.message}")
    except KanboardConnectionError as exc:
        print(f"Cannot reach {exc.url}: {exc.cause}")
    except KanboardAPIError as exc:
        print(f"API error (code={exc.code}, method={exc.method}): {exc.message}")
```

### Auth mode errors

When you call a `me.*` method with Application API auth, the SDK raises
`KanboardAuthError` with a clear message:

```python
from kanboard.exceptions import KanboardAuthError

with KanboardClient(url=URL, token=TOKEN) as kb:  # auth_mode="app" by default
    try:
        me = kb.me.get_me()
    except KanboardAuthError as exc:
        print(exc)
        # → Authentication error: me.get_me() requires user auth mode ...
```

### Exception attributes

| Exception | Extra Attributes |
|---|---|
| `KanboardConfigError` | `field: str \| None` |
| `KanboardConnectionError` | `url: str \| None`, `cause: BaseException \| None` |
| `KanboardAuthError` | `http_status: int \| None` |
| `KanboardAPIError` | `method: str \| None`, `code: int \| None` |
| `KanboardNotFoundError` | `resource: str \| None`, `identifier: str \| int \| None` |
| `KanboardResponseError` | `raw_body: str \| bytes \| None` |

---

## Batch API

Send multiple JSON-RPC calls in a single HTTP request for efficiency.
Responses are reordered to match the original call sequence.

```python
from kanboard import KanboardClient

with KanboardClient(url=URL, token=TOKEN) as kb:
    results = kb.batch([
        ("getVersion", {}),
        ("getTimezone", {}),
        ("getAllProjects", {}),
    ])

    version, timezone, projects_raw = results
    print(f"Server: {version} ({timezone})")
    print(f"Projects returned: {len(projects_raw) if projects_raw else 0}")
```

The `batch()` method raises `KanboardAPIError` if any individual call in the
batch returns an error. Use individual `try/except` blocks around the result
processing if partial failures are expected.

```python
from kanboard.exceptions import KanboardAPIError

with KanboardClient(url=URL, token=TOKEN) as kb:
    try:
        results = kb.batch([
            ("getTask", {"task_id": 42}),
            ("getTask", {"task_id": 43}),
        ])
        task_a_raw, task_b_raw = results
    except KanboardAPIError as exc:
        print(f"Batch failed: {exc}")
```

---

## Low-Level `call()`

For any Kanboard API method not yet wrapped in a resource class, use
`client.call()` directly:

```python
from kanboard import KanboardClient

with KanboardClient(url=URL, token=TOKEN) as kb:
    # Call any JSON-RPC method by name
    result = kb.call("getVersion")
    print(result)  # "1.2.38"

    # Pass keyword arguments as JSON-RPC params
    task_raw = kb.call("getTask", task_id=42)
    print(task_raw)  # dict with raw task fields
```

`call()` returns the raw Python object from the JSON-RPC `result` field
(dict, list, string, int, bool, or `None`). No dataclass conversion is
applied.

---

## Response Models

All SDK read methods return typed dataclass instances from `kanboard.models`.
Models are frozen (`frozen=True`) so they are hashable and immutable.

Common model fields:

| Model | Key Fields |
|---|---|
| `Task` | `id`, `title`, `project_id`, `column_id`, `is_active`, `priority`, `color_id`, `date_due`, `owner_id` |
| `Project` | `id`, `name`, `is_active`, `is_public`, `owner_id`, `identifier`, `last_modified` |
| `Column` | `id`, `title`, `position`, `task_limit`, `project_id` |
| `Swimlane` | `id`, `name`, `project_id`, `position`, `is_active` |
| `Comment` | `id`, `task_id`, `user_id`, `username`, `comment`, `date_creation` |
| `Subtask` | `id`, `title`, `task_id`, `user_id`, `status`, `time_estimated`, `time_spent` |
| `User` | `id`, `username`, `name`, `email`, `role`, `is_active` |
| `Tag` | `id`, `name`, `project_id`, `color_id` |
| `Group` | `id`, `name`, `external_id` |

Models support `dataclasses.asdict()` for serialization:

```python
import dataclasses
from kanboard import KanboardClient

with KanboardClient(url=URL, token=TOKEN) as kb:
    task = kb.tasks.get_task(42)
    task_dict = dataclasses.asdict(task)
    print(task_dict["title"])
```

---

## Cross-Project Orchestration

### Overview

The `kanboard.orchestration` subpackage provides portfolio management, cross-project milestones, dependency analysis, and critical-path computation **without requiring any server-side plugin**. It uses the existing Kanboard task link and metadata APIs as a persistence layer.

**The orchestration classes are opt-in and not wired into `KanboardClient`.** Callers instantiate them separately, passing a `KanboardClient` as a constructor argument.

> **Note:** The orchestration classes work with any standard Kanboard instance — no server-side plugin is required for core functionality. For additional server-side features (UI dashboards, interactive dependency graphs, Gantt timelines, and board-level blocking indicators), see the [Kanboard Portfolio plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management).

```python
from kanboard import KanboardClient
from kanboard.orchestration import (
    DependencyAnalyzer,
    LocalPortfolioStore,
    PortfolioManager,
)

# All three are also re-exported from the top-level package:
from kanboard import DependencyAnalyzer, LocalPortfolioStore, PortfolioManager
```

---

### LocalPortfolioStore

`LocalPortfolioStore` provides JSON-backed CRUD for portfolios and milestones. By default it persists to `~/.config/kanboard/portfolios.json`.

```python
from pathlib import Path
from kanboard.orchestration import LocalPortfolioStore

# Default path: ~/.config/kanboard/portfolios.json
store = LocalPortfolioStore()

# Custom path (useful for testing)
store = LocalPortfolioStore(path=Path("/tmp/my-portfolios.json"))
```

#### Portfolio CRUD

```python
# Create
store.create_portfolio(
    name="Platform Launch",
    description="Q3 release programme",
    project_ids=[1, 2, 3],
)

# Read
portfolio = store.get_portfolio("Platform Launch")  # raises KanboardConfigError if not found
all_portfolios = store.load()                        # returns list[Portfolio]

# Update fields
store.update_portfolio("Platform Launch", description="Q3+Q4 release")

# Project membership
store.add_project("Platform Launch", project_id=4)
store.remove_project("Platform Launch", project_id=1)

# Delete
removed = store.remove_portfolio("Platform Launch")  # returns True/False
```

#### Milestone CRUD

```python
from datetime import datetime

# Add milestone to a portfolio
store.add_milestone(
    portfolio_name="Platform Launch",
    milestone_name="Beta Release",
    target_date=datetime(2026, 6, 30),
)

# Update milestone fields
store.update_milestone(
    "Platform Launch", "Beta Release",
    target_date=datetime(2026, 7, 15),
)

# Task membership
store.add_task_to_milestone(
    portfolio_name="Platform Launch",
    milestone_name="Beta Release",
    task_id=42,
    critical=True,            # adds to both task_ids and critical_task_ids
)
store.remove_task_from_milestone("Platform Launch", "Beta Release", task_id=42)

# Delete milestone
store.remove_milestone("Platform Launch", "Beta Release")
```

---

### PortfolioManager

`PortfolioManager` aggregates task data across multiple projects and computes milestone progress. It makes N+1 API calls by design (one per project/task) — acceptable for Phase 0; the [Kanboard Portfolio plugin](https://github.com/geekmuse/kanboard-plugin-portfolio-management) will solve this at scale in Phase 1.

```python
from kanboard import KanboardClient
from kanboard.orchestration import LocalPortfolioStore, PortfolioManager

with KanboardClient(url=URL, token=TOKEN) as kb:
    store = LocalPortfolioStore()
    manager = PortfolioManager(kb, store)

    # Fetch all projects in the portfolio (skips deleted projects with a warning)
    projects = manager.get_portfolio_projects("Platform Launch")

    # Aggregate tasks across all portfolio projects
    tasks = manager.get_portfolio_tasks("Platform Launch")

    # Filter by status (1=active, 0=closed), assignee, or specific project
    active_tasks = manager.get_portfolio_tasks(
        "Platform Launch",
        status=1,
        assignee_id=7,
        project_id=2,
    )

    # Milestone progress
    progress = manager.get_milestone_progress("Platform Launch", "Beta Release")
    print(f"{progress.milestone_name}: {progress.percent:.0f}%")
    print(f"At risk: {progress.is_at_risk}, Overdue: {progress.is_overdue}")
    print(f"Blocked tasks: {progress.blocked_task_ids}")

    # All milestones at once
    all_progress = manager.get_all_milestone_progress("Platform Launch")
    for p in all_progress:
        status = "🔴 OVERDUE" if p.is_overdue else ("⚠ AT RISK" if p.is_at_risk else "✓")
        print(f"  {status}  {p.milestone_name}: {p.percent:.0f}%")

    # Sync portfolio/milestone membership to Kanboard metadata
    result = manager.sync_metadata("Platform Launch")
    print(f"Synced {result['projects_synced']} projects, {result['tasks_synced']} tasks")
```

**Milestone progress thresholds:**

| Condition | Logic |
|---|---|
| `is_at_risk` | `target_date` within 7 days **and** completion < 80% |
| `is_overdue` | `target_date` in the past **and** completion < 100% |
| `blocked_task_ids` | Tasks with at least one unresolved `is blocked by` link to an open task |

---

### DependencyAnalyzer

`DependencyAnalyzer` builds directed dependency graphs from Kanboard task links (`blocks`/`is blocked by`). It uses topological sort (Kahn's algorithm) for critical-path computation and deduplicates bidirectional edges.

```python
from kanboard import KanboardClient
from kanboard.orchestration import DependencyAnalyzer

with KanboardClient(url=URL, token=TOKEN) as kb:
    analyzer = DependencyAnalyzer(kb)

    # Fetch tasks first (e.g. from PortfolioManager or a single project)
    tasks = kb.tasks.get_all_tasks(project_id=1, status_id=1)

    # Get all dependency edges
    edges = analyzer.get_dependency_edges(tasks)

    # Cross-project edges only
    xp_edges = analyzer.get_dependency_edges(tasks, cross_project_only=True)

    # Tasks with unresolved blockers
    blocked = analyzer.get_blocked_tasks(tasks)
    for task, blocking_edges in blocked:
        print(f"#{task.id} {task.title} is blocked by:")
        for edge in blocking_edges:
            print(f"  #{edge.opposite_task_id} {edge.opposite_task_title}")

    # Open tasks that are blocking others
    blocking = analyzer.get_blocking_tasks(tasks)

    # Critical path (longest dependency chain)
    critical = analyzer.get_critical_path(tasks)
    for i, task in enumerate(critical, start=1):
        print(f"  {i}. #{task.id} {task.title}")

    # Full dependency graph (for custom rendering or export)
    graph = analyzer.get_dependency_graph(tasks, cross_project_only=False)
    # graph = {"nodes": [{"id": ..., "title": ..., ...}], "edges": [...]}
```

**Edge deduplication:** Kanboard returns links from both sides of a relationship. `DependencyAnalyzer` normalises all edges to the canonical `(blocker_id, blocked_id)` direction and deduplicates, so processing both Task A and Task B produces exactly one edge for each `A blocks B` relationship.

**Cycle detection:** If a dependency cycle is detected, a warning is logged and a partial result is returned. Cycles should not occur with standard `blocks`/`is blocked by` usage.

---

### Orchestration Models

The four orchestration models are defined in `kanboard.models` and exported from the top-level `kanboard` package. Unlike resource models, they have **no `from_api()` classmethod** — they are composed client-side from multiple API responses.

```python
from kanboard import Portfolio, Milestone, MilestoneProgress, DependencyEdge
```

| Model | Key Fields |
|---|---|
| `Portfolio` | `name`, `description`, `project_ids: list[int]`, `milestones: list[Milestone]`, `created_at`, `updated_at` |
| `Milestone` | `name`, `portfolio_name`, `target_date`, `task_ids: list[int]`, `critical_task_ids: list[int]` |
| `MilestoneProgress` | `milestone_name`, `portfolio_name`, `target_date`, `total`, `completed`, `percent: float`, `is_at_risk`, `is_overdue`, `blocked_task_ids` |
| `DependencyEdge` | `task_id`, `task_title`, `task_project_id`, `task_project_name`, `opposite_task_id`, `opposite_task_title`, `opposite_task_project_id`, `opposite_task_project_name`, `link_label`, `is_cross_project`, `is_resolved` |

All four models are **mutable** (no `frozen=True`) to support in-place editing before saving to the store.
