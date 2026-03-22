"""Portfolio manager — multi-project aggregation and milestone tracking."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kanboard.client import KanboardClient
    from kanboard.orchestration.store import LocalPortfolioStore


class PortfolioManager:
    """Aggregates task data across multiple Kanboard projects.

    Computes milestone progress and syncs portfolio/milestone membership to
    Kanboard task and project metadata using the ``kanboard_cli:`` key prefix
    convention.  Instantiated separately by callers — not wired into
    :class:`~kanboard.client.KanboardClient` as an attribute.

    Args:
        client: The :class:`~kanboard.client.KanboardClient` used to make API
            calls.
        store: The :class:`~kanboard.orchestration.store.LocalPortfolioStore`
            used to read portfolio/milestone configuration.

    Example:
        >>> manager = PortfolioManager(client, store)
        >>> tasks = manager.get_portfolio_tasks("my-portfolio")
    """

    def __init__(self, client: KanboardClient, store: LocalPortfolioStore) -> None:
        """Initialise with a client and a local portfolio store.

        Args:
            client: The Kanboard API client.
            store: The local portfolio store providing portfolio/milestone data.
        """
        self._client = client
        self._store = store
