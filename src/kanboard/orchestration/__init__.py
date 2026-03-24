"""Kanboard CLI orchestration subpackage — cross-project portfolio management.

Provides portfolio management, milestone tracking, and dependency analysis as
CLI-side meta-constructs.  All orchestration classes are opt-in and
instantiated separately by callers — they are NOT attached as attributes of
:class:`~kanboard.client.KanboardClient`.

Example:
    >>> from kanboard import KanboardClient
    >>> from kanboard.orchestration import (
    ...     DependencyAnalyzer,
    ...     LocalPortfolioStore,
    ...     PortfolioManager,
    ...     create_backend,
    ... )
    >>> store = LocalPortfolioStore()
    >>> with KanboardClient(url, token) as client:
    ...     manager = PortfolioManager(client, store)
    ...     analyzer = DependencyAnalyzer(client)
    ...     backend = create_backend("remote", client=client)
"""

from kanboard.orchestration.backend import (
    PortfolioBackend,
    RemotePortfolioBackend,
    create_backend,
)
from kanboard.orchestration.dependencies import DependencyAnalyzer
from kanboard.orchestration.portfolio import PortfolioManager
from kanboard.orchestration.store import LocalPortfolioStore

__all__ = [
    "DependencyAnalyzer",
    "LocalPortfolioStore",
    "PortfolioBackend",
    "PortfolioManager",
    "RemotePortfolioBackend",
    "create_backend",
]
