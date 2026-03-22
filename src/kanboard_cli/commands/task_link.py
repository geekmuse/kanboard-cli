"""Task link CLI commands — internal task-to-task link management for Kanboard.

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
_LIST_COLUMNS = ["id", "task_id", "opposite_task_id", "link_id"]


# ---------------------------------------------------------------------------
# Task-link command group
# ---------------------------------------------------------------------------


@click.group(name="task-link")
def task_link() -> None:
    """Manage links between tasks."""


# ---------------------------------------------------------------------------
# task-link list
# ---------------------------------------------------------------------------


@task_link.command("list")
@click.argument("task_id", type=int)
@click.pass_context
def task_link_list(ctx: click.Context, task_id: int) -> None:
    r"""List all task links for TASK_ID.

    \b
    Examples:
        kanboard task-link list 42
        kanboard --output json task-link list 42
    """
    app: AppContext = ctx.obj
    try:
        links = app.client.task_links.get_all_task_links(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(links, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task-link get
# ---------------------------------------------------------------------------


@task_link.command("get")
@click.argument("task_link_id", type=int)
@click.pass_context
def task_link_get(ctx: click.Context, task_link_id: int) -> None:
    r"""Show details for task link TASK_LINK_ID.

    \b
    Examples:
        kanboard task-link get 7
        kanboard --output json task-link get 7
    """
    app: AppContext = ctx.obj
    try:
        tl = app.client.task_links.get_task_link_by_id(task_link_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(tl, app.output)


# ---------------------------------------------------------------------------
# task-link create
# ---------------------------------------------------------------------------


@task_link.command("create")
@click.argument("task_id", type=int)
@click.argument("opposite_task_id", type=int)
@click.argument("link_id", type=int)
@click.pass_context
def task_link_create(
    ctx: click.Context,
    task_id: int,
    opposite_task_id: int,
    link_id: int,
) -> None:
    r"""Create a task link from TASK_ID to OPPOSITE_TASK_ID using LINK_ID.

    \b
    Examples:
        kanboard task-link create 10 20 1
    """
    app: AppContext = ctx.obj
    try:
        new_id = app.client.task_links.create_task_link(task_id, opposite_task_id, link_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Task link #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# task-link update
# ---------------------------------------------------------------------------


@task_link.command("update")
@click.argument("task_link_id", type=int)
@click.argument("task_id", type=int)
@click.argument("opposite_task_id", type=int)
@click.argument("link_id", type=int)
@click.pass_context
def task_link_update(
    ctx: click.Context,
    task_link_id: int,
    task_id: int,
    opposite_task_id: int,
    link_id: int,
) -> None:
    r"""Update task link TASK_LINK_ID with new TASK_ID, OPPOSITE_TASK_ID, and LINK_ID.

    \b
    Examples:
        kanboard task-link update 7 10 30 2
    """
    app: AppContext = ctx.obj
    try:
        app.client.task_links.update_task_link(task_link_id, task_id, opposite_task_id, link_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Task link #{task_link_id} updated.", app.output)


# ---------------------------------------------------------------------------
# task-link remove
# ---------------------------------------------------------------------------


@task_link.command("remove")
@click.argument("task_link_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def task_link_remove(ctx: click.Context, task_link_id: int, yes: bool) -> None:
    r"""Permanently delete task link TASK_LINK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard task-link remove 7 --yes
    """
    if not yes:
        click.confirm(
            f"Delete task link #{task_link_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.task_links.remove_task_link(task_link_id)
    format_success(f"Task link #{task_link_id} removed.", app.output)
