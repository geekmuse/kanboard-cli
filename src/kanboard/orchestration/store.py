"""Local portfolio store — JSON persistence for portfolios and milestones."""

from __future__ import annotations

from pathlib import Path


class LocalPortfolioStore:
    """Local file-backed store for portfolio and milestone data.

    Persists portfolio configuration as JSON in the user's config directory.
    Provides CRUD operations for portfolios, milestones, and milestone task
    membership.

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
