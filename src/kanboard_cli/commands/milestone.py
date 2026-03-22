"""Milestone CLI commands — milestone management within portfolios.

Subcommands: list, show, create, remove, add-task, remove-task, progress.

Milestones are stored locally in ``~/.config/kanboard/portfolios.json`` via
:class:`~kanboard.orchestration.store.LocalPortfolioStore`.  Progress is
computed live from the Kanboard API via
:class:`~kanboard.orchestration.portfolio.PortfolioManager`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import (
    KanboardAPIError,
    KanboardConfigError,
    KanboardConnectionError,
)
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard.orchestration.portfolio import PortfolioManager
    from kanboard.orchestration.store import LocalPortfolioStore
    from kanboard_cli.main import AppContext

logger = logging.getLogger(__name__)

# Default columns for ``milestone list`` table output.
_LIST_COLUMNS = ["name", "target_date", "task_count", "critical_count"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_store() -> LocalPortfolioStore:
    """Instantiate the local portfolio store with the default path.

    Returns:
        A :class:`~kanboard.orchestration.store.LocalPortfolioStore` using
        the default ``~/.config/kanboard/portfolios.json`` path.
    """
    from kanboard.orchestration.store import LocalPortfolioStore

    return LocalPortfolioStore()


def _get_manager(app_ctx: AppContext, store: LocalPortfolioStore) -> PortfolioManager:
    """Instantiate PortfolioManager, raising ClickException if no client configured.

    Args:
        app_ctx: The current application context.
        store: The local portfolio store instance.

    Returns:
        A ready-to-use :class:`~kanboard.orchestration.portfolio.PortfolioManager`.

    Raises:
        click.ClickException: If no Kanboard client is configured.
    """
    from kanboard.orchestration.portfolio import PortfolioManager

    if app_ctx.client is None:
        raise click.ClickException("No Kanboard configuration found. Run 'kanboard config init'.")
    return PortfolioManager(app_ctx.client, store)


def _parse_target_date(date_str: str | None) -> datetime | None:
    """Parse a ``YYYY-MM-DD`` date string to a :class:`~datetime.datetime`.

    Args:
        date_str: Date string in ``YYYY-MM-DD`` format, or ``None``.

    Returns:
        A :class:`~datetime.datetime` at midnight, or ``None`` when *date_str*
        is ``None``.

    Raises:
        click.ClickException: If *date_str* cannot be parsed as ``YYYY-MM-DD``.
    """
    if date_str is None:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise click.ClickException(
            f"Invalid date format '{date_str}'. Expected YYYY-MM-DD (e.g. 2026-06-30)."
        ) from exc


# ---------------------------------------------------------------------------
# Milestone command group
# ---------------------------------------------------------------------------


@click.group()
def milestone() -> None:
    """Manage milestones within a portfolio."""


# ---------------------------------------------------------------------------
# milestone list
# ---------------------------------------------------------------------------


@milestone.command("list")
@click.argument("portfolio_name")
@click.pass_context
def milestone_list(ctx: click.Context, portfolio_name: str) -> None:
    r"""List all milestones in PORTFOLIO_NAME.

    \b
    Examples:
        kanboard milestone list "My Portfolio"
        kanboard --output json milestone list "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    try:
        portfolio_obj = store.get_portfolio(portfolio_name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    rows: list[dict[str, Any]] = [
        {
            "name": m.name,
            "target_date": m.target_date.strftime("%Y-%m-%d") if m.target_date else None,
            "task_count": len(m.task_ids),
            "critical_count": len(m.critical_task_ids),
        }
        for m in portfolio_obj.milestones
    ]
    format_output(rows, app_ctx.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# milestone show
# ---------------------------------------------------------------------------


@milestone.command("show")
@click.argument("portfolio_name")
@click.argument("milestone_name")
@click.pass_context
def milestone_show(ctx: click.Context, portfolio_name: str, milestone_name: str) -> None:
    r"""Show progress for MILESTONE_NAME within PORTFOLIO_NAME.

    Displays a progress bar, completion counts, and blocker info.  Falls back
    to cached store data with a warning when the API is unreachable.

    \b
    Examples:
        kanboard milestone show "My Portfolio" "Sprint 1"
    """
    from kanboard_cli.renderers import render_milestone_progress

    app_ctx: AppContext = ctx.obj
    store = _get_store()

    # Verify the portfolio and milestone exist in the store.
    try:
        portfolio_obj = store.get_portfolio(portfolio_name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    milestone_obj = next(
        (m for m in portfolio_obj.milestones if m.name == milestone_name),
        None,
    )
    if milestone_obj is None:
        raise click.ClickException(
            f"Milestone '{milestone_name}' not found in portfolio '{portfolio_name}'."
        )

    # Try to fetch live progress from the API.
    if app_ctx.client is not None:
        try:
            manager = _get_manager(app_ctx, store)
            progress = manager.get_milestone_progress(portfolio_name, milestone_name)
            click.echo(render_milestone_progress(progress, use_color=False), nl=False)
            if progress.total > 0:
                click.echo(f"\nTasks: {progress.total} total, {progress.completed} completed")
            if progress.blocked_task_ids:
                blocked_refs = ", ".join(f"#{t}" for t in progress.blocked_task_ids)
                click.echo(f"⛔ Blocked tasks: {blocked_refs}")
            return
        except (KanboardConnectionError, KanboardAPIError, Exception) as exc:
            click.echo(
                f"⚠ Warning: API unreachable — showing store data only. ({exc})",
                err=True,
            )

    # Fallback: display basic cached store data.
    click.echo(f"Milestone:   {milestone_obj.name}")
    click.echo(f"Portfolio:   {milestone_obj.portfolio_name}")
    target = milestone_obj.target_date.strftime("%Y-%m-%d") if milestone_obj.target_date else "None"
    click.echo(f"Target date: {target}")
    click.echo(
        f"Tasks:       {len(milestone_obj.task_ids)}"
        f" ({len(milestone_obj.critical_task_ids)} critical)"
    )


# ---------------------------------------------------------------------------
# milestone create
# ---------------------------------------------------------------------------


@milestone.command("create")
@click.argument("portfolio_name")
@click.argument("milestone_name")
@click.option(
    "--target-date",
    default=None,
    metavar="YYYY-MM-DD",
    help="Target completion date (e.g. 2026-06-30).",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Milestone description (informational only; not persisted).",
)
@click.pass_context
def milestone_create(
    ctx: click.Context,
    portfolio_name: str,
    milestone_name: str,
    target_date: str | None,
    description: str | None,  # accepted per spec; not stored (Milestone model has no description)
) -> None:
    r"""Create a new milestone MILESTONE_NAME in PORTFOLIO_NAME.

    \b
    Examples:
        kanboard milestone create "My Portfolio" "Sprint 1"
        kanboard milestone create "My Portfolio" "Q2 Release" --target-date 2026-06-30
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    parsed_date = _parse_target_date(target_date)
    try:
        store.add_milestone(portfolio_name, milestone_name, target_date=parsed_date)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(
        f"Milestone '{milestone_name}' created in portfolio '{portfolio_name}'.",
        app_ctx.output,
    )


# ---------------------------------------------------------------------------
# milestone remove
# ---------------------------------------------------------------------------


@milestone.command("remove")
@click.argument("portfolio_name")
@click.argument("milestone_name")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def milestone_remove(
    ctx: click.Context,
    portfolio_name: str,
    milestone_name: str,
    yes: bool,
) -> None:
    r"""Remove MILESTONE_NAME from PORTFOLIO_NAME.

    Performs best-effort task metadata cleanup in Kanboard when a client is
    configured.  Requires ``--yes`` to confirm.

    \b
    Examples:
        kanboard milestone remove "My Portfolio" "Sprint 1" --yes
    """
    if not yes:
        click.confirm(
            f"Remove milestone '{milestone_name}' from portfolio '{portfolio_name}'?"
            " This cannot be undone.",
            abort=True,
        )

    app_ctx: AppContext = ctx.obj
    store = _get_store()

    try:
        removed = store.remove_milestone(portfolio_name, milestone_name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    if not removed:
        raise click.ClickException(
            f"Milestone '{milestone_name}' not found in portfolio '{portfolio_name}'."
        )

    # Best-effort metadata cleanup: re-sync portfolio metadata so the removed
    # milestone is no longer referenced in task/project metadata.
    if app_ctx.client is not None:
        try:
            from kanboard.orchestration.portfolio import PortfolioManager

            manager = PortfolioManager(app_ctx.client, store)
            manager.sync_metadata(portfolio_name)
        except Exception as exc:
            logger.debug(
                "Metadata cleanup failed after removing milestone '%s' from '%s': %s",
                milestone_name,
                portfolio_name,
                exc,
            )

    format_success(
        f"Milestone '{milestone_name}' removed from portfolio '{portfolio_name}'.",
        app_ctx.output,
    )


# ---------------------------------------------------------------------------
# milestone add-task
# ---------------------------------------------------------------------------


@milestone.command("add-task")
@click.argument("portfolio_name")
@click.argument("milestone_name")
@click.argument("task_id", type=int)
@click.option(
    "--critical",
    is_flag=True,
    default=False,
    help="Mark this task as critical for the milestone.",
)
@click.pass_context
def milestone_add_task(
    ctx: click.Context,
    portfolio_name: str,
    milestone_name: str,
    task_id: int,
    critical: bool,
) -> None:
    r"""Add TASK_ID to MILESTONE_NAME within PORTFOLIO_NAME.

    Validates that the task exists in Kanboard and belongs to a project in
    the portfolio before adding it.

    \b
    Examples:
        kanboard milestone add-task "My Portfolio" "Sprint 1" 42
        kanboard milestone add-task "My Portfolio" "Sprint 1" 42 --critical
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()

    # Load portfolio to validate task project membership.
    try:
        portfolio_obj = store.get_portfolio(portfolio_name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    # Validate task exists and belongs to a portfolio project.
    if app_ctx.client is not None:
        try:
            task_obj = app_ctx.client.tasks.get_task(task_id)
        except Exception as exc:
            raise click.ClickException(f"Task #{task_id} not found: {exc}") from exc

        if task_obj.project_id not in portfolio_obj.project_ids:
            raise click.ClickException(
                f"Task #{task_id} belongs to project #{task_obj.project_id}, "
                f"which is not in portfolio '{portfolio_name}'. "
                f"Add project #{task_obj.project_id} to the portfolio first."
            )

    try:
        store.add_task_to_milestone(portfolio_name, milestone_name, task_id, critical=critical)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    label = " (critical)" if critical else ""
    format_success(
        f"Task #{task_id}{label} added to milestone '{milestone_name}'.",
        app_ctx.output,
    )


# ---------------------------------------------------------------------------
# milestone remove-task
# ---------------------------------------------------------------------------


@milestone.command("remove-task")
@click.argument("portfolio_name")
@click.argument("milestone_name")
@click.argument("task_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def milestone_remove_task(
    ctx: click.Context,
    portfolio_name: str,
    milestone_name: str,
    task_id: int,
    yes: bool,
) -> None:
    r"""Remove TASK_ID from MILESTONE_NAME within PORTFOLIO_NAME.

    Requires ``--yes`` to confirm.

    \b
    Examples:
        kanboard milestone remove-task "My Portfolio" "Sprint 1" 42 --yes
    """
    if not yes:
        click.confirm(
            f"Remove task #{task_id} from milestone '{milestone_name}'?",
            abort=True,
        )

    app_ctx: AppContext = ctx.obj
    store = _get_store()

    try:
        store.remove_task_from_milestone(portfolio_name, milestone_name, task_id)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    format_success(
        f"Task #{task_id} removed from milestone '{milestone_name}'.",
        app_ctx.output,
    )


# ---------------------------------------------------------------------------
# milestone progress
# ---------------------------------------------------------------------------


@milestone.command("progress")
@click.argument("portfolio_name")
@click.argument("milestone_name", required=False, default=None)
@click.pass_context
def milestone_progress(
    ctx: click.Context,
    portfolio_name: str,
    milestone_name: str | None,
) -> None:
    r"""Show progress for milestones in PORTFOLIO_NAME.

    With MILESTONE_NAME, shows a single milestone detail view.  Without it,
    shows progress bars for all milestones in the portfolio.

    \b
    Examples:
        kanboard milestone progress "My Portfolio"
        kanboard milestone progress "My Portfolio" "Sprint 1"
    """
    from kanboard_cli.renderers import render_milestone_progress

    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)

    try:
        if milestone_name is not None:
            progress_list = [manager.get_milestone_progress(portfolio_name, milestone_name)]
        else:
            progress_list = manager.get_all_milestone_progress(portfolio_name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    if not progress_list:
        click.echo("No milestones found.")
        return

    for progress in progress_list:
        click.echo(render_milestone_progress(progress, use_color=False), nl=False)
