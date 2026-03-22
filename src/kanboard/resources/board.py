"""Board resource module — board layout retrieval for Kanboard projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class BoardResource:
    """Kanboard Board API resource.

    Exposes the board-related JSON-RPC method as a typed Python method.
    Accessed via ``KanboardClient.board``.

    The board response from Kanboard is a complex nested structure:
    a list of columns, each containing swimlanes and tasks.  Rather than
    modelling this deeply-nested hierarchy with dataclasses, the raw list
    of dicts is returned to the caller unchanged.

    Example:
        >>> columns = client.board.get_board(1)
        >>> for column in columns:
        ...     print(column["title"])
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def get_board(self, project_id: int) -> list[dict[str, Any]]:
        """Fetch the full board layout for a project.

        Maps to the Kanboard ``getBoard`` JSON-RPC method.

        The returned list contains one dict per column, where each column
        dict includes its swimlanes and the tasks within each swimlane.

        Args:
            project_id: Unique integer ID of the project whose board to fetch.

        Returns:
            A list of column dicts representing the board layout.  Returns an
            empty list when the API responds with a falsy value (``False``,
            ``None``, or an empty collection).
        """
        result = self._client.call("getBoard", project_id=project_id)
        if not result:
            return []
        return list(result)
