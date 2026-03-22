"""Tags resource module — tag management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError
from kanboard.models import Tag

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class TagsResource:
    """Kanboard Tags API resource.

    Exposes all seven tag-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.tags``.

    Example:
        >>> tags = client.tags.get_tags_by_project(1)
        >>> for tag in tags:
        ...     print(tag.name)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_all_tags(self) -> list[Tag]:
        """Fetch all tags across all projects.

        Maps to the Kanboard ``getAllTags`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.Tag` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllTags")
        if not result:
            return []
        return [Tag.from_api(item) for item in result]

    def get_tags_by_project(self, project_id: int) -> list[Tag]:
        """Fetch all tags for a specific project.

        Maps to the Kanboard ``getTagsByProject`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project whose tags to fetch.

        Returns:
            A list of :class:`~kanboard.models.Tag` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getTagsByProject", project_id=project_id)
        if not result:
            return []
        return [Tag.from_api(item) for item in result]

    def create_tag(self, project_id: int, tag: str, **kwargs: Any) -> int:
        """Create a new tag in a project.

        Maps to the Kanboard ``createTag`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project to add the tag to.
            tag: The display name for the new tag.
            **kwargs: Optional keyword arguments forwarded to the API (e.g. ``color_id``).

        Returns:
            The integer ID of the newly created tag.

        Raises:
            KanboardAPIError: The API returned ``False`` or ``0`` indicating creation failed.
        """
        result = self._client.call(
            "createTag",
            project_id=project_id,
            tag=tag,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create tag '{tag}' in project {project_id}",
                method="createTag",
            )
        return int(result)

    def update_tag(self, tag_id: int, tag: str, **kwargs: Any) -> bool:
        """Update an existing tag's name and optional fields.

        Maps to the Kanboard ``updateTag`` JSON-RPC method.

        Args:
            tag_id: Unique integer ID of the tag to update.
            tag: The new display name for the tag.
            **kwargs: Optional keyword arguments forwarded to the API (e.g. ``color_id``).

        Returns:
            ``True`` when the tag was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update failed.
        """
        result = self._client.call("updateTag", tag_id=tag_id, tag=tag, **kwargs)
        if not result:
            raise KanboardAPIError(
                f"Failed to update tag {tag_id}",
                method="updateTag",
            )
        return True

    def remove_tag(self, tag_id: int) -> bool:
        """Remove a tag.

        Maps to the Kanboard ``removeTag`` JSON-RPC method.

        Args:
            tag_id: Unique integer ID of the tag to remove.

        Returns:
            ``True`` when the tag was removed, ``False`` otherwise.
        """
        result = self._client.call("removeTag", tag_id=tag_id)
        return bool(result)

    def set_task_tags(
        self,
        project_id: int,
        task_id: int,
        tags: list[str],
    ) -> bool:
        """Assign a list of tags to a task.

        Maps to the Kanboard ``setTaskTags`` JSON-RPC method.  Replaces any
        existing tag assignments on the task with the supplied list.

        Args:
            project_id: Unique integer ID of the project containing the task.
            task_id: Unique integer ID of the task to tag.
            tags: List of tag name strings to assign to the task.

        Returns:
            ``True`` when tags were set successfully, ``False`` otherwise.
        """
        result = self._client.call(
            "setTaskTags",
            project_id=project_id,
            task_id=task_id,
            tags=tags,
        )
        return bool(result)

    def get_task_tags(self, task_id: int) -> dict:
        """Fetch all tags assigned to a task.

        Maps to the Kanboard ``getTaskTags`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task whose tags to fetch.

        Returns:
            A dict mapping tag ID strings to tag name strings.  Returns an
            empty dict when the API responds with a falsy value.
        """
        result = self._client.call("getTaskTags", task_id=task_id)
        if not result:
            return {}
        return dict(result)
