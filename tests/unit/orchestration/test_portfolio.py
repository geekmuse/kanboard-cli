"""Unit tests for PortfolioManager — multi-project aggregation and milestone tracking."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardConfigError
from kanboard.models import Milestone, Portfolio
from kanboard.orchestration.portfolio import (
    _METADATA_KEY_MILESTONE_CRITICAL,
    _METADATA_KEY_MILESTONES,
    _METADATA_KEY_PORTFOLIO,
    PortfolioManager,
)
from kanboard.orchestration.store import LocalPortfolioStore

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _project_data(project_id: int, name: str = "Project") -> dict:
    return {
        "id": str(project_id),
        "name": name,
        "description": "",
        "is_active": "1",
        "token": "",
        "last_modified": "0",
        "is_public": "0",
        "is_private": False,
        "owner_id": "1",
        "identifier": "",
        "start_date": None,
        "end_date": None,
        "url": "",
    }


def _task_data(
    task_id: int,
    project_id: int = 1,
    is_active: bool = True,
    owner_id: int = 0,
) -> dict:
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
        "owner_id": str(owner_id),
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


def _link_types_data() -> list[dict]:
    """Standard Kanboard link types (blocks / is blocked by pairs)."""
    return [
        {"id": "1", "label": "relates to", "opposite_id": "1"},
        {"id": "2", "label": "blocks", "opposite_id": "3"},
        {"id": "3", "label": "is blocked by", "opposite_id": "2"},
        {"id": "4", "label": "duplicates", "opposite_id": "5"},
        {"id": "5", "label": "is duplicated by", "opposite_id": "4"},
    ]


def _task_link_data(link_id: int, task_id: int, opposite_task_id: int) -> dict:
    return {
        "id": "1",
        "task_id": str(task_id),
        "opposite_task_id": str(opposite_task_id),
        "link_id": str(link_id),
    }


def _make_store(tmp_path: Path) -> LocalPortfolioStore:
    return LocalPortfolioStore(path=tmp_path / "portfolios.json")


def _make_portfolio(
    name: str = "Alpha",
    project_ids: list[int] | None = None,
    milestones: list[Milestone] | None = None,
) -> Portfolio:
    now = datetime(2026, 3, 22, 12, 0, 0)
    return Portfolio(
        name=name,
        description="Test portfolio",
        project_ids=project_ids if project_ids is not None else [1, 2],
        milestones=milestones if milestones is not None else [],
        created_at=now,
        updated_at=now,
    )


def _make_milestone(
    name: str = "Sprint 1",
    portfolio_name: str = "Alpha",
    target_date: datetime | None = None,
    task_ids: list[int] | None = None,
    critical_task_ids: list[int] | None = None,
) -> Milestone:
    return Milestone(
        name=name,
        portfolio_name=portfolio_name,
        target_date=target_date,
        task_ids=task_ids or [],
        critical_task_ids=critical_task_ids or [],
    )


def _seed_store(store: LocalPortfolioStore, portfolio: Portfolio) -> None:
    """Persist a portfolio (and its milestones) into the store."""
    store.create_portfolio(portfolio.name, portfolio.description, portfolio.project_ids)
    for milestone in portfolio.milestones:
        store.add_milestone(
            portfolio.name,
            milestone.name,
            target_date=milestone.target_date,
        )
        for task_id in milestone.task_ids:
            critical = task_id in milestone.critical_task_ids
            store.add_task_to_milestone(portfolio.name, milestone.name, task_id, critical=critical)


# ---------------------------------------------------------------------------
# get_portfolio_projects
# ---------------------------------------------------------------------------


def test_get_portfolio_projects_returns_all_projects(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_portfolio_projects() fetches each project by ID and returns a list."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 2])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "Project Alpha")))
    httpx_mock.add_response(json=_rpc_ok(_project_data(2, "Project Beta")))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        projects = manager.get_portfolio_projects("Alpha")

    assert len(projects) == 2
    assert projects[0].id == 1
    assert projects[0].name == "Project Alpha"
    assert projects[1].id == 2
    assert projects[1].name == "Project Beta"


def test_get_portfolio_projects_skips_missing_project(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """get_portfolio_projects() skips projects that no longer exist in Kanboard."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 999])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "Project Alpha")))
    httpx_mock.add_response(json=_rpc_ok(None))  # project 999 not found

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        projects = manager.get_portfolio_projects("Alpha")

    assert len(projects) == 1
    assert projects[0].id == 1


def test_get_portfolio_projects_portfolio_not_found_raises(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """get_portfolio_projects() raises KanboardConfigError for unknown portfolio."""
    store = _make_store(tmp_path)
    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        with pytest.raises(KanboardConfigError):
            manager.get_portfolio_projects("NonExistent")


def test_get_portfolio_projects_empty_project_list(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_portfolio_projects() returns [] for a portfolio with no projects."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[])
    _seed_store(store, portfolio)

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        projects = manager.get_portfolio_projects("Alpha")

    assert projects == []


# ---------------------------------------------------------------------------
# get_portfolio_tasks
# ---------------------------------------------------------------------------


def test_get_portfolio_tasks_aggregates_across_projects(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """get_portfolio_tasks() returns tasks from all portfolio projects."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 2])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok([_task_data(10, project_id=1)]))
    httpx_mock.add_response(
        json=_rpc_ok([_task_data(20, project_id=2), _task_data(21, project_id=2)])
    )

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        tasks = manager.get_portfolio_tasks("Alpha")

    assert len(tasks) == 3
    assert {t.id for t in tasks} == {10, 20, 21}


def test_get_portfolio_tasks_filters_by_assignee(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_portfolio_tasks() filters tasks by assignee_id when provided."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1])
    _seed_store(store, portfolio)

    httpx_mock.add_response(
        json=_rpc_ok(
            [_task_data(1, owner_id=5), _task_data(2, owner_id=7), _task_data(3, owner_id=5)]
        )
    )

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        tasks = manager.get_portfolio_tasks("Alpha", assignee_id=5)

    assert len(tasks) == 2
    assert all(t.owner_id == 5 for t in tasks)


def test_get_portfolio_tasks_filters_by_project_id(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_portfolio_tasks() filters to a single project when project_id is set."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 2])
    _seed_store(store, portfolio)

    # Only one HTTP call expected (project 2 only)
    httpx_mock.add_response(json=_rpc_ok([_task_data(20, project_id=2)]))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        tasks = manager.get_portfolio_tasks("Alpha", project_id=2)

    assert len(tasks) == 1
    assert tasks[0].id == 20


def test_get_portfolio_tasks_project_id_not_in_portfolio_returns_empty(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """get_portfolio_tasks() returns [] when project_id is not a portfolio member."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 2])
    _seed_store(store, portfolio)

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        tasks = manager.get_portfolio_tasks("Alpha", project_id=99)

    assert tasks == []


def test_get_portfolio_tasks_closed_status_filter(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_portfolio_tasks() passes status=0 to getAllTasks when specified."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok([_task_data(5, is_active=False)]))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        tasks = manager.get_portfolio_tasks("Alpha", status=0)

    assert len(tasks) == 1
    assert tasks[0].is_active is False


def test_get_portfolio_tasks_empty_project_returns_empty_list(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """get_portfolio_tasks() handles projects with no tasks gracefully."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(False))  # getAllTasks returns False on empty

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        tasks = manager.get_portfolio_tasks("Alpha")

    assert tasks == []


# ---------------------------------------------------------------------------
# get_milestone_progress — completion counting
# ---------------------------------------------------------------------------


def test_milestone_progress_zero_percent(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Milestone with all active tasks → 0% complete."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1, 2])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks returns empty → blocked_by_link_ids=set() → _has_open_blocker returns
    # immediately without calling getAllTaskLinks (no HTTP call for task links).
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))
    httpx_mock.add_response(json=_rpc_ok(_task_data(2, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.total == 2
    assert progress.completed == 0
    assert progress.percent == 0.0
    assert progress.is_at_risk is False
    assert progress.is_overdue is False
    assert progress.blocked_task_ids == []


def test_milestone_progress_fifty_percent(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Milestone with half closed tasks → 50% complete."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1, 2])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=False)))  # task 1 closed
    httpx_mock.add_response(json=_rpc_ok(_task_data(2, is_active=True)))  # task 2 active

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.total == 2
    assert progress.completed == 1
    assert progress.percent == 50.0


def test_milestone_progress_hundred_percent(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Milestone with all closed tasks → 100% complete."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1, 2])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=False)))
    httpx_mock.add_response(json=_rpc_ok(_task_data(2, is_active=False)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.percent == 100.0
    assert progress.completed == 2


def test_milestone_progress_empty_milestone_is_100_percent(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """Empty milestone (no tasks) → 100% by convention."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.total == 0
    assert progress.percent == 100.0


# ---------------------------------------------------------------------------
# get_milestone_progress — missing tasks
# ---------------------------------------------------------------------------


def test_milestone_progress_excludes_deleted_tasks(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Tasks deleted from Kanboard are excluded from the total count."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1, 999])  # 999 is deleted
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=False)))  # task 1 closed
    httpx_mock.add_response(json=_rpc_ok(None))  # task 999 not found

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    # Only task 1 counted (total=1, completed=1)
    assert progress.total == 1
    assert progress.completed == 1
    assert progress.percent == 100.0


def test_milestone_progress_all_tasks_deleted_is_100_percent(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """When all tasks are deleted, progress defaults to 100% (total=0 guard)."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[999])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(None))  # task 999 not found

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.total == 0
    assert progress.percent == 100.0


# ---------------------------------------------------------------------------
# get_milestone_progress — is_at_risk detection
# ---------------------------------------------------------------------------


def test_milestone_progress_is_at_risk_within_7_days_and_below_80_percent(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """is_at_risk=True when target_date within 7 days and percent < 80."""
    store = _make_store(tmp_path)
    target = datetime.now() + timedelta(days=3)  # 3 days away
    milestone = _make_milestone(task_ids=[1, 2, 3, 4, 5], target_date=target)
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    # 5 tasks all active — 0/5 done = 0%
    for i in range(1, 6):
        httpx_mock.add_response(json=_rpc_ok(_task_data(i, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.is_at_risk is True
    assert progress.is_overdue is False


def test_milestone_progress_not_at_risk_when_above_80_percent(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """is_at_risk=False when percent >= 80 even within 7 days."""
    store = _make_store(tmp_path)
    target = datetime.now() + timedelta(days=2)
    milestone = _make_milestone(task_ids=[1, 2, 3, 4, 5], target_date=target)
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    # tasks 1-4 closed, task 5 open = 4/5 = 80%
    for i in range(1, 5):
        httpx_mock.add_response(json=_rpc_ok(_task_data(i, is_active=False)))
    httpx_mock.add_response(json=_rpc_ok(_task_data(5, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.percent == 80.0
    assert progress.is_at_risk is False


def test_milestone_progress_not_at_risk_when_beyond_7_days(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """is_at_risk=False when target_date is more than 7 days away."""
    store = _make_store(tmp_path)
    target = datetime.now() + timedelta(days=14)
    milestone = _make_milestone(task_ids=[1], target_date=target)
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.is_at_risk is False


# ---------------------------------------------------------------------------
# get_milestone_progress — is_overdue detection
# ---------------------------------------------------------------------------


def test_milestone_progress_is_overdue_past_date_and_incomplete(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """is_overdue=True when target_date is in the past and percent < 100."""
    store = _make_store(tmp_path)
    target = datetime.now() - timedelta(days=2)  # 2 days ago
    milestone = _make_milestone(task_ids=[1], target_date=target)
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))  # open

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.is_overdue is True
    assert progress.is_at_risk is False  # past due, not within future 7 days


def test_milestone_progress_not_overdue_when_complete(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """is_overdue=False when percent == 100 even if target_date is in the past."""
    store = _make_store(tmp_path)
    target = datetime.now() - timedelta(days=1)
    milestone = _make_milestone(task_ids=[1], target_date=target)
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=False)))  # closed

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.is_overdue is False
    assert progress.percent == 100.0


def test_milestone_progress_no_target_date_not_overdue_not_at_risk(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """Milestones with no target_date are never at-risk or overdue."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1], target_date=None)
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks empty → no getAllTaskLinks calls
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.is_at_risk is False
    assert progress.is_overdue is False
    assert progress.target_date is None


# ---------------------------------------------------------------------------
# get_milestone_progress — blocked_task_ids
# ---------------------------------------------------------------------------


def test_milestone_progress_detects_blocked_task(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """blocked_task_ids contains task IDs with unresolved open blockers."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    # getAllLinks — "is blocked by" has link_id=3
    httpx_mock.add_response(json=_rpc_ok(_link_types_data()))
    # getTask(1) — active
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))
    # getAllTaskLinks(1) — task 1 is blocked by task 50 (link_id=3)
    httpx_mock.add_response(
        json=_rpc_ok([_task_link_data(link_id=3, task_id=1, opposite_task_id=50)])
    )
    # getTask(50) — blocker is still active
    httpx_mock.add_response(json=_rpc_ok(_task_data(50, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert 1 in progress.blocked_task_ids


def test_milestone_progress_resolved_blocker_not_in_blocked_ids(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """blocked_task_ids excludes tasks whose blockers are resolved (closed)."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(_link_types_data()))
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))
    httpx_mock.add_response(
        json=_rpc_ok([_task_link_data(link_id=3, task_id=1, opposite_task_id=50)])
    )
    # Blocker is closed (resolved)
    httpx_mock.add_response(json=_rpc_ok(_task_data(50, is_active=False)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.blocked_task_ids == []


def test_milestone_progress_no_blocked_by_links_skips_blocker_check(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """Tasks with only 'blocks' links (not 'is blocked by') are not blocked."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(_link_types_data()))
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))
    # Task 1 has a "blocks" link (link_id=2, not "is blocked by")
    httpx_mock.add_response(
        json=_rpc_ok([_task_link_data(link_id=2, task_id=1, opposite_task_id=50)])
    )

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.blocked_task_ids == []


def test_milestone_progress_missing_blocker_task_skipped(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """Deleted blocker tasks (404) are skipped; task is not added to blocked_ids."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(task_ids=[1])
    portfolio = _make_portfolio(milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(_link_types_data()))
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=True)))
    httpx_mock.add_response(
        json=_rpc_ok([_task_link_data(link_id=3, task_id=1, opposite_task_id=999)])
    )
    # Blocker task deleted
    httpx_mock.add_response(json=_rpc_ok(None))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        progress = manager.get_milestone_progress("Alpha", "Sprint 1")

    assert progress.blocked_task_ids == []


# ---------------------------------------------------------------------------
# get_milestone_progress — error path
# ---------------------------------------------------------------------------


def test_milestone_progress_unknown_milestone_raises(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_milestone_progress() raises KanboardConfigError for unknown milestone."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(milestones=[])
    _seed_store(store, portfolio)

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        with pytest.raises(KanboardConfigError, match="Sprint 1"):
            manager.get_milestone_progress("Alpha", "Sprint 1")


# ---------------------------------------------------------------------------
# get_all_milestone_progress
# ---------------------------------------------------------------------------


def test_get_all_milestone_progress_returns_all_milestones(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """get_all_milestone_progress() returns one MilestoneProgress per milestone."""
    store = _make_store(tmp_path)
    m1 = _make_milestone(name="Sprint 1", task_ids=[1])
    m2 = _make_milestone(name="Sprint 2", task_ids=[2])
    portfolio = _make_portfolio(milestones=[m1, m2])
    _seed_store(store, portfolio)

    # Sprint 1: getAllLinks (empty) → no getAllTaskLinks; getTask(1)
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(1, is_active=False)))
    # Sprint 2: getAllLinks (empty) → no getAllTaskLinks; getTask(2)
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok(_task_data(2, is_active=True)))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        results = manager.get_all_milestone_progress("Alpha")

    assert len(results) == 2
    assert results[0].milestone_name == "Sprint 1"
    assert results[0].percent == 100.0
    assert results[1].milestone_name == "Sprint 2"
    assert results[1].percent == 0.0


def test_get_all_milestone_progress_empty_portfolio(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """get_all_milestone_progress() returns [] for a portfolio with no milestones."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(milestones=[])
    _seed_store(store, portfolio)

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        results = manager.get_all_milestone_progress("Alpha")

    assert results == []


# ---------------------------------------------------------------------------
# sync_metadata
# ---------------------------------------------------------------------------


def test_sync_metadata_writes_portfolio_to_projects(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() writes kanboard_cli:portfolio to all portfolio projects."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 2])
    _seed_store(store, portfolio)

    # Both saveProjectMetadata calls return True
    httpx_mock.add_response(json=_rpc_ok(True))
    httpx_mock.add_response(json=_rpc_ok(True))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        result = manager.sync_metadata("Alpha")

    assert result["projects_synced"] == 2
    assert result["tasks_synced"] == 0


def test_sync_metadata_writes_milestones_to_tasks(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() writes kanboard_cli:milestones to each tracked task."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(name="Sprint 1", task_ids=[10, 20])
    portfolio = _make_portfolio(project_ids=[1], milestones=[milestone])
    _seed_store(store, portfolio)

    # saveProjectMetadata for project 1
    httpx_mock.add_response(json=_rpc_ok(True))
    # saveTaskMetadata for task 10
    httpx_mock.add_response(json=_rpc_ok(True))
    # saveTaskMetadata for task 20
    httpx_mock.add_response(json=_rpc_ok(True))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        result = manager.sync_metadata("Alpha")

    assert result["projects_synced"] == 1
    assert result["tasks_synced"] == 2


def test_sync_metadata_writes_critical_flag_for_critical_tasks(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """sync_metadata() writes kanboard_cli:milestone_critical for critical tasks."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(
        name="Sprint 1",
        task_ids=[10, 20],
        critical_task_ids=[10],
    )
    portfolio = _make_portfolio(project_ids=[1], milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))  # saveProjectMetadata project 1
    httpx_mock.add_response(json=_rpc_ok(True))  # saveTaskMetadata task 10
    httpx_mock.add_response(json=_rpc_ok(True))  # saveTaskMetadata task 20

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        result = manager.sync_metadata("Alpha")

    assert result["tasks_synced"] == 2


def test_sync_metadata_portfolio_metadata_content(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() portfolio metadata JSON contains portfolio name and description."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        manager.sync_metadata("Alpha")

    # Inspect what was sent in the request
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    values = body["params"]["values"]
    portfolio_meta = json.loads(values[_METADATA_KEY_PORTFOLIO])
    assert portfolio_meta["name"] == "Alpha"
    assert portfolio_meta["description"] == "Test portfolio"


def test_sync_metadata_milestones_metadata_content(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() task metadata JSON contains list of milestone names."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(name="Sprint 1", task_ids=[10])
    portfolio = _make_portfolio(project_ids=[1], milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))  # project
    httpx_mock.add_response(json=_rpc_ok(True))  # task

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        manager.sync_metadata("Alpha")

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    task_body = json.loads(requests[1].content)
    values = task_body["params"]["values"]
    milestones_meta = json.loads(values[_METADATA_KEY_MILESTONES])
    assert milestones_meta == ["Sprint 1"]
    assert _METADATA_KEY_MILESTONE_CRITICAL not in values


def test_sync_metadata_critical_milestone_key_present(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """sync_metadata() includes kanboard_cli:milestone_critical key for critical tasks."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(
        name="Sprint 1",
        task_ids=[10],
        critical_task_ids=[10],
    )
    portfolio = _make_portfolio(project_ids=[1], milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))  # project
    httpx_mock.add_response(json=_rpc_ok(True))  # task

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        manager.sync_metadata("Alpha")

    requests = httpx_mock.get_requests()
    task_body = json.loads(requests[1].content)
    values = task_body["params"]["values"]
    assert _METADATA_KEY_MILESTONE_CRITICAL in values
    critical_meta = json.loads(values[_METADATA_KEY_MILESTONE_CRITICAL])
    assert critical_meta == ["Sprint 1"]


def test_sync_metadata_missing_project_skipped(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() skips projects that fail to sync (deleted/unreachable)."""
    store = _make_store(tmp_path)
    portfolio = _make_portfolio(project_ids=[1, 2])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))  # project 1 synced
    httpx_mock.add_response(json=_rpc_ok(False))  # project 2 fails

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        result = manager.sync_metadata("Alpha")

    assert result["projects_synced"] == 1
    assert result["tasks_synced"] == 0


def test_sync_metadata_missing_task_skipped(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() skips tasks that fail to sync (deleted/unreachable)."""
    store = _make_store(tmp_path)
    milestone = _make_milestone(name="Sprint 1", task_ids=[10, 20])
    portfolio = _make_portfolio(project_ids=[1], milestones=[milestone])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))  # project 1
    httpx_mock.add_response(json=_rpc_ok(True))  # task 10 synced
    httpx_mock.add_response(json=_rpc_ok(False))  # task 20 fails

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        result = manager.sync_metadata("Alpha")

    assert result["tasks_synced"] == 1


def test_sync_metadata_task_in_multiple_milestones(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """sync_metadata() lists all milestones for tasks appearing in multiple milestones."""
    store = _make_store(tmp_path)
    m1 = _make_milestone(name="Sprint 1", task_ids=[10])
    m2 = _make_milestone(name="Sprint 2", task_ids=[10])  # task 10 in both
    portfolio = _make_portfolio(project_ids=[1], milestones=[m1, m2])
    _seed_store(store, portfolio)

    httpx_mock.add_response(json=_rpc_ok(True))  # project 1
    httpx_mock.add_response(json=_rpc_ok(True))  # task 10

    with KanboardClient(_URL, _TOKEN) as client:
        manager = PortfolioManager(client, store)
        manager.sync_metadata("Alpha")

    requests = httpx_mock.get_requests()
    task_body = json.loads(requests[1].content)
    values = task_body["params"]["values"]
    milestones_meta = json.loads(values[_METADATA_KEY_MILESTONES])
    assert set(milestones_meta) == {"Sprint 1", "Sprint 2"}
