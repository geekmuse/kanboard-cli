"""Application info resource module - Kanboard instance metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ApplicationResource:
    """Kanboard Application API resource.

    Exposes all seven application-info JSON-RPC methods as typed Python
    methods.  These are read-only queries that return server metadata such
    as version, timezone, colour palette, and role definitions.

    Accessed via ``KanboardClient.application``.

    Example:
        >>> ver = client.application.get_version()
        >>> print(f"Kanboard {ver}")
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_version(self) -> str:
        """Fetch the Kanboard application version string.

        Maps to the Kanboard ``getVersion`` JSON-RPC method.

        Returns:
            The version string (e.g. ``"1.2.30"``).  Returns an empty
            string when the API responds with a falsy value.
        """
        result = self._client.call("getVersion")
        if not result:
            return ""
        return str(result)

    def get_timezone(self) -> str:
        """Fetch the server default timezone.

        Maps to the Kanboard ``getTimezone`` JSON-RPC method.

        Returns:
            The timezone identifier (e.g. ``"UTC"`` or ``"America/New_York"``).
            Returns an empty string when the API responds with a falsy value.
        """
        result = self._client.call("getTimezone")
        if not result:
            return ""
        return str(result)

    def get_default_task_colors(self) -> dict:
        """Fetch all default task colour definitions.

        Maps to the Kanboard ``getDefaultTaskColors`` JSON-RPC method.

        Returns:
            A dict mapping colour identifiers to their CSS definitions.
            Returns an empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getDefaultTaskColors")
        if not result:
            return {}
        return dict(result)

    def get_default_task_color(self) -> str:
        """Fetch the default task colour identifier.

        Maps to the Kanboard ``getDefaultTaskColor`` JSON-RPC method.

        Returns:
            The default colour identifier (e.g. ``"yellow"``).  Returns
            an empty string when the API responds with a falsy value.
        """
        result = self._client.call("getDefaultTaskColor")
        if not result:
            return ""
        return str(result)

    def get_color_list(self) -> dict:
        """Fetch a mapping of colour identifiers to human-readable labels.

        Maps to the Kanboard ``getColorList`` JSON-RPC method.

        Returns:
            A dict mapping colour IDs to labels (e.g. ``{"yellow": "Yellow"}``).
            Returns an empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getColorList")
        if not result:
            return {}
        return dict(result)

    def get_application_roles(self) -> dict:
        """Fetch all application-level roles.

        Maps to the Kanboard ``getApplicationRoles`` JSON-RPC method.

        Returns:
            A dict mapping role identifiers to human-readable labels.
            Returns an empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getApplicationRoles")
        if not result:
            return {}
        return dict(result)

    def get_project_roles(self) -> dict:
        """Fetch all project-level roles.

        Maps to the Kanboard ``getProjectRoles`` JSON-RPC method.

        Returns:
            A dict mapping role identifiers to human-readable labels.
            Returns an empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getProjectRoles")
        if not result:
            return {}
        return dict(result)
