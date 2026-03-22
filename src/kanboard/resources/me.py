"""Current user ("Me") resource module - authenticated user endpoints.

All methods in this module require **User API authentication** (username +
password), which is not yet available in the SDK transport layer.  Every
method raises :class:`~kanboard.exceptions.KanboardAuthError` until User
API auth is implemented (Milestone 4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kanboard.exceptions import KanboardAuthError
from kanboard.models import User

if TYPE_CHECKING:
    from kanboard.client import KanboardClient

_AUTH_MSG = (
    "The 'me' endpoints require User API authentication "
    "(username + password). JSON-RPC API token auth is not supported "
    "for these methods. User API auth will be available in a future release."
)


class MeResource:
    """Kanboard "Me" API resource - current authenticated user.

    Exposes all seven ``getMe*`` / ``createMyPrivateProject`` JSON-RPC
    methods.  These endpoints are unique in that they operate on the
    *currently authenticated user* rather than accepting an explicit user ID.

    .. important::

        All methods require **User API authentication** (username + password
        credentials).  The SDK currently only supports JSON-RPC API token
        auth, so every method raises
        :class:`~kanboard.exceptions.KanboardAuthError` until User API auth
        is implemented.

    Accessed via ``KanboardClient.me``.

    Example (future, once User API auth is available)::

        >>> me = client.me.get_me()
        >>> me.username
        'admin'
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make
                API calls.
        """
        self._client = client

    def get_me(self) -> User:
        """Get the profile of the currently authenticated user.

        Maps to the Kanboard ``getMe`` JSON-RPC method.

        Returns:
            A :class:`~kanboard.models.User` instance for the authenticated user.

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)

    def get_my_dashboard(self) -> dict:
        """Get the dashboard for the currently authenticated user.

        Maps to the Kanboard ``getMyDashboard`` JSON-RPC method.

        Returns:
            A dict containing dashboard data (projects, tasks, subtasks).

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)

    def get_my_activity_stream(self) -> list[dict]:
        """Get the activity stream for the currently authenticated user.

        Maps to the Kanboard ``getMyActivityStream`` JSON-RPC method.

        Returns:
            A list of activity event dicts.

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)

    def create_my_private_project(self, name: str, **kwargs: object) -> int:
        """Create a private project owned by the currently authenticated user.

        Maps to the Kanboard ``createMyPrivateProject`` JSON-RPC method.

        Args:
            name: The project name.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``description``).

        Returns:
            The ID of the newly created project.

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)

    def get_my_projects_list(self) -> dict:
        """Get a list of projects the currently authenticated user has access to.

        Maps to the Kanboard ``getMyProjectsList`` JSON-RPC method.

        Returns:
            A dict mapping project IDs (as strings) to project names.

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)

    def get_my_overdue_tasks(self) -> list[dict]:
        """Get overdue tasks assigned to the currently authenticated user.

        Maps to the Kanboard ``getMyOverdueTasks`` JSON-RPC method.

        Returns:
            A list of dicts representing overdue task data.

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)

    def get_my_projects(self) -> list[dict]:
        """Get all projects the currently authenticated user is a member of.

        Maps to the Kanboard ``getMyProjects`` JSON-RPC method.

        Returns:
            A list of dicts representing project data.

        Raises:
            KanboardAuthError: Always raised - User API auth is required.
        """
        raise KanboardAuthError(_AUTH_MSG)
