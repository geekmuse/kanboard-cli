"""Current user ("Me") resource module — authenticated user endpoints.

These endpoints use the **User API** authentication mode (username +
password / personal access token).  When the client is configured with
``auth_mode='user'``, all methods make real API calls.  When the client
uses the default Application API token auth (``auth_mode='app'``), every
method raises :class:`~kanboard.exceptions.KanboardAuthError` with an
actionable message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAuthError
from kanboard.models import User

if TYPE_CHECKING:
    from kanboard.client import KanboardClient

_AUTH_MODE_USER = "user"

_APP_AUTH_MSG = (
    "The 'me' endpoints require User API authentication "
    "(username + password). Application API token auth is not supported "
    "for these methods. Configure auth_mode = 'user' with a username and "
    "password in your profile, or use --auth-mode user."
)


class MeResource:
    """Kanboard "Me" API resource — current authenticated user.

    Exposes all seven ``getMe*`` / ``createMyPrivateProject`` JSON-RPC
    methods.  These endpoints operate on the *currently authenticated user*
    rather than accepting an explicit user ID.

    .. important::

        All methods require **User API authentication** (``auth_mode='user'``
        with username + password credentials).  When the client uses
        Application API token auth (the default ``auth_mode='app'``), every
        method raises :class:`~kanboard.exceptions.KanboardAuthError` with an
        actionable error message.

    Accessed via ``KanboardClient.me``.

    Example::

        with KanboardClient(
            url="https://kb.example.com/jsonrpc.php",
            auth_mode="user",
            username="admin",
            password="secret",
        ) as client:
            me = client.me.get_me()
            print(me.username)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make
                API calls.
        """
        self._client = client

    def _require_user_auth(self) -> None:
        """Raise :class:`~kanboard.exceptions.KanboardAuthError` if not in user auth mode.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
        """
        if self._client.auth_mode != _AUTH_MODE_USER:
            raise KanboardAuthError(_APP_AUTH_MSG)

    def get_me(self) -> User:
        """Get the profile of the currently authenticated user.

        Maps to the Kanboard ``getMe`` JSON-RPC method.

        Returns:
            A :class:`~kanboard.models.User` instance for the authenticated user.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        data: dict[str, Any] = self._client.call("getMe")
        return User.from_api(data)

    def get_my_dashboard(self) -> dict[str, Any]:
        """Get the dashboard for the currently authenticated user.

        Maps to the Kanboard ``getMyDashboard`` JSON-RPC method.

        Returns:
            A dict containing dashboard data (projects, tasks, subtasks).

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        return self._client.call("getMyDashboard")  # type: ignore[no-any-return]

    def get_my_activity_stream(self) -> list[dict[str, Any]]:
        """Get the activity stream for the currently authenticated user.

        Maps to the Kanboard ``getMyActivityStream`` JSON-RPC method.

        Returns:
            A list of activity event dicts.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        result = self._client.call("getMyActivityStream")
        return result if isinstance(result, list) else []

    def create_my_private_project(self, name: str, **kwargs: Any) -> int:
        """Create a private project owned by the currently authenticated user.

        Maps to the Kanboard ``createMyPrivateProject`` JSON-RPC method.

        Args:
            name: The project name.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``description``).

        Returns:
            The ID of the newly created project.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        result = self._client.call("createMyPrivateProject", name=name, **kwargs)
        return int(result)

    def get_my_projects_list(self) -> dict[str, Any]:
        """Get a mapping of project IDs to names for the current user.

        Maps to the Kanboard ``getMyProjectsList`` JSON-RPC method.

        Returns:
            A dict mapping project IDs (as strings) to project names.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        return self._client.call("getMyProjectsList")  # type: ignore[no-any-return]

    def get_my_overdue_tasks(self) -> list[dict[str, Any]]:
        """Get overdue tasks assigned to the currently authenticated user.

        Maps to the Kanboard ``getMyOverdueTasks`` JSON-RPC method.

        Returns:
            A list of dicts representing overdue task data.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        result = self._client.call("getMyOverdueTasks")
        return result if isinstance(result, list) else []

    def get_my_projects(self) -> list[dict[str, Any]]:
        """Get all projects the currently authenticated user is a member of.

        Maps to the Kanboard ``getMyProjects`` JSON-RPC method.

        Returns:
            A list of dicts representing project data.

        Raises:
            KanboardAuthError: When the client is not using ``auth_mode='user'``.
            KanboardAPIError: The API returned an error response.
        """
        self._require_user_auth()
        result = self._client.call("getMyProjects")
        return result if isinstance(result, list) else []
