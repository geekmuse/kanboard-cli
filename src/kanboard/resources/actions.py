"""Automatic actions resource module - action management for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kanboard.exceptions import KanboardAPIError
from kanboard.models import Action

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ActionsResource:
    """Kanboard Automatic Actions API resource.

    Exposes all six automatic-action JSON-RPC methods as typed Python methods.
    Automatic actions allow you to automate task changes when specific events
    fire (e.g. assign a user when a task is moved to a column).

    Accessed via ``KanboardClient.actions``.

    Example:
        >>> actions = client.actions.get_actions(project_id=1)
        >>> for a in actions:
        ...     print(a.id, a.action_name, a.event_name)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_available_actions(self) -> dict:
        """Fetch all available automatic action types.

        Maps to the Kanboard ``getAvailableActions`` JSON-RPC method.

        Returns:
            A dict mapping action class names to their human-readable labels.
            Returns an empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getAvailableActions")
        if not result:
            return {}
        return dict(result)

    def get_available_action_events(self) -> dict:
        """Fetch all available action events.

        Maps to the Kanboard ``getAvailableActionEvents`` JSON-RPC method.

        Returns:
            A dict mapping event identifiers to their human-readable labels.
            Returns an empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getAvailableActionEvents")
        if not result:
            return {}
        return dict(result)

    def get_compatible_action_events(self, action_name: str) -> list:
        r"""Fetch the events compatible with a given action type.

        Maps to the Kanboard ``getCompatibleActionEvents`` JSON-RPC method.

        Args:
            action_name: The action class name (e.g.
                ``"\\TaskAssignColorColumn"``).

        Returns:
            A list of compatible event identifiers. Returns an empty list
            when the API responds with a falsy value.
        """
        result = self._client.call(
            "getCompatibleActionEvents",
            action_name=action_name,
        )
        if not result:
            return []
        return list(result)

    def get_actions(self, project_id: int) -> list[Action]:
        """Fetch all automatic actions configured for a project.

        Maps to the Kanboard ``getActions`` JSON-RPC method.

        Args:
            project_id: ID of the project whose actions to retrieve.

        Returns:
            A list of :class:`~kanboard.models.Action` instances. Returns
            an empty list when the API responds with a falsy value.
        """
        result = self._client.call("getActions", project_id=project_id)
        if not result:
            return []
        return [Action.from_api(item) for item in result]

    def create_action(
        self,
        project_id: int,
        event_name: str,
        action_name: str,
        params: dict,
    ) -> int:
        """Create a new automatic action for a project.

        Maps to the Kanboard ``createAction`` JSON-RPC method.

        Args:
            project_id: ID of the project.
            event_name: The event identifier that triggers the action.
            action_name: The action class name to execute.
            params: A dict of action-specific parameters.

        Returns:
            The integer ID of the newly created action.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call(
            "createAction",
            project_id=project_id,
            event_name=event_name,
            action_name=action_name,
            params=params,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create action on project {project_id}",
                method="createAction",
            )
        return int(result)

    def remove_action(self, action_id: int) -> bool:
        """Remove an automatic action.

        Maps to the Kanboard ``removeAction`` JSON-RPC method.

        Args:
            action_id: ID of the action to remove.

        Returns:
            ``True`` when the action was removed, ``False`` otherwise.
        """
        result = self._client.call("removeAction", action_id=action_id)
        return bool(result)
