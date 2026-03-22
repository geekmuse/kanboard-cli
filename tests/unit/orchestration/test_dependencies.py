"""Unit tests for DependencyAnalyzer — graph traversal and critical-path computation."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.models import DependencyEdge, Task
from kanboard.orchestration.dependencies import (
    _LINK_LABEL_BLOCKS,
    DependencyAnalyzer,
)

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Shared response helpers
# ---------------------------------------------------------------------------


def _rpc_ok(result, request_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


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
    title: str | None = None,
) -> dict:
    return {
        "id": str(task_id),
        "title": title if title is not None else f"Task {task_id}",
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


def _link_types() -> list[dict]:
    """Standard Kanboard link types."""
    return [
        {"id": "1", "label": "relates to", "opposite_id": "1"},
        {"id": "2", "label": "blocks", "opposite_id": "3"},
        {"id": "3", "label": "is blocked by", "opposite_id": "2"},
        {"id": "4", "label": "duplicates", "opposite_id": "5"},
        {"id": "5", "label": "is duplicated by", "opposite_id": "4"},
    ]


def _task_link(
    tl_id: int,
    task_id: int,
    opposite_task_id: int,
    link_id: int,
) -> dict:
    return {
        "id": str(tl_id),
        "task_id": str(task_id),
        "opposite_task_id": str(opposite_task_id),
        "link_id": str(link_id),
    }


def _make_task(task_id: int, project_id: int = 1, is_active: bool = True) -> Task:
    return Task.from_api(_task_data(task_id, project_id=project_id, is_active=is_active))


# ---------------------------------------------------------------------------
# get_dependency_edges — linear chain
# ---------------------------------------------------------------------------


def test_linear_chain_edges(httpx_mock: HTTPXMock) -> None:
    """A→B→C produces two edges in blocks direction."""
    task_a = _make_task(1)
    task_b = _make_task(2)
    task_c = _make_task(3)

    # Actual call order: getAllLinks → getAllTaskLinks(A) → getProjectById(1) [edge A→B]
    # → getAllTaskLinks(B) [B→C uses cached proj] → getAllTaskLinks(C)
    httpx_mock.add_response(json=_rpc_ok(_link_types()))  # 1. getAllLinks
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # 2. getAllTaskLinks(A)
    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "Project One")))  # 3. getProjectById(1)
    httpx_mock.add_response(json=_rpc_ok([_task_link(11, 2, 3, 2)]))  # 4. getAllTaskLinks(B)
    httpx_mock.add_response(json=_rpc_ok([]))  # 5. getAllTaskLinks(C)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b, task_c])

    assert len(edges) == 2
    assert edges[0].task_id == 1
    assert edges[0].opposite_task_id == 2
    assert edges[0].link_label == _LINK_LABEL_BLOCKS
    assert not edges[0].is_cross_project
    assert not edges[0].is_resolved

    assert edges[1].task_id == 2
    assert edges[1].opposite_task_id == 3
    assert edges[1].link_label == _LINK_LABEL_BLOCKS
    assert not edges[1].is_resolved


# ---------------------------------------------------------------------------
# get_dependency_edges — edge deduplication
# ---------------------------------------------------------------------------


def test_edge_deduplication_blocks_and_blocked_by(httpx_mock: HTTPXMock) -> None:
    """A blocks B queried from both A and B produces exactly one edge."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))  # getAllLinks
    # A's links: A blocks B (link_id=2, "blocks")
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    # B's links: B is blocked by A (link_id=3, "is blocked by")
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 2, 1, 3)]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "P1")))  # getProjectById(1)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1
    assert edges[0].task_id == 1
    assert edges[0].opposite_task_id == 2
    assert edges[0].link_label == _LINK_LABEL_BLOCKS


# ---------------------------------------------------------------------------
# get_dependency_edges — no dependencies
# ---------------------------------------------------------------------------


def test_no_dependencies_returns_empty(httpx_mock: HTTPXMock) -> None:
    """Tasks with no links produce no edges."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok([]))  # A has no links
    httpx_mock.add_response(json=_rpc_ok([]))  # B has no links

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert edges == []


def test_empty_task_list_returns_empty(httpx_mock: HTTPXMock) -> None:
    """An empty task list produces no edges (only getAllLinks is called)."""
    httpx_mock.add_response(json=_rpc_ok(_link_types()))  # getAllLinks

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([])

    assert edges == []


# ---------------------------------------------------------------------------
# get_dependency_edges — cross-project filter
# ---------------------------------------------------------------------------


def test_cross_project_filter_excludes_same_project(httpx_mock: HTTPXMock) -> None:
    """cross_project_only=True excludes same-project edges."""
    task_a = _make_task(1, project_id=1)
    task_b = _make_task(2, project_id=1)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))  # getAllLinks
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B
    httpx_mock.add_response(json=_rpc_ok([]))  # B has no outgoing
    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "P1")))  # getProjectById(1)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b], cross_project_only=True)

    assert edges == []


def test_cross_project_filter_includes_cross_project_edges(httpx_mock: HTTPXMock) -> None:
    """cross_project_only=True returns cross-project edges."""
    task_a = _make_task(1, project_id=1)
    task_b = _make_task(2, project_id=2)

    # getProjectById(1) and (2) called during A→B edge processing, before getAllTaskLinks(B)
    httpx_mock.add_response(json=_rpc_ok(_link_types()))  # 1. getAllLinks
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # 2. getAllTaskLinks(A)
    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "P1")))  # 3. getProjectById(1)
    httpx_mock.add_response(json=_rpc_ok(_project_data(2, "P2")))  # 4. getProjectById(2)
    httpx_mock.add_response(json=_rpc_ok([]))  # 5. getAllTaskLinks(B)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b], cross_project_only=True)

    assert len(edges) == 1
    assert edges[0].is_cross_project
    assert edges[0].task_project_name == "P1"
    assert edges[0].opposite_task_project_name == "P2"


def test_cross_project_flag_set_correctly(httpx_mock: HTTPXMock) -> None:
    """is_cross_project=False for same-project edge."""
    task_a = _make_task(1, project_id=1)
    task_b = _make_task(2, project_id=1)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "P1")))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1
    assert not edges[0].is_cross_project


# ---------------------------------------------------------------------------
# get_dependency_edges — resolved vs unresolved
# ---------------------------------------------------------------------------


def test_resolved_edge_when_blocker_is_closed(httpx_mock: HTTPXMock) -> None:
    """Edge is_resolved=True when the blocking task is inactive."""
    task_a = _make_task(1, is_active=False)  # A is closed
    task_b = _make_task(2, is_active=True)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B
    httpx_mock.add_response(json=_rpc_ok([]))  # B has no outgoing
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1
    assert edges[0].is_resolved


def test_unresolved_edge_when_blocker_is_open(httpx_mock: HTTPXMock) -> None:
    """Edge is_resolved=False when the blocking task is still active."""
    task_a = _make_task(1, is_active=True)  # A is open
    task_b = _make_task(2, is_active=True)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1
    assert not edges[0].is_resolved


# ---------------------------------------------------------------------------
# get_dependency_edges — "is blocked by" normalisation
# ---------------------------------------------------------------------------


def test_is_blocked_by_link_normalised_to_blocks_direction(httpx_mock: HTTPXMock) -> None:
    """An 'is blocked by' link from B's perspective creates a correct blocks edge."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    # A has no outgoing links (queried first)
    httpx_mock.add_response(json=_rpc_ok([]))
    # B has "is blocked by A" (link_id=3)
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 2, 1, 3)]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1
    # Normalised: A (blocker) → B (blocked)
    assert edges[0].task_id == 1
    assert edges[0].opposite_task_id == 2
    assert edges[0].link_label == _LINK_LABEL_BLOCKS


# ---------------------------------------------------------------------------
# get_dependency_edges — task not in list (cross-list enrichment)
# ---------------------------------------------------------------------------


def test_edge_to_task_outside_input_list(httpx_mock: HTTPXMock) -> None:
    """A blocking task outside the input list is fetched via get_task."""
    task_b = _make_task(2)  # only B is in the input list

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    # B is blocked by task 99 (not in input list)
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 2, 99, 3)]))
    # get_task(99) to enrich the blocker
    httpx_mock.add_response(json=_rpc_ok(_task_data(99, project_id=1)))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_b])

    assert len(edges) == 1
    assert edges[0].task_id == 99
    assert edges[0].opposite_task_id == 2


def test_missing_blocker_task_skips_edge(httpx_mock: HTTPXMock) -> None:
    """An edge whose blocker no longer exists is silently skipped."""
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 2, 999, 3)]))  # blocked by 999
    # get_task(999) returns None (not found)
    httpx_mock.add_response(json=_rpc_ok(None))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_b])

    assert edges == []


# ---------------------------------------------------------------------------
# get_dependency_edges — task cache
# ---------------------------------------------------------------------------


def test_task_cache_prevents_redundant_get_task_calls(httpx_mock: HTTPXMock) -> None:
    """Input tasks are cached so get_task is not called for them."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    # A blocks B — both A and B are in input list (no getTask calls needed)
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))  # B's links
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    # pytest-httpx validates no extra responses consumed — exactly 4 calls expected.
    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1  # no extra getTask HTTP calls triggered


# ---------------------------------------------------------------------------
# get_dependency_edges — getAllLinks failure
# ---------------------------------------------------------------------------


def test_get_dependency_edges_returns_empty_on_link_type_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """Returns [] when getAllLinks returns empty (no dependency type info)."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok([]))  # getAllLinks returns empty
    # getAllTaskLinks still called for each task
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    # relevant_link_ids is empty, so all task links are filtered out
    assert edges == []


# ---------------------------------------------------------------------------
# get_blocked_tasks
# ---------------------------------------------------------------------------


def test_get_blocked_tasks_returns_blocked_tasks(httpx_mock: HTTPXMock) -> None:
    """get_blocked_tasks returns tasks with open blockers."""
    task_a = _make_task(1, is_active=True)  # blocker
    task_b = _make_task(2, is_active=True)  # blocked by A

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B
    httpx_mock.add_response(json=_rpc_ok([]))  # B's outgoing links
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        result = analyzer.get_blocked_tasks([task_a, task_b])

    assert len(result) == 1
    task, blocking_edges = result[0]
    assert task.id == 2  # B is blocked
    assert len(blocking_edges) == 1
    assert blocking_edges[0].task_id == 1  # A is the blocker


def test_get_blocked_tasks_excludes_resolved_blockers(httpx_mock: HTTPXMock) -> None:
    """get_blocked_tasks excludes tasks whose blocker is closed."""
    task_a = _make_task(1, is_active=False)  # closed blocker
    task_b = _make_task(2, is_active=True)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        result = analyzer.get_blocked_tasks([task_a, task_b])

    assert result == []  # A is resolved, so B is not "blocked"


def test_get_blocked_tasks_no_deps_returns_empty(httpx_mock: HTTPXMock) -> None:
    """get_blocked_tasks returns [] when no dependency edges exist."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok([]))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        result = analyzer.get_blocked_tasks([task_a, task_b])

    assert result == []


# ---------------------------------------------------------------------------
# get_blocking_tasks
# ---------------------------------------------------------------------------


def test_get_blocking_tasks_returns_active_blockers(httpx_mock: HTTPXMock) -> None:
    """get_blocking_tasks returns open tasks that are blocking others."""
    task_a = _make_task(1, is_active=True)  # open blocker
    task_b = _make_task(2, is_active=True)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        result = analyzer.get_blocking_tasks([task_a, task_b])

    assert len(result) == 1
    task, edges = result[0]
    assert task.id == 1  # A is the blocker
    assert len(edges) == 1
    assert edges[0].opposite_task_id == 2


def test_get_blocking_tasks_excludes_closed_blockers(httpx_mock: HTTPXMock) -> None:
    """get_blocking_tasks excludes closed tasks even if they have block edges."""
    task_a = _make_task(1, is_active=False)  # closed — should not appear
    task_b = _make_task(2, is_active=True)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        result = analyzer.get_blocking_tasks([task_a, task_b])

    assert result == []


def test_get_blocking_tasks_no_deps_returns_empty(httpx_mock: HTTPXMock) -> None:
    """get_blocking_tasks returns [] when no dependency edges exist."""
    task_a = _make_task(1)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([]))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        result = analyzer.get_blocking_tasks([task_a])

    assert result == []


# ---------------------------------------------------------------------------
# get_critical_path — linear chain
# ---------------------------------------------------------------------------


def test_critical_path_linear_chain(httpx_mock: HTTPXMock) -> None:
    """Critical path of A→B→C is [A, B, C]."""
    task_a = _make_task(1)
    task_b = _make_task(2)
    task_c = _make_task(3)

    # Same call order as get_dependency_edges: getProjectById after first edge found
    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # getAllTaskLinks(A)
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))  # getProjectById(1) for A→B edge
    httpx_mock.add_response(json=_rpc_ok([_task_link(11, 2, 3, 2)]))  # getAllTaskLinks(B)
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllTaskLinks(C)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a, task_b, task_c])

    assert [t.id for t in path] == [1, 2, 3]


# ---------------------------------------------------------------------------
# get_critical_path — diamond dependency
# ---------------------------------------------------------------------------


def test_critical_path_diamond(httpx_mock: HTTPXMock) -> None:
    """Diamond A→B→D, A→C→D: critical path is length 3 (any of A→B→D or A→C→D)."""
    task_a = _make_task(1)
    task_b = _make_task(2)
    task_c = _make_task(3)
    task_d = _make_task(4)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    # A blocks B and C
    httpx_mock.add_response(
        json=_rpc_ok(
            [
                _task_link(10, 1, 2, 2),
                _task_link(11, 1, 3, 2),
            ]
        )
    )
    httpx_mock.add_response(json=_rpc_ok([_task_link(12, 2, 4, 2)]))  # B blocks D
    httpx_mock.add_response(json=_rpc_ok([_task_link(13, 3, 4, 2)]))  # C blocks D
    httpx_mock.add_response(json=_rpc_ok([]))  # D has no outgoing
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a, task_b, task_c, task_d])

    assert len(path) == 3
    assert path[0].id == 1  # must start with A
    assert path[-1].id == 4  # must end with D


# ---------------------------------------------------------------------------
# get_critical_path — parallel independent chains
# ---------------------------------------------------------------------------


def test_critical_path_parallel_chains_picks_longest(httpx_mock: HTTPXMock) -> None:
    """Parallel chains A→B (len 2) and C→D→E (len 3): picks C→D→E."""
    task_a = _make_task(1)
    task_b = _make_task(2)
    task_c = _make_task(3)
    task_d = _make_task(4)
    task_e = _make_task(5)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B
    httpx_mock.add_response(json=_rpc_ok([]))  # B
    httpx_mock.add_response(json=_rpc_ok([_task_link(11, 3, 4, 2)]))  # C blocks D
    httpx_mock.add_response(json=_rpc_ok([_task_link(12, 4, 5, 2)]))  # D blocks E
    httpx_mock.add_response(json=_rpc_ok([]))  # E
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a, task_b, task_c, task_d, task_e])

    assert len(path) == 3
    assert path[0].id == 3  # starts with C
    assert path[-1].id == 5  # ends with E


# ---------------------------------------------------------------------------
# get_critical_path — empty / no edges
# ---------------------------------------------------------------------------


def test_critical_path_empty_task_list(httpx_mock: HTTPXMock) -> None:
    """Critical path for empty task list returns []."""
    # No HTTP calls expected (early return before getAllLinks)
    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([])

    assert path == []


def test_critical_path_no_dep_edges(httpx_mock: HTTPXMock) -> None:
    """Critical path returns [] when tasks have no dependency edges."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok([]))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a, task_b])

    assert path == []


def test_critical_path_single_task_no_deps(httpx_mock: HTTPXMock) -> None:
    """A single task with no links returns []."""
    task_a = _make_task(1)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([]))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a])

    assert path == []


# ---------------------------------------------------------------------------
# get_critical_path — inactive tasks excluded
# ---------------------------------------------------------------------------


def test_critical_path_excludes_inactive_tasks(httpx_mock: HTTPXMock) -> None:
    """Closed tasks are excluded from critical path computation."""
    task_a = _make_task(1, is_active=False)  # closed
    task_b = _make_task(2, is_active=True)
    task_c = _make_task(3, is_active=True)

    # get_dependency_edges is called with all tasks (including inactive A)
    # so getAllTaskLinks is called for all three, but no edges are produced
    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllTaskLinks(A) — no links
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllTaskLinks(B)
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllTaskLinks(C)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a, task_b, task_c])

    assert path == []


def test_critical_path_resolved_edge_excluded(httpx_mock: HTTPXMock) -> None:
    """Resolved edges (closed blocker) are not included in critical path."""
    task_a = _make_task(1, is_active=False)  # closed blocker — edge is resolved
    task_b = _make_task(2, is_active=True)

    # get_dependency_edges is called with [task_a, task_b] — A is passed as open_tasks check
    # wait: get_critical_path filters open_tasks first, then calls get_dependency_edges(tasks)
    # with the original full tasks list
    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # A blocks B (resolved)
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        path = analyzer.get_critical_path([task_a, task_b])

    # A→B edge is resolved; A is also not in open_tasks; path = []
    assert path == []


# ---------------------------------------------------------------------------
# get_critical_path — cycle detection
# ---------------------------------------------------------------------------


def test_critical_path_cycle_detection_logs_warning(
    httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Cycle A→B→A logs a warning and returns partial result (not an exception)."""
    import logging

    task_a = _make_task(1)
    task_b = _make_task(2)

    # A blocks B: getProjectById(1) called after first edge; B→A uses cached project
    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # getAllTaskLinks(A)
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))  # getProjectById(1) for A→B
    httpx_mock.add_response(json=_rpc_ok([_task_link(11, 2, 1, 2)]))  # getAllTaskLinks(B)

    with caplog.at_level(logging.WARNING, logger="kanboard.orchestration.dependencies"):
        with KanboardClient(_URL, _TOKEN) as client:
            analyzer = DependencyAnalyzer(client)
            path = analyzer.get_critical_path([task_a, task_b])

    assert "Cycle detected" in caplog.text
    # Returns [] since topo_order is empty when both tasks are in a cycle
    assert path == []


# ---------------------------------------------------------------------------
# get_dependency_graph
# ---------------------------------------------------------------------------


def test_get_dependency_graph_structure(httpx_mock: HTTPXMock) -> None:
    """get_dependency_graph returns correct nodes and edges keys."""
    task_a = _make_task(1)
    task_b = _make_task(2)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        graph = analyzer.get_dependency_graph([task_a, task_b])

    assert "nodes" in graph
    assert "edges" in graph

    node_ids = [n["id"] for n in graph["nodes"]]
    assert 1 in node_ids
    assert 2 in node_ids

    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert edge["task_id"] == 1
    assert edge["opposite_task_id"] == 2
    assert edge["link_label"] == _LINK_LABEL_BLOCKS
    assert not edge["is_cross_project"]
    assert not edge["is_resolved"]


def test_get_dependency_graph_cross_project_only(httpx_mock: HTTPXMock) -> None:
    """get_dependency_graph with cross_project_only=True filters edges."""
    task_a = _make_task(1, project_id=1)
    task_b = _make_task(2, project_id=1)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))
    httpx_mock.add_response(json=_rpc_ok([]))
    httpx_mock.add_response(json=_rpc_ok(_project_data(1)))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        graph = analyzer.get_dependency_graph([task_a, task_b], cross_project_only=True)

    # nodes still includes all input tasks
    assert len(graph["nodes"]) == 2
    # but same-project edge is excluded
    assert graph["edges"] == []


def test_get_dependency_graph_no_edges(httpx_mock: HTTPXMock) -> None:
    """get_dependency_graph with no deps has nodes but empty edges."""
    task_a = _make_task(1)

    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([]))

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        graph = analyzer.get_dependency_graph([task_a])

    assert len(graph["nodes"]) == 1
    assert graph["edges"] == []


# ---------------------------------------------------------------------------
# DependencyEdge model field checks
# ---------------------------------------------------------------------------


def test_dependency_edge_fields_populated(httpx_mock: HTTPXMock) -> None:
    """DependencyEdge has all expected fields correctly populated."""
    task_a = _make_task(1, project_id=1)
    task_b = _make_task(2, project_id=2)

    # Project names fetched during edge processing, before getAllTaskLinks(B)
    httpx_mock.add_response(json=_rpc_ok(_link_types()))
    httpx_mock.add_response(json=_rpc_ok([_task_link(10, 1, 2, 2)]))  # getAllTaskLinks(A)
    httpx_mock.add_response(json=_rpc_ok(_project_data(1, "Alpha")))  # getProjectById(1)
    httpx_mock.add_response(json=_rpc_ok(_project_data(2, "Beta")))  # getProjectById(2)
    httpx_mock.add_response(json=_rpc_ok([]))  # getAllTaskLinks(B)

    with KanboardClient(_URL, _TOKEN) as client:
        analyzer = DependencyAnalyzer(client)
        edges = analyzer.get_dependency_edges([task_a, task_b])

    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, DependencyEdge)
    assert edge.task_id == 1
    assert edge.task_title == "Task 1"
    assert edge.task_project_id == 1
    assert edge.task_project_name == "Alpha"
    assert edge.opposite_task_id == 2
    assert edge.opposite_task_title == "Task 2"
    assert edge.opposite_task_project_id == 2
    assert edge.opposite_task_project_name == "Beta"
    assert edge.link_label == _LINK_LABEL_BLOCKS
    assert edge.is_cross_project
    assert not edge.is_resolved
