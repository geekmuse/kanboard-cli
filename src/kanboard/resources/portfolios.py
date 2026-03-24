"""Portfolios resource module — CRUD and project management for Kanboard Portfolio plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import PluginPortfolio

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class PortfoliosResource:
    """Kanboard Portfolio plugin API resource.

    Exposes all portfolio-related JSON-RPC methods as typed Python methods.
    Requires the ``kanboard-plugin-portfolio-management`` plugin to be installed
    on the Kanboard server.

    Accessed via ``KanboardClient.portfolios``.

    Example:
        >>> pid = client.portfolios.create_portfolio("Q1 Projects")
        >>> portfolio = client.portfolios.get_portfolio(pid)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    # ------------------------------------------------------------------
    # Create / Read
    # ------------------------------------------------------------------

    def create_portfolio(self, name: str, **kwargs: Any) -> int:
        """Create a new portfolio.

        Maps to the plugin ``createPortfolio`` JSON-RPC method.

        Args:
            name: Portfolio name.
            **kwargs: Optional fields accepted by ``createPortfolio``:
                ``description``, ``owner_id``, ``is_active``.

        Returns:
            The integer ID of the newly created portfolio.

        Raises:
            KanboardAPIError: The API returned ``False`` (portfolio creation failed).
        """
        result = self._client.call("createPortfolio", name=name, **kwargs)
        if result is False or result == 0:
            raise KanboardAPIError(
                "createPortfolio returned False — portfolio creation failed",
                method="createPortfolio",
                code=None,
            )
        return int(result)

    def get_portfolio(self, portfolio_id: int) -> PluginPortfolio:
        """Fetch a single portfolio by its numeric ID.

        Maps to the plugin ``getPortfolio`` JSON-RPC method.

        Args:
            portfolio_id: Unique integer ID of the portfolio.

        Returns:
            A :class:`~kanboard.models.PluginPortfolio` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` (portfolio not found).
        """
        result = self._client.call("getPortfolio", portfolio_id=portfolio_id)
        if result is None:
            raise KanboardNotFoundError(
                "Portfolio not found",
                method="getPortfolio",
                code=None,
                resource="PluginPortfolio",
                identifier=str(portfolio_id),
            )
        return PluginPortfolio.from_api(result)

    def get_portfolio_by_name(self, name: str) -> PluginPortfolio:
        """Fetch a portfolio by its name.

        Maps to the plugin ``getPortfolioByName`` JSON-RPC method.

        Args:
            name: The portfolio name to look up.

        Returns:
            A :class:`~kanboard.models.PluginPortfolio` instance.

        Raises:
            KanboardNotFoundError: The API returned ``None`` or ``False``
                (portfolio not found).
        """
        result = self._client.call("getPortfolioByName", name=name)
        if result is None or result is False:
            raise KanboardNotFoundError(
                "Portfolio not found by name",
                method="getPortfolioByName",
                code=None,
                resource="PluginPortfolio",
                identifier=name,
            )
        return PluginPortfolio.from_api(result)

    def get_all_portfolios(self) -> list[PluginPortfolio]:
        """Fetch all portfolios accessible to the authenticated user.

        Maps to the plugin ``getAllPortfolios`` JSON-RPC method.

        Returns:
            A list of :class:`~kanboard.models.PluginPortfolio` instances;
            returns an empty list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getAllPortfolios")
        if not result:
            return []
        return [PluginPortfolio.from_api(p) for p in result]

    # ------------------------------------------------------------------
    # Update / Delete
    # ------------------------------------------------------------------

    def update_portfolio(self, portfolio_id: int, **kwargs: Any) -> bool:
        """Update one or more fields on an existing portfolio.

        Maps to the plugin ``updatePortfolio`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to update.
            **kwargs: Portfolio fields to update: ``name``, ``description``,
                ``owner_id``, ``is_active``.

        Returns:
            ``True`` on success.

        Raises:
            KanboardAPIError: The API returned ``False`` (update failed).
        """
        result = self._client.call("updatePortfolio", portfolio_id=portfolio_id, **kwargs)
        if result is False:
            raise KanboardAPIError(
                "updatePortfolio returned False — portfolio update failed",
                method="updatePortfolio",
                code=None,
            )
        return bool(result)

    def remove_portfolio(self, portfolio_id: int) -> bool:
        """Permanently delete a portfolio.

        Maps to the plugin ``removePortfolio`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to delete.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call("removePortfolio", portfolio_id=portfolio_id)
        return bool(result)

    # ------------------------------------------------------------------
    # Project membership
    # ------------------------------------------------------------------

    def add_project_to_portfolio(self, portfolio_id: int, project_id: int, **kwargs: Any) -> bool:
        """Add a project to a portfolio.

        Maps to the plugin ``addProjectToPortfolio`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio.
            project_id: ID of the project to add.
            **kwargs: Optional fields accepted by ``addProjectToPortfolio``.

        Returns:
            ``True`` on success.

        Raises:
            KanboardAPIError: The API returned ``False`` (operation failed).
        """
        result = self._client.call(
            "addProjectToPortfolio",
            portfolio_id=portfolio_id,
            project_id=project_id,
            **kwargs,
        )
        if result is False:
            raise KanboardAPIError(
                "addProjectToPortfolio returned False — operation failed",
                method="addProjectToPortfolio",
                code=None,
            )
        return bool(result)

    def remove_project_from_portfolio(self, portfolio_id: int, project_id: int) -> bool:
        """Remove a project from a portfolio.

        Maps to the plugin ``removeProjectFromPortfolio`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio.
            project_id: ID of the project to remove.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        result = self._client.call(
            "removeProjectFromPortfolio",
            portfolio_id=portfolio_id,
            project_id=project_id,
        )
        return bool(result)

    def get_portfolio_projects(self, portfolio_id: int) -> list[dict[str, Any]]:
        """Fetch all projects belonging to a portfolio.

        Maps to the plugin ``getPortfolioProjects`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to query.

        Returns:
            A list of project data dicts; returns an empty list when the API
            responds with ``False`` or ``None``.
        """
        result = self._client.call("getPortfolioProjects", portfolio_id=portfolio_id)
        if not result:
            return []
        return list(result)

    def get_project_portfolios(self, project_id: int) -> list[PluginPortfolio]:
        """Fetch all portfolios that contain a given project.

        Maps to the plugin ``getProjectPortfolios`` JSON-RPC method.

        Args:
            project_id: ID of the project to look up.

        Returns:
            A list of :class:`~kanboard.models.PluginPortfolio` instances;
            returns an empty list when the API responds with ``False`` or ``None``.
        """
        result = self._client.call("getProjectPortfolios", project_id=project_id)
        if not result:
            return []
        return [PluginPortfolio.from_api(p) for p in result]

    # ------------------------------------------------------------------
    # Task queries
    # ------------------------------------------------------------------

    def get_portfolio_tasks(self, portfolio_id: int, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch all tasks belonging to a portfolio's projects.

        Maps to the plugin ``getPortfolioTasks`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to query.
            **kwargs: Optional filter fields accepted by ``getPortfolioTasks``.

        Returns:
            A list of task data dicts; returns an empty list when the API
            responds with ``False`` or ``None``.
        """
        result = self._client.call("getPortfolioTasks", portfolio_id=portfolio_id, **kwargs)
        if not result:
            return []
        return list(result)

    def get_portfolio_task_count(self, portfolio_id: int, **kwargs: Any) -> dict[str, Any]:
        """Fetch task count statistics for a portfolio.

        Maps to the plugin ``getPortfolioTaskCount`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to query.
            **kwargs: Optional filter fields accepted by ``getPortfolioTaskCount``.

        Returns:
            A dict with task count statistics (e.g. ``total``, ``open``,
            ``closed``).
        """
        result = self._client.call("getPortfolioTaskCount", portfolio_id=portfolio_id, **kwargs)
        return result or {}

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def get_portfolio_overview(self, portfolio_id: int) -> dict[str, Any]:
        """Fetch a full overview of a portfolio including projects and milestones.

        Maps to the plugin ``getPortfolioOverview`` JSON-RPC method.

        Args:
            portfolio_id: ID of the portfolio to query.

        Returns:
            A dict containing portfolio overview data (projects, milestones,
            task counts, progress).
        """
        result = self._client.call("getPortfolioOverview", portfolio_id=portfolio_id)
        return result or {}
