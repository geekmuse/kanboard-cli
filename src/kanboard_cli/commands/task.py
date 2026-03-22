"""Task CLI commands — CRUD and management operations for Kanboard tasks.

Subcommands: list, get, create, update, close, open, remove, search,
move, move-to-project, duplicate, overdue.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default columns rendered in list / search / overdue table output.
_LIST_COLUMNS = [
    "id",
    "title",
    "is_active",
    "priority",
    "column_id",
    "owner_id",
    "date_due",
]


# ---------------------------------------------------------------------------
# Task command group
# ---------------------------------------------------------------------------


@click.group()
def task() -> None:
    """Manage Kanboard tasks."""


# ---------------------------------------------------------------------------
# task list
# ---------------------------------------------------------------------------


@task.command("list")
@click.argument("project_id", type=int)
@click.option(
    "--status",
    type=click.Choice(["active", "inactive"], case_sensitive=False),
    default="active",
    show_default=True,
    help="Filter by task status.",
)
@click.pass_context
def task_list(ctx: click.Context, project_id: int, status: str) -> None:
    r"""List tasks in PROJECT_ID.

    \b
    Examples:
        kanboard task list 1
        kanboard task list 1 --status inactive
        kanboard --output json task list 1
    """
    app: AppContext = ctx.obj
    status_id = 1 if status == "active" else 0
    try:
        tasks = app.client.tasks.get_all_tasks(project_id, status_id=status_id)
    except (KanboardAPIError, KanboardNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(tasks, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task get
# ---------------------------------------------------------------------------


@task.command("get")
@click.argument("task_id", type=int)
@click.pass_context
def task_get(ctx: click.Context, task_id: int) -> None:
    r"""Show full details for TASK_ID.

    \b
    Examples:
        kanboard task get 42
        kanboard --output json task get 42
    """
    app: AppContext = ctx.obj
    try:
        task_obj = app.client.tasks.get_task(task_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(task_obj, app.output)


# ---------------------------------------------------------------------------
# task create
# ---------------------------------------------------------------------------


@task.command("create")
@click.argument("project_id", type=int)
@click.argument("title")
@click.option("--owner-id", type=int, default=None, help="Assign task to this user ID.")
@click.option("--column-id", type=int, default=None, help="Place task in this column.")
@click.option("--swimlane-id", type=int, default=None, help="Place task in this swimlane.")
@click.option("--due", default=None, metavar="DATE", help="Due date (YYYY-MM-DD).")
@click.option("--description", "-d", default=None, help="Task description.")
@click.option("--color", default=None, help="Color identifier (e.g. red, blue, green).")
@click.option("--category-id", type=int, default=None, help="Category ID.")
@click.option("--score", type=int, default=None, help="Complexity / effort score.")
@click.option("--priority", type=int, default=None, help="Task priority (higher = more urgent).")
@click.option("--reference", default=None, help="External reference (e.g. ticket number).")
@click.option(
    "--tag",
    "tags",
    multiple=True,
    metavar="TAG",
    help="Tag to apply (repeatable: --tag frontend --tag bug).",
)
@click.pass_context
def task_create(
    ctx: click.Context,
    project_id: int,
    title: str,
    owner_id: int | None,
    column_id: int | None,
    swimlane_id: int | None,
    due: str | None,
    description: str | None,
    color: str | None,
    category_id: int | None,
    score: int | None,
    priority: int | None,
    reference: str | None,
    tags: tuple[str, ...],
) -> None:
    r"""Create a new task TITLE in project PROJECT_ID.

    \b
    Examples:
        kanboard task create 1 "Fix login bug"
        kanboard task create 1 "API refactor" --due 2025-12-31 --priority 2
        kanboard task create 1 "Feature" --tag backend --tag api
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if owner_id is not None:
        kwargs["owner_id"] = owner_id
    if column_id is not None:
        kwargs["column_id"] = column_id
    if swimlane_id is not None:
        kwargs["swimlane_id"] = swimlane_id
    if due is not None:
        kwargs["date_due"] = due
    if description is not None:
        kwargs["description"] = description
    if color is not None:
        kwargs["color_id"] = color
    if category_id is not None:
        kwargs["category_id"] = category_id
    if score is not None:
        kwargs["score"] = score
    if priority is not None:
        kwargs["priority"] = priority
    if reference is not None:
        kwargs["reference"] = reference
    if tags:
        kwargs["tags"] = list(tags)
    try:
        new_id = app.client.tasks.create_task(title, project_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Task #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# task update
# ---------------------------------------------------------------------------


@task.command("update")
@click.argument("task_id", type=int)
@click.option("--title", default=None, help="New task title.")
@click.option("--color", default=None, help="New color identifier.")
@click.option("--due", default=None, metavar="DATE", help="New due date (YYYY-MM-DD).")
@click.option("--description", "-d", default=None, help="New task description.")
@click.option("--owner-id", type=int, default=None, help="New owner user ID.")
@click.option("--category-id", type=int, default=None, help="New category ID.")
@click.option("--score", type=int, default=None, help="New complexity / effort score.")
@click.option("--priority", type=int, default=None, help="New task priority.")
@click.option("--reference", default=None, help="New external reference.")
@click.option(
    "--tag",
    "tags",
    multiple=True,
    metavar="TAG",
    help="Replace tag list (repeatable; clears existing tags).",
)
@click.pass_context
def task_update(
    ctx: click.Context,
    task_id: int,
    title: str | None,
    color: str | None,
    due: str | None,
    description: str | None,
    owner_id: int | None,
    category_id: int | None,
    score: int | None,
    priority: int | None,
    reference: str | None,
    tags: tuple[str, ...],
) -> None:
    r"""Update fields on TASK_ID.

    Only supplied options are sent to the API; omitted options remain
    unchanged on the server.

    \b
    Examples:
        kanboard task update 42 --title "Renamed task"
        kanboard task update 42 --priority 3 --due 2025-11-01
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if title is not None:
        kwargs["title"] = title
    if color is not None:
        kwargs["color_id"] = color
    if due is not None:
        kwargs["date_due"] = due
    if description is not None:
        kwargs["description"] = description
    if owner_id is not None:
        kwargs["owner_id"] = owner_id
    if category_id is not None:
        kwargs["category_id"] = category_id
    if score is not None:
        kwargs["score"] = score
    if priority is not None:
        kwargs["priority"] = priority
    if reference is not None:
        kwargs["reference"] = reference
    if tags:
        kwargs["tags"] = list(tags)
    if not kwargs:
        raise click.UsageError(
            "No fields to update — provide at least one option (e.g. --title, --priority)."
        )
    try:
        app.client.tasks.update_task(task_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Task #{task_id} updated.", app.output)


# ---------------------------------------------------------------------------
# task close / open
# ---------------------------------------------------------------------------


@task.command("close")
@click.argument("task_id", type=int)
@click.pass_context
def task_close(ctx: click.Context, task_id: int) -> None:
    """Close (complete) TASK_ID."""
    app: AppContext = ctx.obj
    app.client.tasks.close_task(task_id)
    format_success(f"Task #{task_id} closed.", app.output)


@task.command("open")
@click.argument("task_id", type=int)
@click.pass_context
def task_open(ctx: click.Context, task_id: int) -> None:
    """Reopen TASK_ID."""
    app: AppContext = ctx.obj
    app.client.tasks.open_task(task_id)
    format_success(f"Task #{task_id} reopened.", app.output)


# ---------------------------------------------------------------------------
# task remove
# ---------------------------------------------------------------------------


@task.command("remove")
@click.argument("task_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def task_remove(ctx: click.Context, task_id: int, yes: bool) -> None:
    r"""Permanently delete TASK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard task remove 42 --yes
    """
    if not yes:
        click.confirm(f"Delete task #{task_id}? This cannot be undone.", abort=True)
    app: AppContext = ctx.obj
    app.client.tasks.remove_task(task_id)
    format_success(f"Task #{task_id} removed.", app.output)


# ---------------------------------------------------------------------------
# task search
# ---------------------------------------------------------------------------


@task.command("search")
@click.argument("project_id", type=int)
@click.argument("query")
@click.pass_context
def task_search(ctx: click.Context, project_id: int, query: str) -> None:
    r"""Search tasks in PROJECT_ID matching QUERY.

    Supports Kanboard's filter syntax.

    \b
    Examples:
        kanboard task search 1 "assignee:me status:open"
        kanboard task search 1 "due:<2025-12-31"
    """
    app: AppContext = ctx.obj
    tasks = app.client.tasks.search_tasks(project_id, query)
    format_output(tasks, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task move
# ---------------------------------------------------------------------------


@task.command("move")
@click.argument("task_id", type=int)
@click.option("--project-id", type=int, required=True, help="Project that contains the task.")
@click.option("--column-id", type=int, required=True, help="Target column ID.")
@click.option(
    "--position",
    type=int,
    required=True,
    help="Target position within the column (1-based).",
)
@click.option("--swimlane-id", type=int, required=True, help="Target swimlane ID (0 = default).")
@click.pass_context
def task_move(
    ctx: click.Context,
    task_id: int,
    project_id: int,
    column_id: int,
    position: int,
    swimlane_id: int,
) -> None:
    r"""Move TASK_ID to a new column / position within its project.

    \b
    Examples:
        kanboard task move 42 --project-id 1 --column-id 3 --position 1 --swimlane-id 0
    """
    app: AppContext = ctx.obj
    app.client.tasks.move_task_position(project_id, task_id, column_id, position, swimlane_id)
    format_success(f"Task #{task_id} moved.", app.output)


# ---------------------------------------------------------------------------
# task move-to-project
# ---------------------------------------------------------------------------


@task.command("move-to-project")
@click.argument("task_id", type=int)
@click.argument("project_id", type=int)
@click.option("--swimlane-id", type=int, default=None, help="Target swimlane in destination.")
@click.option("--column-id", type=int, default=None, help="Target column in destination.")
@click.option("--category-id", type=int, default=None, help="Category in destination project.")
@click.option("--owner-id", type=int, default=None, help="Owner in destination project.")
@click.pass_context
def task_move_to_project(
    ctx: click.Context,
    task_id: int,
    project_id: int,
    swimlane_id: int | None,
    column_id: int | None,
    category_id: int | None,
    owner_id: int | None,
) -> None:
    r"""Move TASK_ID to PROJECT_ID.

    \b
    Examples:
        kanboard task move-to-project 42 2
        kanboard task move-to-project 42 2 --column-id 5 --owner-id 3
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if swimlane_id is not None:
        kwargs["swimlane_id"] = swimlane_id
    if column_id is not None:
        kwargs["column_id"] = column_id
    if category_id is not None:
        kwargs["category_id"] = category_id
    if owner_id is not None:
        kwargs["owner_id"] = owner_id
    app.client.tasks.move_task_to_project(task_id, project_id, **kwargs)
    format_success(f"Task #{task_id} moved to project #{project_id}.", app.output)


# ---------------------------------------------------------------------------
# task duplicate
# ---------------------------------------------------------------------------


@task.command("duplicate")
@click.argument("task_id", type=int)
@click.argument("project_id", type=int)
@click.option("--swimlane-id", type=int, default=None, help="Swimlane in destination project.")
@click.option("--column-id", type=int, default=None, help="Column in destination project.")
@click.pass_context
def task_duplicate(
    ctx: click.Context,
    task_id: int,
    project_id: int,
    swimlane_id: int | None,
    column_id: int | None,
) -> None:
    r"""Duplicate TASK_ID into PROJECT_ID.

    \b
    Examples:
        kanboard task duplicate 42 3
        kanboard task duplicate 42 3 --swimlane-id 1 --column-id 2
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if swimlane_id is not None:
        kwargs["swimlane_id"] = swimlane_id
    if column_id is not None:
        kwargs["column_id"] = column_id
    new_id = app.client.tasks.duplicate_task_to_project(task_id, project_id, **kwargs)
    msg = f"Task #{task_id} duplicated as task #{new_id} in project #{project_id}."
    format_success(msg, app.output)


# ---------------------------------------------------------------------------
# task overdue
# ---------------------------------------------------------------------------


@task.command("overdue")
@click.option(
    "--project-id",
    type=int,
    default=None,
    help="Limit results to a specific project.",
)
@click.pass_context
def task_overdue(ctx: click.Context, project_id: int | None) -> None:
    r"""Show overdue tasks.

    Without ``--project-id``, shows overdue tasks across all accessible
    projects.

    \b
    Examples:
        kanboard task overdue
        kanboard task overdue --project-id 1
    """
    app: AppContext = ctx.obj
    if project_id is not None:
        tasks = app.client.tasks.get_overdue_tasks_by_project(project_id)
    else:
        tasks = app.client.tasks.get_overdue_tasks()
    format_output(tasks, app.output, columns=_LIST_COLUMNS)
