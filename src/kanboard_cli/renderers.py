"""ASCII/Unicode renderers for dependency graphs, critical paths, and progress displays.

Used by the portfolio and milestone CLI command groups to produce human-readable
console output.  Colour output is controlled via the ``use_color`` parameter on
each function — pass ``use_color=False`` for piping, CI, or quiet mode.
"""

from __future__ import annotations

import io
from collections import defaultdict
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from kanboard.models import DependencyEdge, MilestoneProgress, Portfolio, Task

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PROGRESS_BAR_WIDTH = 20


def _make_console(buf: io.StringIO, *, use_color: bool) -> Console:
    """Create a :class:`~rich.console.Console` writing to *buf*.

    Forces terminal mode to enable ANSI codes when *use_color* is ``True``.
    Disables syntax highlighting to avoid unexpected markup colouring.

    Args:
        buf: String buffer to write to.
        use_color: When ``False``, all colour and formatting markup is stripped.

    Returns:
        A configured :class:`~rich.console.Console` instance.
    """
    return Console(
        file=buf,
        highlight=False,
        no_color=not use_color,
        force_terminal=use_color,
    )


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from *text* (used internally for tests).

    Args:
        text: String that may contain ANSI escape sequences.

    Returns:
        Plain text with all ANSI sequences removed.
    """
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ---------------------------------------------------------------------------
# Public renderers
# ---------------------------------------------------------------------------


def render_dependency_graph(
    edges: list[DependencyEdge],
    nodes: list[Task],
    cross_project_only: bool = False,
    use_color: bool = True,
) -> str:
    """Render a text-based dependency graph grouped by project.

    Nodes are grouped under their respective project headers.  Each task shows
    its completion status and any blocking / blocked-by relationships as arrow
    annotations.

    Colour coding (when *use_color* is ``True``):

    - green: completed task or resolved edge
    - red: blocked task (has an unresolved inbound blocker) or unresolved inbound edge
    - yellow: open task with no unresolved blockers, or outbound blocking edge

    Args:
        edges: Dependency edges from
            :class:`~kanboard.orchestration.dependencies.DependencyAnalyzer`.
        nodes: Tasks to display as graph nodes.
        cross_project_only: When ``True``, show only cross-project edges and
            limit displayed nodes to those involved in cross-project relationships.
        use_color: When ``False``, disables ANSI colour output.

    Returns:
        Rendered text string suitable for printing to the console.
    """
    if cross_project_only:
        edges = [e for e in edges if e.is_cross_project]
        involved_ids = {e.task_id for e in edges} | {e.opposite_task_id for e in edges}
        nodes = [n for n in nodes if n.id in involved_ids]

    buf = io.StringIO()
    console = _make_console(buf, use_color=use_color)

    # Gather project names from edges (Task has project_id but not project_name).
    project_names: dict[int, str] = {}
    for edge in edges:
        project_names[edge.task_project_id] = edge.task_project_name
        project_names[edge.opposite_task_project_id] = edge.opposite_task_project_name

    # Identify blocked tasks: those with at least one unresolved inbound edge.
    blocked_task_ids: set[int] = set()
    for edge in edges:
        if not edge.is_resolved:
            blocked_task_ids.add(edge.opposite_task_id)

    # Group nodes by project.
    project_tasks: dict[int, list[Task]] = defaultdict(list)
    for task in nodes:
        project_tasks[task.project_id].append(task)

    # Build directional edge lookups.
    # outbound[id] = edges where task_id == id (this task blocks others)
    # inbound[id]  = edges where opposite_task_id == id (this task is blocked)
    outbound: dict[int, list[DependencyEdge]] = defaultdict(list)
    inbound: dict[int, list[DependencyEdge]] = defaultdict(list)
    for edge in edges:
        outbound[edge.task_id].append(edge)
        inbound[edge.opposite_task_id].append(edge)

    if not project_tasks:
        console.print("(no tasks to display)")
        return buf.getvalue()

    for proj_id, tasks in sorted(project_tasks.items()):
        proj_name = project_names.get(proj_id, f"Project #{proj_id}")
        console.print(f"\n[bold]=== {proj_name} ===[/bold]")

        for task in sorted(tasks, key=lambda t: t.id):
            if not task.is_active:
                icon = "✓"
                color = "green"
            elif task.id in blocked_task_ids:
                icon = "●"
                color = "red"
            else:
                icon = "●"
                color = "yellow"

            console.print(f"  [{color}]{icon} #{task.id} {task.title}[/{color}]")

            # Outbound: this task blocks others.
            for edge in outbound.get(task.id, []):
                edge_color = "green" if edge.is_resolved else "yellow"
                console.print(
                    f"    [{edge_color}]"
                    f"→ blocks #{edge.opposite_task_id} {edge.opposite_task_title}"
                    f"[/{edge_color}]"
                )

            # Inbound: this task is blocked by others.
            for edge in inbound.get(task.id, []):
                edge_color = "green" if edge.is_resolved else "red"
                console.print(
                    f"    [{edge_color}]"
                    f"← blocked by #{edge.task_id} {edge.task_title}"
                    f"[/{edge_color}]"
                )

    return buf.getvalue()


def render_critical_path(
    tasks: list[Task],
    edges: list[DependencyEdge],
) -> str:
    """Render the critical path as a numbered sequential list.

    The *bottleneck* task — the task with the highest number of unresolved
    outbound edges pointing to other tasks in the path — is annotated with
    ``← BOTTLENECK``.  When no task has outbound edges, no bottleneck is
    identified.

    Args:
        tasks: Ordered critical-path tasks (from
            :meth:`~kanboard.orchestration.dependencies.DependencyAnalyzer.get_critical_path`).
        edges: Dependency edges for the task set, used to identify the bottleneck.

    Returns:
        Rendered text string suitable for printing to the console.
    """
    if not tasks:
        return "No critical path found.\n"

    task_ids = {t.id for t in tasks}
    blocker_count: dict[int, int] = {t.id: 0 for t in tasks}
    for edge in edges:
        if edge.task_id in task_ids and edge.opposite_task_id in task_ids and not edge.is_resolved:
            blocker_count[edge.task_id] = blocker_count.get(edge.task_id, 0) + 1

    max_count = max(blocker_count.values(), default=0)
    bottleneck_id: int | None = None
    if max_count > 0:
        bottleneck_id = max(blocker_count, key=lambda k: blocker_count[k])

    lines: list[str] = ["Critical Path:\n"]
    for i, task in enumerate(tasks, 1):
        status = "✓" if not task.is_active else "●"
        marker = " ← BOTTLENECK" if task.id == bottleneck_id else ""
        lines.append(f"  {i:2d}. {status} #{task.id} {task.title}{marker}\n")

    return "".join(lines)


def render_milestone_progress(
    progress: MilestoneProgress,
    use_color: bool = True,
) -> str:
    """Render a Unicode progress bar for a single milestone.

    Format::

        ⚠ [████████████░░░░░░░░] 60.0% - Milestone Name (target: 2026-04-01) 🔴

    The progress bar is exactly :data:`_PROGRESS_BAR_WIDTH` characters wide
    (``█`` for filled, ``░`` for empty).  ``⚠`` prefix indicates at-risk;
    ``🔴`` suffix indicates overdue.

    Colour coding (when *use_color* is ``True``):

    - green: on track (not at-risk, not overdue)
    - yellow: at-risk
    - red: overdue

    Args:
        progress: Milestone progress snapshot from
            :meth:`~kanboard.orchestration.portfolio.PortfolioManager.get_milestone_progress`.
        use_color: When ``False``, disables ANSI colour output.

    Returns:
        Rendered progress bar string (includes trailing newline).
    """
    fill = max(0, min(_PROGRESS_BAR_WIDTH, round(progress.percent / 5)))
    bar = "█" * fill + "░" * (_PROGRESS_BAR_WIDTH - fill)
    target_str = progress.target_date.strftime("%Y-%m-%d") if progress.target_date else "no target"
    prefix = "⚠ " if progress.is_at_risk else ""
    suffix = " 🔴" if progress.is_overdue else ""
    pct_str = f"{progress.percent:.1f}%"
    line = f"{prefix}[{bar}] {pct_str} - {progress.milestone_name} (target: {target_str}){suffix}"

    if use_color:
        buf = io.StringIO()
        console = _make_console(buf, use_color=True)
        if progress.is_overdue:
            color = "red"
        elif progress.is_at_risk:
            color = "yellow"
        else:
            color = "green"
        console.print(f"[{color}]{line}[/{color}]")
        return buf.getvalue()

    return line + "\n"


def render_portfolio_summary(
    portfolio: Portfolio,
    milestones: list[MilestoneProgress],
    task_count: int,
    blocked_count: int,
) -> str:
    """Render a dashboard summary for a portfolio.

    Displays the portfolio name, description, and key metrics (project count,
    milestone count, total tasks, blocked tasks).  At-risk and overdue milestone
    counts are shown when non-zero.

    Args:
        portfolio: The portfolio object.
        milestones: Progress snapshots for all milestones in the portfolio.
        task_count: Total number of tasks across all portfolio projects.
        blocked_count: Number of tasks with at least one unresolved blocker.

    Returns:
        Rendered summary string (no trailing newline on last line).
    """
    lines: list[str] = [f"Portfolio: {portfolio.name}\n"]

    if portfolio.description:
        lines.append(f"Description: {portfolio.description}\n")

    project_count = len(portfolio.project_ids)
    milestone_count = len(portfolio.milestones)
    lines.append(
        f"Projects: {project_count}"
        f"  |  Milestones: {milestone_count}"
        f"  |  Tasks: {task_count}"
        f"  |  Blocked: {blocked_count}\n"
    )

    at_risk = sum(1 for m in milestones if m.is_at_risk)
    overdue = sum(1 for m in milestones if m.is_overdue)
    if at_risk or overdue:
        lines.append(f"At-risk milestones: {at_risk}  |  Overdue milestones: {overdue}\n")

    return "".join(lines)
