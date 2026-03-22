"""Links resource module — link-type management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Link

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class LinksResource:
    """Kanboard Links API resource.

    Exposes all seven link-type JSON-RPC methods as typed Python methods.
    Link *types* define the relationship labels between two tasks
    (e.g. "blocks", "is blocked by").  Use
    :class:`~kanboard.resources.task_links.TaskLinksResource` to create
    actual task-to-task associations.

    Accessed via ``KanboardClient.links``.

    Example:
        >>> links = client.links.get_all_links()
        >>> for link in links:
        ...     print(link.id, link.label)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_all_links(self) -> list[Link]:
        """Fetch all link type definitions.

        Maps to the Kanboard ``getAllLinks`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.Link` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllLinks")
        if not result:
            return []
        return [Link.from_api(item) for item in result]

    def get_opposite_link_id(self, link_id: int) -> int:
        """Fetch the opposite link ID for a given link type.

        Maps to the Kanboard ``getOppositeLinkId`` JSON-RPC method.

        Args:
            link_id: Unique integer ID of the link type.

        Returns:
            The integer ID of the opposite link type.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                the operation failed.
        """
        result = self._client.call("getOppositeLinkId", link_id=link_id)
        if not result:
            raise KanboardAPIError(
                f"Failed to get opposite link ID for link {link_id}",
                method="getOppositeLinkId",
            )
        return int(result)

    def get_link_by_label(self, label: str) -> Link:
        """Fetch a link type by its label.

        Maps to the Kanboard ``getLinkByLabel`` JSON-RPC method.

        Args:
            label: The label string of the link type to retrieve.

        Returns:
            A :class:`~kanboard.models.Link` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` —
                no link type with the given label exists.
        """
        result = self._client.call("getLinkByLabel", label=label)
        if not result:
            raise KanboardNotFoundError(
                f"Link with label '{label}' not found",
                resource="Link",
                identifier=label,
            )
        return Link.from_api(result)

    def get_link_by_id(self, link_id: int) -> Link:
        """Fetch a link type by its ID.

        Maps to the Kanboard ``getLinkById`` JSON-RPC method.

        Args:
            link_id: Unique integer ID of the link type.

        Returns:
            A :class:`~kanboard.models.Link` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` —
                no link type with the given ID exists.
        """
        result = self._client.call("getLinkById", link_id=link_id)
        if not result:
            raise KanboardNotFoundError(
                f"Link {link_id} not found",
                resource="Link",
                identifier=link_id,
            )
        return Link.from_api(result)

    def create_link(self, label: str, **kwargs: Any) -> int:
        """Create a new link type definition.

        Maps to the Kanboard ``createLink`` JSON-RPC method.

        Args:
            label: The label for the new link type (e.g. ``"blocks"``).
            **kwargs: Optional keyword arguments forwarded to the API (e.g.
                ``opposite_label``).

        Returns:
            The integer ID of the newly created link type.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call("createLink", label=label, **kwargs)
        if not result:
            raise KanboardAPIError(
                f"Failed to create link '{label}'",
                method="createLink",
            )
        return int(result)

    def update_link(self, link_id: int, opposite_link_id: int, label: str) -> bool:
        """Update an existing link type definition.

        Maps to the Kanboard ``updateLink`` JSON-RPC method.

        Args:
            link_id: Unique integer ID of the link type to update.
            opposite_link_id: ID of the opposite link type.
            label: New label for the link type.

        Returns:
            ``True`` when the link type was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update
                failed.
        """
        result = self._client.call(
            "updateLink",
            link_id=link_id,
            opposite_link_id=opposite_link_id,
            label=label,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to update link {link_id}",
                method="updateLink",
            )
        return True

    def remove_link(self, link_id: int) -> bool:
        """Remove a link type definition.

        Maps to the Kanboard ``removeLink`` JSON-RPC method.

        Args:
            link_id: Unique integer ID of the link type to remove.

        Returns:
            ``True`` when the link type was removed, ``False`` otherwise.
        """
        result = self._client.call("removeLink", link_id=link_id)
        return bool(result)
