"""Timer CLI commands - subtask time tracking for Kanboard.

Subcommands: status, start, stop, spent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext


# ---------------------------------------------------------------------------
# Timer command group
# ---------------------------------------------------------------------------


@click.group(name="timer")
def timer() -> None:
    """Start and stop subtask timers."""


# ---------------------------------------------------------------------------
# timer status
# ---------------------------------------------------------------------------


@timer.command("status")
@click.argument("subtask_id", type=int)
@click.option("--user-id", type=int, default=None, help="User ID (defaults to current user).")
@click.pass_context
def timer_status(ctx: click.Context, subtask_id: int, user_id: int | None) -> None:
    r"""Check whether a timer is running for SUBTASK_ID.

    \b
    Examples:
        kanboard timer status 7
        kanboard timer status 7 --user-id 1
        kanboard --output json timer status 7
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, int] = {}
    if user_id is not None:
        kwargs["user_id"] = user_id
    try:
        running = app.client.subtask_time_tracking.has_subtask_timer(subtask_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    row = {"subtask_id": str(subtask_id), "running": str(running)}
    format_output([row], app.output, columns=["subtask_id", "running"])


# ---------------------------------------------------------------------------
# timer start
# ---------------------------------------------------------------------------


@timer.command("start")
@click.argument("subtask_id", type=int)
@click.option("--user-id", type=int, default=None, help="User ID (defaults to current user).")
@click.pass_context
def timer_start(ctx: click.Context, subtask_id: int, user_id: int | None) -> None:
    r"""Start the timer for SUBTASK_ID.

    \b
    Examples:
        kanboard timer start 7
        kanboard timer start 7 --user-id 1
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, int] = {}
    if user_id is not None:
        kwargs["user_id"] = user_id
    try:
        app.client.subtask_time_tracking.set_subtask_start_time(subtask_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Timer started for subtask #{subtask_id}.", app.output)


# ---------------------------------------------------------------------------
# timer stop
# ---------------------------------------------------------------------------


@timer.command("stop")
@click.argument("subtask_id", type=int)
@click.option("--user-id", type=int, default=None, help="User ID (defaults to current user).")
@click.pass_context
def timer_stop(ctx: click.Context, subtask_id: int, user_id: int | None) -> None:
    r"""Stop the timer for SUBTASK_ID.

    \b
    Examples:
        kanboard timer stop 7
        kanboard timer stop 7 --user-id 1
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, int] = {}
    if user_id is not None:
        kwargs["user_id"] = user_id
    try:
        app.client.subtask_time_tracking.set_subtask_end_time(subtask_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Timer stopped for subtask #{subtask_id}.", app.output)


# ---------------------------------------------------------------------------
# timer spent
# ---------------------------------------------------------------------------


@timer.command("spent")
@click.argument("subtask_id", type=int)
@click.option("--user-id", type=int, default=None, help="User ID (defaults to current user).")
@click.pass_context
def timer_spent(ctx: click.Context, subtask_id: int, user_id: int | None) -> None:
    r"""Show total time spent on SUBTASK_ID in hours.

    \b
    Examples:
        kanboard timer spent 7
        kanboard timer spent 7 --user-id 1
        kanboard --output json timer spent 7
    """
    app: AppContext = ctx.obj
    kwargs: dict[str, int] = {}
    if user_id is not None:
        kwargs["user_id"] = user_id
    try:
        hours = app.client.subtask_time_tracking.get_subtask_time_spent(subtask_id, **kwargs)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    row = {"subtask_id": str(subtask_id), "hours_spent": str(hours)}
    format_output([row], app.output, columns=["subtask_id", "hours_spent"])
