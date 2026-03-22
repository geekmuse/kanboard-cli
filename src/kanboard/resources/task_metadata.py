"""Task metadata resource module - key-value metadata for Kanboard tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class TaskMetadataResource:
    """Kanboard Task Metadata API resource.

    Exposes all four task-metadata-related JSON-RPC methods as typed
    Python methods.  Accessed via ``KanboardClient.task_metadata``.

    Metadata entries are free-form key-value string pairs attached to a
    task.

    Example:
        >>> meta = client.task_metadata.get_task_metadata(42)
        >>> for key, value in meta.items():
        ...     print(key, value)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_task_metadata(self, task_id: int) -> dict[str, str]:
        """Fetch all metadata key-value pairs for a task.

        Maps to the Kanboard ``getTaskMetadata`` JSON-RPC method.

        Note: The Kanboard API returns ``[]`` (an empty list) instead of
        ``{}`` when no metadata exists.  This method normalises that to
        an empty dict.

        Args:
            task_id: Unique integer ID of the task.

        Returns:
            A dict mapping metadata keys to their string values.  Returns an
            empty dict when the API responds with a falsy value or an empty
            list.
        """
        result = self._client.call("getTaskMetadata", task_id=task_id)
        if not result:
            return {}
        # API may return [] on empty instead of {} - normalise
        if isinstance(result, list):
            return {}
        return dict(result)

    def get_task_metadata_by_name(self, task_id: int, name: str) -> str:
        """Fetch a single metadata value by its key name.

        Maps to the Kanboard ``getTaskMetadataByName`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task.
            name: The metadata key name to look up.

        Returns:
            The metadata value as a string, or an empty string when the key
            does not exist or the API returns an empty/falsy value.
        """
        result = self._client.call(
            "getTaskMetadataByName",
            task_id=task_id,
            name=name,
        )
        if result is None or result is False or result == "":
            return ""
        return str(result)

    def save_task_metadata(self, task_id: int, values: dict[str, Any]) -> bool:
        """Save one or more metadata key-value pairs to a task.

        Maps to the Kanboard ``saveTaskMetadata`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task.
            values: A dict of key-value pairs to persist.

        Returns:
            ``True`` when the metadata was saved successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating save failed.
        """
        result = self._client.call(
            "saveTaskMetadata",
            task_id=task_id,
            values=values,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to save metadata on task {task_id}",
                method="saveTaskMetadata",
            )
        return True

    def remove_task_metadata(self, task_id: int, name: str) -> bool:
        """Remove a single metadata key from a task.

        Maps to the Kanboard ``removeTaskMetadata`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task.
            name: The metadata key to remove.

        Returns:
            ``True`` when the key was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeTaskMetadata",
            task_id=task_id,
            name=name,
        )
        return bool(result)
