"""Portfolio manager — multi-project aggregation and milestone tracking."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from kanboard.exceptions import KanboardConfigError, KanboardNotFoundError
from kanboard.models import MilestoneProgress, Project, Task

if TYPE_CHECKING:
    from kanboard.client import KanboardClient
    from kanboard.orchestration.store import LocalPortfolioStore

logger = logging.getLogger(__name__)

_METADATA_KEY_PORTFOLIO = "kanboard_cli:portfolio"
_METADATA_KEY_MILESTONES = "kanboard_cli:milestones"
_METADATA_KEY_MILESTONE_CRITICAL = "kanboard_cli:milestone_critical"
_LINK_LABEL_BLOCKED_BY = "is blocked by"
_AT_RISK_DAYS = 7
_AT_RISK_PERCENT_THRESHOLD = 80.0


class PortfolioManager:
    """Aggregates task data across multiple Kanboard projects.

    Computes milestone progress and syncs portfolio/milestone membership to
    Kanboard task and project metadata using the ``kanboard_cli:`` key prefix
    convention.  Instantiated separately by callers — not wired into
    :class:`~kanboard.client.KanboardClient` as an attribute.

    Args:
        client: The :class:`~kanboard.client.KanboardClient` used to make API
            calls.
        store: The :class:`~kanboard.orchestration.store.LocalPortfolioStore`
            used to read portfolio/milestone configuration.

    Example:
        >>> manager = PortfolioManager(client, store)
        >>> tasks = manager.get_portfolio_tasks("my-portfolio")
    """

    def __init__(self, client: KanboardClient, store: LocalPortfolioStore) -> None:
        """Initialise with a client and a local portfolio store.

        Args:
            client: The Kanboard API client.
            store: The local portfolio store providing portfolio/milestone data.
        """
        self._client = client
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_portfolio_projects(self, portfolio_name: str) -> list[Project]:
        """Fetch the Kanboard Project objects for every project in a portfolio.

        Projects that have been deleted from Kanboard but are still listed in
        the local store are logged as warnings and skipped.

        Args:
            portfolio_name: Name of the portfolio to look up.

        Returns:
            A list of :class:`~kanboard.models.Project` instances, one per
            project ID in the portfolio (excluding any missing ones).

        Raises:
            KanboardConfigError: When the portfolio is not found in the local store.
        """
        portfolio = self._store.get_portfolio(portfolio_name)
        projects: list[Project] = []
        for project_id in portfolio.project_ids:
            try:
                projects.append(self._client.projects.get_project_by_id(project_id))
            except KanboardNotFoundError:
                logger.warning(
                    "Project %d not found in Kanboard (deleted?); skipping",
                    project_id,
                )
        return projects

    def get_portfolio_tasks(
        self,
        portfolio_name: str,
        status: int = 1,
        assignee_id: int | None = None,
        project_id: int | None = None,
    ) -> list[Task]:
        """Fetch tasks across all projects in a portfolio with optional filters.

        Iterates each project in the portfolio and calls ``getAllTasks``.
        Projects that cannot be queried are logged as warnings and skipped.

        Args:
            portfolio_name: Name of the portfolio to look up.
            status: Task status filter — ``1`` = active (default), ``0`` = closed.
            assignee_id: When set, only tasks whose ``owner_id`` matches this
                value are returned.
            project_id: When set, only tasks from this specific project are
                returned (must be a member of the portfolio).

        Returns:
            A flat list of :class:`~kanboard.models.Task` instances from all
            matched projects.

        Raises:
            KanboardConfigError: When the portfolio is not found in the local store.
        """
        portfolio = self._store.get_portfolio(portfolio_name)
        project_ids = list(portfolio.project_ids)

        if project_id is not None:
            if project_id not in project_ids:
                return []
            project_ids = [project_id]

        tasks: list[Task] = []
        for pid in project_ids:
            try:
                project_tasks = self._client.tasks.get_all_tasks(pid, status_id=status)
            except Exception:  # pragma: no cover - network/auth errors skipped
                logger.warning("Failed to fetch tasks for project %d; skipping", pid)
                continue
            if assignee_id is not None:
                project_tasks = [t for t in project_tasks if t.owner_id == assignee_id]
            tasks.extend(project_tasks)
        return tasks

    def get_milestone_progress(
        self,
        portfolio_name: str,
        milestone_name: str,
    ) -> MilestoneProgress:
        """Compute progress for a named milestone within a portfolio.

        Fetches each task tracked by the milestone, counts closed vs total, and
        identifies tasks with unresolved (open) blockers.  Tasks that have been
        deleted from Kanboard are excluded from the total.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to analyse.

        Returns:
            A :class:`~kanboard.models.MilestoneProgress` snapshot with
            completion percentage, at-risk/overdue flags, and blocked task IDs.

        Raises:
            KanboardConfigError: When the portfolio or milestone is not found.
        """
        portfolio = self._store.get_portfolio(portfolio_name)
        milestone = next((m for m in portfolio.milestones if m.name == milestone_name), None)
        if milestone is None:
            raise KanboardConfigError(
                f"Milestone '{milestone_name}' not found in portfolio '{portfolio_name}'"
            )

        # Build link-label map once so we can identify "is blocked by" links.
        link_label_map = self._get_link_label_map()
        blocked_by_link_ids: set[int] = {
            lid for lid, label in link_label_map.items() if label == _LINK_LABEL_BLOCKED_BY
        }

        total = len(milestone.task_ids)
        completed = 0
        blocked_task_ids: list[int] = []

        for task_id in milestone.task_ids:
            try:
                task = self._client.tasks.get_task(task_id)
            except KanboardNotFoundError:
                logger.warning(
                    "Task %d not found in Kanboard (deleted?); excluding from progress",
                    task_id,
                )
                total -= 1
                continue

            if not task.is_active:
                completed += 1

            if self._has_open_blocker(task_id, blocked_by_link_ids):
                blocked_task_ids.append(task_id)

        percent = (completed / total * 100.0) if total > 0 else 100.0

        now = datetime.now()
        is_overdue = False
        is_at_risk = False
        if milestone.target_date is not None:
            is_overdue = milestone.target_date < now and percent < 100.0
            days_remaining = (milestone.target_date - now).total_seconds() / 86400.0
            is_at_risk = (
                0.0 <= days_remaining <= float(_AT_RISK_DAYS)
                and percent < _AT_RISK_PERCENT_THRESHOLD
            )

        return MilestoneProgress(
            milestone_name=milestone_name,
            portfolio_name=portfolio_name,
            target_date=milestone.target_date,
            total=total,
            completed=completed,
            percent=percent,
            is_at_risk=is_at_risk,
            is_overdue=is_overdue,
            blocked_task_ids=blocked_task_ids,
        )

    def get_all_milestone_progress(self, portfolio_name: str) -> list[MilestoneProgress]:
        """Compute progress for every milestone in a portfolio.

        Delegates to :meth:`get_milestone_progress` for each milestone in the
        portfolio.

        Args:
            portfolio_name: Name of the portfolio to analyse.

        Returns:
            A list of :class:`~kanboard.models.MilestoneProgress` snapshots,
            one per milestone in the portfolio (in definition order).

        Raises:
            KanboardConfigError: When the portfolio is not found in the local store.
        """
        portfolio = self._store.get_portfolio(portfolio_name)
        return [
            self.get_milestone_progress(portfolio_name, milestone.name)
            for milestone in portfolio.milestones
        ]

    def sync_metadata(self, portfolio_name: str) -> dict[str, int]:
        """Sync portfolio and milestone membership to Kanboard metadata.

        Writes ``kanboard_cli:portfolio`` to every project's metadata and
        ``kanboard_cli:milestones`` (plus ``kanboard_cli:milestone_critical``
        when applicable) to every tracked task's metadata.  Missing projects
        or tasks are logged as warnings and skipped.

        Args:
            portfolio_name: Name of the portfolio to sync.

        Returns:
            A dict with ``projects_synced`` (int) and ``tasks_synced`` (int)
            keys reflecting the number of successfully updated resources.

        Raises:
            KanboardConfigError: When the portfolio is not found in the local store.
        """
        portfolio = self._store.get_portfolio(portfolio_name)

        portfolio_meta_value = json.dumps(
            {"name": portfolio.name, "description": portfolio.description}
        )

        projects_synced = 0
        for project_id in portfolio.project_ids:
            try:
                self._client.project_metadata.save_project_metadata(
                    project_id,
                    {_METADATA_KEY_PORTFOLIO: portfolio_meta_value},
                )
                projects_synced += 1
            except Exception:
                logger.warning(
                    "Failed to sync metadata to project %d (deleted?); skipping",
                    project_id,
                )

        # Build task → milestone membership index from local store data.
        task_milestones: dict[int, list[str]] = {}
        task_critical: dict[int, list[str]] = {}
        for milestone in portfolio.milestones:
            for task_id in milestone.task_ids:
                task_milestones.setdefault(task_id, []).append(milestone.name)
            for task_id in milestone.critical_task_ids:
                task_critical.setdefault(task_id, []).append(milestone.name)

        tasks_synced = 0
        for task_id, milestone_names in task_milestones.items():
            meta_values: dict[str, str] = {
                _METADATA_KEY_MILESTONES: json.dumps(milestone_names),
            }
            critical_names = task_critical.get(task_id, [])
            if critical_names:
                meta_values[_METADATA_KEY_MILESTONE_CRITICAL] = json.dumps(critical_names)
            try:
                self._client.task_metadata.save_task_metadata(task_id, meta_values)
                tasks_synced += 1
            except Exception:
                logger.warning(
                    "Failed to sync metadata to task %d (deleted?); skipping",
                    task_id,
                )

        return {"projects_synced": projects_synced, "tasks_synced": tasks_synced}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_link_label_map(self) -> dict[int, str]:
        """Fetch all link type definitions and return a ``{link_id: label}`` map.

        Returns an empty dict on failure so callers degrade gracefully and
        blocker detection is simply disabled.

        Returns:
            A dict mapping link type IDs to their label strings.
        """
        try:
            links = self._client.links.get_all_links()
        except Exception:
            logger.warning("Failed to fetch link type definitions; blocker detection disabled")
            return {}
        return {link.id: link.label for link in links}

    def _has_open_blocker(self, task_id: int, blocked_by_link_ids: set[int]) -> bool:
        """Return ``True`` if ``task_id`` has at least one open (active) blocker.

        Fetches all task links for the given task and checks each "is blocked by"
        link to see if the opposite task is still active.

        Args:
            task_id: The task to inspect.
            blocked_by_link_ids: Set of link type IDs whose label is
                ``"is blocked by"``.

        Returns:
            ``True`` when at least one unresolved blocker exists; ``False``
            otherwise (including when ``blocked_by_link_ids`` is empty or
            API calls fail).
        """
        if not blocked_by_link_ids:
            return False
        try:
            task_links = self._client.task_links.get_all_task_links(task_id)
        except Exception:
            return False
        for tl in task_links:
            if tl.link_id not in blocked_by_link_ids:
                continue
            try:
                blocker = self._client.tasks.get_task(tl.opposite_task_id)
                if blocker.is_active:
                    return True
            except KanboardNotFoundError:
                continue
        return False
