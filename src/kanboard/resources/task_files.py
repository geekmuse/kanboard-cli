"""Task files resource module — task-level file management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import TaskFile

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class TaskFilesResource:
    """Kanboard Task Files API resource.

    Exposes all six task-file-related JSON-RPC methods as typed Python
    methods.  Accessed via ``KanboardClient.task_files``.

    Example:
        >>> files = client.task_files.get_all_task_files(42)
        >>> for f in files:
        ...     print(f.name, f.size)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_task_file(
        self,
        project_id: int,
        task_id: int,
        filename: str,
        blob: str,
        **kwargs: Any,
    ) -> int:
        """Upload a file to a task.

        Maps to the Kanboard ``createTaskFile`` JSON-RPC method.
        The *blob* must be a base64-encoded representation of the file content.

        Args:
            project_id: Unique integer ID of the project.
            task_id: Unique integer ID of the task.
            filename: The name to give the uploaded file.
            blob: Base64-encoded file content.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            The integer ID of the newly created task file.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating upload failed.
        """
        result = self._client.call(
            "createTaskFile",
            project_id=project_id,
            task_id=task_id,
            filename=filename,
            blob=blob,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create task file '{filename}' on task {task_id}",
                method="createTaskFile",
            )
        return int(result)

    def get_all_task_files(self, task_id: int) -> list[TaskFile]:
        """Fetch all files attached to a task.

        Maps to the Kanboard ``getAllTaskFiles`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task.

        Returns:
            A list of :class:`~kanboard.models.TaskFile` instances.  Returns
            an empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllTaskFiles", task_id=task_id)
        if not result:
            return []
        return [TaskFile.from_api(item) for item in result]

    def get_task_file(self, file_id: int) -> TaskFile:
        """Fetch a single task file by its ID.

        Maps to the Kanboard ``getTaskFile`` JSON-RPC method.

        Args:
            file_id: Unique integer ID of the file to fetch.

        Returns:
            A :class:`~kanboard.models.TaskFile` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` —
                file does not exist.
        """
        result = self._client.call("getTaskFile", file_id=file_id)
        if not result:
            raise KanboardNotFoundError(
                f"Task file {file_id} not found",
                resource="TaskFile",
                identifier=file_id,
            )
        return TaskFile.from_api(result)

    def download_task_file(self, file_id: int) -> str:
        """Download a task file and return its base64-encoded content.

        Maps to the Kanboard ``downloadTaskFile`` JSON-RPC method.

        Args:
            file_id: Unique integer ID of the file to download.

        Returns:
            The base64-encoded file content as a string.
        """
        result = self._client.call("downloadTaskFile", file_id=file_id)
        return str(result or "")

    def remove_task_file(self, file_id: int) -> bool:
        """Remove a single file from a task.

        Maps to the Kanboard ``removeTaskFile`` JSON-RPC method.

        Args:
            file_id: Unique integer ID of the file to remove.

        Returns:
            ``True`` when the file was removed, ``False`` otherwise.
        """
        result = self._client.call("removeTaskFile", file_id=file_id)
        return bool(result)

    def remove_all_task_files(self, task_id: int) -> bool:
        """Remove all files from a task.

        Maps to the Kanboard ``removeAllTaskFiles`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task whose files to remove.

        Returns:
            ``True`` when all files were removed, ``False`` otherwise.
        """
        result = self._client.call("removeAllTaskFiles", task_id=task_id)
        return bool(result)
