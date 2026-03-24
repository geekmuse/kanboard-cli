"""Milestones resource module — CRUD and task management for Kanboard Portfolio plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import PluginMilestone, PluginMilestoneProgress

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class MilestonesResource:
    """Kanboard Portfolio plugin milestone API resource.

    Exposes all milestone-related JSON-RPC methods as typed Python methods.
    Requires the ``kanboard-plugin-portfolio-management`` plugin to be installed
    on the Kanboard server.

    Accessed via ``KanboardClient.milestones``.

    Example:
        >>> mid = client.milestones.create_milestone(portfolio_id=1, name="v1.0")
        >>> milestone = client.milestones.get_milestone(mid)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    # ------------------------------------------------------------------
    # Create / Read
    # ------------------------------------------------------------------

    def create_milestone(self, portfolio_id: int, name: str, **kwargs: Any) -> int:
        """Create a new milestone in a portfolio.

        Maps to the plugin ``createMilestone`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to add the milestone to.
            name: Milestone name.
            **kwargs: Optional fields accepted by ``createMilestone``:
                ``description``, ``target_date``, ``status``, ``color_id``,
                ``owner_id``.

        Returns:
            The integer ID of the newly created milestone.

        Raises:
            KanboardAPIError: The API returned ``False`` (milestone creation failed).
        """
        result = self._client.call(
            "createMilestone", portfolio_id=portfolio_id, name=name, **kwargs
        )
        if result is False or result == 0:
            raise KanboardAPIError(
                "createMilestone returned False — milestone creation failed",
                method="createMilestone",
                code=None,
            )
        return int(result)

    def get_milestone(self, milestone_id: int) -> PluginMilestone:
        """Fetch a single milestone by its numeric ID.

        Maps to the plugin ``getMilestone`` JSON-RPC method.

        Args:
            milestone_id: Unique integer ID of the milestone.

        Returns:
            A :class:`~kanboard.models.PluginMilestone` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (milestone not found).
        """
        result = self._client.call("getMilestone", milestone_id=milestone_id)
        if result is None:
            raise KanboardNotFoundError(
                "Milestone not found",
                method="getMilestone",
                code=None,
                resource="PluginMilestone",
                identifier=str(milestone_id),
            )
        return PluginMilestone.from_api(result)

    def get_portfolio_milestones(self, portfolio_id: int) -> list[PluginMilestone]:
        """Fetch all milestones belonging to a portfolio.

        Maps to the plugin ``getPortfolioMilestones`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to query.

        Returns:
            A list of :class:`~kanboard.models.PluginMilestone` instances;
            returns an empty list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getPortfolioMilestones", portfolio_id=portfolio_id)
        if not result:
            return []
        return [PluginMilestone.from_api(m) for m in result]

    # ------------------------------------------------------------------
    # Update / Delete
    # ------------------------------------------------------------------

    def update_milestone(self, milestone_id: int, **kwargs: Any) -> bool:
        """Update one or more fields on an existing milestone.

        Maps to the plugin ``updateMilestone`` JSON-RPC method.

        Args:
            milestone_id: ID of the milestone to update.
            **kwargs: Milestone fields to update: ``name``, ``description``,
                ``target_date``, ``status``, ``color_id``, ``owner_id``.

        Returns:
            ``True`` on success.

        Raises:
            KanboardAPIError: The API returned ``False`` (update failed).
        """
        result = self._client.call("updateMilestone", milestone_id=milestone_id, **kwargs)
        if result is False:
            raise KanboardAPIError(
                "updateMilestone returned False — milestone update failed",
                method="updateMilestone",
                code=None,
            )
        return bool(result)

    def remove_milestone(self, milestone_id: int) -> bool:
        """Permanently delete a milestone.

        Maps to the plugin ``removeMilestone`` JSON-RPC method.

        Args:
            milestone_id: ID of the milestone to delete.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("removeMilestone", milestone_id=milestone_id)
        return bool(result)

    # ------------------------------------------------------------------
    # Task membership
    # ------------------------------------------------------------------

    def add_task_to_milestone(self, milestone_id: int, task_id: int, **kwargs: Any) -> bool:
        """Add a task to a milestone.

        Maps to the plugin ``addTaskToMilestone`` JSON-RPC method.

        Args:
            milestone_id: ID of the milestone.
            task_id: ID of the task to add.
            **kwargs: Optional fields accepted by ``addTaskToMilestone``.

        Returns:
            ``True`` on success.

        Raises:
            KanboardAPIError: The API returned ``False`` (operation failed).
        """
        result = self._client.call(
            "addTaskToMilestone",
            milestone_id=milestone_id,
            task_id=task_id,
            **kwargs,
        )
        if result is False:
            raise KanboardAPIError(
                "addTaskToMilestone returned False — operation failed",
                method="addTaskToMilestone",
                code=None,
            )
        return bool(result)

    def remove_task_from_milestone(self, milestone_id: int, task_id: int) -> bool:
        """Remove a task from a milestone.

        Maps to the plugin ``removeTaskFromMilestone`` JSON-RPC method.

        Args:
            milestone_id: ID of the milestone.
            task_id: ID of the task to remove.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call(
            "removeTaskFromMilestone",
            milestone_id=milestone_id,
            task_id=task_id,
        )
        return bool(result)

    def get_milestone_tasks(self, milestone_id: int) -> list[dict[str, Any]]:
        """Fetch all tasks assigned to a milestone.

        Maps to the plugin ``getMilestoneTasks`` JSON-RPC method.

        Args:
            milestone_id: ID of the milestone to query.

        Returns:
            A list of task data dicts; returns an empty list when the API
            responds with ``False`` or ``None``.
        """
        result = self._client.call("getMilestoneTasks", milestone_id=milestone_id)
        if not result:
            return []
        return list(result)

    def get_task_milestones(self, task_id: int) -> list[PluginMilestone]:
        """Fetch all milestones that a given task belongs to.

        Maps to the plugin ``getTaskMilestones`` JSON-RPC method.

        Args:
            task_id: ID of the task to look up.

        Returns:
            A list of :class:`~kanboard.models.PluginMilestone` instances;
            returns an empty list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getTaskMilestones", task_id=task_id)
        if not result:
            return []
        return [PluginMilestone.from_api(m) for m in result]

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def get_milestone_progress(self, milestone_id: int) -> PluginMilestoneProgress:
        """Fetch server-computed progress for a milestone.

        Maps to the plugin ``getMilestoneProgress`` JSON-RPC method.

        Args:
            milestone_id: ID of the milestone to query.

        Returns:
            A :class:`~kanboard.models.PluginMilestoneProgress` instance with
            task counts, completion percentage, and risk/overdue flags.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (milestone not found).
        """
        result = self._client.call("getMilestoneProgress", milestone_id=milestone_id)
        if result is None:
            raise KanboardNotFoundError(
                "Milestone progress not found",
                method="getMilestoneProgress",
                code=None,
                resource="PluginMilestoneProgress",
                identifier=str(milestone_id),
            )
        return PluginMilestoneProgress.from_api(result)
