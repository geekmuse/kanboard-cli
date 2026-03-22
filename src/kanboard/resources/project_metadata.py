"""Project metadata resource module — key-value metadata for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ProjectMetadataResource:
    """Kanboard Project Metadata API resource.

    Exposes all four project-metadata-related JSON-RPC methods as typed
    Python methods.  Accessed via ``KanboardClient.project_metadata``.

    Metadata entries are free-form key-value string pairs attached to a
    project.

    Example:
        >>> meta = client.project_metadata.get_project_metadata(1)
        >>> for key, value in meta.items():
        ...     print(key, value)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_project_metadata(self, project_id: int) -> dict[str, str]:
        """Fetch all metadata key-value pairs for a project.

        Maps to the Kanboard ``getProjectMetadata`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.

        Returns:
            A dict mapping metadata keys to their string values.  Returns an
            empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getProjectMetadata", project_id=project_id)
        if not result:
            return {}
        return dict(result)

    def get_project_metadata_by_name(self, project_id: int, name: str) -> str:
        """Fetch a single metadata value by its key name.

        Maps to the Kanboard ``getProjectMetadataByName`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            name: The metadata key name to look up.

        Returns:
            The metadata value as a string, or an empty string when the key
            does not exist or the API returns an empty/falsy value.
        """
        result = self._client.call(
            "getProjectMetadataByName",
            project_id=project_id,
            name=name,
        )
        if result is None or result is False or result == "":
            return ""
        return str(result)

    def save_project_metadata(self, project_id: int, values: dict[str, Any]) -> bool:
        """Save one or more metadata key-value pairs to a project.

        Maps to the Kanboard ``saveProjectMetadata`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            values: A dict of key-value pairs to persist.

        Returns:
            ``True`` when the metadata was saved successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating save failed.
        """
        result = self._client.call(
            "saveProjectMetadata",
            project_id=project_id,
            values=values,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to save metadata on project {project_id}",
                method="saveProjectMetadata",
            )
        return True

    def remove_project_metadata(self, project_id: int, name: str) -> bool:
        """Remove a single metadata key from a project.

        Maps to the Kanboard ``removeProjectMetadata`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            name: The metadata key to remove.

        Returns:
            ``True`` when the key was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeProjectMetadata",
            project_id=project_id,
            name=name,
        )
        return bool(result)
