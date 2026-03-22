"""Project CLI commands — CRUD and management operations for Kanboard projects.

Subcommands: list, get, create, update, remove, enable, disable, activity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default columns rendered in list / table output.
_LIST_COLUMNS = [
    "id",
    "name",
    "is_active",
    "is_public",
    "owner_id",
    "identifier",
    "last_modified",
]


# ---------------------------------------------------------------------------
# Project command group
# ---------------------------------------------------------------------------


@click.group()
def project() -> None:
    """Manage Kanboard projects."""


# ---------------------------------------------------------------------------
# project list
# ---------------------------------------------------------------------------


@project.command("list")
@click.pass_context
def project_list(ctx: click.Context) -> None:
    r"""List all accessible projects.

    \b
    Examples:
        kanboard project list
        kanboard --output json project list
    """
    app: AppContext = ctx.obj
    try:
        projects = app.client.projects.get_all_projects()
    except (KanboardAPIError, KanboardNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(projects, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# project get
# ---------------------------------------------------------------------------


@project.command("get")
@click.argument("project_id", type=int)
@click.pass_context
def project_get(ctx: click.Context, project_id: int) -> None:
    r"""Show full details for PROJECT_ID.

    \b
    Examples:
        kanboard project get 1
        kanboard --output json project get 1
    """
    app: AppContext = ctx.obj
    try:
        proj = app.client.projects.get_project_by_id(project_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(proj, app.output)


# ---------------------------------------------------------------------------
# project create
# ---------------------------------------------------------------------------


@project.command("create")
@click.argument("name")
@click.option("--description", "-d", default=None, help="Project description.")
@click.option("--owner-id", type=int, default=None, help="User ID of the project owner.")
@click.option(
    "--identifier",
    default=None,
    metavar="CODE",
    help="Short identifier code (e.g. PROJ).",
)
@click.option("--start-date", default=None, metavar="DATE", help="Start date (YYYY-MM-DD).")
@click.option("--end-date", default=None, metavar="DATE", help="End date (YYYY-MM-DD).")
@click.pass_context
def project_create(
    ctx: click.Context,
    name: str,
    description: str | None,
    owner_id: int | None,
    identifier: str | None,
    start_date: str | None,
    end_date: str | None,
) -> None:
    r"""Create a new project named NAME.

    \b
    Examples:
        kanboard project create "My Project"
        kanboard project create "Backend" --owner-id 2 --identifier BACK
        kanboard project create "Sprint" --start-date 2025-01-01 --end-date 2025-03-31
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if description is not None:
        kwargs["description"] = description
    if owner_id is not None:
        kwargs["owner_id"] = owner_id
    if identifier is not None:
        kwargs["identifier"] = identifier
    if start_date is not None:
        kwargs["start_date"] = start_date
    if end_date is not None:
        kwargs["end_date"] = end_date
    try:
        new_id = app.client.projects.create_project(name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Project #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# project update
# ---------------------------------------------------------------------------


@project.command("update")
@click.argument("project_id", type=int)
@click.option("--name", default=None, help="New project name.")
@click.option("--description", "-d", default=None, help="New project description.")
@click.option("--owner-id", type=int, default=None, help="New owner user ID.")
@click.option("--identifier", default=None, metavar="CODE", help="New short identifier code.")
@click.pass_context
def project_update(
    ctx: click.Context,
    project_id: int,
    name: str | None,
    description: str | None,
    owner_id: int | None,
    identifier: str | None,
) -> None:
    r"""Update fields on PROJECT_ID.

    Only supplied options are sent to the API; omitted options remain
    unchanged on the server.

    \b
    Examples:
        kanboard project update 1 --name "Renamed Project"
        kanboard project update 1 --owner-id 3 --identifier NEW
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if owner_id is not None:
        kwargs["owner_id"] = owner_id
    if identifier is not None:
        kwargs["identifier"] = identifier
    if not kwargs:
        raise click.UsageError(
            "No fields to update — provide at least one option (e.g. --name, --description)."
        )
    try:
        app.client.projects.update_project(project_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Project #{project_id} updated.", app.output)


# ---------------------------------------------------------------------------
# project remove
# ---------------------------------------------------------------------------


@project.command("remove")
@click.argument("project_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def project_remove(ctx: click.Context, project_id: int, yes: bool) -> None:
    r"""Permanently delete PROJECT_ID and all its data.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard project remove 1 --yes
    """
    if not yes:
        click.confirm(f"Delete project #{project_id}? This cannot be undone.", abort=True)
    app: AppContext = ctx.obj
    app.client.projects.remove_project(project_id)
    format_success(f"Project #{project_id} removed.", app.output)


# ---------------------------------------------------------------------------
# project enable / disable
# ---------------------------------------------------------------------------


@project.command("enable")
@click.argument("project_id", type=int)
@click.pass_context
def project_enable(ctx: click.Context, project_id: int) -> None:
    """Enable (activate) PROJECT_ID."""
    app: AppContext = ctx.obj
    app.client.projects.enable_project(project_id)
    format_success(f"Project #{project_id} enabled.", app.output)


@project.command("disable")
@click.argument("project_id", type=int)
@click.pass_context
def project_disable(ctx: click.Context, project_id: int) -> None:
    """Disable (deactivate) PROJECT_ID."""
    app: AppContext = ctx.obj
    app.client.projects.disable_project(project_id)
    format_success(f"Project #{project_id} disabled.", app.output)


# ---------------------------------------------------------------------------
# project activity
# ---------------------------------------------------------------------------


@project.command("activity")
@click.argument("project_id", type=int)
@click.pass_context
def project_activity(ctx: click.Context, project_id: int) -> None:
    r"""Show the activity feed for PROJECT_ID.

    \b
    Examples:
        kanboard project activity 1
        kanboard --output json project activity 1
    """
    app: AppContext = ctx.obj
    try:
        events = app.client.projects.get_project_activity(project_id)
    except (KanboardAPIError, KanboardNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(events, app.output)
