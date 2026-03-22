"""Tasks resource module — CRUD and management operations for Kanboard tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Task

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class TasksResource:
    """Kanboard Tasks API resource.

    Exposes all task-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.tasks``.

    Example:
        >>> task = client.tasks.get_task(42)
        >>> task_id = client.tasks.create_task("Fix bug", project_id=1)
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

    def create_task(self, title: str, project_id: int, **kwargs: Any) -> int:
        """Create a new task in the specified project.

        Maps to the Kanboard ``createTask`` JSON-RPC method.

        Args:
            title: Task title.
            project_id: ID of the project to create the task in.
            **kwargs: Optional task fields accepted by ``createTask``:
                ``owner_id``, ``color_id``, ``column_id``, ``description``,
                ``category_id``, ``score``, ``swimlane_id``, ``priority``,
                ``reference``, ``tags``, ``date_due``.

        Returns:
            The integer ID of the newly created task.

        Raises:
            KanboardAPIError: The API returned ``False`` (task creation failed).
        """
        result = self._client.call("createTask", title=title, project_id=project_id, **kwargs)
        if result is False or result == 0:
            raise KanboardAPIError(
                "createTask returned False — task creation failed",
                method="createTask",
                code=None,
            )
        return int(result)

    def get_task(self, task_id: int) -> Task:
        """Fetch a single task by its numeric ID.

        Maps to the Kanboard ``getTask`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task.

        Returns:
            A :class:`~kanboard.models.Task` instance populated from the API response.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (task not found).
        """
        result = self._client.call("getTask", task_id=task_id)
        if result is None:
            raise KanboardNotFoundError(
                "Task not found",
                method="getTask",
                code=None,
                resource="Task",
                identifier=str(task_id),
            )
        return Task.from_api(result)

    def get_task_by_reference(self, project_id: int, reference: str) -> Task:
        """Fetch a task by its external reference string within a project.

        Maps to the Kanboard ``getTaskByReference`` JSON-RPC method.

        Args:
            project_id: ID of the project that owns the task.
            reference: External reference string for the task (e.g. ``"REF-001"``).

        Returns:
            A :class:`~kanboard.models.Task` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (task not found).
        """
        result = self._client.call(
            "getTaskByReference", project_id=project_id, reference=reference
        )
        if result is None:
            raise KanboardNotFoundError(
                "Task not found by reference",
                method="getTaskByReference",
                code=None,
                resource="Task",
                identifier=reference,
            )
        return Task.from_api(result)

    def get_all_tasks(self, project_id: int, status_id: int = 1) -> list[Task]:
        """Fetch all tasks in a project, filtered by status.

        Maps to the Kanboard ``getAllTasks`` JSON-RPC method.

        Args:
            project_id: ID of the project.
            status_id: Task status filter — ``1`` = active (default), ``0`` = inactive.

        Returns:
            A list of :class:`~kanboard.models.Task` instances; returns an empty
            list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getAllTasks", project_id=project_id, status_id=status_id)
        if not result:
            return []
        return [Task.from_api(t) for t in result]

    def get_overdue_tasks(self) -> list[Task]:
        """Fetch all overdue tasks across every accessible project.

        Maps to the Kanboard ``getOverdueTasks`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.Task` instances; returns an empty
            list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getOverdueTasks")
        if not result:
            return []
        return [Task.from_api(t) for t in result]

    def get_overdue_tasks_by_project(self, project_id: int) -> list[Task]:
        """Fetch all overdue tasks for a specific project.

        Maps to the Kanboard ``getOverdueTasksByProject`` JSON-RPC method.

        Args:
            project_id: ID of the project to query.

        Returns:
            A list of :class:`~kanboard.models.Task` instances; returns an empty
            list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getOverdueTasksByProject", project_id=project_id)
        if not result:
            return []
        return [Task.from_api(t) for t in result]

    def search_tasks(self, project_id: int, query: str) -> list[Task]:
        """Search tasks in a project using Kanboard's filter syntax.

        Maps to the Kanboard ``searchTasks`` JSON-RPC method.

        Args:
            project_id: ID of the project to search within.
            query: Search query string supporting Kanboard's filter syntax
                (e.g. ``"assignee:me status:open"``).

        Returns:
            A list of matching :class:`~kanboard.models.Task` instances; returns
            an empty list when no results are found or the API returns
            ``False``/``None``.
        """
        result = self._client.call("searchTasks", project_id=project_id, query=query)
        if not result:
            return []
        return [Task.from_api(t) for t in result]

    # ------------------------------------------------------------------
    # Update / State transitions
    # ------------------------------------------------------------------

    def update_task(self, task_id: int, **kwargs: Any) -> bool:
        """Update one or more fields on an existing task.

        Maps to the Kanboard ``updateTask`` JSON-RPC method.

        Note:
            The Kanboard API uses ``id`` (not ``task_id``) as the parameter name
            for the task identifier; this is handled internally.

        Args:
            task_id: ID of the task to update.
            **kwargs: Task fields to update: ``title``, ``color_id``,
                ``owner_id``, ``date_due``, ``description``, ``category_id``,
                ``score``, ``priority``, ``reference``, ``tags``.

        Returns:
            ``True`` on success.

        Raises:
            KanboardAPIError: The API returned ``False`` (update failed).
        """
        result = self._client.call("updateTask", id=task_id, **kwargs)
        if result is False:
            raise KanboardAPIError(
                "updateTask returned False — task update failed",
                method="updateTask",
                code=None,
            )
        return bool(result)

    def open_task(self, task_id: int) -> bool:
        """Reopen a previously closed task.

        Maps to the Kanboard ``openTask`` JSON-RPC method.

        Args:
            task_id: ID of the task to reopen.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("openTask", task_id=task_id)
        return bool(result)

    def close_task(self, task_id: int) -> bool:
        """Close (complete) an active task.

        Maps to the Kanboard ``closeTask`` JSON-RPC method.

        Args:
            task_id: ID of the task to close.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("closeTask", task_id=task_id)
        return bool(result)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def remove_task(self, task_id: int) -> bool:
        """Permanently delete a task.

        Maps to the Kanboard ``removeTask`` JSON-RPC method.

        Args:
            task_id: ID of the task to delete.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("removeTask", task_id=task_id)
        return bool(result)

    # ------------------------------------------------------------------
    # Move / Duplicate
    # ------------------------------------------------------------------

    def move_task_position(
        self,
        project_id: int,
        task_id: int,
        column_id: int,
        position: int,
        swimlane_id: int,
    ) -> bool:
        """Move a task to a specific column, position, and swimlane within its project.

        Maps to the Kanboard ``moveTaskPosition`` JSON-RPC method.

        Args:
            project_id: ID of the project containing the task.
            task_id: ID of the task to move.
            column_id: Target column ID.
            position: Target position within the column (1-based integer).
            swimlane_id: Target swimlane ID (use ``0`` for the default swimlane).

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call(
            "moveTaskPosition",
            project_id=project_id,
            task_id=task_id,
            column_id=column_id,
            position=position,
            swimlane_id=swimlane_id,
        )
        return bool(result)

    def move_task_to_project(self, task_id: int, project_id: int, **kwargs: Any) -> bool:
        """Move a task to a different project.

        Maps to the Kanboard ``moveTaskToProject`` JSON-RPC method.

        Args:
            task_id: ID of the task to move.
            project_id: ID of the destination project.
            **kwargs: Optional placement fields: ``swimlane_id``, ``column_id``,
                ``category_id``, ``owner_id``.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call(
            "moveTaskToProject", task_id=task_id, project_id=project_id, **kwargs
        )
        return bool(result)

    def duplicate_task_to_project(self, task_id: int, project_id: int, **kwargs: Any) -> int:
        """Duplicate a task into a different project.

        Maps to the Kanboard ``duplicateTaskToProject`` JSON-RPC method.

        Args:
            task_id: ID of the task to duplicate.
            project_id: ID of the destination project.
            **kwargs: Optional placement fields: ``swimlane_id``, ``column_id``.

        Returns:
            The integer ID of the newly created duplicate task.
        """
        result = self._client.call(
            "duplicateTaskToProject", task_id=task_id, project_id=project_id, **kwargs
        )
        return int(result)
