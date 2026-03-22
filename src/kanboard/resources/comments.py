"""Comments resource module — task comment management for Kanboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Comment

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class CommentsResource:
    """Kanboard Comments API resource.

    Exposes all five comment-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.comments``.

    Example:
        >>> comments = client.comments.get_all_comments(42)
        >>> for c in comments:
        ...     print(c.comment)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def create_comment(
        self,
        task_id: int,
        user_id: int,
        content: str,
        **kwargs: Any,
    ) -> int:
        """Create a new comment on a task.

        Maps to the Kanboard ``createComment`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task to comment on.
            user_id: Unique integer ID of the user creating the comment.
            content: The comment text body.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            The integer ID of the newly created comment.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating creation failed.
        """
        result = self._client.call(
            "createComment",
            task_id=task_id,
            user_id=user_id,
            content=content,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to create comment on task {task_id}",
                method="createComment",
            )
        return int(result)

    def get_comment(self, comment_id: int) -> Comment:
        """Fetch a single comment by its ID.

        Maps to the Kanboard ``getComment`` JSON-RPC method.

        Args:
            comment_id: Unique integer ID of the comment to fetch.

        Returns:
            A :class:`~kanboard.models.Comment` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — comment does not exist.
        """
        result = self._client.call("getComment", comment_id=comment_id)
        if result is None:
            raise KanboardNotFoundError(
                f"Comment {comment_id} not found",
                resource="Comment",
                identifier=comment_id,
            )
        return Comment.from_api(result)

    def get_all_comments(self, task_id: int) -> list[Comment]:
        """Fetch all comments for a task.

        Maps to the Kanboard ``getAllComments`` JSON-RPC method.

        Args:
            task_id: Unique integer ID of the task whose comments to fetch.

        Returns:
            A list of :class:`~kanboard.models.Comment` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getAllComments", task_id=task_id)
        if not result:
            return []
        return [Comment.from_api(item) for item in result]

    def update_comment(self, id: int, content: str) -> bool:
        """Update the text content of an existing comment.

        Maps to the Kanboard ``updateComment`` JSON-RPC method.

        Args:
            id: Unique integer ID of the comment to update.
            content: The new comment text.

        Returns:
            ``True`` when the comment was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update failed.
        """
        result = self._client.call("updateComment", id=id, content=content)
        if not result:
            raise KanboardAPIError(
                f"Failed to update comment {id}",
                method="updateComment",
            )
        return True

    def remove_comment(self, comment_id: int) -> bool:
        """Remove a comment from a task.

        Maps to the Kanboard ``removeComment`` JSON-RPC method.

        Args:
            comment_id: Unique integer ID of the comment to remove.

        Returns:
            ``True`` when the comment was removed, ``False`` otherwise.
        """
        result = self._client.call("removeComment", comment_id=comment_id)
        return bool(result)
