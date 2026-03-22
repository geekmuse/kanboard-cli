"""Portfolio CLI commands — CRUD and aggregation for cross-project portfolio management.

Subcommands: list, show, create, remove, add-project, remove-project, tasks, sync,
dependencies, blocked, blocking, critical-path.

Portfolios are stored locally in ``~/.config/kanboard/portfolios.json`` via
:class:`~kanboard.orchestration.store.LocalPortfolioStore`.  Live task and
milestone data is fetched from the Kanboard API via
:class:`~kanboard.orchestration.portfolio.PortfolioManager`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import click

from kanboard.exceptions import (
    KanboardAPIError,
    KanboardConfigError,
    KanboardConnectionError,
    KanboardNotFoundError,
)
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard.orchestration.dependencies import DependencyAnalyzer
    from kanboard.orchestration.portfolio import PortfolioManager
    from kanboard.orchestration.store import LocalPortfolioStore
    from kanboard_cli.main import AppContext

logger = logging.getLogger(__name__)

# Default columns for ``portfolio tasks`` table output.
_TASKS_COLUMNS = [
    "id",
    "title",
    "project_name",
    "column_title",
    "owner_username",
    "date_due",
    "priority",
]

# Default columns for ``portfolio list`` table output.
_LIST_COLUMNS = ["name", "description", "project_count", "milestone_count"]

# Columns for ``portfolio dependencies --format table`` (flat DependencyEdge rows).
_DEP_EDGE_COLUMNS = [
    "task_id",
    "task_title",
    "task_project_name",
    "opposite_task_id",
    "opposite_task_title",
    "opposite_task_project_name",
    "link_label",
    "is_cross_project",
    "is_resolved",
]

# Columns for ``portfolio blocked`` table output.
_BLOCKED_COLUMNS = ["task_id", "title", "project", "blocked_by_task", "blocked_by_project"]

# Columns for ``portfolio blocking`` table output.
_BLOCKING_COLUMNS = ["task_id", "title", "project", "blocks_task", "blocks_project"]


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


def _get_analyzer(app_ctx: AppContext) -> DependencyAnalyzer:
    """Instantiate DependencyAnalyzer, raising ClickException if no client configured.

    Args:
        app_ctx: The current application context.

    Returns:
        A ready-to-use :class:`~kanboard.orchestration.dependencies.DependencyAnalyzer`.

    Raises:
        click.ClickException: If no Kanboard client is configured.
    """
    from kanboard.orchestration.dependencies import DependencyAnalyzer

    if app_ctx.client is None:
        raise click.ClickException("No Kanboard configuration found. Run 'kanboard config init'.")
    return DependencyAnalyzer(app_ctx.client)


# ---------------------------------------------------------------------------
# Portfolio command group
# ---------------------------------------------------------------------------


@click.group()
def portfolio() -> None:
    """Manage portfolios — cross-project collections with milestone tracking."""


# ---------------------------------------------------------------------------
# portfolio list
# ---------------------------------------------------------------------------


@portfolio.command("list")
@click.pass_context
def portfolio_list(ctx: click.Context) -> None:
    r"""List all portfolios from the local store.

    \b
    Examples:
        kanboard portfolio list
        kanboard --output json portfolio list
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    portfolios = store.load()
    rows: list[dict[str, Any]] = [
        {
            "name": p.name,
            "description": p.description,
            "project_count": len(p.project_ids),
            "milestone_count": len(p.milestones),
        }
        for p in portfolios
    ]
    format_output(rows, app_ctx.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# portfolio show
# ---------------------------------------------------------------------------


@portfolio.command("show")
@click.argument("name")
@click.pass_context
def portfolio_show(ctx: click.Context, name: str) -> None:
    r"""Show portfolio NAME — summary, milestone progress bars, and at-risk items.

    Falls back to cached local-store data with a warning when the Kanboard API
    is unreachable.

    \b
    Examples:
        kanboard portfolio show "My Portfolio"
    """
    from kanboard.orchestration.portfolio import PortfolioManager
    from kanboard_cli.renderers import render_milestone_progress, render_portfolio_summary

    app_ctx: AppContext = ctx.obj
    store = _get_store()

    try:
        portfolio_obj = store.get_portfolio(name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    milestone_progress: list = []
    task_count = 0
    blocked_count = 0
    api_ok = False

    if app_ctx.client is not None:
        try:
            manager = PortfolioManager(app_ctx.client, store)
            tasks = manager.get_portfolio_tasks(name)
            task_count = len(tasks)
            blocked_count = sum(1 for t in tasks if not t.is_active)
            milestone_progress = manager.get_all_milestone_progress(name)
            api_ok = True
        except (KanboardConnectionError, KanboardAPIError, Exception) as exc:
            click.echo(
                f"⚠ Warning: API unreachable — showing cached store data. ({exc})",
                err=True,
            )
    else:
        click.echo(
            "⚠ Warning: No Kanboard configuration — showing cached store data.",
            err=True,
        )

    # Print dashboard summary.
    click.echo(
        render_portfolio_summary(portfolio_obj, milestone_progress, task_count, blocked_count),
        nl=False,
    )

    # Print milestone progress bars.
    if milestone_progress:
        click.echo("\nMilestone Progress:")
        for mp in milestone_progress:
            click.echo(render_milestone_progress(mp, use_color=False), nl=False)
    elif api_ok and not portfolio_obj.milestones:
        click.echo("No milestones defined.")


# ---------------------------------------------------------------------------
# portfolio create
# ---------------------------------------------------------------------------


@portfolio.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Portfolio description.")
@click.pass_context
def portfolio_create(ctx: click.Context, name: str, description: str) -> None:
    r"""Create a new portfolio NAME in the local store.

    \b
    Examples:
        kanboard portfolio create "My Portfolio"
        kanboard portfolio create "Q2 Release" --description "All Q2 work"
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    try:
        store.create_portfolio(name, description)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Portfolio '{name}' created.", app_ctx.output)


# ---------------------------------------------------------------------------
# portfolio remove
# ---------------------------------------------------------------------------


@portfolio.command("remove")
@click.argument("name")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def portfolio_remove(ctx: click.Context, name: str, yes: bool) -> None:
    r"""Remove portfolio NAME from the local store.

    Performs best-effort metadata cleanup in Kanboard when a client is
    configured.  Requires ``--yes`` to confirm.

    \b
    Examples:
        kanboard portfolio remove "My Portfolio" --yes
    """
    if not yes:
        click.confirm(f"Remove portfolio '{name}'? This cannot be undone.", abort=True)

    app_ctx: AppContext = ctx.obj
    store = _get_store()

    # Best-effort metadata cleanup before removing from store.
    if app_ctx.client is not None:
        try:
            from kanboard.orchestration.portfolio import PortfolioManager

            manager = PortfolioManager(app_ctx.client, store)
            manager.sync_metadata(name)
        except Exception as exc:
            logger.debug("Metadata cleanup failed for portfolio '%s': %s", name, exc)

    removed = store.remove_portfolio(name)
    if not removed:
        raise click.ClickException(f"Portfolio '{name}' not found.")
    format_success(f"Portfolio '{name}' removed.", app_ctx.output)


# ---------------------------------------------------------------------------
# portfolio add-project
# ---------------------------------------------------------------------------


@portfolio.command("add-project")
@click.argument("name")
@click.argument("project_id", type=int)
@click.pass_context
def portfolio_add_project(ctx: click.Context, name: str, project_id: int) -> None:
    r"""Add PROJECT_ID to portfolio NAME, validating it exists via the API.

    \b
    Examples:
        kanboard portfolio add-project "My Portfolio" 3
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()

    # Validate the project exists in Kanboard before adding.
    if app_ctx.client is not None:
        try:
            app_ctx.client.projects.get_project_by_id(project_id)
        except (KanboardNotFoundError, KanboardAPIError) as exc:
            raise click.ClickException(f"Project #{project_id} not found: {exc}") from exc

    try:
        store.add_project(name, project_id)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Project #{project_id} added to portfolio '{name}'.", app_ctx.output)


# ---------------------------------------------------------------------------
# portfolio remove-project
# ---------------------------------------------------------------------------


@portfolio.command("remove-project")
@click.argument("name")
@click.argument("project_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm removal without an interactive prompt.",
)
@click.pass_context
def portfolio_remove_project(ctx: click.Context, name: str, project_id: int, yes: bool) -> None:
    r"""Remove PROJECT_ID from portfolio NAME.

    Requires ``--yes`` to confirm.

    \b
    Examples:
        kanboard portfolio remove-project "My Portfolio" 3 --yes
    """
    if not yes:
        click.confirm(
            f"Remove project #{project_id} from portfolio '{name}'?",
            abort=True,
        )

    app_ctx: AppContext = ctx.obj
    store = _get_store()

    try:
        store.remove_project(name, project_id)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(
        f"Project #{project_id} removed from portfolio '{name}'.",
        app_ctx.output,
    )


# ---------------------------------------------------------------------------
# portfolio tasks
# ---------------------------------------------------------------------------


@portfolio.command("tasks")
@click.argument("name")
@click.option(
    "--status",
    type=click.Choice(["active", "closed"], case_sensitive=False),
    default="active",
    show_default=True,
    help="Filter tasks by status (active or closed).",
)
@click.option(
    "--project",
    "project_id",
    type=int,
    default=None,
    help="Limit results to a specific project ID.",
)
@click.option(
    "--assignee",
    "assignee_id",
    type=int,
    default=None,
    help="Limit results to tasks assigned to this user ID.",
)
@click.pass_context
def portfolio_tasks(
    ctx: click.Context,
    name: str,
    status: str,
    project_id: int | None,
    assignee_id: int | None,
) -> None:
    r"""List tasks across all projects in portfolio NAME.

    All four output formats are supported (table, json, csv, quiet).

    \b
    Examples:
        kanboard portfolio tasks "My Portfolio"
        kanboard portfolio tasks "My Portfolio" --status closed --project 2
        kanboard --output json portfolio tasks "My Portfolio" --assignee 5
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)

    status_id = 1 if status == "active" else 0
    try:
        tasks = manager.get_portfolio_tasks(
            name,
            status=status_id,
            project_id=project_id,
            assignee_id=assignee_id,
        )
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    # Enrich tasks with project names — cache to avoid redundant API calls.
    project_name_cache: dict[int, str] = {}
    for task_obj in tasks:
        pid = task_obj.project_id
        if pid not in project_name_cache:
            try:
                project = app_ctx.client.projects.get_project_by_id(pid)  # type: ignore[union-attr]
                project_name_cache[pid] = project.name
            except Exception:
                project_name_cache[pid] = f"Project #{pid}"

    rows: list[dict[str, Any]] = [
        {
            "id": t.id,
            "title": t.title,
            "project_name": project_name_cache.get(t.project_id, f"Project #{t.project_id}"),
            "column_title": t.column_id,
            "owner_username": t.owner_id,
            "date_due": t.date_due,
            "priority": t.priority,
        }
        for t in tasks
    ]
    format_output(rows, app_ctx.output, columns=_TASKS_COLUMNS)


# ---------------------------------------------------------------------------
# portfolio sync
# ---------------------------------------------------------------------------


@portfolio.command("sync")
@click.argument("name")
@click.pass_context
def portfolio_sync(ctx: click.Context, name: str) -> None:
    r"""Sync portfolio NAME metadata to Kanboard projects and tasks.

    Writes ``kanboard_cli:portfolio`` to each project's metadata and
    ``kanboard_cli:milestones`` to each task's metadata.

    \b
    Examples:
        kanboard portfolio sync "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)

    try:
        result = manager.sync_metadata(name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    projects_synced = result.get("projects_synced", 0)
    tasks_synced = result.get("tasks_synced", 0)
    click.echo(f"Synced {projects_synced} projects, {tasks_synced} tasks.")


# ---------------------------------------------------------------------------
# portfolio dependencies
# ---------------------------------------------------------------------------


@portfolio.command("dependencies")
@click.argument("name")
@click.option(
    "--cross-project-only",
    is_flag=True,
    default=False,
    help="Show only cross-project dependency edges.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["graph", "table", "json"], case_sensitive=False),
    default="graph",
    show_default=True,
    help="Visualization format: graph=ASCII render, table=flat rows, json=structured dict.",
)
@click.pass_context
def portfolio_dependencies(
    ctx: click.Context,
    name: str,
    cross_project_only: bool,
    fmt: str,
) -> None:
    r"""Show the dependency graph for all tasks in portfolio NAME.

    Defaults to an ASCII dependency graph.  Use ``--format table`` for flat
    DependencyEdge rows or ``--format json`` for a machine-readable dict.

    \b
    Examples:
        kanboard portfolio dependencies "My Portfolio"
        kanboard portfolio dependencies "My Portfolio" --cross-project-only
        kanboard portfolio dependencies "My Portfolio" --format json
        kanboard --output csv portfolio dependencies "My Portfolio" --format table
    """
    from kanboard_cli.renderers import render_dependency_graph

    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)
    analyzer = _get_analyzer(app_ctx)

    try:
        tasks = manager.get_portfolio_tasks(name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    if fmt == "graph":
        edges = analyzer.get_dependency_edges(tasks, cross_project_only=cross_project_only)
        output = render_dependency_graph(
            edges, tasks, cross_project_only=cross_project_only, use_color=False
        )
        click.echo(output, nl=False)

    elif fmt == "table":
        edges = analyzer.get_dependency_edges(tasks, cross_project_only=cross_project_only)
        rows: list[dict[str, Any]] = [
            {
                "task_id": e.task_id,
                "task_title": e.task_title,
                "task_project_name": e.task_project_name,
                "opposite_task_id": e.opposite_task_id,
                "opposite_task_title": e.opposite_task_title,
                "opposite_task_project_name": e.opposite_task_project_name,
                "link_label": e.link_label,
                "is_cross_project": e.is_cross_project,
                "is_resolved": e.is_resolved,
            }
            for e in edges
        ]
        format_output(rows, app_ctx.output, columns=_DEP_EDGE_COLUMNS)

    else:  # json
        import json

        graph = analyzer.get_dependency_graph(tasks, cross_project_only=cross_project_only)
        click.echo(json.dumps(graph, indent=2))


# ---------------------------------------------------------------------------
# portfolio blocked
# ---------------------------------------------------------------------------


@portfolio.command("blocked")
@click.argument("name")
@click.pass_context
def portfolio_blocked(ctx: click.Context, name: str) -> None:
    r"""List tasks in portfolio NAME that are blocked by cross-project dependencies.

    Shows only edges where the blocking task belongs to a different project
    (``is_cross_project=True``).  All four output formats are supported.

    \b
    Examples:
        kanboard portfolio blocked "My Portfolio"
        kanboard --output json portfolio blocked "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)
    analyzer = _get_analyzer(app_ctx)

    try:
        tasks = manager.get_portfolio_tasks(name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    blocked = analyzer.get_blocked_tasks(tasks)

    rows: list[dict[str, Any]] = []
    for task, edges in blocked:
        for edge in edges:
            if not edge.is_cross_project:
                continue
            rows.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "project": edge.opposite_task_project_name
                    or f"Project #{edge.opposite_task_project_id}",
                    "blocked_by_task": f"#{edge.task_id} {edge.task_title}",
                    "blocked_by_project": edge.task_project_name
                    or f"Project #{edge.task_project_id}",
                }
            )

    format_output(rows, app_ctx.output, columns=_BLOCKED_COLUMNS)


# ---------------------------------------------------------------------------
# portfolio blocking
# ---------------------------------------------------------------------------


@portfolio.command("blocking")
@click.argument("name")
@click.pass_context
def portfolio_blocking(ctx: click.Context, name: str) -> None:
    r"""List tasks in portfolio NAME that are blocking other tasks cross-project.

    Shows only edges where the blocking task and the blocked task belong to
    different projects (``is_cross_project=True``).  All four output formats
    are supported.

    \b
    Examples:
        kanboard portfolio blocking "My Portfolio"
        kanboard --output json portfolio blocking "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)
    analyzer = _get_analyzer(app_ctx)

    try:
        tasks = manager.get_portfolio_tasks(name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    blocking = analyzer.get_blocking_tasks(tasks)

    rows: list[dict[str, Any]] = []
    for task, edges in blocking:
        for edge in edges:
            if not edge.is_cross_project:
                continue
            rows.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "project": edge.task_project_name or f"Project #{edge.task_project_id}",
                    "blocks_task": f"#{edge.opposite_task_id} {edge.opposite_task_title}",
                    "blocks_project": edge.opposite_task_project_name
                    or f"Project #{edge.opposite_task_project_id}",
                }
            )

    format_output(rows, app_ctx.output, columns=_BLOCKING_COLUMNS)


# ---------------------------------------------------------------------------
# portfolio critical-path
# ---------------------------------------------------------------------------


@portfolio.command("critical-path")
@click.argument("name")
@click.pass_context
def portfolio_critical_path(ctx: click.Context, name: str) -> None:
    r"""Show the critical dependency chain for portfolio NAME.

    Identifies the longest unresolved dependency chain across all portfolio
    tasks and annotates the bottleneck — the task whose completion would
    unblock the most downstream work.

    \b
    Examples:
        kanboard portfolio critical-path "My Portfolio"
    """
    from kanboard_cli.renderers import render_critical_path

    app_ctx: AppContext = ctx.obj
    store = _get_store()
    manager = _get_manager(app_ctx, store)
    analyzer = _get_analyzer(app_ctx)

    try:
        tasks = manager.get_portfolio_tasks(name)
    except KanboardConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    except (KanboardAPIError, KanboardConnectionError) as exc:
        raise click.ClickException(str(exc)) from exc

    # Fetch edges first so the task cache is populated.  get_critical_path
    # internally calls get_dependency_edges again; the task cache prevents
    # duplicate getTask calls even though getAllTaskLinks is still fetched twice.
    edges = analyzer.get_dependency_edges(tasks)
    critical = analyzer.get_critical_path(tasks)
    output = render_critical_path(critical, edges)
    click.echo(output, nl=False)
