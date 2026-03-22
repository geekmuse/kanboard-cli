"""Local portfolio store — JSON persistence for portfolios and milestones."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from kanboard.exceptions import KanboardConfigError
from kanboard.models import Milestone, Portfolio

_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _dt_to_str(value: datetime | None) -> str | None:
    """Serialise a :class:`~datetime.datetime` to an ISO-8601 string.

    Args:
        value: A datetime object, or ``None``.

    Returns:
        ISO-8601 string (e.g. ``"2026-03-22T18:00:00"``), or ``None``.
    """
    if value is None:
        return None
    return value.isoformat()


def _str_to_dt(value: str | None) -> datetime | None:
    """Deserialise an ISO-8601 string to a :class:`~datetime.datetime`.

    Args:
        value: An ISO-8601 string, or ``None``.

    Returns:
        A :class:`~datetime.datetime`, or ``None`` when *value* is ``None``.
    """
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _milestone_to_dict(m: Milestone) -> dict[str, Any]:
    """Convert a :class:`~kanboard.models.Milestone` to a JSON-serialisable dict.

    Args:
        m: The milestone to serialise.

    Returns:
        A dictionary suitable for :func:`json.dump`.
    """
    return {
        "name": m.name,
        "portfolio_name": m.portfolio_name,
        "target_date": _dt_to_str(m.target_date),
        "task_ids": list(m.task_ids),
        "critical_task_ids": list(m.critical_task_ids),
    }


def _milestone_from_dict(d: dict[str, Any]) -> Milestone:
    """Construct a :class:`~kanboard.models.Milestone` from a raw dict.

    Args:
        d: A dictionary as read from the JSON store.

    Returns:
        A populated :class:`~kanboard.models.Milestone`.
    """
    return Milestone(
        name=str(d["name"]),
        portfolio_name=str(d["portfolio_name"]),
        target_date=_str_to_dt(d.get("target_date")),
        task_ids=list(d.get("task_ids") or []),
        critical_task_ids=list(d.get("critical_task_ids") or []),
    )


def _portfolio_to_dict(p: Portfolio) -> dict[str, Any]:
    """Convert a :class:`~kanboard.models.Portfolio` to a JSON-serialisable dict.

    Args:
        p: The portfolio to serialise.

    Returns:
        A dictionary suitable for :func:`json.dump`.
    """
    return {
        "name": p.name,
        "description": p.description,
        "project_ids": list(p.project_ids),
        "milestones": [_milestone_to_dict(m) for m in p.milestones],
        "created_at": _dt_to_str(p.created_at),
        "updated_at": _dt_to_str(p.updated_at),
    }


def _portfolio_from_dict(d: dict[str, Any]) -> Portfolio:
    """Construct a :class:`~kanboard.models.Portfolio` from a raw dict.

    Args:
        d: A dictionary as read from the JSON store.

    Returns:
        A populated :class:`~kanboard.models.Portfolio`.
    """
    return Portfolio(
        name=str(d["name"]),
        description=str(d.get("description", "")),
        project_ids=list(d.get("project_ids") or []),
        milestones=[_milestone_from_dict(m) for m in (d.get("milestones") or [])],
        created_at=_str_to_dt(d.get("created_at")),
        updated_at=_str_to_dt(d.get("updated_at")),
    )


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class LocalPortfolioStore:
    """Local file-backed store for portfolio and milestone data.

    Persists portfolio configuration as JSON in the user's config directory.
    Provides CRUD operations for portfolios, milestones, and milestone task
    membership.

    File format::

        {
          "version": 1,
          "portfolios": [ ... ]
        }

    Raises :class:`~kanboard.exceptions.KanboardConfigError` on malformed JSON
    or schema version mismatches.  All writes are *atomic* — the data is first
    written to a temporary file in the same directory, then renamed over the
    target path to prevent corruption.

    Args:
        path: Path to the JSON store file.  Defaults to
            ``CONFIG_DIR / 'portfolios.json'`` when ``None``.

    Example:
        >>> store = LocalPortfolioStore()
        >>> portfolios = store.load()
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialise the store with an optional custom file path.

        Args:
            path: Override the default store file path.  When ``None``, the
                store defaults to ``CONFIG_DIR / 'portfolios.json'``.
        """
        if path is None:
            from kanboard.config import CONFIG_DIR

            path = CONFIG_DIR / "portfolios.json"
        self._path: Path = path

    # ------------------------------------------------------------------
    # Core I/O
    # ------------------------------------------------------------------

    def load(self) -> list[Portfolio]:
        """Load all portfolios from the store file.

        Returns an empty list when the file does not yet exist.

        Returns:
            A list of :class:`~kanboard.models.Portfolio` objects.

        Raises:
            KanboardConfigError: If the file contains malformed JSON or the
                stored schema version does not match :data:`_SCHEMA_VERSION`.
        """
        if not self._path.exists():
            return []
        try:
            raw = self._path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise KanboardConfigError(
                f"Malformed JSON in portfolio store '{self._path}': {exc}"
            ) from exc

        version = data.get("version")
        if version != _SCHEMA_VERSION:
            raise KanboardConfigError(
                f"Portfolio store schema version mismatch: "
                f"expected {_SCHEMA_VERSION}, got {version!r} in '{self._path}'"
            )
        return [_portfolio_from_dict(p) for p in (data.get("portfolios") or [])]

    def save(self, portfolios: list[Portfolio]) -> None:
        """Atomically write portfolios to the store file.

        Creates the parent directory (and any missing ancestors) automatically.
        Uses a write-then-rename strategy to prevent partial writes from
        corrupting the store.

        Args:
            portfolios: The full list of portfolios to persist.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": _SCHEMA_VERSION,
            "portfolios": [_portfolio_to_dict(p) for p in portfolios],
        }
        dir_ = self._path.parent
        fd, tmp_path_str = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp_path_str, self._path)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # Portfolio CRUD
    # ------------------------------------------------------------------

    def create_portfolio(
        self,
        name: str,
        description: str = "",
        project_ids: list[int] | None = None,
    ) -> Portfolio:
        """Create a new portfolio and persist it to the store.

        Args:
            name: Unique portfolio name (case-sensitive).
            description: Optional human-readable description.
            project_ids: Initial list of Kanboard project IDs.

        Returns:
            The newly created :class:`~kanboard.models.Portfolio`.

        Raises:
            ValueError: If a portfolio with *name* already exists.
        """
        portfolios = self.load()
        if any(p.name == name for p in portfolios):
            raise ValueError(f"Portfolio '{name}' already exists")
        now = datetime.now()
        portfolio = Portfolio(
            name=name,
            description=description,
            project_ids=list(project_ids or []),
            milestones=[],
            created_at=now,
            updated_at=now,
        )
        portfolios.append(portfolio)
        self.save(portfolios)
        return portfolio

    def get_portfolio(self, name: str) -> Portfolio:
        """Retrieve a portfolio by name.

        Args:
            name: The portfolio name to look up.

        Returns:
            The matching :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardConfigError: If no portfolio with *name* exists.
        """
        for portfolio in self.load():
            if portfolio.name == name:
                return portfolio
        raise KanboardConfigError(f"Portfolio '{name}' not found")

    def update_portfolio(self, name: str, **kwargs: Any) -> Portfolio:
        """Update one or more fields of an existing portfolio and persist.

        Only fields that are valid :class:`~kanboard.models.Portfolio`
        attributes are updated; unknown keyword arguments are silently ignored.
        ``updated_at`` is always refreshed to the current time.

        Args:
            name: Name of the portfolio to update.
            **kwargs: Field names and new values to apply.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardConfigError: If no portfolio with *name* exists.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == name:
                for key, value in kwargs.items():
                    if hasattr(portfolio, key):
                        setattr(portfolio, key, value)
                portfolio.updated_at = datetime.now()
                self.save(portfolios)
                return portfolio
        raise KanboardConfigError(f"Portfolio '{name}' not found")

    def remove_portfolio(self, name: str) -> bool:
        """Remove a portfolio from the store.

        Args:
            name: Name of the portfolio to remove.

        Returns:
            ``True`` if the portfolio was found and removed, ``False`` if it
            did not exist.
        """
        portfolios = self.load()
        new_portfolios = [p for p in portfolios if p.name != name]
        if len(new_portfolios) == len(portfolios):
            return False
        self.save(new_portfolios)
        return True

    # ------------------------------------------------------------------
    # Project membership
    # ------------------------------------------------------------------

    def add_project(self, portfolio_name: str, project_id: int) -> Portfolio:
        """Add a Kanboard project ID to a portfolio.

        A no-op (idempotent) if *project_id* is already present.

        Args:
            portfolio_name: Name of the target portfolio.
            project_id: Kanboard project ID to add.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardConfigError: If the portfolio does not exist.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                if project_id not in portfolio.project_ids:
                    portfolio.project_ids.append(project_id)
                portfolio.updated_at = datetime.now()
                self.save(portfolios)
                return portfolio
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")

    def remove_project(self, portfolio_name: str, project_id: int) -> Portfolio:
        """Remove a Kanboard project ID from a portfolio.

        A no-op if *project_id* is not currently a member.

        Args:
            portfolio_name: Name of the target portfolio.
            project_id: Kanboard project ID to remove.

        Returns:
            The updated :class:`~kanboard.models.Portfolio`.

        Raises:
            KanboardConfigError: If the portfolio does not exist.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                portfolio.project_ids = [pid for pid in portfolio.project_ids if pid != project_id]
                portfolio.updated_at = datetime.now()
                self.save(portfolios)
                return portfolio
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")

    # ------------------------------------------------------------------
    # Milestone CRUD
    # ------------------------------------------------------------------

    def add_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        target_date: datetime | None = None,
    ) -> Milestone:
        """Add a new milestone to a portfolio.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Unique milestone name within the portfolio.
            target_date: Optional due date for the milestone.

        Returns:
            The newly created :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardConfigError: If the portfolio does not exist.
            ValueError: If a milestone with *milestone_name* already exists
                in the portfolio.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                if any(m.name == milestone_name for m in portfolio.milestones):
                    raise ValueError(
                        f"Milestone '{milestone_name}' already exists "
                        f"in portfolio '{portfolio_name}'"
                    )
                milestone = Milestone(
                    name=milestone_name,
                    portfolio_name=portfolio_name,
                    target_date=target_date,
                )
                portfolio.milestones.append(milestone)
                portfolio.updated_at = datetime.now()
                self.save(portfolios)
                return milestone
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")

    def update_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        **kwargs: Any,
    ) -> Milestone:
        """Update one or more fields of an existing milestone and persist.

        Only fields that are valid :class:`~kanboard.models.Milestone`
        attributes are updated; unknown keyword arguments are silently ignored.
        The parent portfolio's ``updated_at`` is refreshed.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to update.
            **kwargs: Field names and new values to apply.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardConfigError: If the portfolio or milestone does not exist.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                for milestone in portfolio.milestones:
                    if milestone.name == milestone_name:
                        for key, value in kwargs.items():
                            if hasattr(milestone, key):
                                setattr(milestone, key, value)
                        portfolio.updated_at = datetime.now()
                        self.save(portfolios)
                        return milestone
                raise KanboardConfigError(
                    f"Milestone '{milestone_name}' not found in portfolio '{portfolio_name}'"
                )
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")

    def remove_milestone(self, portfolio_name: str, milestone_name: str) -> bool:
        """Remove a milestone from a portfolio.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the milestone to remove.

        Returns:
            ``True`` if the milestone was found and removed; ``False`` if it
            did not exist within the portfolio.

        Raises:
            KanboardConfigError: If the portfolio does not exist.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                new_milestones = [m for m in portfolio.milestones if m.name != milestone_name]
                if len(new_milestones) == len(portfolio.milestones):
                    return False
                portfolio.milestones = new_milestones
                portfolio.updated_at = datetime.now()
                self.save(portfolios)
                return True
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")

    # ------------------------------------------------------------------
    # Milestone task membership
    # ------------------------------------------------------------------

    def add_task_to_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        task_id: int,
        critical: bool = False,
    ) -> Milestone:
        """Add a task to a milestone, optionally marking it as critical.

        Idempotent — if *task_id* is already in ``task_ids`` it is not
        duplicated.  Similarly, *critical_task_ids* is only extended if
        ``critical=True`` and the task is not already listed there.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the target milestone.
            task_id: Kanboard task ID to add.
            critical: When ``True``, also add *task_id* to
                ``critical_task_ids``.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardConfigError: If the portfolio or milestone does not exist.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                for milestone in portfolio.milestones:
                    if milestone.name == milestone_name:
                        if task_id not in milestone.task_ids:
                            milestone.task_ids.append(task_id)
                        if critical and task_id not in milestone.critical_task_ids:
                            milestone.critical_task_ids.append(task_id)
                        portfolio.updated_at = datetime.now()
                        self.save(portfolios)
                        return milestone
                raise KanboardConfigError(
                    f"Milestone '{milestone_name}' not found in portfolio '{portfolio_name}'"
                )
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")

    def remove_task_from_milestone(
        self,
        portfolio_name: str,
        milestone_name: str,
        task_id: int,
    ) -> Milestone:
        """Remove a task from a milestone.

        Removes *task_id* from both ``task_ids`` and ``critical_task_ids``.
        A no-op on each list if the task is not present.

        Args:
            portfolio_name: Name of the parent portfolio.
            milestone_name: Name of the target milestone.
            task_id: Kanboard task ID to remove.

        Returns:
            The updated :class:`~kanboard.models.Milestone`.

        Raises:
            KanboardConfigError: If the portfolio or milestone does not exist.
        """
        portfolios = self.load()
        for portfolio in portfolios:
            if portfolio.name == portfolio_name:
                for milestone in portfolio.milestones:
                    if milestone.name == milestone_name:
                        milestone.task_ids = [tid for tid in milestone.task_ids if tid != task_id]
                        milestone.critical_task_ids = [
                            tid for tid in milestone.critical_task_ids if tid != task_id
                        ]
                        portfolio.updated_at = datetime.now()
                        self.save(portfolios)
                        return milestone
                raise KanboardConfigError(
                    f"Milestone '{milestone_name}' not found in portfolio '{portfolio_name}'"
                )
        raise KanboardConfigError(f"Portfolio '{portfolio_name}' not found")
