"""Link type CLI commands — link type definition management for Kanboard.

Subcommands: list, get, get-by-label, create, update, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "label", "opposite_id"]


# ---------------------------------------------------------------------------
# Link command group
# ---------------------------------------------------------------------------


@click.group()
def link() -> None:
    """Manage link type definitions."""


# ---------------------------------------------------------------------------
# link list
# ---------------------------------------------------------------------------


@link.command("list")
@click.pass_context
def link_list(ctx: click.Context) -> None:
    r"""List all link type definitions.

    \b
    Examples:
        kanboard link list
        kanboard --output json link list
    """
    app: AppContext = ctx.obj
    try:
        links = app.client.links.get_all_links()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(links, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# link get
# ---------------------------------------------------------------------------


@link.command("get")
@click.argument("link_id", type=int)
@click.pass_context
def link_get(ctx: click.Context, link_id: int) -> None:
    r"""Show full details for link type LINK_ID.

    \b
    Examples:
        kanboard link get 1
        kanboard --output json link get 1
    """
    app: AppContext = ctx.obj
    try:
        lnk = app.client.links.get_link_by_id(link_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(lnk, app.output)


# ---------------------------------------------------------------------------
# link get-by-label
# ---------------------------------------------------------------------------


@link.command("get-by-label")
@click.argument("label")
@click.pass_context
def link_get_by_label(ctx: click.Context, label: str) -> None:
    r"""Look up a link type by its LABEL.

    \b
    Examples:
        kanboard link get-by-label blocks
        kanboard --output json link get-by-label "is blocked by"
    """
    app: AppContext = ctx.obj
    try:
        lnk = app.client.links.get_link_by_label(label)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(lnk, app.output)


# ---------------------------------------------------------------------------
# link create
# ---------------------------------------------------------------------------


@link.command("create")
@click.argument("label")
@click.option(
    "--opposite-label",
    default=None,
    help="Label for the opposite (reverse) side of this link type.",
)
@click.pass_context
def link_create(ctx: click.Context, label: str, opposite_label: str | None) -> None:
    r"""Create a new link type with LABEL.

    \b
    Examples:
        kanboard link create blocks --opposite-label "is blocked by"
        kanboard link create duplicates
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, Any] = {}
    if opposite_label is not None:
        kwargs["opposite_label"] = opposite_label
    try:
        new_id = app.client.links.create_link(label, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Link type #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# link update
# ---------------------------------------------------------------------------


@link.command("update")
@click.argument("link_id", type=int)
@click.argument("opposite_link_id", type=int)
@click.argument("label")
@click.pass_context
def link_update(
    ctx: click.Context,
    link_id: int,
    opposite_link_id: int,
    label: str,
) -> None:
    r"""Update link type LINK_ID with OPPOSITE_LINK_ID and LABEL.

    \b
    Examples:
        kanboard link update 1 2 blocks
    """
    app: AppContext = ctx.obj
    try:
        app.client.links.update_link(link_id, opposite_link_id, label)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Link type #{link_id} updated.", app.output)


# ---------------------------------------------------------------------------
# link remove
# ---------------------------------------------------------------------------


@link.command("remove")
@click.argument("link_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def link_remove(ctx: click.Context, link_id: int, yes: bool) -> None:
    r"""Permanently delete link type LINK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard link remove 5 --yes
    """
    if not yes:
        click.confirm(
            f"Delete link type #{link_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.links.remove_link(link_id)
    format_success(f"Link type #{link_id} removed.", app.output)
