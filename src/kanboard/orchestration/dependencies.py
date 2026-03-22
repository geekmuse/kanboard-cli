"""Dependency analyzer — graph traversal and critical-path computation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class DependencyAnalyzer:
    """Builds directed dependency graphs from Kanboard task links.

    Uses topological sort (Kahn's algorithm) for critical-path computation.
    Caches fetched tasks to avoid redundant API calls and deduplicates
    bidirectional edges.  Instantiated separately by callers — not wired into
    :class:`~kanboard.client.KanboardClient` as an attribute.

    Args:
        client: The :class:`~kanboard.client.KanboardClient` used to fetch
            task links and task data.

    Example:
        >>> analyzer = DependencyAnalyzer(client)
        >>> edges = analyzer.get_dependency_edges(tasks)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a Kanboard API client.

        Args:
            client: The Kanboard API client used to fetch task links and tasks.
        """
        self._client = client
