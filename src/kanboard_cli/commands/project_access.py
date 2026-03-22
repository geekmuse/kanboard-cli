"""Project access CLI commands - manage user/group permissions on projects.

Subcommands: list, assignable, add-user, add-group, remove-user, remove-group,
set-user-role, set-group-role, user-role.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default columns for user list tables.
_USER_LIST_COLUMNS = ["user_id", "username"]

# Default columns for single role output.
_ROLE_COLUMNS = ["user_id", "role"]


# ---------------------------------------------------------------------------
# project-access command group
# ---------------------------------------------------------------------------


@click.group(name="project-access")
def project_access() -> None:
    """Manage project user and group access."""


# ---------------------------------------------------------------------------
# project-access list
# ---------------------------------------------------------------------------


@project_access.command("list")
@click.argument("project_id", type=int)
@click.pass_context
def project_access_list(ctx: click.Context, project_id: int) -> None:
    r"""List all users assigned to PROJECT_ID.

    Displays user IDs and usernames for the project.

    \b
    Examples:
        kanboard project-access list 1
        kanboard --output json project-access list 1
    """
    app: AppContext = ctx.obj
    try:
        users = app.client.project_permissions.get_project_users(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"user_id": k, "username": v} for k, v in users.items()]
    format_output(rows, app.output, columns=_USER_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# project-access assignable
# ---------------------------------------------------------------------------


@project_access.command("assignable")
@click.argument("project_id", type=int)
@click.pass_context
def project_access_assignable(ctx: click.Context, project_id: int) -> None:
    r"""List all users assignable to tasks in PROJECT_ID.

    \b
    Examples:
        kanboard project-access assignable 1
        kanboard --output json project-access assignable 1
    """
    app: AppContext = ctx.obj
    try:
        users = app.client.project_permissions.get_assignable_users(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"user_id": k, "username": v} for k, v in users.items()]
    format_output(rows, app.output, columns=_USER_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# project-access add-user
# ---------------------------------------------------------------------------


@project_access.command("add-user")
@click.argument("project_id", type=int)
@click.argument("user_id", type=int)
@click.option("--role", default=None, help="Role to assign (e.g. project-member, project-manager).")
@click.pass_context
def project_access_add_user(
    ctx: click.Context,
    project_id: int,
    user_id: int,
    role: str | None,
) -> None:
    r"""Add a user to PROJECT_ID with an optional role.

    \b
    Examples:
        kanboard project-access add-user 1 42
        kanboard project-access add-user 1 42 --role project-manager
    """
    app: AppContext = ctx.obj
    kwargs = {}
    if role is not None:
        kwargs["role"] = role
    try:
        app.client.project_permissions.add_project_user(project_id, user_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"User {user_id} added to project {project_id}.", app.output)


# ---------------------------------------------------------------------------
# project-access add-group
# ---------------------------------------------------------------------------


@project_access.command("add-group")
@click.argument("project_id", type=int)
@click.argument("group_id", type=int)
@click.option("--role", default=None, help="Role to assign (e.g. project-member, project-viewer).")
@click.pass_context
def project_access_add_group(
    ctx: click.Context,
    project_id: int,
    group_id: int,
    role: str | None,
) -> None:
    r"""Add a group to PROJECT_ID with an optional role.

    \b
    Examples:
        kanboard project-access add-group 1 5
        kanboard project-access add-group 1 5 --role project-viewer
    """
    app: AppContext = ctx.obj
    kwargs = {}
    if role is not None:
        kwargs["role"] = role
    try:
        app.client.project_permissions.add_project_group(project_id, group_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Group {group_id} added to project {project_id}.", app.output)


# ---------------------------------------------------------------------------
# project-access remove-user
# ---------------------------------------------------------------------------


@project_access.command("remove-user")
@click.argument("project_id", type=int)
@click.argument("user_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def project_access_remove_user(
    ctx: click.Context,
    project_id: int,
    user_id: int,
    yes: bool,
) -> None:
    r"""Remove a user from PROJECT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard project-access remove-user 1 42 --yes
    """
    if not yes:
        click.confirm(
            f"Remove user {user_id} from project {project_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.project_permissions.remove_project_user(project_id, user_id)
    format_success(f"User {user_id} removed from project {project_id}.", app.output)


# ---------------------------------------------------------------------------
# project-access remove-group
# ---------------------------------------------------------------------------


@project_access.command("remove-group")
@click.argument("project_id", type=int)
@click.argument("group_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def project_access_remove_group(
    ctx: click.Context,
    project_id: int,
    group_id: int,
    yes: bool,
) -> None:
    r"""Remove a group from PROJECT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard project-access remove-group 1 5 --yes
    """
    if not yes:
        click.confirm(
            f"Remove group {group_id} from project {project_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.project_permissions.remove_project_group(project_id, group_id)
    format_success(f"Group {group_id} removed from project {project_id}.", app.output)


# ---------------------------------------------------------------------------
# project-access set-user-role
# ---------------------------------------------------------------------------


@project_access.command("set-user-role")
@click.argument("project_id", type=int)
@click.argument("user_id", type=int)
@click.argument("role", type=str)
@click.pass_context
def project_access_set_user_role(
    ctx: click.Context,
    project_id: int,
    user_id: int,
    role: str,
) -> None:
    r"""Change the role of USER_ID in PROJECT_ID.

    \b
    Examples:
        kanboard project-access set-user-role 1 42 project-manager
    """
    app: AppContext = ctx.obj
    try:
        app.client.project_permissions.change_project_user_role(project_id, user_id, role)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(
        f"Role for user {user_id} in project {project_id} changed to '{role}'.",
        app.output,
    )


# ---------------------------------------------------------------------------
# project-access set-group-role
# ---------------------------------------------------------------------------


@project_access.command("set-group-role")
@click.argument("project_id", type=int)
@click.argument("group_id", type=int)
@click.argument("role", type=str)
@click.pass_context
def project_access_set_group_role(
    ctx: click.Context,
    project_id: int,
    group_id: int,
    role: str,
) -> None:
    r"""Change the role of GROUP_ID in PROJECT_ID.

    \b
    Examples:
        kanboard project-access set-group-role 1 5 project-viewer
    """
    app: AppContext = ctx.obj
    try:
        app.client.project_permissions.change_project_group_role(project_id, group_id, role)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(
        f"Role for group {group_id} in project {project_id} changed to '{role}'.",
        app.output,
    )


# ---------------------------------------------------------------------------
# project-access user-role
# ---------------------------------------------------------------------------


@project_access.command("user-role")
@click.argument("project_id", type=int)
@click.argument("user_id", type=int)
@click.pass_context
def project_access_user_role(
    ctx: click.Context,
    project_id: int,
    user_id: int,
) -> None:
    r"""Get the role of USER_ID in PROJECT_ID.

    \b
    Examples:
        kanboard project-access user-role 1 42
        kanboard --output json project-access user-role 1 42
    """
    app: AppContext = ctx.obj
    try:
        role = app.client.project_permissions.get_project_user_role(project_id, user_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    row = {"user_id": str(user_id), "role": role}
    format_output(row, app.output, columns=_ROLE_COLUMNS)
