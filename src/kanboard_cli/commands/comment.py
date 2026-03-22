"""Comment CLI commands — task comment management for Kanboard.

Subcommands: list, get, add, update, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "task_id", "user_id", "username", "name", "comment"]


# ---------------------------------------------------------------------------
# Comment command group
# ---------------------------------------------------------------------------


@click.group()
def comment() -> None:
    """Manage task comments."""


# ---------------------------------------------------------------------------
# comment list
# ---------------------------------------------------------------------------


@comment.command("list")
@click.argument("task_id", type=int)
@click.pass_context
def comment_list(ctx: click.Context, task_id: int) -> None:
    r"""List all comments for TASK_ID.

    \b
    Examples:
        kanboard comment list 42
        kanboard --output json comment list 42
    """
    app: AppContext = ctx.obj
    try:
        comments = app.client.comments.get_all_comments(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(comments, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# comment get
# ---------------------------------------------------------------------------


@comment.command("get")
@click.argument("comment_id", type=int)
@click.pass_context
def comment_get(ctx: click.Context, comment_id: int) -> None:
    r"""Show full details for COMMENT_ID.

    \b
    Examples:
        kanboard comment get 7
        kanboard --output json comment get 7
    """
    app: AppContext = ctx.obj
    try:
        c = app.client.comments.get_comment(comment_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(c, app.output)


# ---------------------------------------------------------------------------
# comment add
# ---------------------------------------------------------------------------


@comment.command("add")
@click.argument("task_id", type=int)
@click.argument("content")
@click.option(
    "--user-id",
    type=int,
    required=True,
    help="ID of the user creating the comment.",
)
@click.pass_context
def comment_add(
    ctx: click.Context,
    task_id: int,
    content: str,
    user_id: int,
) -> None:
    r"""Add a new comment CONTENT to TASK_ID.

    \b
    Examples:
        kanboard comment add 42 "Looks good to me." --user-id 1
        kanboard --output json comment add 42 "Needs review." --user-id 2
    """
    app: AppContext = ctx.obj
    try:
        new_id = app.client.comments.create_comment(task_id, user_id, content)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Comment #{new_id} added.", app.output)


# ---------------------------------------------------------------------------
# comment update
# ---------------------------------------------------------------------------


@comment.command("update")
@click.argument("comment_id", type=int)
@click.argument("content")
@click.pass_context
def comment_update(ctx: click.Context, comment_id: int, content: str) -> None:
    r"""Update COMMENT_ID with new CONTENT.

    \b
    Examples:
        kanboard comment update 7 "Updated comment text."
        kanboard --output json comment update 7 "Revised notes."
    """
    app: AppContext = ctx.obj
    try:
        app.client.comments.update_comment(comment_id, content)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Comment #{comment_id} updated.", app.output)


# ---------------------------------------------------------------------------
# comment remove
# ---------------------------------------------------------------------------


@comment.command("remove")
@click.argument("comment_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def comment_remove(ctx: click.Context, comment_id: int, yes: bool) -> None:
    r"""Permanently delete COMMENT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard comment remove 7 --yes
    """
    if not yes:
        click.confirm(
            f"Delete comment #{comment_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.comments.remove_comment(comment_id)
    format_success(f"Comment #{comment_id} removed.", app.output)
