"""Me CLI commands — current authenticated user information.

Subcommands: (default) show, dashboard, activity, projects, overdue,
create-project.

All commands require User API authentication (``--auth-mode user`` with
``KANBOARD_USERNAME`` and ``KANBOARD_PASSWORD``).  When Application API
token auth is active (the default), every command displays a clear error
message directing the user to switch auth modes.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAuthError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext


# ---------------------------------------------------------------------------
# Me command group
# ---------------------------------------------------------------------------


@click.group(name="me", invoke_without_command=True)
@click.pass_context
def me(ctx: click.Context) -> None:
    r"""Commands for the authenticated user ("me" endpoints).

    All subcommands require User API authentication.  Use
    ``--auth-mode user`` together with ``KANBOARD_USERNAME`` and
    ``KANBOARD_PASSWORD`` environment variables (or set them in your
    config profile).

    When invoked without a subcommand, shows the current user profile.

    \b
    Examples:
        kanboard --auth-mode user me
        kanboard --auth-mode user me dashboard
        kanboard --auth-mode user me activity
        kanboard --auth-mode user me projects
        kanboard --auth-mode user me overdue
        kanboard --auth-mode user me create-project "My Project"
    """
    if ctx.invoked_subcommand is None:
        _show_me(ctx)


# ---------------------------------------------------------------------------
# me (default - show current user)
# ---------------------------------------------------------------------------

_USER_COLUMNS = ["id", "username", "name", "email", "role", "is_active"]


def _show_me(ctx: click.Context) -> None:
    """Show the current authenticated user profile.

    Args:
        ctx: The Click context carrying the :class:`~kanboard_cli.main.AppContext`.
    """
    app: AppContext = ctx.obj
    try:
        user = app.client.me.get_me()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output([dataclasses.asdict(user)], app.output, columns=_USER_COLUMNS)


# ---------------------------------------------------------------------------
# me dashboard
# ---------------------------------------------------------------------------


@me.command("dashboard")
@click.pass_context
def me_dashboard(ctx: click.Context) -> None:
    r"""Show the dashboard for the current user.

    Displays a summary of the current user's projects, tasks, and subtasks.

    \b
    Examples:
        kanboard --auth-mode user me dashboard
        kanboard --auth-mode user --output json me dashboard
    """
    app: AppContext = ctx.obj
    try:
        dashboard: dict[str, Any] = app.client.me.get_my_dashboard()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
    # Dashboard is a nested dict; render as a single-row JSON-friendly output
    format_output([dashboard] if dashboard else [], app.output)


# ---------------------------------------------------------------------------
# me activity
# ---------------------------------------------------------------------------


@me.command("activity")
@click.pass_context
def me_activity(ctx: click.Context) -> None:
    r"""Show the activity stream for the current user.

    Lists recent activity events for the authenticated user.

    \b
    Examples:
        kanboard --auth-mode user me activity
        kanboard --auth-mode user --output json me activity
    """
    app: AppContext = ctx.obj
    try:
        events: list[dict[str, Any]] = app.client.me.get_my_activity_stream()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(events, app.output)


# ---------------------------------------------------------------------------
# me projects
# ---------------------------------------------------------------------------


@me.command("projects")
@click.pass_context
def me_projects(ctx: click.Context) -> None:
    r"""List projects the current user is a member of.

    \b
    Examples:
        kanboard --auth-mode user me projects
        kanboard --auth-mode user --output json me projects
    """
    app: AppContext = ctx.obj
    try:
        projects: list[dict[str, Any]] = app.client.me.get_my_projects()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(projects, app.output)


# ---------------------------------------------------------------------------
# me overdue
# ---------------------------------------------------------------------------


@me.command("overdue")
@click.pass_context
def me_overdue(ctx: click.Context) -> None:
    r"""List overdue tasks for the current user.

    \b
    Examples:
        kanboard --auth-mode user me overdue
        kanboard --auth-mode user --output json me overdue
    """
    app: AppContext = ctx.obj
    try:
        tasks: list[dict[str, Any]] = app.client.me.get_my_overdue_tasks()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(tasks, app.output)


# ---------------------------------------------------------------------------
# me create-project
# ---------------------------------------------------------------------------


@me.command("create-project")
@click.argument("name")
@click.option("--description", default=None, help="Project description.")
@click.pass_context
def me_create_project(
    ctx: click.Context,
    name: str,
    description: str | None,
) -> None:
    r"""Create a private project for the current user.

    NAME is the project title.

    \b
    Examples:
        kanboard --auth-mode user me create-project "My Private Project"
        kanboard --auth-mode user me create-project "My Project" --description "Notes"
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, str] = {}
    if description is not None:
        kwargs["description"] = description
    try:
        project_id = app.client.me.create_my_private_project(name, **kwargs)
        format_success(f"Created private project #{project_id}.", app.output)
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
