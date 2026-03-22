"""Columns resource module — board column management for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Column

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class ColumnsResource:
    """Kanboard Columns API resource.

    Exposes the six column-related JSON-RPC methods as typed Python methods.
    Accessed via ``KanboardClient.columns``.

    Example:
        >>> columns = client.columns.get_columns(1)
        >>> for col in columns:
        ...     print(col.title)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_columns(self, project_id: int) -> list[Column]:
        """Fetch all columns for a project.

        Maps to the Kanboard ``getColumns`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project whose columns to fetch.

        Returns:
            A list of :class:`~kanboard.models.Column` instances.  Returns an
            empty list when the API responds with a falsy value.
        """
        result = self._client.call("getColumns", project_id=project_id)
        if not result:
            return []
        return [Column.from_api(item) for item in result]

    def get_column(self, column_id: int) -> Column:
        """Fetch a single column by its ID.

        Maps to the Kanboard ``getColumn`` JSON-RPC method.

        Args:
            column_id: Unique integer ID of the column to fetch.

        Returns:
            A :class:`~kanboard.models.Column` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` — column does not exist.
        """
        result = self._client.call("getColumn", column_id=column_id)
        if result is None:
            raise KanboardNotFoundError(
                f"Column {column_id} not found",
                resource="Column",
                identifier=column_id,
            )
        return Column.from_api(result)

    def change_column_position(
        self,
        project_id: int,
        column_id: int,
        position: int,
    ) -> bool:
        """Move a column to a new position within the board.

        Maps to the Kanboard ``changeColumnPosition`` JSON-RPC method.

        Args:
            project_id: Unique integer ID of the project the column belongs to.
            column_id: Unique integer ID of the column to move.
            position: The new 1-based position for the column.

        Returns:
            ``True`` when the position was updated successfully.
        """
        result = self._client.call(
            "changeColumnPosition",
            project_id=project_id,
            column_id=column_id,
            position=position,
        )
        return bool(result)

    def update_column(
        self,
        column_id: int,
        title: str,
        **kwargs: Any,
    ) -> bool:
        """Update a column's title and optional attributes.

        Maps to the Kanboard ``updateColumn`` JSON-RPC method.

        Supported ``kwargs``:
            - ``task_limit`` (int): Maximum number of tasks allowed in the column.
            - ``description`` (str): Column description.

        Args:
            column_id: Unique integer ID of the column to update.
            title: New title for the column.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            ``True`` when the column was updated successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the update failed.
        """
        result = self._client.call(
            "updateColumn",
            column_id=column_id,
            title=title,
            **kwargs,
        )
        if result is False:
            raise KanboardAPIError(
                f"Failed to update column {column_id}",
                method="updateColumn",
            )
        return bool(result)

    def add_column(
        self,
        project_id: int,
        title: str,
        **kwargs: Any,
    ) -> int:
        """Add a new column to a project board.

        Maps to the Kanboard ``addColumn`` JSON-RPC method.

        Supported ``kwargs``:
            - ``task_limit`` (int): Maximum number of tasks allowed in the column.
            - ``description`` (str): Column description.

        Args:
            project_id: Unique integer ID of the project to add the column to.
            title: Title for the new column.
            **kwargs: Optional keyword arguments forwarded to the API.

        Returns:
            The integer ID of the newly created column.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating creation failed.
        """
        result = self._client.call(
            "addColumn",
            project_id=project_id,
            title=title,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to add column '{title}' to project {project_id}",
                method="addColumn",
            )
        return int(result)

    def remove_column(self, column_id: int) -> bool:
        """Remove a column from the board.

        Maps to the Kanboard ``removeColumn`` JSON-RPC method.

        Args:
            column_id: Unique integer ID of the column to remove.

        Returns:
            ``True`` when the column was removed, ``False`` otherwise.
        """
        result = self._client.call("removeColumn", column_id=column_id)
        return bool(result)
