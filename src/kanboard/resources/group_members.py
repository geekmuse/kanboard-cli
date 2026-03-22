"""Group members resource module - group membership management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kanboard.exceptions import KanboardAPIError
from kanboard.models import Group, User

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class GroupMembersResource:
    """Kanboard Group Members API resource.

    Exposes all five group-member-related JSON-RPC methods as typed Python
    methods.  Accessed via ``KanboardClient.group_members``.

    Example:
        >>> members = client.group_members.get_group_members(1)
        >>> for u in members:
        ...     print(u.id, u.username)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_member_groups(self, user_id: int) -> list[Group]:
        """Fetch all groups that a user belongs to.

        Maps to the Kanboard ``getMemberGroups`` JSON-RPC method.

        Args:
            user_id: Unique integer ID of the user.

        Returns:
            A list of :class:`~kanboard.models.Group` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getMemberGroups", user_id=user_id)
        if not result:
            return []
        return [Group.from_api(item) for item in result]

    def get_group_members(self, group_id: int) -> list[User]:
        """Fetch all members of a group.

        Maps to the Kanboard ``getGroupMembers`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group.

        Returns:
            A list of :class:`~kanboard.models.User` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getGroupMembers", group_id=group_id)
        if not result:
            return []
        return [User.from_api(item) for item in result]

    def add_group_member(self, group_id: int, user_id: int) -> bool:
        """Add a user to a group.

        Maps to the Kanboard ``addGroupMember`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group.
            user_id: Unique integer ID of the user to add.

        Returns:
            ``True`` when the member was added successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                member could not be added.
        """
        result = self._client.call("addGroupMember", group_id=group_id, user_id=user_id)
        if not result:
            raise KanboardAPIError(
                f"Failed to add user {user_id} to group {group_id}",
                method="addGroupMember",
            )
        return bool(result)

    def remove_group_member(self, group_id: int, user_id: int) -> bool:
        """Remove a user from a group.

        Maps to the Kanboard ``removeGroupMember`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group.
            user_id: Unique integer ID of the user to remove.

        Returns:
            ``True`` when the member was removed, ``False`` otherwise.
        """
        result = self._client.call("removeGroupMember", group_id=group_id, user_id=user_id)
        return bool(result)

    def is_group_member(self, group_id: int, user_id: int) -> bool:
        """Check whether a user is a member of a group.

        Maps to the Kanboard ``isGroupMember`` JSON-RPC method.

        Args:
            group_id: Unique integer ID of the group.
            user_id: Unique integer ID of the user to check.

        Returns:
            ``True`` if the user is a member of the group, ``False`` otherwise.
        """
        result = self._client.call("isGroupMember", group_id=group_id, user_id=user_id)
        return bool(result)
