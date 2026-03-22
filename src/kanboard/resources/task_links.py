"""Task links resource module — internal task-to-task link management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import TaskLink

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class TaskLinksResource:
    """Kanboard Task Links API resource.

    Exposes all five internal task-link JSON-RPC methods as typed Python methods.
    Task links associate two tasks via a link type (see
    :class:`~kanboard.resources.links.LinksResource` for link type management).

    Accessed via ``KanboardClient.task_links``.

    Example:
        >>> link_id = client.task_links.create_task_link(
        ...     task_id=10, opposite_task_id=20, link_id=1
        ... )
        >>> links = client.task_links.get_all_task_links(task_id=10)
        >>> for tl in links:
        ...     print(tl.id, tl.link_id)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_task_link(
        self,
        task_id: int,
        opposite_task_id: int,
        link_id: int,
    ) -> int:
        """Create an internal task-to-task link.

        Maps to the Kanboard ``createTaskLink`` JSON-RPC method.

        Args:
            task_id: ID of the source task.
            opposite_task_id: ID of the target (opposite) task.
            link_id: ID of the link type defining the relationship.

        Returns:
            The integer ID of the newly created task link.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call(
            "createTaskLink",
            task_id=task_id,
            opposite_task_id=opposite_task_id,
            link_id=link_id,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create task link between task {task_id} and {opposite_task_id}",
                method="createTaskLink",
            )
        return int(result)

    def update_task_link(
        self,
        task_link_id: int,
        task_id: int,
        opposite_task_id: int,
        link_id: int,
    ) -> bool:
        """Update an existing internal task-to-task link.

        Maps to the Kanboard ``updateTaskLink`` JSON-RPC method.

        Args:
            task_link_id: Unique integer ID of the task link to update.
            task_id: ID of the source task.
            opposite_task_id: ID of the target (opposite) task.
            link_id: ID of the link type defining the relationship.

        Returns:
            ``True`` when the task link was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update
                failed.
        """
        result = self._client.call(
            "updateTaskLink",
            task_link_id=task_link_id,
            task_id=task_id,
            opposite_task_id=opposite_task_id,
            link_id=link_id,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to update task link {task_link_id}",
                method="updateTaskLink",
            )
        return True

    def get_task_link_by_id(self, task_link_id: int) -> TaskLink:
        """Fetch a single task link by its ID.

        Maps to the Kanboard ``getTaskLinkById`` JSON-RPC method.

        Args:
            task_link_id: Unique integer ID of the task link.

        Returns:
            A :class:`~kanboard.models.TaskLink` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` —
                no task link with the given ID exists.
        """
        result = self._client.call("getTaskLinkById", task_link_id=task_link_id)
        if not result:
            raise KanboardNotFoundError(
                f"TaskLink {task_link_id} not found",
                resource="TaskLink",
                identifier=task_link_id,
            )
        return TaskLink.from_api(result)

    def get_all_task_links(self, task_id: int) -> list[TaskLink]:
        """Fetch all internal task links for a given task.

        Maps to the Kanboard ``getAllTaskLinks`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task whose links to retrieve.

        Returns:
            A list of :class:`~kanboard.models.TaskLink` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllTaskLinks", task_id=task_id)
        if not result:
            return []
        return [TaskLink.from_api(item) for item in result]

    def remove_task_link(self, task_link_id: int) -> bool:
        """Remove an internal task-to-task link.

        Maps to the Kanboard ``removeTaskLink`` JSON-RPC method.

        Args:
            task_link_id: Unique integer ID of the task link to remove.

        Returns:
            ``True`` when the task link was removed, ``False`` otherwise.
        """
        result = self._client.call("removeTaskLink", task_link_id=task_link_id)
        return bool(result)
