"""Shared pytest fixtures for orchestration unit tests.

Provides standardised building blocks:
- ``mock_link_types``   — standard Kanboard link-type list (JSON-RPC ready)
- ``mock_task_links``   — cross-project blocking relationships (JSON-RPC ready)
- ``mock_tasks``        — 10 Task model instances across 3 projects
- ``sample_portfolio``  — Portfolio with 3 projects and 2 milestones
- ``seeded_store``      — LocalPortfolioStore pre-seeded with sample_portfolio
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kanboard.models import Milestone, Portfolio, Task
from kanboard.orchestration.store import LocalPortfolioStore

# ---------------------------------------------------------------------------
# Link-type / task-link raw-data fixtures (JSON-RPC response shapes)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_link_types() -> list[dict]:
    """Standard Kanboard link types as returned by ``getAllLinks``.

    Pairs: relates-to (1↔1), blocks (2) / is-blocked-by (3), duplicates (4) /
    is-duplicated-by (5).
    """
    return [
        {"id": "1", "label": "relates to", "opposite_id": "1"},
        {"id": "2", "label": "blocks", "opposite_id": "3"},
        {"id": "3", "label": "is blocked by", "opposite_id": "2"},
        {"id": "4", "label": "duplicates", "opposite_id": "5"},
        {"id": "5", "label": "is duplicated by", "opposite_id": "4"},
    ]


@pytest.fixture()
def mock_task_links() -> list[dict]:
    """Cross-project blocking task-link rows (``getAllTaskLinks`` shape).

    Relationships::

        Task 1 (project 1) → blocks → Task 4 (project 2)
        Task 4 (project 2) → blocks → Task 7 (project 3)

    Both links use ``link_id="2"`` (the "blocks" link type).
    """
    return [
        {
            "id": "1",
            "task_id": "1",
            "opposite_task_id": "4",
            "link_id": "2",  # "blocks"
        },
        {
            "id": "2",
            "task_id": "4",
            "opposite_task_id": "7",
            "link_id": "2",  # "blocks"
        },
    ]


# ---------------------------------------------------------------------------
# Task model fixture (10 tasks across 3 projects)
# ---------------------------------------------------------------------------


def _raw_task(task_id: int, project_id: int, is_active: bool = True) -> dict:
    """Return a minimal raw task dict suitable for ``Task.from_api()``."""
    return {
        "id": str(task_id),
        "title": f"Task {task_id}",
        "description": "",
        "date_creation": "1711077600",
        "date_modification": "1711077600",
        "date_due": None,
        "date_completed": None,
        "date_moved": None,
        "color_id": "yellow",
        "project_id": str(project_id),
        "column_id": "1",
        "swimlane_id": "0",
        "owner_id": "0",
        "creator_id": "1",
        "category_id": "0",
        "is_active": "1" if is_active else "0",
        "priority": "0",
        "score": "0",
        "position": "1",
        "reference": "",
        "tags": [],
        "url": "",
    }


@pytest.fixture()
def mock_tasks() -> list[Task]:
    """10 Task model instances spread across 3 projects.

    Distribution::

        Project 1: tasks 1, 2, 3 (active) + task 10 (closed)
        Project 2: tasks 4, 5, 6 (active)
        Project 3: tasks 7, 8, 9 (active)

    Task IDs 1→4→7 form the cross-project blocking chain in
    :fixture:`mock_task_links`.
    """
    specs: list[tuple[int, int, bool]] = [
        # (task_id, project_id, is_active)
        (1, 1, True),
        (2, 1, True),
        (3, 1, True),
        (4, 2, True),
        (5, 2, True),
        (6, 2, True),
        (7, 3, True),
        (8, 3, True),
        (9, 3, True),
        (10, 1, False),  # closed task in project 1
    ]
    return [Task.from_api(_raw_task(tid, pid, active)) for tid, pid, active in specs]


# ---------------------------------------------------------------------------
# Portfolio / store fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_portfolio() -> Portfolio:
    """A Portfolio spanning 3 projects with 2 milestones.

    Structure::

        Portfolio "MyPortfolio"
        ├── project_ids: [1, 2, 3]
        ├── Milestone "Sprint 1"
        │   task_ids=[1, 4, 7]  critical_task_ids=[1]  target=+14 days
        └── Milestone "Sprint 2"
            task_ids=[2, 5, 8]  critical_task_ids=[]   target=+30 days

    The milestone task IDs align with the cross-project blocking chain in
    :fixture:`mock_task_links` (task 1 → task 4 → task 7).
    """
    now = datetime(2026, 3, 22, 12, 0, 0)
    target_sprint1 = datetime.now() + timedelta(days=14)
    target_sprint2 = datetime.now() + timedelta(days=30)

    sprint1 = Milestone(
        name="Sprint 1",
        portfolio_name="MyPortfolio",
        target_date=target_sprint1,
        task_ids=[1, 4, 7],
        critical_task_ids=[1],
    )
    sprint2 = Milestone(
        name="Sprint 2",
        portfolio_name="MyPortfolio",
        target_date=target_sprint2,
        task_ids=[2, 5, 8],
        critical_task_ids=[],
    )
    return Portfolio(
        name="MyPortfolio",
        description="Cross-project orchestration test portfolio",
        project_ids=[1, 2, 3],
        milestones=[sprint1, sprint2],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def seeded_store(tmp_path: Path, sample_portfolio: Portfolio) -> LocalPortfolioStore:
    """``LocalPortfolioStore`` backed by ``tmp_path``, pre-seeded with ``sample_portfolio``.

    Uses only ``tmp_path`` — never touches ``~/.config/kanboard/``.
    """
    store = LocalPortfolioStore(path=tmp_path / "portfolios.json")
    store.create_portfolio(
        sample_portfolio.name,
        sample_portfolio.description,
        sample_portfolio.project_ids,
    )
    for milestone in sample_portfolio.milestones:
        store.add_milestone(
            sample_portfolio.name,
            milestone.name,
            target_date=milestone.target_date,
        )
        for task_id in milestone.task_ids:
            critical = task_id in milestone.critical_task_ids
            store.add_task_to_milestone(
                sample_portfolio.name,
                milestone.name,
                task_id,
                critical=critical,
            )
    return store
