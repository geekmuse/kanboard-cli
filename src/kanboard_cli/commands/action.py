"""Action CLI commands - automatic action management for Kanboard projects.

Subcommands: list, available, events, compatible-events, create, remove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "project_id", "event_name", "action_name"]


# ---------------------------------------------------------------------------
# Action command group
# ---------------------------------------------------------------------------


@click.group(name="action")
def action() -> None:
    """Manage automatic actions on projects."""


# ---------------------------------------------------------------------------
# action list
# ---------------------------------------------------------------------------


@action.command("list")
@click.argument("project_id", type=int)
@click.pass_context
def action_list(ctx: click.Context, project_id: int) -> None:
    r"""List all automatic actions for PROJECT_ID.

    \b
    Examples:
        kanboard action list 1
        kanboard --output json action list 1
    """
    app: AppContext = ctx.obj
    try:
        actions = app.client.actions.get_actions(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(actions, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# action available
# ---------------------------------------------------------------------------


@action.command("available")
@click.pass_context
def action_available(ctx: click.Context) -> None:
    r"""List all available automatic action types.

    \b
    Examples:
        kanboard action available
        kanboard --output json action available
    """
    app: AppContext = ctx.obj
    try:
        actions_dict = app.client.actions.get_available_actions()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"action": k, "label": v} for k, v in actions_dict.items()]
    format_output(rows, app.output, columns=["action", "label"])


# ---------------------------------------------------------------------------
# action events
# ---------------------------------------------------------------------------


@action.command("events")
@click.pass_context
def action_events(ctx: click.Context) -> None:
    r"""List all available action events.

    \b
    Examples:
        kanboard action events
        kanboard --output json action events
    """
    app: AppContext = ctx.obj
    try:
        events_dict = app.client.actions.get_available_action_events()
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [{"event": k, "label": v} for k, v in events_dict.items()]
    format_output(rows, app.output, columns=["event", "label"])


# ---------------------------------------------------------------------------
# action compatible-events
# ---------------------------------------------------------------------------


@action.command("compatible-events")
@click.argument("action_name", type=str)
@click.pass_context
def action_compatible_events(ctx: click.Context, action_name: str) -> None:
    r"""List events compatible with ACTION_NAME.

    \b
    Examples:
        kanboard action compatible-events "\\TaskAssignColorColumn"
        kanboard --output json action compatible-events "\\TaskClose"
    """
    app: AppContext = ctx.obj
    try:
        events = app.client.actions.get_compatible_action_events(action_name)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    # events is a list (could be list of strings or dict); handle both
    if events and isinstance(events[0], dict):
        format_output(events, app.output)
    else:
        rows = [{"event": e} for e in events]
        format_output(rows, app.output, columns=["event"])


# ---------------------------------------------------------------------------
# action create
# ---------------------------------------------------------------------------


@action.command("create")
@click.argument("project_id", type=int)
@click.argument("event_name", type=str)
@click.argument("action_name", type=str)
@click.option(
    "--param",
    "-p",
    "params",
    multiple=True,
    metavar="KEY=VALUE",
    help="Action parameter as key=value (repeatable).",
)
@click.pass_context
def action_create(
    ctx: click.Context,
    project_id: int,
    event_name: str,
    action_name: str,
    params: tuple[str, ...],
) -> None:
    r"""Create an automatic action for PROJECT_ID.

    \b
    Examples:
        kanboard action create 1 task.move.column "\\TaskClose" -p column_id=5
        kanboard action create 1 task.create "\\TaskAssignUser" -p user_id=1
    """
    app: AppContext = ctx.obj
    params_dict: dict[str, str] = {}
    for p in params:
        if "=" not in p:
            raise click.ClickException(f"Invalid param format: '{p}'. Expected KEY=VALUE.")
        key, value = p.split("=", 1)
        params_dict[key] = value
    try:
        new_id = app.client.actions.create_action(project_id, event_name, action_name, params_dict)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Action #{new_id} created.", app.output)


# ---------------------------------------------------------------------------
# action remove
# ---------------------------------------------------------------------------


@action.command("remove")
@click.argument("action_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def action_remove(ctx: click.Context, action_id: int, yes: bool) -> None:
    r"""Remove automatic action ACTION_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard action remove 5 --yes
    """
    if not yes:
        click.confirm(
            f"Delete action #{action_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.actions.remove_action(action_id)
    format_success(f"Action #{action_id} removed.", app.output)
