"""Portfolio CLI commands — CRUD and aggregation for cross-project portfolio management.

Subcommands: list, show, create, remove, add-project, remove-project, tasks, sync,
dependencies, blocked, blocking, critical-path.

Portfolios are stored and retrieved via a configurable backend:

- **local** (default): ``~/.config/kanboard/portfolios.json`` via
  :class:`~kanboard.orchestration.store.LocalPortfolioStore`.
- **remote**: Kanboard Portfolio Management plugin API via
  :class:`~kanboard.orchestration.backend.RemotePortfolioBackend`.

Select the backend with ``--portfolio-backend local|remote`` (CLI flag),
``KANBOARD_PORTFOLIO_BACKEND`` (env var), or ``portfolio_backend`` (config TOML key).

Live task and milestone data is fetched from the Kanboard API via
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
    from kanboard.models import PluginPortfolio, Portfolio
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

# Columns for ``portfolio migrate diff`` table output.
_DIFF_COLUMNS = ["portfolio", "category", "item", "local", "remote", "status"]


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


def _get_backend(app_ctx: AppContext) -> Any:
    """Return the configured portfolio backend.

    Reads ``app_ctx.config.portfolio_backend`` to select the backend:

    - ``"local"`` (default): :class:`~kanboard.orchestration.store.LocalPortfolioStore`
    - ``"remote"``: :class:`~kanboard.orchestration.backend.RemotePortfolioBackend`

    For the local backend this delegates to :func:`_get_store`, which means
    tests that patch ``_get_store`` continue to work without modification.

    Args:
        app_ctx: The current application context.

    Returns:
        A backend instance satisfying the
        :class:`~kanboard.orchestration.backend.PortfolioBackend` protocol.

    Raises:
        click.ClickException: Remote backend requested but no client configured.
    """
    backend_type = "local"
    if app_ctx.config is not None:
        backend_type = app_ctx.config.portfolio_backend

    if backend_type == "remote":
        if app_ctx.client is None:
            raise click.ClickException(
                "Remote portfolio backend requires Kanboard configuration. "
                "Run 'kanboard config init'."
            )
        from kanboard.orchestration.backend import create_backend

        return create_backend("remote", client=app_ctx.client)

    # Local backend — delegate to _get_store so existing test patches still work.
    return _get_store()


def _is_remote_backend(app_ctx: AppContext) -> bool:
    """Return ``True`` when the configured portfolio backend is ``"remote"``.

    Args:
        app_ctx: The current application context.

    Returns:
        ``True`` if ``portfolio_backend == "remote"``, ``False`` otherwise.
    """
    return bool(app_ctx.config and app_ctx.config.portfolio_backend == "remote")


def _get_manager(app_ctx: AppContext, backend: Any) -> PortfolioManager:
    """Instantiate PortfolioManager, raising ClickException if no client configured.

    Args:
        app_ctx: The current application context.
        backend: The portfolio backend (local store or remote adapter) used as
            the data source for portfolio/milestone metadata lookups.

    Returns:
        A ready-to-use :class:`~kanboard.orchestration.portfolio.PortfolioManager`.

    Raises:
        click.ClickException: If no Kanboard client is configured.
    """
    from kanboard.orchestration.portfolio import PortfolioManager

    if app_ctx.client is None:
        raise click.ClickException("No Kanboard configuration found. Run 'kanboard config init'.")
    return PortfolioManager(app_ctx.client, backend)  # type: ignore[arg-type]


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


def _build_portfolio_diff_rows(
    portfolio_name: str,
    local_pf: Portfolio | None,
    remote_pf: Portfolio | None,
) -> list[dict[str, Any]]:
    """Build diff rows comparing a local and remote portfolio.

    Compares project membership, milestone names, and task assignments
    between the two portfolio instances.  Either side may be ``None`` when
    the portfolio does not exist on that backend.

    Args:
        portfolio_name: Name of the portfolio being compared.
        local_pf: Local portfolio model, or ``None`` if absent locally.
        remote_pf: Remote portfolio model, or ``None`` if absent on remote.

    Returns:
        List of diff row dicts with keys: ``portfolio``, ``category``,
        ``item``, ``local``, ``remote``, ``status``.
    """

    def _row(category: str, item: str, has_local: bool, has_remote: bool) -> dict[str, Any]:
        if has_local and has_remote:
            status = "both"
        elif has_local:
            status = "local only"
        elif has_remote:
            status = "remote only"
        else:
            status = "not found"
        return {
            "portfolio": portfolio_name,
            "category": category,
            "item": item,
            "local": "yes" if has_local else "-",
            "remote": "yes" if has_remote else "-",
            "status": status,
        }

    rows: list[dict[str, Any]] = []

    # Portfolio-level existence row
    rows.append(_row("portfolio", portfolio_name, local_pf is not None, remote_pf is not None))

    # Project membership
    local_pids: set[int] = set(local_pf.project_ids) if local_pf else set()
    remote_pids: set[int] = set(remote_pf.project_ids) if remote_pf else set()
    for pid in sorted(local_pids | remote_pids):
        rows.append(_row("project", f"#{pid}", pid in local_pids, pid in remote_pids))

    # Milestone membership + task assignments
    local_ms: dict[str, Any] = {m.name: m for m in local_pf.milestones} if local_pf else {}
    remote_ms: dict[str, Any] = {m.name: m for m in remote_pf.milestones} if remote_pf else {}
    for mname in sorted(set(local_ms) | set(remote_ms)):
        rows.append(_row("milestone", mname, mname in local_ms, mname in remote_ms))
        lm = local_ms.get(mname)
        rm = remote_ms.get(mname)
        local_tids: set[int] = set(lm.task_ids) if lm else set()
        remote_tids: set[int] = set(rm.task_ids) if rm else set()
        for tid in sorted(local_tids | remote_tids):
            rows.append(_row("task", f"#{tid} ({mname})", tid in local_tids, tid in remote_tids))

    return rows


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
    r"""List all portfolios from the configured backend.

    \b
    Examples:
        kanboard portfolio list
        kanboard --output json portfolio list
        kanboard --portfolio-backend remote portfolio list
    """
    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)
    portfolios = backend.load()
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

    Falls back to cached backend data with a warning when the Kanboard API
    is unreachable.

    \b
    Examples:
        kanboard portfolio show "My Portfolio"
        kanboard --portfolio-backend remote portfolio show "My Portfolio"
    """
    from kanboard.orchestration.portfolio import PortfolioManager
    from kanboard_cli.renderers import render_milestone_progress, render_portfolio_summary

    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)

    try:
        portfolio_obj = backend.get_portfolio(name)
    except (KanboardConfigError, KanboardNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc

    milestone_progress: list = []
    task_count = 0
    blocked_count = 0
    api_ok = False

    if app_ctx.client is not None:
        try:
            manager = PortfolioManager(app_ctx.client, backend)  # type: ignore[arg-type]
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
    r"""Create a new portfolio NAME via the configured backend.

    \b
    Examples:
        kanboard portfolio create "My Portfolio"
        kanboard portfolio create "Q2 Release" --description "All Q2 work"
        kanboard --portfolio-backend remote portfolio create "Remote Portfolio"
    """
    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)
    try:
        backend.create_portfolio(name, description)
    except (ValueError, KanboardAPIError) as exc:
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
    r"""Remove portfolio NAME from the configured backend.

    For the local backend, performs best-effort metadata cleanup in Kanboard
    when a client is configured.  Requires ``--yes`` to confirm.

    \b
    Examples:
        kanboard portfolio remove "My Portfolio" --yes
        kanboard --portfolio-backend remote portfolio remove "My Portfolio" --yes
    """
    if not yes:
        click.confirm(f"Remove portfolio '{name}'? This cannot be undone.", abort=True)

    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)

    # Best-effort metadata cleanup for local backend only.
    if not _is_remote_backend(app_ctx) and app_ctx.client is not None:
        try:
            from kanboard.orchestration.portfolio import PortfolioManager

            manager = PortfolioManager(app_ctx.client, backend)  # type: ignore[arg-type]
            manager.sync_metadata(name)
        except Exception as exc:
            logger.debug("Metadata cleanup failed for portfolio '%s': %s", name, exc)

    removed = backend.remove_portfolio(name)
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
        kanboard --portfolio-backend remote portfolio add-project "My Portfolio" 3
    """
    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)

    # Validate the project exists in Kanboard before adding.
    if app_ctx.client is not None:
        try:
            app_ctx.client.projects.get_project_by_id(project_id)
        except (KanboardNotFoundError, KanboardAPIError) as exc:
            raise click.ClickException(f"Project #{project_id} not found: {exc}") from exc

    try:
        backend.add_project(name, project_id)
    except (KanboardConfigError, KanboardNotFoundError, KanboardAPIError) as exc:
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
        kanboard --portfolio-backend remote portfolio remove-project "My Portfolio" 3 --yes
    """
    if not yes:
        click.confirm(
            f"Remove project #{project_id} from portfolio '{name}'?",
            abort=True,
        )

    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)

    try:
        backend.remove_project(name, project_id)
    except (KanboardConfigError, KanboardNotFoundError, KanboardAPIError) as exc:
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
        kanboard --portfolio-backend remote portfolio tasks "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj
    backend = _get_backend(app_ctx)
    manager = _get_manager(app_ctx, backend)

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

    For the **local** backend, writes ``kanboard_cli:portfolio`` to each
    project's metadata and ``kanboard_cli:milestones`` to each task's metadata.

    For the **remote** backend, this command is a no-op — the plugin manages
    its own server-side data and does not require client-side metadata sync.

    \b
    Examples:
        kanboard portfolio sync "My Portfolio"
        kanboard --portfolio-backend remote portfolio sync "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj

    # Remote backend manages its own server-side data — sync is a no-op.
    if _is_remote_backend(app_ctx):
        click.echo(
            "Portfolio sync is a no-op for the remote backend — "
            "data is already managed server-side."
        )
        return

    backend = _get_backend(app_ctx)
    manager = _get_manager(app_ctx, backend)

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

    For the **local** backend, defaults to an ASCII dependency graph computed
    client-side.  Use ``--format table`` for flat rows or ``--format json``
    for a machine-readable dict.

    For the **remote** backend, delegates to the plugin's server-side SQL
    dependency analysis.  The result is always rendered as flat rows or JSON
    (``--format graph`` falls back to flat rows for remote).

    \b
    Examples:
        kanboard portfolio dependencies "My Portfolio"
        kanboard portfolio dependencies "My Portfolio" --cross-project-only
        kanboard portfolio dependencies "My Portfolio" --format json
        kanboard --output csv portfolio dependencies "My Portfolio" --format table
        kanboard --portfolio-backend remote portfolio dependencies "My Portfolio"
    """
    import json as _json

    app_ctx: AppContext = ctx.obj

    # ------------------------------------------------------------------
    # Remote path — server-side dependency analysis
    # ------------------------------------------------------------------
    if _is_remote_backend(app_ctx):
        if app_ctx.client is None:  # pragma: no cover — _get_backend ensures this
            raise click.ClickException(
                "Remote portfolio backend requires Kanboard configuration. "
                "Run 'kanboard config init'."
            )
        try:
            plugin_pf = app_ctx.client.portfolios.get_portfolio_by_name(name)
        except KanboardNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

        deps = app_ctx.client.portfolios.get_portfolio_dependencies(
            plugin_pf.id, cross_project_only=cross_project_only
        )

        if fmt == "json":
            click.echo(_json.dumps(deps, indent=2))
        else:
            # graph format not available server-side — render as flat rows.
            format_output(deps, app_ctx.output)
        return

    # ------------------------------------------------------------------
    # Local path — client-side DependencyAnalyzer
    # ------------------------------------------------------------------
    from kanboard_cli.renderers import render_dependency_graph

    backend = _get_backend(app_ctx)
    manager = _get_manager(app_ctx, backend)
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
        graph = analyzer.get_dependency_graph(tasks, cross_project_only=cross_project_only)
        click.echo(_json.dumps(graph, indent=2))


# ---------------------------------------------------------------------------
# portfolio blocked
# ---------------------------------------------------------------------------


@portfolio.command("blocked")
@click.argument("name")
@click.pass_context
def portfolio_blocked(ctx: click.Context, name: str) -> None:
    r"""List tasks in portfolio NAME that are blocked by cross-project dependencies.

    For the **local** backend, computes blocked tasks client-side using the
    dependency graph.  For the **remote** backend, delegates to the plugin's
    server-side ``getBlockedTasks`` query.

    \b
    Examples:
        kanboard portfolio blocked "My Portfolio"
        kanboard --output json portfolio blocked "My Portfolio"
        kanboard --portfolio-backend remote portfolio blocked "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj

    # ------------------------------------------------------------------
    # Remote path — server-side blocked-task query
    # ------------------------------------------------------------------
    if _is_remote_backend(app_ctx):
        if app_ctx.client is None:  # pragma: no cover — _get_backend ensures this
            raise click.ClickException(
                "Remote portfolio backend requires Kanboard configuration. "
                "Run 'kanboard config init'."
            )
        try:
            plugin_pf = app_ctx.client.portfolios.get_portfolio_by_name(name)
        except KanboardNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

        data = app_ctx.client.portfolios.get_blocked_tasks(plugin_pf.id)
        format_output(data, app_ctx.output)
        return

    # ------------------------------------------------------------------
    # Local path — client-side DependencyAnalyzer
    # ------------------------------------------------------------------
    backend = _get_backend(app_ctx)
    manager = _get_manager(app_ctx, backend)
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

    For the **local** backend, computes blocking tasks client-side using the
    dependency graph.  For the **remote** backend, delegates to the plugin's
    server-side ``getBlockingTasks`` query.

    \b
    Examples:
        kanboard portfolio blocking "My Portfolio"
        kanboard --output json portfolio blocking "My Portfolio"
        kanboard --portfolio-backend remote portfolio blocking "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj

    # ------------------------------------------------------------------
    # Remote path — server-side blocking-task query
    # ------------------------------------------------------------------
    if _is_remote_backend(app_ctx):
        if app_ctx.client is None:  # pragma: no cover — _get_backend ensures this
            raise click.ClickException(
                "Remote portfolio backend requires Kanboard configuration. "
                "Run 'kanboard config init'."
            )
        try:
            plugin_pf = app_ctx.client.portfolios.get_portfolio_by_name(name)
        except KanboardNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

        data = app_ctx.client.portfolios.get_blocking_tasks(plugin_pf.id)
        format_output(data, app_ctx.output)
        return

    # ------------------------------------------------------------------
    # Local path — client-side DependencyAnalyzer
    # ------------------------------------------------------------------
    backend = _get_backend(app_ctx)
    manager = _get_manager(app_ctx, backend)
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

    For the **local** backend, identifies the longest unresolved dependency
    chain across all portfolio tasks and annotates the bottleneck.

    For the **remote** backend, delegates to the plugin's server-side
    ``getPortfolioCriticalPath`` query and outputs the result as JSON.

    \b
    Examples:
        kanboard portfolio critical-path "My Portfolio"
        kanboard --portfolio-backend remote portfolio critical-path "My Portfolio"
    """
    import json as _json

    app_ctx: AppContext = ctx.obj

    # ------------------------------------------------------------------
    # Remote path — server-side critical-path query
    # ------------------------------------------------------------------
    if _is_remote_backend(app_ctx):
        if app_ctx.client is None:  # pragma: no cover — _get_backend ensures this
            raise click.ClickException(
                "Remote portfolio backend requires Kanboard configuration. "
                "Run 'kanboard config init'."
            )
        try:
            plugin_pf = app_ctx.client.portfolios.get_portfolio_by_name(name)
        except KanboardNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

        path = app_ctx.client.portfolios.get_portfolio_critical_path(plugin_pf.id)
        click.echo(_json.dumps(path, indent=2))
        return

    # ------------------------------------------------------------------
    # Local path — client-side DependencyAnalyzer
    # ------------------------------------------------------------------
    from kanboard_cli.renderers import render_critical_path

    backend = _get_backend(app_ctx)
    manager = _get_manager(app_ctx, backend)
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


# ---------------------------------------------------------------------------
# portfolio migrate (read-only migration helpers)
# ---------------------------------------------------------------------------


@portfolio.group("migrate")
def portfolio_migrate() -> None:
    """Read-only migration helpers — compare local and remote backend data."""


@portfolio_migrate.command("status")
@click.pass_context
def migrate_status(ctx: click.Context) -> None:
    r"""Show migration status: backend config, local counts, remote counts.

    Reads the local store and probes the remote plugin API (if configured).
    All operations are non-destructive.

    \b
    Examples:
        kanboard portfolio migrate status
    """
    import os

    app_ctx: AppContext = ctx.obj

    # ── Backend configuration ──────────────────────────────────────────────
    backend_value = "local"
    if app_ctx.config is not None:
        backend_value = app_ctx.config.portfolio_backend

    env_val = os.environ.get("KANBOARD_PORTFOLIO_BACKEND")
    config_source = (
        f"env var (KANBOARD_PORTFOLIO_BACKEND={env_val!r})" if env_val else "config file / default"
    )

    click.echo("Backend Configuration")
    click.echo(f"  Active backend : {backend_value}")
    click.echo(f"  Config source  : {config_source}")
    click.echo()

    # ── Local store ────────────────────────────────────────────────────────
    click.echo("Local Store")
    local_store = _get_store()
    try:
        local_portfolios = local_store.load()
        local_portfolio_count = len(local_portfolios)
        local_milestone_count = sum(len(p.milestones) for p in local_portfolios)
        local_task_count = sum(len(m.task_ids) for p in local_portfolios for m in p.milestones)
        click.echo(f"  Portfolios       : {local_portfolio_count}")
        click.echo(f"  Milestones       : {local_milestone_count}")
        click.echo(f"  Task assignments : {local_task_count}")
    except Exception as exc:
        click.echo(f"  Status : \u26a0 Error reading store \u2014 {exc}")
    click.echo()

    # ── Remote (plugin API) ────────────────────────────────────────────────
    click.echo("Remote (Plugin API)")
    if app_ctx.client is None:
        click.echo("  Status : Not configured (no Kanboard URL/token)")
        return

    from kanboard.orchestration.backend import create_backend

    try:
        remote_backend = create_backend("remote", client=app_ctx.client)
        remote_portfolios = remote_backend.load()
        remote_milestone_count = sum(len(p.milestones) for p in remote_portfolios)
        remote_task_count = sum(len(m.task_ids) for p in remote_portfolios for m in p.milestones)
        click.echo("  Plugin detected  : Yes")
        click.echo(f"  Portfolios       : {len(remote_portfolios)}")
        click.echo(f"  Milestones       : {remote_milestone_count}")
        click.echo(f"  Task assignments : {remote_task_count}")
    except KanboardConfigError as exc:
        if "kanboard-plugin-portfolio-management" in str(exc):
            click.echo("  Plugin detected  : No")
            click.echo(f"  Detail           : {exc}")
        else:
            click.echo(f"  Status : \u26a0 Configuration error \u2014 {exc}")
    except (KanboardConnectionError, KanboardAPIError, Exception) as exc:
        click.echo(f"  Status : \u26a0 Unreachable \u2014 {exc}")


def _migrate_one_portfolio_local_to_remote(
    pf: Portfolio,
    app_ctx: AppContext,
    *,
    dry_run: bool,
    on_conflict: str,
) -> str:
    """Migrate a single portfolio from local store to the remote plugin backend.

    On success returns ``"ok"``.  When the portfolio is skipped due to a
    ``"skip"`` conflict strategy, returns ``"skip"``.  All other failures
    raise an exception so the caller can log them and continue (``--all``
    mode) or convert them to :class:`~click.ClickException` (single mode).

    Args:
        pf: The local :class:`~kanboard.models.Portfolio` to migrate.
        app_ctx: Current application context.
        dry_run: When ``True``, print planned operations without executing
            any remote API calls.
        on_conflict: Conflict resolution strategy — ``"fail"``, ``"skip"``,
            or ``"overwrite"``.

    Returns:
        ``"ok"`` on success, ``"skip"`` when portfolio was intentionally
        skipped.

    Raises:
        ValueError: *on_conflict* is ``"fail"`` and a same-named portfolio
            already exists on the server.
        KanboardAPIError: A remote API call failed.
        KanboardNotFoundError: An unexpected lookup failure occurred.
    """
    prefix = "[dry-run] " if dry_run else ""

    # ── Conflict detection (remote read — skipped in dry-run) ──────────────
    if not dry_run:
        try:
            existing = app_ctx.client.portfolios.get_portfolio_by_name(pf.name)  # type: ignore[union-attr]
            # Portfolio exists on remote — apply conflict strategy.
            if on_conflict == "fail":
                raise ValueError(
                    f"Portfolio '{pf.name}' already exists on the server. "
                    "Use --on-conflict skip or --on-conflict overwrite to handle conflicts."
                )
            if on_conflict == "skip":
                click.echo(f"Portfolio '{pf.name}' already exists on server — skipping.")
                return "skip"
            # overwrite — remove the existing remote portfolio first.
            click.echo(f"Removing existing remote portfolio '{pf.name}'...")
            app_ctx.client.portfolios.remove_portfolio(existing.id)  # type: ignore[union-attr]
        except KanboardNotFoundError:
            pass  # No conflict — proceed with migration.

    # ── Create portfolio ───────────────────────────────────────────────────
    click.echo(f"{prefix}Creating portfolio '{pf.name}'...")
    portfolio_id: int | None = None
    if not dry_run:
        portfolio_id = app_ctx.client.portfolios.create_portfolio(  # type: ignore[union-attr]
            pf.name, description=pf.description
        )

    # ── Add projects ───────────────────────────────────────────────────────
    for project_id in pf.project_ids:
        click.echo(f"{prefix}  Adding project #{project_id}...")
        if not dry_run:
            app_ctx.client.portfolios.add_project_to_portfolio(  # type: ignore[union-attr]
                portfolio_id, project_id
            )

    # ── Create milestones and add tasks ────────────────────────────────────
    for milestone in pf.milestones:
        click.echo(f"{prefix}  Creating milestone '{milestone.name}'...")
        milestone_id: int | None = None
        if not dry_run:
            ms_kwargs: dict[str, Any] = {}
            if milestone.target_date is not None:
                ms_kwargs["target_date"] = milestone.target_date
            milestone_id = app_ctx.client.milestones.create_milestone(  # type: ignore[union-attr]
                portfolio_id, milestone.name, **ms_kwargs
            )
        for task_id in milestone.task_ids:
            click.echo(f"{prefix}    Adding task #{task_id} to milestone '{milestone.name}'...")
            if not dry_run:
                app_ctx.client.milestones.add_task_to_milestone(  # type: ignore[union-attr]
                    milestone_id, task_id
                )

    click.echo(f"{prefix}Portfolio '{pf.name}' migrated successfully.")
    return "ok"


@portfolio_migrate.command("local-to-remote")
@click.argument("name", required=False, default=None)
@click.option(
    "--all",
    "all_portfolios",
    is_flag=True,
    default=False,
    help="Migrate all local portfolios to the remote backend.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print planned operations without executing any remote API calls.",
)
@click.option(
    "--on-conflict",
    type=click.Choice(["skip", "overwrite", "fail"], case_sensitive=False),
    default="fail",
    show_default=True,
    help=(
        "Conflict resolution when a same-named portfolio already exists on the server: "
        "fail=abort (default), skip=continue, overwrite=remove and recreate (requires --yes)."
    ),
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm destructive overwrite without an interactive prompt.",
)
@click.pass_context
def migrate_local_to_remote(
    ctx: click.Context,
    name: str | None,
    all_portfolios: bool,
    dry_run: bool,
    on_conflict: str,
    yes: bool,
) -> None:
    r"""Migrate portfolio(s) from the local store to the remote plugin backend.

    NAME migrates a single named portfolio.  Use ``--all`` to migrate every
    portfolio found in the local store.

    Progress is printed step-by-step.  Use ``--dry-run`` to preview all
    planned operations without making any remote API calls.

    Conflict resolution (``--on-conflict``) determines what happens when a
    same-named portfolio already exists on the server:

    \b
    - fail (default): abort with an error
    - skip: skip the portfolio and continue (useful with --all)
    - overwrite: remove the server portfolio and recreate from local data
      (requires --yes to confirm the destructive action)

    Migration is **not** transactional — partial failures leave partial state
    on the server that can be cleaned up with ``portfolio remove``.

    \b
    Examples:
        kanboard portfolio migrate local-to-remote "My Portfolio"
        kanboard portfolio migrate local-to-remote --all
        kanboard portfolio migrate local-to-remote "My Portfolio" --dry-run
        kanboard portfolio migrate local-to-remote --all --on-conflict skip
        kanboard portfolio migrate local-to-remote "My Portfolio" \\
            --on-conflict overwrite --yes
    """
    app_ctx: AppContext = ctx.obj

    if not all_portfolios and name is None:
        raise click.UsageError("Provide a portfolio NAME or use --all to migrate all portfolios.")

    # Overwrite mode is destructive — require explicit confirmation.
    if on_conflict == "overwrite" and not yes and not dry_run:
        click.confirm(
            "Overwrite will remove and recreate existing server portfolios. Continue?",
            abort=True,
        )

    # Client is required for remote API calls (not needed in dry-run).
    if not dry_run and app_ctx.client is None:
        raise click.ClickException(
            "Remote portfolio backend requires Kanboard configuration. Run 'kanboard config init'."
        )

    # Load the local portfolio store.
    local_store = _get_store()
    try:
        local_portfolios = local_store.load()
    except Exception as exc:
        raise click.ClickException(f"Failed to read local store: {exc}") from exc

    # Determine which portfolio(s) to migrate.
    if all_portfolios:
        portfolios_to_migrate = local_portfolios
    else:
        assert name is not None
        matching = [p for p in local_portfolios if p.name == name]
        if not matching:
            raise click.ClickException(f"Portfolio '{name}' not found in local store.")
        portfolios_to_migrate = matching

    if not portfolios_to_migrate:
        click.echo("No portfolios to migrate.")
        return

    migrated = 0
    failed = 0

    for pf in portfolios_to_migrate:
        try:
            status = _migrate_one_portfolio_local_to_remote(
                pf,
                app_ctx,
                dry_run=dry_run,
                on_conflict=on_conflict,
            )
            if status == "ok":
                migrated += 1
            # "skip" status: intentionally skipped — not counted as migrated or failed
        except click.exceptions.Abort:
            raise
        except Exception as exc:
            if all_portfolios:
                click.echo(f"  \u2717 Error migrating '{pf.name}': {exc}", err=True)
                failed += 1
            else:
                if isinstance(exc, click.ClickException):
                    raise
                raise click.ClickException(str(exc)) from exc

    click.echo()
    click.echo(f"Migrated {migrated} portfolio{'s' if migrated != 1 else ''} ({failed} failed).")


def _migrate_one_portfolio_remote_to_local(
    plugin_pf: PluginPortfolio,
    app_ctx: AppContext,
    local_store: LocalPortfolioStore,
    *,
    dry_run: bool,
    on_conflict: str,
) -> str:
    """Migrate a single portfolio from the remote plugin backend to the local store.

    On success returns ``"ok"``.  When the portfolio is skipped due to a
    ``"skip"`` conflict strategy, returns ``"skip"``.  All other failures
    raise an exception so the caller can log them and continue (``--all``
    mode) or convert them to :class:`~click.ClickException` (single mode).

    Args:
        plugin_pf: The remote :class:`~kanboard.models.PluginPortfolio` to migrate.
        app_ctx: Current application context.
        local_store: The local portfolio store to write to.
        dry_run: When ``True``, print planned operations without writing to
            the local store.  Remote API calls are still made to determine
            what would be migrated.
        on_conflict: Conflict resolution strategy -- ``"fail"``, ``"skip"``,
            or ``"overwrite"``.

    Returns:
        ``"ok"`` on success, ``"skip"`` when portfolio was intentionally
        skipped.

    Raises:
        ValueError: *on_conflict* is ``"fail"`` and a same-named portfolio
            already exists in the local store.
        KanboardAPIError: A remote API call failed.
        KanboardConfigError: An unexpected lookup failure occurred.
    """
    prefix = "[dry-run] " if dry_run else ""

    # ── Conflict detection (local read -- OK in dry-run) ──────────────────
    local_portfolios = local_store.load()
    local_names = {p.name for p in local_portfolios}
    if plugin_pf.name in local_names:
        if on_conflict == "fail":
            raise ValueError(
                f"Portfolio '{plugin_pf.name}' already exists in the local store. "
                "Use --on-conflict skip or --on-conflict overwrite to handle conflicts."
            )
        if on_conflict == "skip":
            click.echo(f"Portfolio '{plugin_pf.name}' already exists locally — skipping.")
            return "skip"
        # overwrite -- remove existing local portfolio first.
        click.echo(f"Removing existing local portfolio '{plugin_pf.name}'...")
        if not dry_run:
            local_store.remove_portfolio(plugin_pf.name)

    # ── Fetch remote data (read-only; done even in dry-run to show the plan) ──
    project_dicts = app_ctx.client.portfolios.get_portfolio_projects(  # type: ignore[union-attr]
        plugin_pf.id
    )
    plugin_milestones = app_ctx.client.milestones.get_portfolio_milestones(  # type: ignore[union-attr]
        plugin_pf.id
    )
    milestone_tasks: dict[int, list[int]] = {}
    for ms in plugin_milestones:
        raw_tasks = app_ctx.client.milestones.get_milestone_tasks(ms.id)  # type: ignore[union-attr]
        milestone_tasks[ms.id] = [int(t["id"]) for t in raw_tasks if t.get("id")]

    # ── Create portfolio locally ───────────────────────────────────────────
    click.echo(f"{prefix}Creating portfolio '{plugin_pf.name}'...")
    if not dry_run:
        local_store.create_portfolio(plugin_pf.name, plugin_pf.description)

    # ── Add projects ──────────────────────────────────────────────────────
    project_ids = [int(p["id"]) for p in project_dicts if p.get("id")]
    for pid in project_ids:
        click.echo(f"{prefix}  Adding project #{pid}...")
        if not dry_run:
            local_store.add_project(plugin_pf.name, pid)

    # ── Create milestones and add tasks ────────────────────────────────────
    for ms in plugin_milestones:
        click.echo(f"{prefix}  Creating milestone '{ms.name}'...")
        if not dry_run:
            local_store.add_milestone(plugin_pf.name, ms.name, target_date=ms.target_date)
        for task_id in milestone_tasks.get(ms.id, []):
            click.echo(f"{prefix}    Adding task #{task_id} to milestone '{ms.name}'...")
            if not dry_run:
                local_store.add_task_to_milestone(plugin_pf.name, ms.name, task_id)

    click.echo(f"{prefix}Portfolio '{plugin_pf.name}' migrated successfully.")
    return "ok"


@portfolio_migrate.command("remote-to-local")
@click.argument("name", required=False, default=None)
@click.option(
    "--all",
    "all_portfolios",
    is_flag=True,
    default=False,
    help="Migrate all remote portfolios to the local store.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help=(
        "Print planned operations without writing to the local store.  "
        "Remote API calls are still made to determine what would be migrated."
    ),
)
@click.option(
    "--on-conflict",
    type=click.Choice(["skip", "overwrite", "fail"], case_sensitive=False),
    default="fail",
    show_default=True,
    help=(
        "Conflict resolution when a same-named portfolio already exists locally: "
        "fail=abort (default), skip=continue, overwrite=remove and recreate (requires --yes)."
    ),
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm destructive overwrite without an interactive prompt.",
)
@click.pass_context
def migrate_remote_to_local(
    ctx: click.Context,
    name: str | None,
    all_portfolios: bool,
    dry_run: bool,
    on_conflict: str,
    yes: bool,
) -> None:
    r"""Migrate portfolio(s) from the remote plugin backend to the local store.

    NAME migrates a single named portfolio.  Use ``--all`` to migrate every
    portfolio found on the remote backend.

    Progress is printed step-by-step.  Use ``--dry-run`` to preview all
    planned operations without writing to the local store (remote API calls
    are still made to determine what would be migrated).

    Conflict resolution (``--on-conflict``) determines what happens when a
    same-named portfolio already exists in the local store:

    \b
    - fail (default): abort with an error
    - skip: skip the portfolio and continue (useful with --all)
    - overwrite: remove the local portfolio and recreate from remote data
      (requires --yes to confirm the destructive action)

    Migration is **not** transactional -- partial failures leave partial state
    in the local store that can be cleaned up with ``portfolio remove``.

    \b
    Examples:
        kanboard portfolio migrate remote-to-local "My Portfolio"
        kanboard portfolio migrate remote-to-local --all
        kanboard portfolio migrate remote-to-local "My Portfolio" --dry-run
        kanboard portfolio migrate remote-to-local --all --on-conflict skip
        kanboard portfolio migrate remote-to-local "My Portfolio" \\
            --on-conflict overwrite --yes
    """
    app_ctx: AppContext = ctx.obj

    if not all_portfolios and name is None:
        raise click.UsageError("Provide a portfolio NAME or use --all to migrate all portfolios.")

    # Overwrite mode is destructive -- require explicit confirmation.
    if on_conflict == "overwrite" and not yes and not dry_run:
        click.confirm(
            "Overwrite will remove and recreate existing local portfolios. Continue?",
            abort=True,
        )

    # Client is required to fetch from the remote plugin API.
    if app_ctx.client is None:
        raise click.ClickException(
            "Remote portfolio backend requires Kanboard configuration. Run 'kanboard config init'."
        )

    # Local store to write migrated portfolios into.
    local_store = _get_store()

    # Determine which portfolio(s) to migrate.
    if all_portfolios:
        try:
            plugin_portfolios = app_ctx.client.portfolios.get_all_portfolios()
        except (KanboardConfigError, KanboardAPIError) as exc:
            raise click.ClickException(f"Failed to fetch remote portfolios: {exc}") from exc
    else:
        assert name is not None
        try:
            plugin_pf = app_ctx.client.portfolios.get_portfolio_by_name(name)
        except KanboardNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc
        plugin_portfolios = [plugin_pf]

    if not plugin_portfolios:
        click.echo("No portfolios to migrate.")
        return

    migrated = 0
    failed = 0

    for pf in plugin_portfolios:
        try:
            status = _migrate_one_portfolio_remote_to_local(
                pf,
                app_ctx,
                local_store,
                dry_run=dry_run,
                on_conflict=on_conflict,
            )
            if status == "ok":
                migrated += 1
            # "skip" status: intentionally skipped -- not counted as migrated or failed
        except click.exceptions.Abort:
            raise
        except Exception as exc:
            if all_portfolios:
                click.echo(f"  \u2717 Error migrating '{pf.name}': {exc}", err=True)
                failed += 1
            else:
                if isinstance(exc, click.ClickException):
                    raise
                raise click.ClickException(str(exc)) from exc

    click.echo()
    click.echo(f"Migrated {migrated} portfolio{'s' if migrated != 1 else ''} ({failed} failed).")


@portfolio_migrate.command("diff")
@click.argument("name", required=False, default=None)
@click.option(
    "--all",
    "all_portfolios",
    is_flag=True,
    default=False,
    help="Compare all portfolios found on either side.",
)
@click.pass_context
def migrate_diff(ctx: click.Context, name: str | None, all_portfolios: bool) -> None:
    r"""Compare local and remote portfolio state, showing differences.

    NAME compares a single named portfolio.  Use ``--all`` to compare every
    portfolio found on either the local store or the remote plugin API.

    \b
    Examples:
        kanboard portfolio migrate diff "My Portfolio"
        kanboard portfolio migrate diff --all
        kanboard --output json portfolio migrate diff "My Portfolio"
    """
    app_ctx: AppContext = ctx.obj

    if not all_portfolios and name is None:
        raise click.UsageError("Provide a portfolio NAME or use --all to compare all portfolios.")

    # ── Fetch local portfolios ─────────────────────────────────────────────
    local_store = _get_store()
    try:
        local_portfolios_list = local_store.load()
    except Exception as exc:
        raise click.ClickException(f"Failed to read local store: {exc}") from exc
    local_by_name: dict[str, Any] = {p.name: p for p in local_portfolios_list}

    # ── Fetch remote portfolios ────────────────────────────────────────────
    remote_by_name: dict[str, Any] = {}
    remote_ok = False
    if app_ctx.client is not None:
        from kanboard.orchestration.backend import create_backend

        try:
            remote_backend = create_backend("remote", client=app_ctx.client)
            remote_portfolios_list = remote_backend.load()
            remote_by_name = {p.name: p for p in remote_portfolios_list}
            remote_ok = True
        except KanboardConfigError as exc:
            click.echo(f"\u26a0 Warning: Remote backend unavailable \u2014 {exc}", err=True)
        except (KanboardConnectionError, KanboardAPIError, Exception) as exc:
            click.echo(f"\u26a0 Warning: Remote unreachable \u2014 {exc}", err=True)
    else:
        click.echo(
            "\u26a0 Warning: No Kanboard configuration \u2014 remote data unavailable.",
            err=True,
        )

    # ── Determine which portfolios to compare ─────────────────────────────
    if all_portfolios:
        names_to_compare = sorted(set(local_by_name) | set(remote_by_name))
    else:
        assert name is not None  # validated above
        names_to_compare = [name]

    if not names_to_compare:
        click.echo("No portfolios found on either side.")
        return

    # ── Build and render diff rows ─────────────────────────────────────────
    all_rows: list[dict[str, Any]] = []
    for pf_name in names_to_compare:
        local_pf = local_by_name.get(pf_name)
        remote_pf = remote_by_name.get(pf_name) if remote_ok else None
        all_rows.extend(_build_portfolio_diff_rows(pf_name, local_pf, remote_pf))

    format_output(all_rows, app_ctx.output, columns=_DIFF_COLUMNS)
