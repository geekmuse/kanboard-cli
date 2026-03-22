"""Project files resource module — project-level file management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import ProjectFile

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ProjectFilesResource:
    """Kanboard Project Files API resource.

    Exposes all six project-file-related JSON-RPC methods as typed Python
    methods.  Accessed via ``KanboardClient.project_files``.

    Example:
        >>> files = client.project_files.get_all_project_files(1)
        >>> for f in files:
        ...     print(f.name, f.size)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_project_file(
        self,
        project_id: int,
        filename: str,
        blob: str,
        **kwargs: Any,
    ) -> int:
        """Upload a file to a project.

        Maps to the Kanboard ``createProjectFile`` JSON-RPC method.
        The *blob* must be a base64-encoded representation of the file content.

        Args:
            project_id: Unique integer ID of the project.
            filename: The name to give the uploaded file.
            blob: Base64-encoded file content.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            The integer ID of the newly created project file.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating upload failed.
        """
        result = self._client.call(
            "createProjectFile",
            project_id=project_id,
            filename=filename,
            blob=blob,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create project file '{filename}' on project {project_id}",
                method="createProjectFile",
            )
        return int(result)

    def get_all_project_files(self, project_id: int) -> list[ProjectFile]:
        """Fetch all files attached to a project.

        Maps to the Kanboard ``getAllProjectFiles`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.

        Returns:
            A list of :class:`~kanboard.models.ProjectFile` instances.  Returns
            an empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllProjectFiles", project_id=project_id)
        if not result:
            return []
        return [ProjectFile.from_api(item) for item in result]

    def get_project_file(self, project_id: int, file_id: int) -> ProjectFile:
        """Fetch a single project file by its ID.

        Maps to the Kanboard ``getProjectFile`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            file_id: Unique integer ID of the file to fetch.

        Returns:
            A :class:`~kanboard.models.ProjectFile` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` —
                file does not exist.
        """
        result = self._client.call(
            "getProjectFile",
            project_id=project_id,
            file_id=file_id,
        )
        if not result:
            raise KanboardNotFoundError(
                f"Project file {file_id} not found in project {project_id}",
                resource="ProjectFile",
                identifier=file_id,
            )
        return ProjectFile.from_api(result)

    def download_project_file(self, project_id: int, file_id: int) -> str:
        """Download a project file and return its base64-encoded content.

        Maps to the Kanboard ``downloadProjectFile`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            file_id: Unique integer ID of the file to download.

        Returns:
            The base64-encoded file content as a string.
        """
        result = self._client.call(
            "downloadProjectFile",
            project_id=project_id,
            file_id=file_id,
        )
        return str(result or "")

    def remove_project_file(self, project_id: int, file_id: int) -> bool:
        """Remove a single file from a project.

        Maps to the Kanboard ``removeProjectFile`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            file_id: Unique integer ID of the file to remove.

        Returns:
            ``True`` when the file was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeProjectFile",
            project_id=project_id,
            file_id=file_id,
        )
        return bool(result)

    def remove_all_project_files(self, project_id: int) -> bool:
        """Remove all files from a project.

        Maps to the Kanboard ``removeAllProjectFiles`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project whose files to remove.

        Returns:
            ``True`` when all files were removed, ``False`` otherwise.
        """
        result = self._client.call("removeAllProjectFiles", project_id=project_id)
        return bool(result)
