"""Application info CLI commands - Kanboard instance metadata.

Subcommands: version, timezone, colors, default-color, roles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext


# ---------------------------------------------------------------------------
# App command group
# ---------------------------------------------------------------------------


@click.group(name="app")
def app() -> None:
    """Application-level information and settings."""


# ---------------------------------------------------------------------------
# app version
# ---------------------------------------------------------------------------


@app.command("version")
@click.pass_context
def app_version(ctx: click.Context) -> None:
    r"""Show the Kanboard server version.

    \b
    Examples:
        kanboard app version
        kanboard --output json app version
    """
    app_ctx: AppContext = ctx.obj
    try:
        version = app_ctx.client.application.get_version()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(
        [{"key": "version", "value": version}],
        app_ctx.output,
        columns=["key", "value"],
    )


# ---------------------------------------------------------------------------
# app timezone
# ---------------------------------------------------------------------------


@app.command("timezone")
@click.pass_context
def app_timezone(ctx: click.Context) -> None:
    r"""Show the server default timezone.

    \b
    Examples:
        kanboard app timezone
        kanboard --output json app timezone
    """
    app_ctx: AppContext = ctx.obj
    try:
        tz = app_ctx.client.application.get_timezone()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(
        [{"key": "timezone", "value": tz}],
        app_ctx.output,
        columns=["key", "value"],
    )


# ---------------------------------------------------------------------------
# app colors
# ---------------------------------------------------------------------------


@app.command("colors")
@click.pass_context
def app_colors(ctx: click.Context) -> None:
    r"""Show the default task colour definitions.

    \b
    Examples:
        kanboard app colors
        kanboard --output json app colors
    """
    app_ctx: AppContext = ctx.obj
    try:
        colors = app_ctx.client.application.get_default_task_colors()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"color_id": k, "definition": str(v)} for k, v in colors.items()]
    if not rows:
        rows = []
    format_output(rows, app_ctx.output, columns=["color_id", "definition"])


# ---------------------------------------------------------------------------
# app default-color
# ---------------------------------------------------------------------------


@app.command("default-color")
@click.pass_context
def app_default_color(ctx: click.Context) -> None:
    r"""Show the default task colour identifier.

    \b
    Examples:
        kanboard app default-color
        kanboard --output json app default-color
    """
    app_ctx: AppContext = ctx.obj
    try:
        color = app_ctx.client.application.get_default_task_color()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(
        [{"key": "default_color", "value": color}],
        app_ctx.output,
        columns=["key", "value"],
    )


# ---------------------------------------------------------------------------
# app roles
# ---------------------------------------------------------------------------


@app.command("roles")
@click.pass_context
def app_roles(ctx: click.Context) -> None:
    r"""Show application-level and project-level roles.

    \b
    Examples:
        kanboard app roles
        kanboard --output json app roles
    """
    app_ctx: AppContext = ctx.obj
    try:
        app_roles_dict = app_ctx.client.application.get_application_roles()
        project_roles_dict = app_ctx.client.application.get_project_roles()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows: list[dict[str, str]] = []
    for role_id, label in app_roles_dict.items():
        rows.append({"scope": "application", "role_id": role_id, "label": label})
    for role_id, label in project_roles_dict.items():
        rows.append({"scope": "project", "role_id": role_id, "label": label})
    format_output(rows, app_ctx.output, columns=["scope", "role_id", "label"])
