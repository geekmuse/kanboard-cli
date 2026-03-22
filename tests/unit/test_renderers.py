"""Unit tests for src/kanboard_cli/renderers.py."""

from __future__ import annotations

from datetime import datetime

from kanboard.models import DependencyEdge, Milestone, MilestoneProgress, Portfolio, Task
from kanboard_cli.renderers import (
    _PROGRESS_BAR_WIDTH,
    render_critical_path,
    render_dependency_graph,
    render_milestone_progress,
    render_portfolio_summary,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_task(
    task_id: int,
    title: str | None = None,
    project_id: int = 1,
    is_active: bool = True,
) -> Task:
    """Build a minimal :class:`Task` for renderer tests."""
    return Task(
        id=task_id,
        title=title if title is not None else f"Task {task_id}",
        description="",
        date_creation=None,
        date_modification=None,
        date_due=None,
        date_completed=None,
        date_moved=None,
        color_id="yellow",
        project_id=project_id,
        column_id=1,
        swimlane_id=0,
        owner_id=0,
        creator_id=0,
        category_id=0,
        is_active=is_active,
        priority=0,
        score=0,
        position=1,
        reference="",
        tags=[],
        url="",
    )


def _make_edge(
    blocker_id: int,
    blocker_title: str,
    blocker_project_id: int,
    blocker_project_name: str,
    blocked_id: int,
    blocked_title: str,
    blocked_project_id: int,
    blocked_project_name: str,
    is_resolved: bool = False,
) -> DependencyEdge:
    """Build a :class:`DependencyEdge` where *blocker_id* blocks *blocked_id*."""
    return DependencyEdge(
        task_id=blocker_id,
        task_title=blocker_title,
        task_project_id=blocker_project_id,
        task_project_name=blocker_project_name,
        opposite_task_id=blocked_id,
        opposite_task_title=blocked_title,
        opposite_task_project_id=blocked_project_id,
        opposite_task_project_name=blocked_project_name,
        link_label="blocks",
        is_cross_project=blocker_project_id != blocked_project_id,
        is_resolved=is_resolved,
    )


def _make_progress(
    name: str = "Milestone 1",
    portfolio: str = "Portfolio A",
    total: int = 10,
    completed: int = 6,
    percent: float = 60.0,
    is_at_risk: bool = False,
    is_overdue: bool = False,
    target_date: datetime | None = None,
    blocked_task_ids: list[int] | None = None,
) -> MilestoneProgress:
    """Build a :class:`MilestoneProgress` for renderer tests."""
    return MilestoneProgress(
        milestone_name=name,
        portfolio_name=portfolio,
        target_date=target_date,
        total=total,
        completed=completed,
        percent=percent,
        is_at_risk=is_at_risk,
        is_overdue=is_overdue,
        blocked_task_ids=blocked_task_ids if blocked_task_ids is not None else [],
    )


def _make_portfolio(
    name: str = "My Portfolio",
    description: str = "A test portfolio",
    project_ids: list[int] | None = None,
    milestones: list[Milestone] | None = None,
) -> Portfolio:
    """Build a :class:`Portfolio` for renderer tests."""
    return Portfolio(
        name=name,
        description=description,
        project_ids=project_ids if project_ids is not None else [1, 2, 3],
        milestones=milestones if milestones is not None else [],
    )


# ---------------------------------------------------------------------------
# render_dependency_graph
# ---------------------------------------------------------------------------


class TestRenderDependencyGraph:
    """Tests for :func:`render_dependency_graph`."""

    def test_shows_project_header(self) -> None:
        """Project name appears as section header."""
        t1 = _make_task(1, "Task Alpha", project_id=1)
        t2 = _make_task(2, "Task Beta", project_id=1)
        edge = _make_edge(1, "Task Alpha", 1, "Alpha Project", 2, "Task Beta", 1, "Alpha Project")
        result = render_dependency_graph([edge], [t1, t2], use_color=False)
        assert "Alpha Project" in result

    def test_shows_task_ids_and_titles(self) -> None:
        """Task IDs and titles are present in the output."""
        t1 = _make_task(10, "Fix the bug", project_id=1)
        t2 = _make_task(20, "Deploy release", project_id=1)
        edge = _make_edge(10, "Fix the bug", 1, "Proj", 20, "Deploy release", 1, "Proj")
        result = render_dependency_graph([edge], [t1, t2], use_color=False)
        assert "#10" in result
        assert "Fix the bug" in result
        assert "#20" in result
        assert "Deploy release" in result

    def test_shows_blocking_arrow(self) -> None:
        """Blocking relationship shown as '→ blocks' annotation."""
        t1 = _make_task(1, "Blocker", project_id=1)
        t2 = _make_task(2, "Blocked", project_id=1)
        edge = _make_edge(1, "Blocker", 1, "Proj", 2, "Blocked", 1, "Proj")
        result = render_dependency_graph([edge], [t1, t2], use_color=False)
        assert "→ blocks" in result
        assert "#2" in result

    def test_shows_blocked_by_arrow(self) -> None:
        """Blocked-by relationship shown as '← blocked by' annotation."""
        t1 = _make_task(1, "Blocker", project_id=1)
        t2 = _make_task(2, "Blocked", project_id=1)
        edge = _make_edge(1, "Blocker", 1, "Proj", 2, "Blocked", 1, "Proj")
        result = render_dependency_graph([edge], [t1, t2], use_color=False)
        assert "← blocked by" in result
        assert "#1" in result

    def test_cross_project_only_filters_edges(self) -> None:
        """cross_project_only=True keeps only cross-project edges."""
        t1 = _make_task(1, "Alpha Task", project_id=1)
        t2 = _make_task(2, "Beta Task", project_id=2)
        t3 = _make_task(3, "Same Project", project_id=1)

        cross_edge = _make_edge(1, "Alpha Task", 1, "Alpha", 2, "Beta Task", 2, "Beta")
        same_edge = _make_edge(1, "Alpha Task", 1, "Alpha", 3, "Same Project", 1, "Alpha")

        result_filtered = render_dependency_graph(
            [cross_edge, same_edge],
            [t1, t2, t3],
            cross_project_only=True,
            use_color=False,
        )
        # Cross-project tasks present
        assert "Alpha Task" in result_filtered
        assert "Beta Task" in result_filtered
        # Same-project task excluded
        assert "Same Project" not in result_filtered

    def test_cross_project_only_false_shows_all_edges(self) -> None:
        """cross_project_only=False (default) shows all tasks."""
        t1 = _make_task(1, "Alpha Task", project_id=1)
        t2 = _make_task(2, "Beta Task", project_id=2)
        t3 = _make_task(3, "Same Project", project_id=1)
        cross_edge = _make_edge(1, "Alpha Task", 1, "Alpha", 2, "Beta Task", 2, "Beta")
        same_edge = _make_edge(1, "Alpha Task", 1, "Alpha", 3, "Same Project", 1, "Alpha")
        result = render_dependency_graph([cross_edge, same_edge], [t1, t2, t3], use_color=False)
        assert "Same Project" in result
        assert "Beta Task" in result

    def test_multiple_projects_shown(self) -> None:
        """Tasks from two different projects both appear in the output."""
        t1 = _make_task(1, "Task P1", project_id=1)
        t2 = _make_task(2, "Task P2", project_id=2)
        edge = _make_edge(1, "Task P1", 1, "Project One", 2, "Task P2", 2, "Project Two")
        result = render_dependency_graph([edge], [t1, t2], use_color=False)
        assert "Project One" in result
        assert "Project Two" in result

    def test_resolved_edge_shows_check(self) -> None:
        """Resolved (is_resolved=True) blocker task shows check-mark icon."""
        t1 = _make_task(1, "Done Task", project_id=1, is_active=False)
        t2 = _make_task(2, "Open Task", project_id=1)
        edge = _make_edge(1, "Done Task", 1, "Proj", 2, "Open Task", 1, "Proj", is_resolved=True)
        result = render_dependency_graph([edge], [t1, t2], use_color=False)
        assert "✓" in result

    def test_no_nodes_empty_message(self) -> None:
        """Empty node list produces '(no tasks to display)' message."""
        result = render_dependency_graph([], [], use_color=False)
        assert "no tasks to display" in result

    def test_use_color_true_does_not_crash(self) -> None:
        """use_color=True runs without error and returns non-empty string."""
        t1 = _make_task(1, "Task A", project_id=1)
        edge = _make_edge(1, "Task A", 1, "Proj", 2, "Task B", 1, "Proj")
        t2 = _make_task(2, "Task B", project_id=1)
        result = render_dependency_graph([edge], [t1, t2], use_color=True)
        assert "Task A" in result
        assert "Task B" in result

    def test_project_name_fallback_for_orphan_node(self) -> None:
        """A node with no edge uses 'Project #N' as fallback project header."""
        t1 = _make_task(5, "Orphan Task", project_id=99)
        result = render_dependency_graph([], [t1], use_color=False)
        assert "Project #99" in result
        assert "Orphan Task" in result


# ---------------------------------------------------------------------------
# render_critical_path
# ---------------------------------------------------------------------------


class TestRenderCriticalPath:
    """Tests for :func:`render_critical_path`."""

    def test_numbered_list(self) -> None:
        """Tasks appear in numbered order."""
        tasks = [_make_task(1, "First"), _make_task(2, "Second"), _make_task(3, "Third")]
        result = render_critical_path(tasks, [])
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_task_ids_and_titles_present(self) -> None:
        """Task IDs and titles are in the output."""
        tasks = [_make_task(10, "Start Task"), _make_task(20, "End Task")]
        result = render_critical_path(tasks, [])
        assert "#10" in result
        assert "Start Task" in result
        assert "#20" in result
        assert "End Task" in result

    def test_bottleneck_marked(self) -> None:
        """Task with most unresolved outbound edges is marked as BOTTLENECK."""
        t1 = _make_task(1, "Blocker")
        t2 = _make_task(2, "Dependent A")
        t3 = _make_task(3, "Dependent B")
        edge1 = _make_edge(1, "Blocker", 1, "P", 2, "Dependent A", 1, "P")
        edge2 = _make_edge(1, "Blocker", 1, "P", 3, "Dependent B", 1, "P")
        result = render_critical_path([t1, t2, t3], [edge1, edge2])
        assert "BOTTLENECK" in result
        assert "#1" in result

    def test_no_bottleneck_when_no_edges(self) -> None:
        """BOTTLENECK is not shown when no edges exist."""
        tasks = [_make_task(1, "Solo A"), _make_task(2, "Solo B")]
        result = render_critical_path(tasks, [])
        assert "BOTTLENECK" not in result

    def test_empty_tasks_returns_message(self) -> None:
        """Empty task list returns 'No critical path found.' message."""
        result = render_critical_path([], [])
        assert "No critical path found." in result

    def test_single_task(self) -> None:
        """Single task appears with index 1."""
        tasks = [_make_task(7, "Only Task")]
        result = render_critical_path(tasks, [])
        assert "1." in result
        assert "#7" in result
        assert "Only Task" in result

    def test_completed_task_shows_checkmark(self) -> None:
        """Completed (is_active=False) task shows '✓' icon."""
        tasks = [_make_task(1, "Done", is_active=False), _make_task(2, "Pending")]
        result = render_critical_path(tasks, [])
        assert "✓" in result

    def test_resolved_edge_not_counted_for_bottleneck(self) -> None:
        """Resolved edges do not contribute to bottleneck count."""
        t1 = _make_task(1, "Task A")
        t2 = _make_task(2, "Task B")
        resolved_edge = _make_edge(1, "Task A", 1, "P", 2, "Task B", 1, "P", is_resolved=True)
        result = render_critical_path([t1, t2], [resolved_edge])
        assert "BOTTLENECK" not in result

    def test_header_line_present(self) -> None:
        """Output begins with 'Critical Path:' header."""
        tasks = [_make_task(1, "Task A")]
        result = render_critical_path(tasks, [])
        assert "Critical Path:" in result


# ---------------------------------------------------------------------------
# render_milestone_progress
# ---------------------------------------------------------------------------


class TestRenderMilestoneProgress:
    """Tests for :func:`render_milestone_progress`."""

    def test_progress_bar_width(self) -> None:
        """Progress bar is exactly 20 characters wide."""
        progress = _make_progress(percent=50.0)
        result = render_milestone_progress(progress, use_color=False)
        # Extract the content between brackets
        start = result.index("[") + 1
        end = result.index("]")
        bar = result[start:end]
        assert len(bar) == _PROGRESS_BAR_WIDTH

    def test_fill_at_60_percent(self) -> None:
        """60% fills 12 blocks (round(60/5)=12)."""
        progress = _make_progress(percent=60.0)
        result = render_milestone_progress(progress, use_color=False)
        start = result.index("[") + 1
        end = result.index("]")
        bar = result[start:end]
        assert bar.count("█") == 12
        assert bar.count("░") == 8

    def test_fill_at_0_percent(self) -> None:
        """0% produces all empty blocks."""
        progress = _make_progress(percent=0.0)
        result = render_milestone_progress(progress, use_color=False)
        start = result.index("[") + 1
        end = result.index("]")
        bar = result[start:end]
        assert bar.count("█") == 0
        assert bar.count("░") == _PROGRESS_BAR_WIDTH

    def test_fill_at_100_percent(self) -> None:
        """100% produces all filled blocks."""
        progress = _make_progress(percent=100.0)
        result = render_milestone_progress(progress, use_color=False)
        start = result.index("[") + 1
        end = result.index("]")
        bar = result[start:end]
        assert bar.count("█") == _PROGRESS_BAR_WIDTH
        assert bar.count("░") == 0

    def test_milestone_name_in_output(self) -> None:
        """Milestone name appears in the rendered string."""
        progress = _make_progress(name="Q2 Release")
        result = render_milestone_progress(progress, use_color=False)
        assert "Q2 Release" in result

    def test_percent_shown(self) -> None:
        """Percentage value is included in the output."""
        progress = _make_progress(percent=75.0)
        result = render_milestone_progress(progress, use_color=False)
        assert "75.0%" in result

    def test_target_date_shown(self) -> None:
        """Target date in YYYY-MM-DD format is shown."""
        dt = datetime(2026, 6, 30)
        progress = _make_progress(target_date=dt)
        result = render_milestone_progress(progress, use_color=False)
        assert "2026-06-30" in result

    def test_no_target_shown(self) -> None:
        """'no target' is shown when target_date is None."""
        progress = _make_progress(target_date=None)
        result = render_milestone_progress(progress, use_color=False)
        assert "no target" in result

    def test_at_risk_prefix(self) -> None:
        """At-risk milestones have the '⚠' warning prefix."""
        progress = _make_progress(is_at_risk=True, is_overdue=False)
        result = render_milestone_progress(progress, use_color=False)
        assert "⚠" in result

    def test_overdue_suffix(self) -> None:
        """Overdue milestones have the '🔴' suffix."""
        progress = _make_progress(is_overdue=True, is_at_risk=False)
        result = render_milestone_progress(progress, use_color=False)
        assert "🔴" in result

    def test_no_markers_when_on_track(self) -> None:
        """On-track milestones (not at-risk, not overdue) have no ⚠ or 🔴."""
        progress = _make_progress(is_at_risk=False, is_overdue=False)
        result = render_milestone_progress(progress, use_color=False)
        assert "⚠" not in result
        assert "🔴" not in result

    def test_use_color_true_does_not_crash(self) -> None:
        """use_color=True runs without error."""
        progress = _make_progress(percent=40.0, is_at_risk=True)
        result = render_milestone_progress(progress, use_color=True)
        assert "Q1" in result or "Milestone" in result  # name is present

    def test_use_color_true_overdue(self) -> None:
        """use_color=True with overdue milestone runs without error."""
        progress = _make_progress(percent=20.0, is_overdue=True)
        result = render_milestone_progress(progress, use_color=True)
        assert result  # non-empty

    def test_output_ends_with_newline(self) -> None:
        """Rendered string ends with a newline."""
        progress = _make_progress()
        result_no_color = render_milestone_progress(progress, use_color=False)
        assert result_no_color.endswith("\n")

    def test_progress_bar_rounding(self) -> None:
        """round(percent/5) boundary: 52% → round(10.4)=10 blocks."""
        progress = _make_progress(percent=52.0)
        result = render_milestone_progress(progress, use_color=False)
        start = result.index("[") + 1
        end = result.index("]")
        bar = result[start:end]
        assert bar.count("█") == 10


# ---------------------------------------------------------------------------
# render_portfolio_summary
# ---------------------------------------------------------------------------


class TestRenderPortfolioSummary:
    """Tests for :func:`render_portfolio_summary`."""

    def test_portfolio_name_in_output(self) -> None:
        """Portfolio name appears in summary header."""
        portfolio = _make_portfolio(name="Acme Platform")
        result = render_portfolio_summary(portfolio, [], 0, 0)
        assert "Acme Platform" in result

    def test_description_shown(self) -> None:
        """Description is included when non-empty."""
        portfolio = _make_portfolio(description="Our flagship product portfolio")
        result = render_portfolio_summary(portfolio, [], 5, 0)
        assert "Our flagship product portfolio" in result

    def test_project_count_shown(self) -> None:
        """Number of projects is shown in the metrics line."""
        portfolio = _make_portfolio(project_ids=[1, 2, 3])
        result = render_portfolio_summary(portfolio, [], 20, 1)
        assert "Projects: 3" in result

    def test_task_count_shown(self) -> None:
        """Total task count is shown in the metrics line."""
        portfolio = _make_portfolio(project_ids=[1])
        result = render_portfolio_summary(portfolio, [], 42, 3)
        assert "Tasks: 42" in result

    def test_blocked_count_shown(self) -> None:
        """Blocked task count is shown in the metrics line."""
        portfolio = _make_portfolio(project_ids=[1])
        result = render_portfolio_summary(portfolio, [], 42, 5)
        assert "Blocked: 5" in result

    def test_milestone_count_shown(self) -> None:
        """Milestone count derived from portfolio.milestones length."""
        ms1 = Milestone(name="M1", portfolio_name="P", target_date=None)
        ms2 = Milestone(name="M2", portfolio_name="P", target_date=None)
        portfolio = _make_portfolio(milestones=[ms1, ms2])
        result = render_portfolio_summary(portfolio, [], 10, 0)
        assert "Milestones: 2" in result

    def test_at_risk_line_shown(self) -> None:
        """At-risk milestone count line is shown when non-zero."""
        portfolio = _make_portfolio()
        mp = _make_progress(is_at_risk=True, is_overdue=False)
        result = render_portfolio_summary(portfolio, [mp], 10, 0)
        assert "At-risk milestones: 1" in result

    def test_overdue_line_shown(self) -> None:
        """Overdue milestone count line is shown when non-zero."""
        portfolio = _make_portfolio()
        mp = _make_progress(is_overdue=True, is_at_risk=False)
        result = render_portfolio_summary(portfolio, [mp], 10, 0)
        assert "Overdue milestones: 1" in result

    def test_no_risk_line_when_all_on_track(self) -> None:
        """At-risk/overdue line omitted when all milestones are on track."""
        portfolio = _make_portfolio()
        mp = _make_progress(is_at_risk=False, is_overdue=False)
        result = render_portfolio_summary(portfolio, [mp], 10, 0)
        assert "At-risk" not in result
        assert "Overdue" not in result

    def test_empty_description_omitted(self) -> None:
        """Empty description string does not produce a 'Description:' line."""
        portfolio = _make_portfolio(description="")
        result = render_portfolio_summary(portfolio, [], 5, 0)
        assert "Description:" not in result

    def test_zero_tasks_and_blocked(self) -> None:
        """Zero task / blocked counts render correctly."""
        portfolio = _make_portfolio(project_ids=[1])
        result = render_portfolio_summary(portfolio, [], 0, 0)
        assert "Tasks: 0" in result
        assert "Blocked: 0" in result
