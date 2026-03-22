"""External link CLI commands - external URL link management for Kanboard tasks.

Subcommands: types, dependencies, list, get, create, update, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "task_id", "title", "url", "dependency", "link_type"]


# ---------------------------------------------------------------------------
# External-link command group
# ---------------------------------------------------------------------------


@click.group(name="external-link")
def external_link() -> None:
    """Manage external links on tasks."""


# ---------------------------------------------------------------------------
# external-link types
# ---------------------------------------------------------------------------


@external_link.command("types")
@click.pass_context
def external_link_types(ctx: click.Context) -> None:
    r"""List all registered external link provider types.

    \b
    Examples:
        kanboard external-link types
        kanboard --output json external-link types
    """
    app: AppContext = ctx.obj
    try:
        types_dict = app.client.external_task_links.get_external_task_link_types()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"provider": k, "label": v} for k, v in types_dict.items()]
    format_output(rows, app.output, columns=["provider", "label"])


# ---------------------------------------------------------------------------
# external-link dependencies
# ---------------------------------------------------------------------------


@external_link.command("dependencies")
@click.argument("provider_name", type=str)
@click.pass_context
def external_link_dependencies(ctx: click.Context, provider_name: str) -> None:
    r"""List dependency types for PROVIDER_NAME.

    \b
    Examples:
        kanboard external-link dependencies weblink
        kanboard --output json external-link dependencies weblink
    """
    app: AppContext = ctx.obj
    try:
        deps = app.client.external_task_links.get_external_task_link_provider_dependencies(
            provider_name
        )
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"dependency": k, "label": v} for k, v in deps.items()]
    format_output(rows, app.output, columns=["dependency", "label"])


# ---------------------------------------------------------------------------
# external-link list
# ---------------------------------------------------------------------------


@external_link.command("list")
@click.argument("task_id", type=int)
@click.pass_context
def external_link_list(ctx: click.Context, task_id: int) -> None:
    r"""List all external links for TASK_ID.

    \b
    Examples:
        kanboard external-link list 42
        kanboard --output json external-link list 42
    """
    app: AppContext = ctx.obj
    try:
        links = app.client.external_task_links.get_all_external_task_links(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(links, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# external-link get
# ---------------------------------------------------------------------------


@external_link.command("get")
@click.argument("task_id", type=int)
@click.argument("link_id", type=int)
@click.pass_context
def external_link_get(ctx: click.Context, task_id: int, link_id: int) -> None:
    r"""Show details for external link LINK_ID on TASK_ID.

    \b
    Examples:
        kanboard external-link get 42 5
        kanboard --output json external-link get 42 5
    """
    app: AppContext = ctx.obj
    try:
        el = app.client.external_task_links.get_external_task_link_by_id(task_id, link_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(el, app.output)


# ---------------------------------------------------------------------------
# external-link create
# ---------------------------------------------------------------------------


@external_link.command("create")
@click.argument("task_id", type=int)
@click.argument("url", type=str)
@click.argument("dependency", type=str)
@click.option("--type", "link_type", default=None, help="External link provider type.")
@click.option("--title", default=None, help="Display title for the link.")
@click.pass_context
def external_link_create(
    ctx: click.Context,
    task_id: int,
    url: str,
    dependency: str,
    link_type: str | None,
    title: str | None,
) -> None:
    r"""Create an external link on TASK_ID.

    \b
    Examples:
        kanboard external-link create 42 https://github.com/issue/1 related
        kanboard external-link create 42 https://doc.example.com related --title "Spec"
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, object] = {}
    if link_type is not None:
        kwargs["type"] = link_type
    if title is not None:
        kwargs["title"] = title
    try:
        new_id = app.client.external_task_links.create_external_task_link(
            task_id, url, dependency, **kwargs
        )
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"External link #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# external-link update
# ---------------------------------------------------------------------------


@external_link.command("update")
@click.argument("task_id", type=int)
@click.argument("link_id", type=int)
@click.argument("title", type=str)
@click.argument("url", type=str)
@click.option("--dependency", default=None, help="New dependency type for the link.")
@click.pass_context
def external_link_update(
    ctx: click.Context,
    task_id: int,
    link_id: int,
    title: str,
    url: str,
    dependency: str | None,
) -> None:
    r"""Update external link LINK_ID on TASK_ID with new TITLE and URL.

    \b
    Examples:
        kanboard external-link update 42 5 "New Title" https://new.example.com
        kanboard external-link update 42 5 "Title" https://url.com --dependency blocked
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, object] = {}
    if dependency is not None:
        kwargs["dependency"] = dependency
    try:
        app.client.external_task_links.update_external_task_link(
            task_id, link_id, title, url, **kwargs
        )
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"External link #{link_id} updated.", app.output)


# ---------------------------------------------------------------------------
# external-link remove
# ---------------------------------------------------------------------------


@external_link.command("remove")
@click.argument("task_id", type=int)
@click.argument("link_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def external_link_remove(ctx: click.Context, task_id: int, link_id: int, yes: bool) -> None:
    r"""Permanently delete external link LINK_ID from TASK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard external-link remove 42 5 --yes
    """
    if not yes:
        click.confirm(
            f"Delete external link #{link_id} from task #{task_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.external_task_links.remove_external_task_link(task_id, link_id)
    format_success(f"External link #{link_id} removed.", app.output)
