"""Subtask CLI commands — subtask management for Kanboard tasks.

Subcommands: list, get, create, update, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "title", "task_id", "user_id", "status", "time_estimated", "time_spent"]


# ---------------------------------------------------------------------------
# Subtask command group
# ---------------------------------------------------------------------------


@click.group()
def subtask() -> None:
    """Manage task subtasks."""


# ---------------------------------------------------------------------------
# subtask list
# ---------------------------------------------------------------------------


@subtask.command("list")
@click.argument("task_id", type=int)
@click.pass_context
def subtask_list(ctx: click.Context, task_id: int) -> None:
    r"""List all subtasks for TASK_ID.

    \b
    Examples:
        kanboard subtask list 42
        kanboard --output json subtask list 42
    """
    app: AppContext = ctx.obj
    try:
        subtasks = app.client.subtasks.get_all_subtasks(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(subtasks, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# subtask get
# ---------------------------------------------------------------------------


@subtask.command("get")
@click.argument("subtask_id", type=int)
@click.pass_context
def subtask_get(ctx: click.Context, subtask_id: int) -> None:
    r"""Show full details for SUBTASK_ID.

    \b
    Examples:
        kanboard subtask get 10
        kanboard --output json subtask get 10
    """
    app: AppContext = ctx.obj
    try:
        st = app.client.subtasks.get_subtask(subtask_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(st, app.output)


# ---------------------------------------------------------------------------
# subtask create
# ---------------------------------------------------------------------------


@subtask.command("create")
@click.argument("task_id", type=int)
@click.argument("title")
@click.option("--user-id", type=int, default=None, help="User ID to assign the subtask to.")
@click.option(
    "--time-estimated",
    type=float,
    default=None,
    help="Estimated hours for the subtask.",
)
@click.option(
    "--status",
    type=int,
    default=None,
    help="Subtask status: 0=todo, 1=in progress, 2=done.",
)
@click.pass_context
def subtask_create(
    ctx: click.Context,
    task_id: int,
    title: str,
    user_id: int | None,
    time_estimated: float | None,
    status: int | None,
) -> None:
    r"""Create a new subtask TITLE on TASK_ID.

    \b
    Examples:
        kanboard subtask create 42 "Write tests"
        kanboard subtask create 42 "Review PR" --user-id 3 --time-estimated 1.5
        kanboard subtask create 42 "Deploy" --status 0
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if user_id is not None:
        kwargs["user_id"] = user_id
    if time_estimated is not None:
        kwargs["time_estimated"] = time_estimated
    if status is not None:
        kwargs["status"] = status
    try:
        new_id = app.client.subtasks.create_subtask(task_id, title, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Subtask #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# subtask update
# ---------------------------------------------------------------------------


@subtask.command("update")
@click.argument("subtask_id", type=int)
@click.argument("task_id", type=int)
@click.option("--title", default=None, help="New title for the subtask.")
@click.option("--user-id", type=int, default=None, help="New user ID to assign the subtask to.")
@click.option(
    "--time-estimated",
    type=float,
    default=None,
    help="New estimated hours for the subtask.",
)
@click.option(
    "--time-spent",
    type=float,
    default=None,
    help="Hours actually spent on the subtask.",
)
@click.option(
    "--status",
    type=int,
    default=None,
    help="New status: 0=todo, 1=in progress, 2=done.",
)
@click.pass_context
def subtask_update(
    ctx: click.Context,
    subtask_id: int,
    task_id: int,
    title: str | None,
    user_id: int | None,
    time_estimated: float | None,
    time_spent: float | None,
    status: int | None,
) -> None:
    r"""Update SUBTASK_ID (which belongs to TASK_ID).

    \b
    Examples:
        kanboard subtask update 10 42 --title "Revised title"
        kanboard subtask update 10 42 --status 1 --time-spent 0.5
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if title is not None:
        kwargs["title"] = title
    if user_id is not None:
        kwargs["user_id"] = user_id
    if time_estimated is not None:
        kwargs["time_estimated"] = time_estimated
    if time_spent is not None:
        kwargs["time_spent"] = time_spent
    if status is not None:
        kwargs["status"] = status
    try:
        app.client.subtasks.update_subtask(subtask_id, task_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Subtask #{subtask_id} updated.", app.output)


# ---------------------------------------------------------------------------
# subtask remove
# ---------------------------------------------------------------------------


@subtask.command("remove")
@click.argument("subtask_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def subtask_remove(ctx: click.Context, subtask_id: int, yes: bool) -> None:
    r"""Permanently delete SUBTASK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard subtask remove 10 --yes
    """
    if not yes:
        click.confirm(
            f"Delete subtask #{subtask_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.subtasks.remove_subtask(subtask_id)
    format_success(f"Subtask #{subtask_id} removed.", app.output)
