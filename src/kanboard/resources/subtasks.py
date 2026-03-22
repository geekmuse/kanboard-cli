"""Subtasks resource module — subtask management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Subtask

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class SubtasksResource:
    """Kanboard Subtasks API resource.

    Exposes all five subtask-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.subtasks``.

    Example:
        >>> subtasks = client.subtasks.get_all_subtasks(task_id=42)
        >>> for subtask in subtasks:
        ...     print(subtask.title, subtask.status)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_subtask(self, task_id: int, title: str, **kwargs: Any) -> int:
        """Create a new subtask on a task.

        Maps to the Kanboard ``createSubtask`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the parent task.
            title: Display title for the new subtask.
            **kwargs: Optional keyword arguments forwarded to the API (e.g.
                ``user_id``, ``time_estimated``, ``status``).

        Returns:
            The integer ID of the newly created subtask.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call(
            "createSubtask",
            task_id=task_id,
            title=title,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create subtask '{title}' on task {task_id}",
                method="createSubtask",
            )
        return int(result)

    def get_subtask(self, subtask_id: int) -> Subtask:
        """Fetch a single subtask by ID.

        Maps to the Kanboard ``getSubtask`` JSON-RPC method.

        Args:
            subtask_id: Unique integer ID of the subtask to retrieve.

        Returns:
            A :class:`~kanboard.models.Subtask` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — no subtask with
                the given ID exists.
        """
        result = self._client.call("getSubtask", subtask_id=subtask_id)
        if result is None:
            raise KanboardNotFoundError(
                f"Subtask {subtask_id} not found",
                resource="Subtask",
                identifier=subtask_id,
            )
        return Subtask.from_api(result)

    def get_all_subtasks(self, task_id: int) -> list[Subtask]:
        """Fetch all subtasks belonging to a task.

        Maps to the Kanboard ``getAllSubtasks`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the parent task.

        Returns:
            A list of :class:`~kanboard.models.Subtask` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllSubtasks", task_id=task_id)
        if not result:
            return []
        return [Subtask.from_api(item) for item in result]

    def update_subtask(self, id: int, task_id: int, **kwargs: Any) -> bool:
        """Update an existing subtask.

        Maps to the Kanboard ``updateSubtask`` JSON-RPC method.

        Args:
            id: Unique integer ID of the subtask to update.
            task_id: Unique integer ID of the parent task.
            **kwargs: Optional keyword arguments forwarded to the API (e.g.
                ``title``, ``user_id``, ``time_estimated``, ``time_spent``,
                ``status``).

        Returns:
            ``True`` when the subtask was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update
                failed.
        """
        result = self._client.call(
            "updateSubtask",
            id=id,
            task_id=task_id,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to update subtask {id}",
                method="updateSubtask",
            )
        return True

    def remove_subtask(self, subtask_id: int) -> bool:
        """Remove a subtask.

        Maps to the Kanboard ``removeSubtask`` JSON-RPC method.

        Args:
            subtask_id: Unique integer ID of the subtask to remove.

        Returns:
            ``True`` when the subtask was removed, ``False`` otherwise.
        """
        result = self._client.call("removeSubtask", subtask_id=subtask_id)
        return bool(result)
