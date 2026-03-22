"""Groups resource module - user group management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Group

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class GroupsResource:
    """Kanboard Groups API resource.

    Exposes all five group-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.groups``.

    Example:
        >>> groups = client.groups.get_all_groups()
        >>> for g in groups:
        ...     print(g.id, g.name)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_group(self, name: str, **kwargs: Any) -> int:
        """Create a new user group.

        Maps to the Kanboard ``createGroup`` JSON-RPC method.

        Args:
            name: The name for the new group.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``external_id``).

        Returns:
            The integer ID of the newly created group.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                the group could not be created.
        """
        result = self._client.call("createGroup", name=name, **kwargs)
        if not result:
            raise KanboardAPIError(
                f"Failed to create group '{name}'",
                method="createGroup",
            )
        return int(result)

    def get_group(self, group_id: int) -> Group:
        """Fetch a single group by its ID.

        Maps to the Kanboard ``getGroup`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group to fetch.

        Returns:
            A :class:`~kanboard.models.Group` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` -
                the group does not exist.
        """
        result = self._client.call("getGroup", group_id=group_id)
        if not result:
            raise KanboardNotFoundError(
                f"Group {group_id} not found",
                resource="Group",
                identifier=group_id,
            )
        return Group.from_api(result)

    def get_all_groups(self) -> list[Group]:
        """Fetch all user groups.

        Maps to the Kanboard ``getAllGroups`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.Group` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllGroups")
        if not result:
            return []
        return [Group.from_api(item) for item in result]

    def update_group(self, group_id: int, **kwargs: Any) -> bool:
        """Update an existing group.

        Maps to the Kanboard ``updateGroup`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group to update.
            **kwargs: Fields to update (e.g. ``name``, ``external_id``).

        Returns:
            ``True`` when the update succeeded.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update
                failed.
        """
        result = self._client.call("updateGroup", group_id=group_id, **kwargs)
        if not result:
            raise KanboardAPIError(
                f"Failed to update group {group_id}",
                method="updateGroup",
            )
        return bool(result)

    def remove_group(self, group_id: int) -> bool:
        """Remove a group.

        Maps to the Kanboard ``removeGroup`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group to remove.

        Returns:
            ``True`` when the group was removed, ``False`` otherwise.
        """
        result = self._client.call("removeGroup", group_id=group_id)
        return bool(result)
