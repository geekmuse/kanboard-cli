"""Group CLI commands - user group management for Kanboard.

Subcommands: list, get, create, update, remove, member (sub-group).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "name", "external_id"]
_MEMBER_COLUMNS = ["id", "username", "name", "email", "role"]


# ---------------------------------------------------------------------------
# group command group
# ---------------------------------------------------------------------------


@click.group()
def group() -> None:
    """Manage Kanboard user groups."""


# ---------------------------------------------------------------------------
# group list
# ---------------------------------------------------------------------------


@group.command("list")
@click.pass_context
def group_list(ctx: click.Context) -> None:
    r"""List all user groups.

    \b
    Examples:
        kanboard group list
        kanboard --output json group list
    """
    app: AppContext = ctx.obj
    try:
        groups = app.client.groups.get_all_groups()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(groups, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# group get
# ---------------------------------------------------------------------------


@group.command("get")
@click.argument("group_id", type=int)
@click.pass_context
def group_get(ctx: click.Context, group_id: int) -> None:
    r"""Show details for GROUP_ID.

    \b
    Examples:
        kanboard group get 1
        kanboard --output json group get 1
    """
    app: AppContext = ctx.obj
    try:
        grp = app.client.groups.get_group(group_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(grp, app.output)


# ---------------------------------------------------------------------------
# group create
# ---------------------------------------------------------------------------


@group.command("create")
@click.argument("name")
@click.option("--external-id", default=None, help="Optional external ID for the group.")
@click.pass_context
def group_create(ctx: click.Context, name: str, external_id: str | None) -> None:
    r"""Create a new user group with NAME.

    \b
    Examples:
        kanboard group create "Developers"
        kanboard group create "External" --external-id "ldap-123"
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if external_id is not None:
        kwargs["external_id"] = external_id
    try:
        new_id = app.client.groups.create_group(name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Group '{name}' created with ID #{new_id}.", app.output)


# ---------------------------------------------------------------------------
# group update
# ---------------------------------------------------------------------------


@group.command("update")
@click.argument("group_id", type=int)
@click.option("--name", default=None, help="New name for the group.")
@click.option("--external-id", default=None, help="New external ID for the group.")
@click.pass_context
def group_update(
    ctx: click.Context,
    group_id: int,
    name: str | None,
    external_id: str | None,
) -> None:
    r"""Update GROUP_ID with new values.

    At least one of ``--name`` or ``--external-id`` must be provided.

    \b
    Examples:
        kanboard group update 1 --name "New Name"
        kanboard group update 1 --external-id "ldap-456"
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if name is not None:
        kwargs["name"] = name
    if external_id is not None:
        kwargs["external_id"] = external_id
    if not kwargs:
        raise click.ClickException("Provide at least one of --name or --external-id to update.")
    try:
        app.client.groups.update_group(group_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Group #{group_id} updated.", app.output)


# ---------------------------------------------------------------------------
# group remove
# ---------------------------------------------------------------------------


@group.command("remove")
@click.argument("group_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def group_remove(ctx: click.Context, group_id: int, yes: bool) -> None:
    r"""Permanently delete GROUP_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard group remove 1 --yes
    """
    if not yes:
        click.confirm(
            f"Delete group #{group_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.groups.remove_group(group_id)
    format_success(f"Group #{group_id} removed.", app.output)


# ===========================================================================
# group member sub-group
# ===========================================================================


@group.group("member")
def member() -> None:
    """Manage group membership."""


# ---------------------------------------------------------------------------
# group member list
# ---------------------------------------------------------------------------


@member.command("list")
@click.argument("group_id", type=int)
@click.pass_context
def member_list(ctx: click.Context, group_id: int) -> None:
    r"""List members of GROUP_ID.

    \b
    Examples:
        kanboard group member list 1
        kanboard --output json group member list 1
    """
    app: AppContext = ctx.obj
    try:
        members = app.client.group_members.get_group_members(group_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(members, app.output, columns=_MEMBER_COLUMNS)


# ---------------------------------------------------------------------------
# group member groups
# ---------------------------------------------------------------------------


@member.command("groups")
@click.argument("user_id", type=int)
@click.pass_context
def member_groups(ctx: click.Context, user_id: int) -> None:
    r"""List groups that USER_ID belongs to.

    \b
    Examples:
        kanboard group member groups 1
        kanboard --output json group member groups 1
    """
    app: AppContext = ctx.obj
    try:
        groups = app.client.group_members.get_member_groups(user_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(groups, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# group member add
# ---------------------------------------------------------------------------


@member.command("add")
@click.argument("group_id", type=int)
@click.argument("user_id", type=int)
@click.pass_context
def member_add(ctx: click.Context, group_id: int, user_id: int) -> None:
    r"""Add USER_ID to GROUP_ID.

    \b
    Examples:
        kanboard group member add 1 5
    """
    app: AppContext = ctx.obj
    try:
        app.client.group_members.add_group_member(group_id, user_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"User #{user_id} added to group #{group_id}.", app.output)


# ---------------------------------------------------------------------------
# group member remove
# ---------------------------------------------------------------------------


@member.command("remove")
@click.argument("group_id", type=int)
@click.argument("user_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def member_remove(ctx: click.Context, group_id: int, user_id: int, yes: bool) -> None:
    r"""Remove USER_ID from GROUP_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard group member remove 1 5 --yes
    """
    if not yes:
        click.confirm(
            f"Remove user #{user_id} from group #{group_id}?",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.group_members.remove_group_member(group_id, user_id)
    format_success(f"User #{user_id} removed from group #{group_id}.", app.output)


# ---------------------------------------------------------------------------
# group member check
# ---------------------------------------------------------------------------


@member.command("check")
@click.argument("group_id", type=int)
@click.argument("user_id", type=int)
@click.pass_context
def member_check(ctx: click.Context, group_id: int, user_id: int) -> None:
    r"""Check whether USER_ID is a member of GROUP_ID.

    \b
    Examples:
        kanboard group member check 1 5
        kanboard --output json group member check 1 5
    """
    app: AppContext = ctx.obj
    try:
        result = app.client.group_members.is_group_member(group_id, user_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    data = {
        "group_id": group_id,
        "user_id": user_id,
        "is_member": result,
    }
    format_output(data, app.output)
