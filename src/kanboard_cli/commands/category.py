"""Category CLI commands — task category management for Kanboard.

Subcommands: list, get, create, update, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "name", "project_id", "color_id"]


# ---------------------------------------------------------------------------
# Category command group
# ---------------------------------------------------------------------------


@click.group()
def category() -> None:
    """Manage task categories."""


# ---------------------------------------------------------------------------
# category list
# ---------------------------------------------------------------------------


@category.command("list")
@click.argument("project_id", type=int)
@click.pass_context
def category_list(ctx: click.Context, project_id: int) -> None:
    r"""List all categories for PROJECT_ID.

    \b
    Examples:
        kanboard category list 1
        kanboard --output json category list 1
    """
    app: AppContext = ctx.obj
    try:
        categories = app.client.categories.get_all_categories(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(categories, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# category get
# ---------------------------------------------------------------------------


@category.command("get")
@click.argument("category_id", type=int)
@click.pass_context
def category_get(ctx: click.Context, category_id: int) -> None:
    r"""Show full details for CATEGORY_ID.

    \b
    Examples:
        kanboard category get 3
        kanboard --output json category get 3
    """
    app: AppContext = ctx.obj
    try:
        cat = app.client.categories.get_category(category_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(cat, app.output)


# ---------------------------------------------------------------------------
# category create
# ---------------------------------------------------------------------------


@category.command("create")
@click.argument("project_id", type=int)
@click.argument("name")
@click.option("--color-id", default=None, help="Color ID for the category.")
@click.pass_context
def category_create(
    ctx: click.Context,
    project_id: int,
    name: str,
    color_id: str | None,
) -> None:
    r"""Create a new category NAME in PROJECT_ID.

    \b
    Examples:
        kanboard category create 1 "Frontend"
        kanboard category create 1 "Backend" --color-id blue
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if color_id is not None:
        kwargs["color_id"] = color_id
    try:
        new_id = app.client.categories.create_category(project_id, name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Category #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# category update
# ---------------------------------------------------------------------------


@category.command("update")
@click.argument("category_id", type=int)
@click.argument("name")
@click.option("--color-id", default=None, help="New color ID for the category.")
@click.pass_context
def category_update(
    ctx: click.Context,
    category_id: int,
    name: str,
    color_id: str | None,
) -> None:
    r"""Update CATEGORY_ID with a new NAME.

    \b
    Examples:
        kanboard category update 3 "Renamed Category"
        kanboard category update 3 "Frontend" --color-id green
    """
    app: AppContext = ctx.obj
    kwargs: dict = {}
    if color_id is not None:
        kwargs["color_id"] = color_id
    try:
        app.client.categories.update_category(category_id, name, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Category #{category_id} updated.", app.output)


# ---------------------------------------------------------------------------
# category remove
# ---------------------------------------------------------------------------


@category.command("remove")
@click.argument("category_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def category_remove(ctx: click.Context, category_id: int, yes: bool) -> None:
    r"""Permanently delete CATEGORY_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard category remove 3 --yes
    """
    if not yes:
        click.confirm(
            f"Delete category #{category_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.categories.remove_category(category_id)
    format_success(f"Category #{category_id} removed.", app.output)
