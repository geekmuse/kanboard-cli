"""Task metadata CLI commands - key-value metadata for Kanboard tasks.

Subcommands: list, get, set, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["key", "value"]


# ---------------------------------------------------------------------------
# task-meta command group
# ---------------------------------------------------------------------------


@click.group(name="task-meta")
def task_meta() -> None:
    """Manage task metadata (key-value pairs)."""


# ---------------------------------------------------------------------------
# task-meta list
# ---------------------------------------------------------------------------


@task_meta.command("list")
@click.argument("task_id", type=int)
@click.pass_context
def task_meta_list(ctx: click.Context, task_id: int) -> None:
    r"""List all metadata for TASK_ID.

    Displays metadata as key-value pairs.

    \b
    Examples:
        kanboard task-meta list 42
        kanboard --output json task-meta list 42
    """
    app: AppContext = ctx.obj
    try:
        meta = app.client.task_metadata.get_task_metadata(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"key": k, "value": v} for k, v in meta.items()]
    format_output(rows, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task-meta get
# ---------------------------------------------------------------------------


@task_meta.command("get")
@click.argument("task_id", type=int)
@click.argument("name", type=str)
@click.pass_context
def task_meta_get(ctx: click.Context, task_id: int, name: str) -> None:
    r"""Get a single metadata value by NAME from TASK_ID.

    \b
    Examples:
        kanboard task-meta get 42 priority
        kanboard --output json task-meta get 42 priority
    """
    app: AppContext = ctx.obj
    try:
        value = app.client.task_metadata.get_task_metadata_by_name(task_id, name)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    row = {"key": name, "value": value}
    format_output(row, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task-meta set
# ---------------------------------------------------------------------------


@task_meta.command("set")
@click.argument("task_id", type=int)
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.pass_context
def task_meta_set(ctx: click.Context, task_id: int, key: str, value: str) -> None:
    r"""Set a metadata KEY to VALUE on TASK_ID.

    Creates or updates a single metadata entry.

    \b
    Examples:
        kanboard task-meta set 42 priority "high"
        kanboard --output json task-meta set 42 status "reviewed"
    """
    app: AppContext = ctx.obj
    try:
        app.client.task_metadata.save_task_metadata(task_id, {key: value})
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Metadata '{key}' saved on task {task_id}.", app.output)


# ---------------------------------------------------------------------------
# task-meta remove
# ---------------------------------------------------------------------------


@task_meta.command("remove")
@click.argument("task_id", type=int)
@click.argument("name", type=str)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def task_meta_remove(
    ctx: click.Context,
    task_id: int,
    name: str,
    yes: bool,
) -> None:
    r"""Remove metadata key NAME from TASK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard task-meta remove 42 priority --yes
    """
    if not yes:
        click.confirm(
            f"Delete metadata key '{name}' from task {task_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.task_metadata.remove_task_metadata(task_id, name)
    format_success(f"Metadata '{name}' removed from task {task_id}.", app.output)
