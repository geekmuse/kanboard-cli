"""Backend abstraction layer for portfolio storage.

Provides:

- :class:`PortfolioBackend` — :mod:`typing` Protocol defining the 12-method
  interface shared by both backend implementations.
- :class:`RemotePortfolioBackend` — adapter wrapping
  :class:`~kanboard.resources.portfolios.PortfoliosResource` and
  :class:`~kanboard.resources.milestones.MilestonesResource`.
- :func:`create_backend` — factory returning the correct backend instance
  based on a *backend_type* string (``"local"`` or ``"remote"``).

Example::

    from kanboard import KanboardClient
    from kanboard.orchestration import create_backend

    # Local (file-backed) backend — default
    backend = create_backend("local")

    # Remote (plugin API) backend
    with KanboardClient(url, token) as client:
        backend = create_backend("remote", client=client)
        portfolios = backend.load()
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from kanboard.exceptions import KanboardConfigError
from kanboard.models import Milestone, Portfolio
from kanboard.orchestration.store import LocalPortfolioStore

if TYPE_CHECKING:
    from kanboard.client import KanboardClient
    from kanboard.models import PluginMilestone, PluginPortfolio
    from kanboard.resources.milestones import MilestonesResource
    from kanboard.resources.portfolios import PortfoliosResource


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PortfolioBackend(Protocol):
    """Protocol defining the 12-method interface for portfolio storage backends.

    Both :class:`~kanboard.orchestration.store.LocalPortfolioStore` and
    :class:`RemotePortfolioBackend` satisfy this protocol, enabling
    configuration-driven backend selection without code changes in callers.

    The interface uses name-based lookups (not numeric IDs) for all portfolio
    and milestone operations, matching the local store's API design.
    """

    def load(self) -> list[Portfolio]:
        """Return all portfolios accessible via this backend.

        Returns:
            A list of :class:`~kanboard.models.Portfolio` objects.
        """
        ...

    def create_portfolio(
        self,
        name: str,
        description: str = "",
        project_ids: list[int] | None = None,
    ) -> Portfolio:
        """Create a new portfolio and return it.

        Args:
            name: Unique portfolio name.
            description: Optional human-readable description.
            project_ids: Initial list of Kanboard project IDs.

        Returns:
            The newly created :class:`~kanboard.models.Portfolio`.
        """
        ...

    def get_portfolio(self, name: str) -> Portfolio:
        """Retrieve a portfolio by name.

        Args:
            name: The portfolio name to look up.

        Returns:
            The matching :class:`~kanboard.models.Portfolio`.
        """
        ...

    def update_portfolio(self, name: str, **kwargs: Any) -> Portfolio:
        """Update fields on a portfolio and return the updated model.

        Args:
            name: Name of the portfolio to update.
            **kwargs: Field names and new values to apply.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.
        """
        ...

    def remove_portfolio(self, name: str) -> bool:
        """Remove a portfolio from the backend.

        Args:
            name: Name of the portfolio to remove.

        Returns:
            ``True`` if the portfolio was removed, ``False`` if not found.
        """
        ...

    def add_project(self, portfolio_name: str, project_id: int) -> Portfolio:
        """Add a Kanboard project to a portfolio and return the updated portfolio.

        Args:
            portfolio_name: Name of the target portfolio.
            project_id: Kanboard project ID to add.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.
        """
        ...

    def remove_project(self, portfolio_name: str, project_id: int) -> Portfolio:
        """Remove a Kanboard project from a portfolio and return the updated portfolio.

        Args:
            portfolio_name: Name of the target portfolio.
            project_id: Kanboard project ID to remove.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.
        """
        ...

    def add_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        target_date: datetime | None = None,
    ) -> Milestone:
        """Add a milestone to a portfolio and return the new milestone.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Unique milestone name within the portfolio.
            target_date: Optional due date for the milestone.

        Returns:
            The newly created :class:`~kanboard.models.Milestone`.
        """
        ...

    def update_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        **kwargs: Any,
    ) -> Milestone:
        """Update fields on a milestone and return the updated model.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to update.
            **kwargs: Field names and new values to apply.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.
        """
        ...

    def remove_milestone(self, portfolio_name: str, milestone_name: str) -> bool:
        """Remove a milestone from a portfolio.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to remove.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        ...

    def add_task_to_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        task_id: int,
        critical: bool = False,
    ) -> Milestone:
        """Add a task to a milestone and return the updated milestone.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the target milestone.
            task_id: Kanboard task ID to add.
            critical: When ``True``, also mark *task_id* as critical.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.
        """
        ...

    def remove_task_from_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        task_id: int,
    ) -> Milestone:
        """Remove a task from a milestone and return the updated milestone.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the target milestone.
            task_id: Kanboard task ID to remove.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.
        """
        ...


# ---------------------------------------------------------------------------
# Remote backend
# ---------------------------------------------------------------------------


class RemotePortfolioBackend:
    """Portfolio backend backed by the Kanboard Portfolio Management plugin.

    Translates the name-based :class:`PortfolioBackend` interface into
    ID-based calls against :class:`~kanboard.resources.portfolios.PortfoliosResource`
    and :class:`~kanboard.resources.milestones.MilestonesResource`.

    Requires the ``kanboard-plugin-portfolio-management`` plugin to be installed
    on the Kanboard server.

    Args:
        client: An authenticated :class:`~kanboard.client.KanboardClient`.

    Example:
        >>> backend = RemotePortfolioBackend(client)
        >>> portfolios = backend.load()
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with an authenticated KanboardClient.

        Args:
            client: The KanboardClient providing access to the portfolio plugin.
        """
        self._client = client
        self._portfolios: PortfoliosResource = client.portfolios  # type: ignore[assignment]
        self._milestones: MilestonesResource = client.milestones  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_portfolio_id(self, portfolio_name: str) -> int:
        """Resolve a portfolio name to its numeric ID via the plugin API.

        Args:
            portfolio_name: Portfolio name to look up.

        Returns:
            The numeric portfolio ID.

        Raises:
            KanboardNotFoundError: The portfolio does not exist on the server.
        """
        plugin_portfolio = self._portfolios.get_portfolio_by_name(portfolio_name)
        return plugin_portfolio.id

    def _resolve_milestone_id(self, portfolio_id: int, milestone_name: str) -> int:
        """Find a milestone's numeric ID within a portfolio by name.

        Args:
            portfolio_id: Numeric portfolio ID.
            milestone_name: Milestone name to look up.

        Returns:
            The numeric milestone ID.

        Raises:
            KanboardConfigError: No milestone with *milestone_name* found in
                the portfolio.
        """
        milestones = self._milestones.get_portfolio_milestones(portfolio_id)
        for m in milestones:
            if m.name == milestone_name:
                return m.id
        raise KanboardConfigError(
            f"Milestone '{milestone_name}' not found in portfolio {portfolio_id}"
        )

    def _to_milestone(self, plugin_milestone: PluginMilestone, portfolio_name: str) -> Milestone:
        """Convert a PluginMilestone to a local Milestone, fetching its task IDs.

        Args:
            plugin_milestone: Server-side milestone from the plugin API.
            portfolio_name: Name of the parent portfolio.

        Returns:
            A :class:`~kanboard.models.Milestone` with ``task_ids`` populated.
        """
        tasks = self._milestones.get_milestone_tasks(plugin_milestone.id)
        task_ids = [int(t["id"]) for t in tasks if t.get("id")]
        return Milestone(
            name=plugin_milestone.name,
            portfolio_name=portfolio_name,
            target_date=plugin_milestone.target_date,
            task_ids=task_ids,
        )

    def _build_portfolio(self, plugin_portfolio: PluginPortfolio) -> Portfolio:
        """Build a full Portfolio from a PluginPortfolio, fetching projects and milestones.

        Makes two additional API calls per portfolio to populate ``project_ids``
        and ``milestones``.

        Args:
            plugin_portfolio: Server-side portfolio from the plugin API.

        Returns:
            A fully-populated :class:`~kanboard.models.Portfolio`.
        """
        projects = self._portfolios.get_portfolio_projects(plugin_portfolio.id)
        project_ids = [int(p["id"]) for p in projects if p.get("id")]

        plugin_milestones = self._milestones.get_portfolio_milestones(plugin_portfolio.id)
        milestones = [self._to_milestone(m, plugin_portfolio.name) for m in plugin_milestones]

        return Portfolio(
            name=plugin_portfolio.name,
            description=plugin_portfolio.description,
            project_ids=project_ids,
            milestones=milestones,
            created_at=plugin_portfolio.created_at,
            updated_at=plugin_portfolio.updated_at,
        )

    # ------------------------------------------------------------------
    # PortfolioBackend interface — portfolio CRUD
    # ------------------------------------------------------------------

    def load(self) -> list[Portfolio]:
        """Return all portfolios from the plugin API.

        Returns:
            A list of fully-populated :class:`~kanboard.models.Portfolio` objects.
        """
        plugin_portfolios = self._portfolios.get_all_portfolios()
        return [self._build_portfolio(p) for p in plugin_portfolios]

    def create_portfolio(
        self,
        name: str,
        description: str = "",
        project_ids: list[int] | None = None,
    ) -> Portfolio:
        """Create a portfolio via the plugin API and return it.

        Creates the portfolio, optionally adds initial projects, then returns
        the fully-populated portfolio model.

        Args:
            name: Portfolio name.
            description: Optional description.
            project_ids: Optional initial list of project IDs to add.

        Returns:
            The newly created :class:`~kanboard.models.Portfolio`.
        """
        portfolio_id = self._portfolios.create_portfolio(name, description=description)
        for project_id in project_ids or []:
            self._portfolios.add_project_to_portfolio(portfolio_id, project_id)
        plugin_portfolio = self._portfolios.get_portfolio(portfolio_id)
        return self._build_portfolio(plugin_portfolio)

    def get_portfolio(self, name: str) -> Portfolio:
        """Fetch a portfolio by name via the plugin API.

        Args:
            name: The portfolio name to look up.

        Returns:
            The fully-populated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardNotFoundError: No portfolio with *name* exists on the server.
        """
        plugin_portfolio = self._portfolios.get_portfolio_by_name(name)
        return self._build_portfolio(plugin_portfolio)

    def update_portfolio(self, name: str, **kwargs: Any) -> Portfolio:
        """Update fields on a portfolio and return the updated model.

        Args:
            name: Name of the portfolio to update.
            **kwargs: Fields to update (e.g. ``description``, ``is_active``).

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardNotFoundError: No portfolio with *name* exists on the server.
        """
        portfolio_id = self._resolve_portfolio_id(name)
        self._portfolios.update_portfolio(portfolio_id, **kwargs)
        plugin_portfolio = self._portfolios.get_portfolio(portfolio_id)
        return self._build_portfolio(plugin_portfolio)

    def remove_portfolio(self, name: str) -> bool:
        """Remove a portfolio via the plugin API.

        Args:
            name: Name of the portfolio to remove.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        try:
            portfolio_id = self._resolve_portfolio_id(name)
        except Exception:
            return False
        return self._portfolios.remove_portfolio(portfolio_id)

    # ------------------------------------------------------------------
    # PortfolioBackend interface — project membership
    # ------------------------------------------------------------------

    def add_project(self, portfolio_name: str, project_id: int) -> Portfolio:
        """Add a project to a portfolio and return the updated portfolio.

        Args:
            portfolio_name: Name of the target portfolio.
            project_id: Kanboard project ID to add.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        self._portfolios.add_project_to_portfolio(portfolio_id, project_id)
        plugin_portfolio = self._portfolios.get_portfolio(portfolio_id)
        return self._build_portfolio(plugin_portfolio)

    def remove_project(self, portfolio_name: str, project_id: int) -> Portfolio:
        """Remove a project from a portfolio and return the updated portfolio.

        Args:
            portfolio_name: Name of the target portfolio.
            project_id: Kanboard project ID to remove.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        self._portfolios.remove_project_from_portfolio(portfolio_id, project_id)
        plugin_portfolio = self._portfolios.get_portfolio(portfolio_id)
        return self._build_portfolio(plugin_portfolio)

    # ------------------------------------------------------------------
    # PortfolioBackend interface — milestone CRUD
    # ------------------------------------------------------------------

    def add_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        target_date: datetime | None = None,
    ) -> Milestone:
        """Create a milestone in a portfolio and return it.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the new milestone.
            target_date: Optional target completion date.

        Returns:
            The newly created :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        kwargs: dict[str, Any] = {}
        if target_date is not None:
            kwargs["target_date"] = target_date
        milestone_id = self._milestones.create_milestone(portfolio_id, milestone_name, **kwargs)
        plugin_milestone = self._milestones.get_milestone(milestone_id)
        return self._to_milestone(plugin_milestone, portfolio_name)

    def update_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        **kwargs: Any,
    ) -> Milestone:
        """Update fields on a milestone and return the updated model.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to update.
            **kwargs: Fields to update (e.g. ``target_date``, ``status``).

        Returns:
            The updated :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
            KanboardConfigError: No milestone with *milestone_name* in the
                portfolio.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        milestone_id = self._resolve_milestone_id(portfolio_id, milestone_name)
        self._milestones.update_milestone(milestone_id, **kwargs)
        plugin_milestone = self._milestones.get_milestone(milestone_id)
        return self._to_milestone(plugin_milestone, portfolio_name)

    def remove_milestone(self, portfolio_name: str, milestone_name: str) -> bool:
        """Remove a milestone from a portfolio.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to remove.

        Returns:
            ``True`` if the milestone was removed, ``False`` if not found.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        try:
            milestone_id = self._resolve_milestone_id(portfolio_id, milestone_name)
        except KanboardConfigError:
            return False
        return self._milestones.remove_milestone(milestone_id)

    # ------------------------------------------------------------------
    # PortfolioBackend interface — milestone task membership
    # ------------------------------------------------------------------

    def add_task_to_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        task_id: int,
        critical: bool = False,
    ) -> Milestone:
        """Add a task to a milestone and return the updated milestone.

        The plugin API does not natively support a ``critical`` flag;
        *critical* is accepted for protocol compatibility but is not forwarded
        to the server.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the target milestone.
            task_id: Kanboard task ID to add.
            critical: Accepted for interface compatibility; ignored server-side.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
            KanboardConfigError: No milestone with *milestone_name* in the
                portfolio.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        milestone_id = self._resolve_milestone_id(portfolio_id, milestone_name)
        self._milestones.add_task_to_milestone(milestone_id, task_id)
        plugin_milestone = self._milestones.get_milestone(milestone_id)
        return self._to_milestone(plugin_milestone, portfolio_name)

    def remove_task_from_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        task_id: int,
    ) -> Milestone:
        """Remove a task from a milestone and return the updated milestone.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the target milestone.
            task_id: Kanboard task ID to remove.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardNotFoundError: No portfolio with *portfolio_name* exists.
            KanboardConfigError: No milestone with *milestone_name* in the
                portfolio.
        """
        portfolio_id = self._resolve_portfolio_id(portfolio_name)
        milestone_id = self._resolve_milestone_id(portfolio_id, milestone_name)
        self._milestones.remove_task_from_milestone(milestone_id, task_id)
        plugin_milestone = self._milestones.get_milestone(milestone_id)
        return self._to_milestone(plugin_milestone, portfolio_name)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_backend(
    backend_type: str,
    *,
    client: KanboardClient | None = None,
    path: Path | None = None,
) -> PortfolioBackend:
    """Create and return the appropriate portfolio backend.

    Args:
        backend_type: One of ``"local"`` or ``"remote"``.
        client: Required when *backend_type* is ``"remote"``. An authenticated
            :class:`~kanboard.client.KanboardClient`.
        path: Optional override for the local store file path. Only used when
            *backend_type* is ``"local"``.

    Returns:
        A :class:`PortfolioBackend`-compatible instance.

    Raises:
        KanboardConfigError: *backend_type* is ``"remote"`` and no *client*
            was provided, or *backend_type* is not one of the supported values.

    Example:
        >>> backend = create_backend("local")
        >>> with KanboardClient(url, token) as client:
        ...     backend = create_backend("remote", client=client)
    """
    if backend_type == "local":
        return LocalPortfolioStore(path=path)
    if backend_type == "remote":
        if client is None:
            raise KanboardConfigError(
                "create_backend requires client= for backend_type='remote'. "
                "Pass an authenticated KanboardClient or use backend_type='local'.",
                field="portfolio_backend",
            )
        return RemotePortfolioBackend(client)
    raise KanboardConfigError(
        f"Unknown portfolio_backend '{backend_type}'. Choose 'local' or 'remote'.",
        field="portfolio_backend",
    )
