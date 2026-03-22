"""Users resource module — user management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import User

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class UsersResource:
    """Kanboard Users API resource.

    Exposes all ten user-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.users``.

    Example:
        >>> users = client.users.get_all_users()
        >>> for user in users:
        ...     print(user.username, user.email)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_user(self, username: str, password: str, **kwargs: Any) -> int:
        """Create a new local user account.

        Maps to the Kanboard ``createUser`` JSON-RPC method.

        Args:
            username: Unique login name for the new user.
            password: Password for the new user account.
            **kwargs: Optional keyword arguments forwarded to the API (e.g.
                ``name``, ``email``, ``role``).

        Returns:
            The integer ID of the newly created user.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call(
            "createUser",
            username=username,
            password=password,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create user '{username}'",
                method="createUser",
            )
        return int(result)

    def create_ldap_user(self, username: str) -> int:
        """Create a new LDAP user account.

        Maps to the Kanboard ``createLdapUser`` JSON-RPC method.

        Args:
            username: LDAP login name for the new user.

        Returns:
            The integer ID of the newly created LDAP user.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call("createLdapUser", username=username)
        if not result:
            raise KanboardAPIError(
                f"Failed to create LDAP user '{username}'",
                method="createLdapUser",
            )
        return int(result)

    def get_user(self, user_id: int) -> User:
        """Fetch a single user by ID.

        Maps to the Kanboard ``getUser`` JSON-RPC method.

        Args:
            user_id: Unique integer ID of the user to retrieve.

        Returns:
            A :class:`~kanboard.models.User` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — no user with
                the given ID exists.
        """
        result = self._client.call("getUser", user_id=user_id)
        if result is None:
            raise KanboardNotFoundError(
                f"User {user_id} not found",
                resource="User",
                identifier=user_id,
            )
        return User.from_api(result)

    def get_user_by_name(self, username: str) -> User:
        """Fetch a single user by username.

        Maps to the Kanboard ``getUserByName`` JSON-RPC method.

        Args:
            username: Login name of the user to retrieve.

        Returns:
            A :class:`~kanboard.models.User` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — no user with
                the given username exists.
        """
        result = self._client.call("getUserByName", username=username)
        if result is None:
            raise KanboardNotFoundError(
                f"User '{username}' not found",
                resource="User",
                identifier=username,
            )
        return User.from_api(result)

    def get_all_users(self) -> list[User]:
        """Fetch all users.

        Maps to the Kanboard ``getAllUsers`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.User` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllUsers")
        if not result:
            return []
        return [User.from_api(item) for item in result]

    def update_user(self, id: int, **kwargs: Any) -> bool:
        """Update an existing user.

        Maps to the Kanboard ``updateUser`` JSON-RPC method.

        Args:
            id: Unique integer ID of the user to update.
            **kwargs: Optional keyword arguments forwarded to the API (e.g.
                ``username``, ``name``, ``email``, ``role``).

        Returns:
            ``True`` when the user was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update
                failed.
        """
        result = self._client.call("updateUser", id=id, **kwargs)
        if not result:
            raise KanboardAPIError(
                f"Failed to update user {id}",
                method="updateUser",
            )
        return True

    def remove_user(self, user_id: int) -> bool:
        """Remove a user.

        Maps to the Kanboard ``removeUser`` JSON-RPC method.

        Args:
            user_id: Unique integer ID of the user to remove.

        Returns:
            ``True`` when the user was removed, ``False`` otherwise.
        """
        result = self._client.call("removeUser", user_id=user_id)
        return bool(result)

    def disable_user(self, user_id: int) -> bool:
        """Disable a user account.

        Maps to the Kanboard ``disableUser`` JSON-RPC method.

        Args:
            user_id: Unique integer ID of the user to disable.

        Returns:
            ``True`` when the user was disabled, ``False`` otherwise.
        """
        result = self._client.call("disableUser", user_id=user_id)
        return bool(result)

    def enable_user(self, user_id: int) -> bool:
        """Enable a previously disabled user account.

        Maps to the Kanboard ``enableUser`` JSON-RPC method.

        Args:
            user_id: Unique integer ID of the user to enable.

        Returns:
            ``True`` when the user was enabled, ``False`` otherwise.
        """
        result = self._client.call("enableUser", user_id=user_id)
        return bool(result)

    def is_active_user(self, user_id: int) -> bool:
        """Check whether a user account is active.

        Maps to the Kanboard ``isActiveUser`` JSON-RPC method.

        Args:
            user_id: Unique integer ID of the user to check.

        Returns:
            ``True`` when the user is active, ``False`` otherwise.
        """
        result = self._client.call("isActiveUser", user_id=user_id)
        return bool(result)
