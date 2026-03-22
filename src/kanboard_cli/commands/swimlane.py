"""Swimlane CLI commands — swimlane management for Kanboard projects.

Subcommands: list, get, get-by-name, add, update, remove, enable, disable, move.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "name", "project_id", "position", "is_active", "description"]


# ---------------------------------------------------------------------------
# Swimlane command group
# ---------------------------------------------------------------------------


@click.group()
def swimlane() -> None:
    """Manage project swimlanes."""


# ---------------------------------------------------------------------------
# swimlane list
# ---------------------------------------------------------------------------


@swimlane.command("list")
@click.argument("project_id", type=int)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    default=False,
    help="Show all swimlanes (including inactive); default shows only active ones.",
)
@click.pass_context
def swimlane_list(ctx: click.Context, project_id: int, show_all: bool) -> None:
    r"""List swimlanes for PROJECT_ID.

    By default only active swimlanes are listed.  Pass ``--all`` to include
    inactive ones as well.

    \b
    Examples:
        kanboard swimlane list 1
        kanboard swimlane list 1 --all
        kanboard --output json swimlane list 1
    """
    app: AppContext = ctx.obj
    try:
        if show_all:
            lanes = app.client.swimlanes.get_all_swimlanes(project_id)
        else:
            lanes = app.client.swimlanes.get_active_swimlanes(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(lanes, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# swimlane get
# ---------------------------------------------------------------------------


@swimlane.command("get")
@click.argument("swimlane_id", type=int)
@click.pass_context
def swimlane_get(ctx: click.Context, swimlane_id: int) -> None:
    r"""Show full details for SWIMLANE_ID.

    \b
    Examples:
        kanboard swimlane get 3
        kanboard --output json swimlane get 3
    """
    app: AppContext = ctx.obj
    try:
        lane = app.client.swimlanes.get_swimlane(swimlane_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(lane, app.output)


# ---------------------------------------------------------------------------
# swimlane get-by-name
# ---------------------------------------------------------------------------


@swimlane.command("get-by-name")
@click.argument("project_id", type=int)
@click.argument("name")
@click.pass_context
def swimlane_get_by_name(ctx: click.Context, project_id: int, name: str) -> None:
    r"""Look up a swimlane by NAME within PROJECT_ID.

    \b
    Examples:
        kanboard swimlane get-by-name 1 "Default"
        kanboard --output json swimlane get-by-name 1 "Default"
    """
    app: AppContext = ctx.obj
    try:
        lane = app.client.swimlanes.get_swimlane_by_name(project_id, name)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(lane, app.output)


# ---------------------------------------------------------------------------
# swimlane add
# ---------------------------------------------------------------------------


@swimlane.command("add")
@click.argument("project_id", type=int)
@click.argument("name")
@click.option("--description", "-d", default=None, help="Swimlane description.")
@click.pass_context
def swimlane_add(
    ctx: click.Context,
    project_id: int,
    name: str,
    description: str | None,
) -> None:
    r"""Add a new swimlane NAME to PROJECT_ID.

    \b
    Examples:
        kanboard swimlane add 1 "High Priority"
        kanboard swimlane add 1 "Low Priority" --description "Non-urgent work"
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if description is not None:
        kwargs["description"] = description
    try:
        new_id = app.client.swimlanes.add_swimlane(project_id, name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Swimlane #{new_id} added.", app.output)


# ---------------------------------------------------------------------------
# swimlane update
# ---------------------------------------------------------------------------


@swimlane.command("update")
@click.argument("project_id", type=int)
@click.argument("swimlane_id", type=int)
@click.argument("name")
@click.option("--description", "-d", default=None, help="New swimlane description.")
@click.pass_context
def swimlane_update(
    ctx: click.Context,
    project_id: int,
    swimlane_id: int,
    name: str,
    description: str | None,
) -> None:
    r"""Update SWIMLANE_ID in PROJECT_ID with a new NAME and optional fields.

    \b
    Examples:
        kanboard swimlane update 1 3 "Critical Path"
        kanboard swimlane update 1 3 "Critical Path" --description "Top priority items"
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if description is not None:
        kwargs["description"] = description
    try:
        app.client.swimlanes.update_swimlane(project_id, swimlane_id, name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Swimlane #{swimlane_id} updated.", app.output)


# ---------------------------------------------------------------------------
# swimlane remove
# ---------------------------------------------------------------------------


@swimlane.command("remove")
@click.argument("project_id", type=int)
@click.argument("swimlane_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def swimlane_remove(
    ctx: click.Context,
    project_id: int,
    swimlane_id: int,
    yes: bool,
) -> None:
    r"""Permanently delete SWIMLANE_ID from PROJECT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard swimlane remove 1 3 --yes
    """
    if not yes:
        click.confirm(
            f"Delete swimlane #{swimlane_id} from project #{project_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.swimlanes.remove_swimlane(project_id, swimlane_id)
    format_success(f"Swimlane #{swimlane_id} removed.", app.output)


# ---------------------------------------------------------------------------
# swimlane enable
# ---------------------------------------------------------------------------


@swimlane.command("enable")
@click.argument("project_id", type=int)
@click.argument("swimlane_id", type=int)
@click.pass_context
def swimlane_enable(ctx: click.Context, project_id: int, swimlane_id: int) -> None:
    r"""Enable SWIMLANE_ID in PROJECT_ID.

    \b
    Examples:
        kanboard swimlane enable 1 3
    """
    app: AppContext = ctx.obj
    app.client.swimlanes.enable_swimlane(project_id, swimlane_id)
    format_success(f"Swimlane #{swimlane_id} enabled.", app.output)


# ---------------------------------------------------------------------------
# swimlane disable
# ---------------------------------------------------------------------------


@swimlane.command("disable")
@click.argument("project_id", type=int)
@click.argument("swimlane_id", type=int)
@click.pass_context
def swimlane_disable(ctx: click.Context, project_id: int, swimlane_id: int) -> None:
    r"""Disable SWIMLANE_ID in PROJECT_ID.

    \b
    Examples:
        kanboard swimlane disable 1 3
    """
    app: AppContext = ctx.obj
    app.client.swimlanes.disable_swimlane(project_id, swimlane_id)
    format_success(f"Swimlane #{swimlane_id} disabled.", app.output)


# ---------------------------------------------------------------------------
# swimlane move
# ---------------------------------------------------------------------------


@swimlane.command("move")
@click.argument("project_id", type=int)
@click.argument("swimlane_id", type=int)
@click.argument("position", type=int)
@click.pass_context
def swimlane_move(
    ctx: click.Context,
    project_id: int,
    swimlane_id: int,
    position: int,
) -> None:
    r"""Move SWIMLANE_ID to POSITION within PROJECT_ID.

    POSITION is 1-based (1 = topmost swimlane on the board).

    \b
    Examples:
        kanboard swimlane move 1 3 2
    """
    app: AppContext = ctx.obj
    app.client.swimlanes.change_swimlane_position(project_id, swimlane_id, position)
    format_success(f"Swimlane #{swimlane_id} moved to position {position}.", app.output)
