"""Me CLI commands - current authenticated user information.

Subcommands: (default) show, dashboard, activity, projects, overdue,
create-project.

All commands require User API authentication (username + password). Until
that auth method is implemented, every command displays a clear error message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    When invoked without a subcommand, shows the current user profile.

    \b
    Examples:
        kanboard me
        kanboard me dashboard
        kanboard me activity
        kanboard me projects
        kanboard me overdue
        kanboard me create-project "My Project"
    """
    if ctx.invoked_subcommand is None:
        _show_me(ctx)


# ---------------------------------------------------------------------------
# me (default - show current user)
# ---------------------------------------------------------------------------

_USER_COLUMNS = ["id", "username", "name", "email", "role", "is_active"]


def _show_me(ctx: click.Context) -> None:
    """Show the current authenticated user profile."""
    app: AppContext = ctx.obj
    try:
        user = app.client.me.get_me()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc
    from dataclasses import asdict

    format_output([asdict(user)], app.output, columns=_USER_COLUMNS)


# ---------------------------------------------------------------------------
# me dashboard
# ---------------------------------------------------------------------------


@me.command("dashboard")
@click.pass_context
def me_dashboard(ctx: click.Context) -> None:
    r"""Show the dashboard for the current user.

    \b
    Examples:
        kanboard me dashboard
        kanboard --output json me dashboard
    """
    app: AppContext = ctx.obj
    try:
        app.client.me.get_my_dashboard()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# me activity
# ---------------------------------------------------------------------------


@me.command("activity")
@click.pass_context
def me_activity(ctx: click.Context) -> None:
    r"""Show the activity stream for the current user.

    \b
    Examples:
        kanboard me activity
        kanboard --output json me activity
    """
    app: AppContext = ctx.obj
    try:
        app.client.me.get_my_activity_stream()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# me projects
# ---------------------------------------------------------------------------


@me.command("projects")
@click.pass_context
def me_projects(ctx: click.Context) -> None:
    r"""List projects the current user is a member of.

    \b
    Examples:
        kanboard me projects
        kanboard --output json me projects
    """
    app: AppContext = ctx.obj
    try:
        app.client.me.get_my_projects()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# me overdue
# ---------------------------------------------------------------------------


@me.command("overdue")
@click.pass_context
def me_overdue(ctx: click.Context) -> None:
    r"""List overdue tasks for the current user.

    \b
    Examples:
        kanboard me overdue
        kanboard --output json me overdue
    """
    app: AppContext = ctx.obj
    try:
        app.client.me.get_my_overdue_tasks()
    except KanboardAuthError as exc:
        raise click.ClickException(str(exc)) from exc


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

    \b
    Examples:
        kanboard me create-project "My Private Project"
        kanboard me create-project "My Project" --description "Notes"
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
