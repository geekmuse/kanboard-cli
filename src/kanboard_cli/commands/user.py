"""User CLI commands — user management for Kanboard.

Subcommands: list, get, get-by-name, create, update, remove, enable, disable, is-active.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "username", "name", "email", "role", "is_active"]


# ---------------------------------------------------------------------------
# User command group
# ---------------------------------------------------------------------------


@click.group()
def user() -> None:
    """Manage Kanboard users."""


# ---------------------------------------------------------------------------
# user list
# ---------------------------------------------------------------------------


@user.command("list")
@click.pass_context
def user_list(ctx: click.Context) -> None:
    r"""List all users.

    \b
    Examples:
        kanboard user list
        kanboard --output json user list
    """
    app: AppContext = ctx.obj
    try:
        users = app.client.users.get_all_users()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(users, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# user get
# ---------------------------------------------------------------------------


@user.command("get")
@click.argument("user_id", type=int)
@click.pass_context
def user_get(ctx: click.Context, user_id: int) -> None:
    r"""Show full details for USER_ID.

    \b
    Examples:
        kanboard user get 3
        kanboard --output json user get 3
    """
    app: AppContext = ctx.obj
    try:
        u = app.client.users.get_user(user_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(u, app.output)


# ---------------------------------------------------------------------------
# user get-by-name
# ---------------------------------------------------------------------------


@user.command("get-by-name")
@click.argument("username")
@click.pass_context
def user_get_by_name(ctx: click.Context, username: str) -> None:
    r"""Look up a user by USERNAME.

    \b
    Examples:
        kanboard user get-by-name jdoe
        kanboard --output json user get-by-name jdoe
    """
    app: AppContext = ctx.obj
    try:
        u = app.client.users.get_user_by_name(username)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(u, app.output)


# ---------------------------------------------------------------------------
# user create
# ---------------------------------------------------------------------------


@user.command("create")
@click.argument("username")
@click.option(
    "--password",
    default=None,
    help="Password for the new user (prompted interactively when not supplied).",
)
@click.option("--name", default=None, help="Full display name for the new user.")
@click.option("--email", default=None, help="Email address for the new user.")
@click.option(
    "--role",
    default=None,
    help="Role for the new user (e.g. app-user, app-admin).",
)
@click.pass_context
def user_create(
    ctx: click.Context,
    username: str,
    password: str | None,
    name: str | None,
    email: str | None,
    role: str | None,
) -> None:
    r"""Create a new user with USERNAME.

    If ``--password`` is not given, you will be prompted for one interactively
    (the input is hidden).

    \b
    Examples:
        kanboard user create jdoe --name "John Doe" --email jdoe@example.com
        kanboard user create jdoe --password s3cret --role app-admin
    """
    if password is None:
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if email is not None:
        kwargs["email"] = email
    if role is not None:
        kwargs["role"] = role
    try:
        new_id = app.client.users.create_user(username, password, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"User #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# user update
# ---------------------------------------------------------------------------


@user.command("update")
@click.argument("user_id", type=int)
@click.option("--username", default=None, help="New login name.")
@click.option("--name", default=None, help="New full display name.")
@click.option("--email", default=None, help="New email address.")
@click.option("--role", default=None, help="New role (e.g. app-user, app-admin).")
@click.pass_context
def user_update(
    ctx: click.Context,
    user_id: int,
    username: str | None,
    name: str | None,
    email: str | None,
    role: str | None,
) -> None:
    r"""Update USER_ID with the supplied field(s).

    \b
    Examples:
        kanboard user update 3 --name "Jane Doe"
        kanboard user update 3 --email jane@example.com --role app-admin
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if username is not None:
        kwargs["username"] = username
    if name is not None:
        kwargs["name"] = name
    if email is not None:
        kwargs["email"] = email
    if role is not None:
        kwargs["role"] = role
    try:
        app.client.users.update_user(user_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"User #{user_id} updated.", app.output)


# ---------------------------------------------------------------------------
# user remove
# ---------------------------------------------------------------------------


@user.command("remove")
@click.argument("user_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def user_remove(ctx: click.Context, user_id: int, yes: bool) -> None:
    r"""Permanently delete USER_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard user remove 3 --yes
    """
    if not yes:
        click.confirm(
            f"Delete user #{user_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.users.remove_user(user_id)
    format_success(f"User #{user_id} removed.", app.output)


# ---------------------------------------------------------------------------
# user enable
# ---------------------------------------------------------------------------


@user.command("enable")
@click.argument("user_id", type=int)
@click.pass_context
def user_enable(ctx: click.Context, user_id: int) -> None:
    r"""Enable USER_ID.

    \b
    Examples:
        kanboard user enable 3
    """
    app: AppContext = ctx.obj
    app.client.users.enable_user(user_id)
    format_success(f"User #{user_id} enabled.", app.output)


# ---------------------------------------------------------------------------
# user disable
# ---------------------------------------------------------------------------


@user.command("disable")
@click.argument("user_id", type=int)
@click.pass_context
def user_disable(ctx: click.Context, user_id: int) -> None:
    r"""Disable USER_ID.

    \b
    Examples:
        kanboard user disable 3
    """
    app: AppContext = ctx.obj
    app.client.users.disable_user(user_id)
    format_success(f"User #{user_id} disabled.", app.output)


# ---------------------------------------------------------------------------
# user is-active
# ---------------------------------------------------------------------------


@user.command("is-active")
@click.argument("user_id", type=int)
@click.pass_context
def user_is_active(ctx: click.Context, user_id: int) -> None:
    r"""Report whether USER_ID is currently active.

    \b
    Examples:
        kanboard user is-active 3
    """
    app: AppContext = ctx.obj
    active = app.client.users.is_active_user(user_id)
    status = "active" if active else "inactive"
    format_success(f"User #{user_id} is {status}.", app.output)
