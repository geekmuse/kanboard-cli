"""Column CLI commands — board column management for Kanboard projects.

Subcommands: list, get, add, update, remove, move.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "title", "position", "task_limit", "project_id", "description"]


# ---------------------------------------------------------------------------
# Column command group
# ---------------------------------------------------------------------------


@click.group()
def column() -> None:
    """Manage board columns."""


# ---------------------------------------------------------------------------
# column list
# ---------------------------------------------------------------------------


@column.command("list")
@click.argument("project_id", type=int)
@click.pass_context
def column_list(ctx: click.Context, project_id: int) -> None:
    r"""List all columns for PROJECT_ID.

    \b
    Examples:
        kanboard column list 1
        kanboard --output json column list 1
    """
    app: AppContext = ctx.obj
    try:
        cols = app.client.columns.get_columns(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(cols, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# column get
# ---------------------------------------------------------------------------


@column.command("get")
@click.argument("column_id", type=int)
@click.pass_context
def column_get(ctx: click.Context, column_id: int) -> None:
    r"""Show full details for COLUMN_ID.

    \b
    Examples:
        kanboard column get 5
        kanboard --output json column get 5
    """
    app: AppContext = ctx.obj
    try:
        col = app.client.columns.get_column(column_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(col, app.output)


# ---------------------------------------------------------------------------
# column add
# ---------------------------------------------------------------------------


@column.command("add")
@click.argument("project_id", type=int)
@click.argument("title")
@click.option(
    "--task-limit",
    type=int,
    default=None,
    help="Maximum number of tasks allowed in this column (0 = unlimited).",
)
@click.option("--description", "-d", default=None, help="Column description.")
@click.pass_context
def column_add(
    ctx: click.Context,
    project_id: int,
    title: str,
    task_limit: int | None,
    description: str | None,
) -> None:
    r"""Add a new column TITLE to PROJECT_ID.

    \b
    Examples:
        kanboard column add 1 "In Review"
        kanboard column add 1 "Done" --task-limit 20 --description "Completed tasks"
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if task_limit is not None:
        kwargs["task_limit"] = task_limit
    if description is not None:
        kwargs["description"] = description
    try:
        new_id = app.client.columns.add_column(project_id, title, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Column #{new_id} added.", app.output)


# ---------------------------------------------------------------------------
# column update
# ---------------------------------------------------------------------------


@column.command("update")
@click.argument("column_id", type=int)
@click.argument("title")
@click.option(
    "--task-limit",
    type=int,
    default=None,
    help="New maximum number of tasks allowed in this column (0 = unlimited).",
)
@click.option("--description", "-d", default=None, help="New column description.")
@click.pass_context
def column_update(
    ctx: click.Context,
    column_id: int,
    title: str,
    task_limit: int | None,
    description: str | None,
) -> None:
    r"""Update COLUMN_ID with a new TITLE and optional fields.

    \b
    Examples:
        kanboard column update 5 "In Progress"
        kanboard column update 5 "WIP" --task-limit 10 --description "Work in progress"
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if task_limit is not None:
        kwargs["task_limit"] = task_limit
    if description is not None:
        kwargs["description"] = description
    try:
        app.client.columns.update_column(column_id, title, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Column #{column_id} updated.", app.output)


# ---------------------------------------------------------------------------
# column remove
# ---------------------------------------------------------------------------


@column.command("remove")
@click.argument("column_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def column_remove(ctx: click.Context, column_id: int, yes: bool) -> None:
    r"""Permanently delete COLUMN_ID from its board.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard column remove 5 --yes
    """
    if not yes:
        click.confirm(f"Delete column #{column_id}? This cannot be undone.", abort=True)
    app: AppContext = ctx.obj
    app.client.columns.remove_column(column_id)
    format_success(f"Column #{column_id} removed.", app.output)


# ---------------------------------------------------------------------------
# column move
# ---------------------------------------------------------------------------


@column.command("move")
@click.argument("project_id", type=int)
@click.argument("column_id", type=int)
@click.argument("position", type=int)
@click.pass_context
def column_move(ctx: click.Context, project_id: int, column_id: int, position: int) -> None:
    r"""Move COLUMN_ID to POSITION within PROJECT_ID.

    POSITION is 1-based (1 = leftmost column on the board).

    \b
    Examples:
        kanboard column move 1 5 3
    """
    app: AppContext = ctx.obj
    app.client.columns.change_column_position(project_id, column_id, position)
    format_success(f"Column #{column_id} moved to position {position}.", app.output)
