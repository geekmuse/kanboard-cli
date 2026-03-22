"""Project metadata CLI commands — key-value metadata for Kanboard projects.

Subcommands: list, get, set, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["key", "value"]


# ---------------------------------------------------------------------------
# project-meta command group
# ---------------------------------------------------------------------------


@click.group(name="project-meta")
def project_meta() -> None:
    """Manage project metadata (key-value pairs)."""


# ---------------------------------------------------------------------------
# project-meta list
# ---------------------------------------------------------------------------


@project_meta.command("list")
@click.argument("project_id", type=int)
@click.pass_context
def project_meta_list(ctx: click.Context, project_id: int) -> None:
    r"""List all metadata for PROJECT_ID.

    Displays metadata as key-value pairs.

    \b
    Examples:
        kanboard project-meta list 1
        kanboard --output json project-meta list 1
    """
    app: AppContext = ctx.obj
    try:
        meta = app.client.project_metadata.get_project_metadata(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"key": k, "value": v} for k, v in meta.items()]
    format_output(rows, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# project-meta get
# ---------------------------------------------------------------------------


@project_meta.command("get")
@click.argument("project_id", type=int)
@click.argument("name", type=str)
@click.pass_context
def project_meta_get(ctx: click.Context, project_id: int, name: str) -> None:
    r"""Get a single metadata value by NAME from PROJECT_ID.

    \b
    Examples:
        kanboard project-meta get 1 owner
        kanboard --output json project-meta get 1 owner
    """
    app: AppContext = ctx.obj
    try:
        value = app.client.project_metadata.get_project_metadata_by_name(project_id, name)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    row = {"key": name, "value": value}
    format_output(row, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# project-meta set
# ---------------------------------------------------------------------------


@project_meta.command("set")
@click.argument("project_id", type=int)
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.pass_context
def project_meta_set(ctx: click.Context, project_id: int, key: str, value: str) -> None:
    r"""Set a metadata KEY to VALUE on PROJECT_ID.

    Creates or updates a single metadata entry.

    \b
    Examples:
        kanboard project-meta set 1 owner "Alice"
        kanboard --output json project-meta set 1 priority "high"
    """
    app: AppContext = ctx.obj
    try:
        app.client.project_metadata.save_project_metadata(project_id, {key: value})
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Metadata '{key}' saved on project {project_id}.", app.output)


# ---------------------------------------------------------------------------
# project-meta remove
# ---------------------------------------------------------------------------


@project_meta.command("remove")
@click.argument("project_id", type=int)
@click.argument("name", type=str)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def project_meta_remove(
    ctx: click.Context,
    project_id: int,
    name: str,
    yes: bool,
) -> None:
    r"""Remove metadata key NAME from PROJECT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard project-meta remove 1 owner --yes
    """
    if not yes:
        click.confirm(
            f"Delete metadata key '{name}' from project {project_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.project_metadata.remove_project_metadata(project_id, name)
    format_success(f"Metadata '{name}' removed from project {project_id}.", app.output)
