"""Project permissions resource module - user/group access for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ProjectPermissionsResource:
    """Kanboard Project Permissions API resource.

    Exposes all nine project-permission-related JSON-RPC methods as typed
    Python methods.  Accessed via ``KanboardClient.project_permissions``.

    Covers user and group assignment/removal, role querying, and role
    changes for a given project.

    Example:
        >>> users = client.project_permissions.get_project_users(1)
        >>> for user_id, username in users.items():
        ...     print(user_id, username)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_project_users(self, project_id: int) -> dict[str, str]:
        """Fetch all users assigned to a project.

        Maps to the Kanboard ``getProjectUsers`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.

        Returns:
            A dict mapping user IDs (as strings) to usernames.  Returns an
            empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getProjectUsers", project_id=project_id)
        if not result:
            return {}
        return dict(result)

    def get_assignable_users(
        self,
        project_id: int,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Fetch all users who can be assigned tasks in a project.

        Maps to the Kanboard ``getAssignableUsers`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            **kwargs: Optional parameters forwarded to the API (e.g.
                ``prepend_unassigned=True``).

        Returns:
            A dict mapping user IDs (as strings) to usernames.  Returns an
            empty dict when the API responds with a falsy value.
        """
        result = self._client.call(
            "getAssignableUsers",
            project_id=project_id,
            **kwargs,
        )
        if not result:
            return {}
        return dict(result)

    def get_project_user_role(self, project_id: int, user_id: int) -> str:
        """Fetch the role of a specific user in a project.

        Maps to the Kanboard ``getProjectUserRole`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            user_id: Unique integer ID of the user.

        Returns:
            The role string (e.g. ``"project-manager"``), or an empty string
            when the user has no role in the project.
        """
        result = self._client.call(
            "getProjectUserRole",
            project_id=project_id,
            user_id=user_id,
        )
        if result is None or result is False or result == "":
            return ""
        return str(result)

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def add_project_user(
        self,
        project_id: int,
        user_id: int,
        **kwargs: Any,
    ) -> bool:
        """Add a user to a project.

        Maps to the Kanboard ``addProjectUser`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            user_id: Unique integer ID of the user to add.
            **kwargs: Optional parameters (e.g. ``role="project-manager"``).

        Returns:
            ``True`` when the user was added successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                operation failed.
        """
        result = self._client.call(
            "addProjectUser",
            project_id=project_id,
            user_id=user_id,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to add user {user_id} to project {project_id}",
                method="addProjectUser",
            )
        return True

    def remove_project_user(self, project_id: int, user_id: int) -> bool:
        """Remove a user from a project.

        Maps to the Kanboard ``removeProjectUser`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            user_id: Unique integer ID of the user to remove.

        Returns:
            ``True`` when the user was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeProjectUser",
            project_id=project_id,
            user_id=user_id,
        )
        return bool(result)

    def change_project_user_role(
        self,
        project_id: int,
        user_id: int,
        role: str,
    ) -> bool:
        """Change the role of a user in a project.

        Maps to the Kanboard ``changeProjectUserRole`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            user_id: Unique integer ID of the user.
            role: The new role to assign (e.g. ``"project-manager"``).

        Returns:
            ``True`` when the role was changed successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                role change failed.
        """
        result = self._client.call(
            "changeProjectUserRole",
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to change role for user {user_id} in project {project_id}",
                method="changeProjectUserRole",
            )
        return True

    # ------------------------------------------------------------------
    # Group management
    # ------------------------------------------------------------------

    def add_project_group(
        self,
        project_id: int,
        group_id: int,
        **kwargs: Any,
    ) -> bool:
        """Add a group to a project.

        Maps to the Kanboard ``addProjectGroup`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            group_id: Unique integer ID of the group to add.
            **kwargs: Optional parameters (e.g. ``role="project-viewer"``).

        Returns:
            ``True`` when the group was added successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                operation failed.
        """
        result = self._client.call(
            "addProjectGroup",
            project_id=project_id,
            group_id=group_id,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to add group {group_id} to project {project_id}",
                method="addProjectGroup",
            )
        return True

    def remove_project_group(self, project_id: int, group_id: int) -> bool:
        """Remove a group from a project.

        Maps to the Kanboard ``removeProjectGroup`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            group_id: Unique integer ID of the group to remove.

        Returns:
            ``True`` when the group was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeProjectGroup",
            project_id=project_id,
            group_id=group_id,
        )
        return bool(result)

    def change_project_group_role(
        self,
        project_id: int,
        group_id: int,
        role: str,
    ) -> bool:
        """Change the role of a group in a project.

        Maps to the Kanboard ``changeProjectGroupRole`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project.
            group_id: Unique integer ID of the group.
            role: The new role to assign (e.g. ``"project-viewer"``).

        Returns:
            ``True`` when the role was changed successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                role change failed.
        """
        result = self._client.call(
            "changeProjectGroupRole",
            project_id=project_id,
            group_id=group_id,
            role=role,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to change role for group {group_id} in project {project_id}",
                method="changeProjectGroupRole",
            )
        return True
