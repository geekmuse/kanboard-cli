"""External task links resource module - external URL link management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import ExternalTaskLink

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ExternalTaskLinksResource:
    """Kanboard External Task Links API resource.

    Exposes all seven external-task-link JSON-RPC methods as typed Python
    methods.  External task links associate a task with an external URL
    (e.g. a GitHub issue, a document, or a web page).

    Accessed via ``KanboardClient.external_task_links``.

    Example:
        >>> link_id = client.external_task_links.create_external_task_link(
        ...     task_id=10, url="https://github.com/org/repo/issues/1",
        ...     dependency="related",
        ... )
        >>> links = client.external_task_links.get_all_external_task_links(task_id=10)
        >>> for el in links:
        ...     print(el.id, el.url)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_external_task_link_types(self) -> dict:
        """Fetch all registered external link provider types.

        Maps to the Kanboard ``getExternalTaskLinkTypes`` JSON-RPC method.

        Returns:
            A dict mapping provider names to their display labels.
        """
        result = self._client.call("getExternalTaskLinkTypes")
        if not result:
            return {}
        return dict(result)

    def get_external_task_link_provider_dependencies(
        self,
        provider_name: str,
    ) -> dict:
        """Fetch the dependency types for a given external link provider.

        Maps to the Kanboard ``getExternalTaskLinkProviderDependencies``
        JSON-RPC method.

        Args:
            provider_name: Name of the external link provider
                (e.g. ``"weblink"``).

        Returns:
            A dict mapping dependency identifiers to their display labels.
        """
        result = self._client.call(
            "getExternalTaskLinkProviderDependencies",
            providerName=provider_name,
        )
        if not result:
            return {}
        return dict(result)

    def create_external_task_link(
        self,
        task_id: int,
        url: str,
        dependency: str,
        **kwargs: object,
    ) -> int:
        """Create an external link on a task.

        Maps to the Kanboard ``createExternalTaskLink`` JSON-RPC method.

        Args:
            task_id: ID of the task to link.
            url: The external URL.
            dependency: Dependency type (e.g. ``"related"``).
            **kwargs: Optional parameters such as ``type`` or ``title``.

        Returns:
            The integer ID of the newly created external task link.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating
                creation failed.
        """
        result = self._client.call(
            "createExternalTaskLink",
            task_id=task_id,
            url=url,
            dependency=dependency,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create external task link on task {task_id}",
                method="createExternalTaskLink",
            )
        return int(result)

    def update_external_task_link(
        self,
        task_id: int,
        link_id: int,
        title: str,
        url: str,
        **kwargs: object,
    ) -> bool:
        """Update an existing external task link.

        Maps to the Kanboard ``updateExternalTaskLink`` JSON-RPC method.

        Args:
            task_id: ID of the task owning the link.
            link_id: ID of the external link to update.
            title: New title for the link.
            url: New URL for the link.
            **kwargs: Optional parameters such as ``dependency``.

        Returns:
            ``True`` when the link was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                update failed.
        """
        result = self._client.call(
            "updateExternalTaskLink",
            task_id=task_id,
            link_id=link_id,
            title=title,
            url=url,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to update external task link {link_id} on task {task_id}",
                method="updateExternalTaskLink",
            )
        return True

    def get_external_task_link_by_id(
        self,
        task_id: int,
        link_id: int,
    ) -> ExternalTaskLink:
        """Fetch a single external task link by its ID.

        Maps to the Kanboard ``getExternalTaskLinkById`` JSON-RPC method.

        Args:
            task_id: ID of the task owning the link.
            link_id: ID of the external link.

        Returns:
            An :class:`~kanboard.models.ExternalTaskLink` instance.

        Raises:
            KanboardNotFoundError: The API returned ``False`` or ``None`` -
                no external link with the given ID exists.
        """
        result = self._client.call(
            "getExternalTaskLinkById",
            task_id=task_id,
            link_id=link_id,
        )
        if not result:
            raise KanboardNotFoundError(
                f"ExternalTaskLink {link_id} not found on task {task_id}",
                resource="ExternalTaskLink",
                identifier=link_id,
            )
        return ExternalTaskLink.from_api(result)

    def get_all_external_task_links(self, task_id: int) -> list[ExternalTaskLink]:
        """Fetch all external links for a given task.

        Maps to the Kanboard ``getAllExternalTaskLinks`` JSON-RPC method.

        Args:
            task_id: ID of the task whose external links to retrieve.

        Returns:
            A list of :class:`~kanboard.models.ExternalTaskLink` instances.
            Returns an empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllExternalTaskLinks", task_id=task_id)
        if not result:
            return []
        return [ExternalTaskLink.from_api(item) for item in result]

    def remove_external_task_link(self, task_id: int, link_id: int) -> bool:
        """Remove an external task link.

        Maps to the Kanboard ``removeExternalTaskLink`` JSON-RPC method.

        Args:
            task_id: ID of the task owning the link.
            link_id: ID of the external link to remove.

        Returns:
            ``True`` when the link was removed, ``False`` otherwise.
        """
        result = self._client.call(
            "removeExternalTaskLink",
            task_id=task_id,
            link_id=link_id,
        )
        return bool(result)
