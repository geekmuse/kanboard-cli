"""Swimlanes resource module — swimlane management for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Swimlane

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class SwimlanesResource:
    """Kanboard Swimlanes API resource.

    Exposes all eleven swimlane-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.swimlanes``.

    Example:
        >>> swimlanes = client.swimlanes.get_active_swimlanes(1)
        >>> for lane in swimlanes:
        ...     print(lane.name)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_active_swimlanes(self, project_id: int) -> list[Swimlane]:
        """Fetch all active swimlanes for a project.

        Maps to the Kanboard ``getActiveSwimlanes`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project whose active swimlanes
                to fetch.

        Returns:
            A list of :class:`~kanboard.models.Swimlane` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getActiveSwimlanes", project_id=project_id)
        if not result:
            return []
        return [Swimlane.from_api(item) for item in result]

    def get_all_swimlanes(self, project_id: int) -> list[Swimlane]:
        """Fetch all swimlanes (active and inactive) for a project.

        Maps to the Kanboard ``getAllSwimlanes`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project whose swimlanes to fetch.

        Returns:
            A list of :class:`~kanboard.models.Swimlane` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllSwimlanes", project_id=project_id)
        if not result:
            return []
        return [Swimlane.from_api(item) for item in result]

    def get_swimlane(self, swimlane_id: int) -> Swimlane:
        """Fetch a single swimlane by its ID.

        Maps to the Kanboard ``getSwimlane`` JSON-RPC method.

        Args:
            swimlane_id: Unique integer ID of the swimlane to fetch.

        Returns:
            A :class:`~kanboard.models.Swimlane` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — swimlane does not exist.
        """
        result = self._client.call("getSwimlane", swimlane_id=swimlane_id)
        if result is None:
            raise KanboardNotFoundError(
                f"Swimlane {swimlane_id} not found",
                resource="Swimlane",
                identifier=swimlane_id,
            )
        return Swimlane.from_api(result)

    def get_swimlane_by_id(self, swimlane_id: int) -> Swimlane:
        """Fetch a single swimlane by its ID using the explicit-ID endpoint.

        Maps to the Kanboard ``getSwimlaneById`` JSON-RPC method.

        Args:
            swimlane_id: Unique integer ID of the swimlane to fetch.

        Returns:
            A :class:`~kanboard.models.Swimlane` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — swimlane does not exist.
        """
        result = self._client.call("getSwimlaneById", swimlane_id=swimlane_id)
        if result is None:
            raise KanboardNotFoundError(
                f"Swimlane {swimlane_id} not found",
                resource="Swimlane",
                identifier=swimlane_id,
            )
        return Swimlane.from_api(result)

    def get_swimlane_by_name(self, project_id: int, name: str) -> Swimlane:
        """Fetch a swimlane by its name within a project.

        Maps to the Kanboard ``getSwimlaneByName`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project to search.
            name: The swimlane name to look up.

        Returns:
            A :class:`~kanboard.models.Swimlane` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — no swimlane with
                the given name exists in the project.
        """
        result = self._client.call(
            "getSwimlaneByName",
            project_id=project_id,
            name=name,
        )
        if result is None:
            raise KanboardNotFoundError(
                f"Swimlane '{name}' not found in project {project_id}",
                resource="Swimlane",
                identifier=name,
            )
        return Swimlane.from_api(result)

    def change_swimlane_position(
        self,
        project_id: int,
        swimlane_id: int,
        position: int,
    ) -> bool:
        """Move a swimlane to a new position within the project board.

        Maps to the Kanboard ``changeSwimlanePosition`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project the swimlane belongs to.
            swimlane_id: Unique integer ID of the swimlane to move.
            position: The new 1-based position for the swimlane.

        Returns:
            ``True`` when the position was updated successfully.
        """
        result = self._client.call(
            "changeSwimlanePosition",
            project_id=project_id,
            swimlane_id=swimlane_id,
            position=position,
        )
        return bool(result)

    def update_swimlane(
        self,
        project_id: int,
        swimlane_id: int,
        name: str,
        **kwargs: Any,
    ) -> bool:
        """Update a swimlane's name and optional attributes.

        Maps to the Kanboard ``updateSwimlane`` JSON-RPC method.

        Supported ``kwargs``:
            - ``description`` (str): Swimlane description.

        Args:
            project_id: Unique integer ID of the project the swimlane belongs to.
            swimlane_id: Unique integer ID of the swimlane to update.
            name: New name for the swimlane.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            ``True`` when the swimlane was updated successfully, ``False`` otherwise.
        """
        result = self._client.call(
            "updateSwimlane",
            project_id=project_id,
            swimlane_id=swimlane_id,
            name=name,
            **kwargs,
        )
        return bool(result)

    def add_swimlane(
        self,
        project_id: int,
        name: str,
        **kwargs: Any,
    ) -> int:
        """Add a new swimlane to a project.

        Maps to the Kanboard ``addSwimlane`` JSON-RPC method.

        Supported ``kwargs``:
            - ``description`` (str): Swimlane description.

        Args:
            project_id: Unique integer ID of the project to add the swimlane to.
            name: Name for the new swimlane.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            The integer ID of the newly created swimlane.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating creation failed.
        """
        result = self._client.call(
            "addSwimlane",
            project_id=project_id,
            name=name,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to add swimlane '{name}' to project {project_id}",
                method="addSwimlane",
            )
        return int(result)

    def remove_swimlane(self, project_id: int, swimlane_id: int) -> bool:
        """Remove a swimlane from a project.

        Maps to the Kanboard ``removeSwimlane`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project the swimlane belongs to.
            swimlane_id: Unique integer ID of the swimlane to remove.

        Returns:
            ``True`` when the swimlane was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeSwimlane",
            project_id=project_id,
            swimlane_id=swimlane_id,
        )
        return bool(result)

    def disable_swimlane(self, project_id: int, swimlane_id: int) -> bool:
        """Disable a swimlane in a project.

        Maps to the Kanboard ``disableSwimlane`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project the swimlane belongs to.
            swimlane_id: Unique integer ID of the swimlane to disable.

        Returns:
            ``True`` when the swimlane was disabled, ``False`` otherwise.
        """
        result = self._client.call(
            "disableSwimlane",
            project_id=project_id,
            swimlane_id=swimlane_id,
        )
        return bool(result)

    def enable_swimlane(self, project_id: int, swimlane_id: int) -> bool:
        """Enable a swimlane in a project.

        Maps to the Kanboard ``enableSwimlane`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project the swimlane belongs to.
            swimlane_id: Unique integer ID of the swimlane to enable.

        Returns:
            ``True`` when the swimlane was enabled, ``False`` otherwise.
        """
        result = self._client.call(
            "enableSwimlane",
            project_id=project_id,
            swimlane_id=swimlane_id,
        )
        return bool(result)
