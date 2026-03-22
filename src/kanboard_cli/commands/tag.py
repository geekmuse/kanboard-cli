"""Tag CLI commands — tag management for Kanboard.

Subcommands: list, get, create, update, remove, set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "name", "project_id", "color_id"]


# ---------------------------------------------------------------------------
# Tag command group
# ---------------------------------------------------------------------------


@click.group()
def tag() -> None:
    """Manage task tags."""


# ---------------------------------------------------------------------------
# tag list
# ---------------------------------------------------------------------------


@tag.command("list")
@click.option(
    "--project-id",
    type=int,
    default=None,
    help="Filter tags by project ID.",
)
@click.pass_context
def tag_list(ctx: click.Context, project_id: int | None) -> None:
    r"""List all tags, optionally filtered by --project-id.

    \b
    Examples:
        kanboard tag list
        kanboard tag list --project-id 1
        kanboard --output json tag list --project-id 2
    """
    app: AppContext = ctx.obj
    try:
        if project_id is not None:
            tags = app.client.tags.get_tags_by_project(project_id)
        else:
            tags = app.client.tags.get_all_tags()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(tags, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# tag get
# ---------------------------------------------------------------------------


@tag.command("get")
@click.argument("task_id", type=int)
@click.pass_context
def tag_get(ctx: click.Context, task_id: int) -> None:
    r"""Show tags assigned to TASK_ID.

    Returns a mapping of tag ID to tag name.

    \b
    Examples:
        kanboard tag get 42
        kanboard --output json tag get 42
    """
    app: AppContext = ctx.obj
    try:
        task_tags = app.client.tags.get_task_tags(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(task_tags, app.output)


# ---------------------------------------------------------------------------
# tag create
# ---------------------------------------------------------------------------


@tag.command("create")
@click.argument("project_id", type=int)
@click.argument("tag_name")
@click.option("--color-id", default=None, help="Color ID for the tag.")
@click.pass_context
def tag_create(
    ctx: click.Context,
    project_id: int,
    tag_name: str,
    color_id: str | None,
) -> None:
    r"""Create a new TAG_NAME in PROJECT_ID.

    \b
    Examples:
        kanboard tag create 1 "urgent"
        kanboard tag create 1 "bug" --color-id red
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if color_id is not None:
        kwargs["color_id"] = color_id
    try:
        new_id = app.client.tags.create_tag(project_id, tag_name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Tag #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# tag update
# ---------------------------------------------------------------------------


@tag.command("update")
@click.argument("tag_id", type=int)
@click.argument("tag_name")
@click.option("--color-id", default=None, help="New color ID for the tag.")
@click.pass_context
def tag_update(
    ctx: click.Context,
    tag_id: int,
    tag_name: str,
    color_id: str | None,
) -> None:
    r"""Update TAG_ID with a new TAG_NAME.

    \b
    Examples:
        kanboard tag update 5 "critical"
        kanboard tag update 5 "urgent" --color-id orange
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if color_id is not None:
        kwargs["color_id"] = color_id
    try:
        app.client.tags.update_tag(tag_id, tag_name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Tag #{tag_id} updated.", app.output)


# ---------------------------------------------------------------------------
# tag remove
# ---------------------------------------------------------------------------


@tag.command("remove")
@click.argument("tag_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def tag_remove(ctx: click.Context, tag_id: int, yes: bool) -> None:
    r"""Permanently delete TAG_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard tag remove 5 --yes
    """
    if not yes:
        click.confirm(
            f"Delete tag #{tag_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.tags.remove_tag(tag_id)
    format_success(f"Tag #{tag_id} removed.", app.output)


# ---------------------------------------------------------------------------
# tag set
# ---------------------------------------------------------------------------


@tag.command("set")
@click.argument("project_id", type=int)
@click.argument("task_id", type=int)
@click.argument("tags", nargs=-1, required=True)
@click.pass_context
def tag_set(
    ctx: click.Context,
    project_id: int,
    task_id: int,
    tags: tuple[str, ...],
) -> None:
    r"""Assign TAGS to TASK_ID in PROJECT_ID.

    Pass one or more tag names as space-separated arguments.  Replaces any
    existing tag assignments on the task.

    \b
    Examples:
        kanboard tag set 1 42 urgent bug
        kanboard tag set 1 42 "needs review"
    """
    app: AppContext = ctx.obj
    try:
        app.client.tags.set_task_tags(project_id, task_id, list(tags))
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(
        f"Tags set on task #{task_id}: {', '.join(tags)}.",
        app.output,
    )
