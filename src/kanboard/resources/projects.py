"""Projects resource module — CRUD and management operations for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Project

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ProjectsResource:
    """Kanboard Projects API resource.

    Exposes all project-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.projects``.

    Example:
        >>> project = client.projects.get_project_by_id(1)
        >>> project_id = client.projects.create_project("My Project")
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

    def create_project(self, name: str, **kwargs: Any) -> int:
        """Create a new project.

        Maps to the Kanboard ``createProject`` JSON-RPC method.

        Args:
            name: Project name.
            **kwargs: Optional project fields accepted by ``createProject``:
                ``description``, ``owner_id``, ``identifier``, ``start_date``,
                ``end_date``.

        Returns:
            The integer ID of the newly created project.

        Raises:
            KanboardAPIError: The API returned ``False`` (project creation failed).
        """
        result = self._client.call("createProject", name=name, **kwargs)
        if result is False or result == 0:
            raise KanboardAPIError(
                "createProject returned False — project creation failed",
                method="createProject",
                code=None,
            )
        return int(result)

    def get_project_by_id(self, project_id: int) -> Project:
        """Fetch a single project by its numeric ID.

        Maps to the Kanboard ``getProjectById`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.

        Returns:
            A :class:`~kanboard.models.Project` instance populated from the API response.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (project not found).
        """
        result = self._client.call("getProjectById", project_id=project_id)
        if result is None:
            raise KanboardNotFoundError(
                "Project not found",
                method="getProjectById",
                code=None,
                resource="Project",
                identifier=str(project_id),
            )
        return Project.from_api(result)

    def get_project_by_name(self, name: str) -> Project:
        """Fetch a single project by its name.

        Maps to the Kanboard ``getProjectByName`` JSON-RPC method.

        Args:
            name: The exact project name to look up.

        Returns:
            A :class:`~kanboard.models.Project` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (project not found).
        """
        result = self._client.call("getProjectByName", name=name)
        if result is None:
            raise KanboardNotFoundError(
                "Project not found by name",
                method="getProjectByName",
                code=None,
                resource="Project",
                identifier=name,
            )
        return Project.from_api(result)

    def get_project_by_identifier(self, identifier: str) -> Project:
        """Fetch a single project by its short identifier string.

        Maps to the Kanboard ``getProjectByIdentifier`` JSON-RPC method.

        Args:
            identifier: The project's short identifier (e.g. ``"PROJ"``).

        Returns:
            A :class:`~kanboard.models.Project` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (project not found).
        """
        result = self._client.call("getProjectByIdentifier", identifier=identifier)
        if result is None:
            raise KanboardNotFoundError(
                "Project not found by identifier",
                method="getProjectByIdentifier",
                code=None,
                resource="Project",
                identifier=identifier,
            )
        return Project.from_api(result)

    def get_project_by_email(self, email: str) -> Project:
        """Fetch a single project by its notification email address.

        Maps to the Kanboard ``getProjectByEmail`` JSON-RPC method.

        Args:
            email: The project's notification e-mail address.

        Returns:
            A :class:`~kanboard.models.Project` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (project not found).
        """
        result = self._client.call("getProjectByEmail", email=email)
        if result is None:
            raise KanboardNotFoundError(
                "Project not found by email",
                method="getProjectByEmail",
                code=None,
                resource="Project",
                identifier=email,
            )
        return Project.from_api(result)

    def get_all_projects(self) -> list[Project]:
        """Fetch all projects accessible to the authenticated user.

        Maps to the Kanboard ``getAllProjects`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.Project` instances; returns an empty
            list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getAllProjects")
        if not result:
            return []
        return [Project.from_api(p) for p in result]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_project(self, project_id: int, **kwargs: Any) -> bool:
        """Update one or more fields on an existing project.

        Maps to the Kanboard ``updateProject`` JSON-RPC method.

        Note:
            The Kanboard API uses ``id`` (not ``project_id``) as the parameter
            name for the project identifier; this is handled internally.

        Args:
            project_id: ID of the project to update.
            **kwargs: Project fields to update: ``name``, ``description``,
                ``owner_id``, ``identifier``, ``start_date``, ``end_date``.

        Returns:
            ``True`` on success.

        Raises:
            KanboardAPIError: The API returned ``False`` (update failed).
        """
        result = self._client.call("updateProject", project_id=project_id, **kwargs)
        if result is False:
            raise KanboardAPIError(
                "updateProject returned False — project update failed",
                method="updateProject",
                code=None,
            )
        return bool(result)

    # ------------------------------------------------------------------
    # Delete / Enable / Disable
    # ------------------------------------------------------------------

    def remove_project(self, project_id: int) -> bool:
        """Permanently delete a project and all its data.

        Maps to the Kanboard ``removeProject`` JSON-RPC method.

        Args:
            project_id: ID of the project to delete.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("removeProject", project_id=project_id)
        return bool(result)

    def enable_project(self, project_id: int) -> bool:
        """Enable (activate) a previously disabled project.

        Maps to the Kanboard ``enableProject`` JSON-RPC method.

        Args:
            project_id: ID of the project to enable.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("enableProject", project_id=project_id)
        return bool(result)

    def disable_project(self, project_id: int) -> bool:
        """Disable (deactivate) an active project.

        Maps to the Kanboard ``disableProject`` JSON-RPC method.

        Args:
            project_id: ID of the project to disable.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("disableProject", project_id=project_id)
        return bool(result)

    def enable_project_public_access(self, project_id: int) -> bool:
        """Enable public (anonymous) access for a project.

        Maps to the Kanboard ``enableProjectPublicAccess`` JSON-RPC method.

        Args:
            project_id: ID of the project.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("enableProjectPublicAccess", project_id=project_id)
        return bool(result)

    def disable_project_public_access(self, project_id: int) -> bool:
        """Disable public (anonymous) access for a project.

        Maps to the Kanboard ``disableProjectPublicAccess`` JSON-RPC method.

        Args:
            project_id: ID of the project.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("disableProjectPublicAccess", project_id=project_id)
        return bool(result)

    # ------------------------------------------------------------------
    # Activity
    # ------------------------------------------------------------------

    def get_project_activity(self, project_id: int) -> list[dict[str, Any]]:
        """Fetch the activity feed for a single project.

        Maps to the Kanboard ``getProjectActivity`` JSON-RPC method.

        Args:
            project_id: ID of the project.

        Returns:
            A list of activity event dicts; returns an empty list when the API
            responds with ``False`` or ``None``.
        """
        result = self._client.call("getProjectActivity", project_id=project_id)
        if not result:
            return []
        return list(result)

    def get_project_activities(self, project_ids: list[int]) -> list[dict[str, Any]]:
        """Fetch the activity feed for multiple projects in a single call.

        Maps to the Kanboard ``getProjectActivities`` JSON-RPC method.

        Args:
            project_ids: List of project IDs to query.

        Returns:
            A list of activity event dicts; returns an empty list when the API
            responds with ``False`` or ``None``.
        """
        result = self._client.call("getProjectActivities", project_ids=project_ids)
        if not result:
            return []
        return list(result)
