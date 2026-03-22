"""Unit tests for TasksResource — all 14 task API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Task

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TASK_DATA: dict = {
    "id": "1",
    "title": "Test Task",
    "description": "A test task",
    "date_creation": "1711077600",
    "date_modification": "1711077600",
    "date_due": None,
    "date_completed": None,
    "date_moved": None,
    "color_id": "yellow",
    "project_id": "1",
    "column_id": "1",
    "swimlane_id": "0",
    "owner_id": "0",
    "creator_id": "1",
    "category_id": "0",
    "is_active": "1",
    "priority": "0",
    "score": "0",
    "position": "1",
    "reference": "",
    "tags": [],
    "url": "http://kanboard.test/?controller=TaskViewController&action=show&task_id=1",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


def test_create_task_returns_new_id(httpx_mock: HTTPXMock) -> None:
    """create_task() returns the new task ID as an integer on success."""
    httpx_mock.add_response(json=_rpc_ok(42))
    with KanboardClient(_URL, _TOKEN) as client:
        task_id = client.tasks.create_task("My Task", project_id=1)
    assert task_id == 42


def test_create_task_with_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_task() passes optional kwargs to the API call."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        task_id = client.tasks.create_task("My Task", project_id=1, color_id="blue", score=5)
    assert task_id == 7


def test_create_task_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_task() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createTask"):
            client.tasks.create_task("Bad Task", project_id=99)


def test_create_task_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_task() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.tasks.create_task("Blocked Task", project_id=1)


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------


def test_get_task_returns_task_instance(httpx_mock: HTTPXMock) -> None:
    """get_task() returns a populated Task dataclass for a valid task_id."""
    httpx_mock.add_response(json=_rpc_ok(_TASK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        task = client.tasks.get_task(1)
    assert isinstance(task, Task)
    assert task.id == 1
    assert task.title == "Test Task"
    assert task.is_active is True


def test_get_task_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.tasks.get_task(999)
    assert "999" in str(exc_info.value)


def test_get_task_not_found_identifies_resource(httpx_mock: HTTPXMock) -> None:
    """get_task() KanboardNotFoundError carries resource='Task'."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.tasks.get_task(42)
    assert exc_info.value.resource == "Task"
    assert exc_info.value.identifier == "42"


# ---------------------------------------------------------------------------
# get_task_by_reference
# ---------------------------------------------------------------------------


def test_get_task_by_reference_returns_task(httpx_mock: HTTPXMock) -> None:
    """get_task_by_reference() returns a Task for a valid reference."""
    data = dict(_TASK_DATA)
    data["reference"] = "REF-001"
    httpx_mock.add_response(json=_rpc_ok(data))
    with KanboardClient(_URL, _TOKEN) as client:
        task = client.tasks.get_task_by_reference(project_id=1, reference="REF-001")
    assert isinstance(task, Task)
    assert task.reference == "REF-001"


def test_get_task_by_reference_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_by_reference() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.tasks.get_task_by_reference(project_id=1, reference="NOPE")
    assert "NOPE" in str(exc_info.value)
    assert exc_info.value.identifier == "NOPE"


# ---------------------------------------------------------------------------
# get_all_tasks
# ---------------------------------------------------------------------------


def test_get_all_tasks_returns_list_of_tasks(httpx_mock: HTTPXMock) -> None:
    """get_all_tasks() returns a list of Task instances."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.get_all_tasks(project_id=1)
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)


def test_get_all_tasks_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_tasks() returns an empty list when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.get_all_tasks(project_id=1) == []


def test_get_all_tasks_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_tasks() returns an empty list when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.get_all_tasks(project_id=1) == []


def test_get_all_tasks_with_inactive_status(httpx_mock: HTTPXMock) -> None:
    """get_all_tasks() passes status_id=0 for inactive tasks."""
    closed = dict(_TASK_DATA)
    closed["is_active"] = "0"
    httpx_mock.add_response(json=_rpc_ok([closed]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.get_all_tasks(project_id=1, status_id=0)
    assert len(tasks) == 1
    assert tasks[0].is_active is False


def test_get_all_tasks_multiple_results(httpx_mock: HTTPXMock) -> None:
    """get_all_tasks() returns multiple Task instances from the API response."""
    task2 = dict(_TASK_DATA)
    task2["id"] = "2"
    task2["title"] = "Second Task"
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA, task2]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.get_all_tasks(project_id=1)
    assert len(tasks) == 2
    assert tasks[1].title == "Second Task"


# ---------------------------------------------------------------------------
# get_overdue_tasks
# ---------------------------------------------------------------------------


def test_get_overdue_tasks_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_overdue_tasks() returns a list of Task instances."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.get_overdue_tasks()
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)


def test_get_overdue_tasks_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_overdue_tasks() returns empty list when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.get_overdue_tasks() == []


def test_get_overdue_tasks_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_overdue_tasks() returns empty list when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.get_overdue_tasks() == []


# ---------------------------------------------------------------------------
# get_overdue_tasks_by_project
# ---------------------------------------------------------------------------


def test_get_overdue_tasks_by_project_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_overdue_tasks_by_project() returns a list of Task instances."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.get_overdue_tasks_by_project(project_id=1)
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)


def test_get_overdue_tasks_by_project_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_overdue_tasks_by_project() returns empty list when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.get_overdue_tasks_by_project(project_id=1) == []


def test_get_overdue_tasks_by_project_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_overdue_tasks_by_project() returns empty list when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.get_overdue_tasks_by_project(project_id=1) == []


# ---------------------------------------------------------------------------
# update_task
# ---------------------------------------------------------------------------


def test_update_task_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_task() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tasks.update_task(1, title="Updated Title")
    assert result is True


def test_update_task_with_multiple_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_task() passes all kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tasks.update_task(1, title="New", color_id="red", score=3)
    assert result is True


def test_update_task_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_task() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="updateTask"):
            client.tasks.update_task(999, title="Bad update")


# ---------------------------------------------------------------------------
# open_task
# ---------------------------------------------------------------------------


def test_open_task_returns_true(httpx_mock: HTTPXMock) -> None:
    """open_task() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.open_task(1) is True


def test_open_task_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """open_task() returns False when the API returns False (already open)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.open_task(1) is False


# ---------------------------------------------------------------------------
# close_task
# ---------------------------------------------------------------------------


def test_close_task_returns_true(httpx_mock: HTTPXMock) -> None:
    """close_task() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.close_task(1) is True


def test_close_task_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """close_task() returns False when the API returns False (already closed)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.close_task(1) is False


# ---------------------------------------------------------------------------
# remove_task
# ---------------------------------------------------------------------------


def test_remove_task_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_task() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.remove_task(1) is True


def test_remove_task_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """remove_task() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.remove_task(1) is False


# ---------------------------------------------------------------------------
# move_task_position
# ---------------------------------------------------------------------------


def test_move_task_position_returns_true(httpx_mock: HTTPXMock) -> None:
    """move_task_position() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tasks.move_task_position(
            project_id=1, task_id=1, column_id=2, position=1, swimlane_id=0
        )
    assert result is True


def test_move_task_position_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """move_task_position() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tasks.move_task_position(
            project_id=1, task_id=1, column_id=2, position=1, swimlane_id=0
        )
    assert result is False


# ---------------------------------------------------------------------------
# move_task_to_project
# ---------------------------------------------------------------------------


def test_move_task_to_project_returns_true(httpx_mock: HTTPXMock) -> None:
    """move_task_to_project() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tasks.move_task_to_project(task_id=1, project_id=2)
    assert result is True


def test_move_task_to_project_with_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """move_task_to_project() passes optional placement kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tasks.move_task_to_project(
            task_id=1, project_id=2, swimlane_id=1, column_id=3
        )
    assert result is True


def test_move_task_to_project_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """move_task_to_project() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.move_task_to_project(task_id=1, project_id=99) is False


# ---------------------------------------------------------------------------
# duplicate_task_to_project
# ---------------------------------------------------------------------------


def test_duplicate_task_to_project_returns_new_task_id(httpx_mock: HTTPXMock) -> None:
    """duplicate_task_to_project() returns the new task ID as an integer."""
    httpx_mock.add_response(json=_rpc_ok(99))
    with KanboardClient(_URL, _TOKEN) as client:
        new_id = client.tasks.duplicate_task_to_project(task_id=1, project_id=2)
    assert new_id == 99


def test_duplicate_task_to_project_with_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """duplicate_task_to_project() passes optional placement kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(55))
    with KanboardClient(_URL, _TOKEN) as client:
        new_id = client.tasks.duplicate_task_to_project(
            task_id=1, project_id=2, swimlane_id=1, column_id=3
        )
    assert new_id == 55


# ---------------------------------------------------------------------------
# search_tasks
# ---------------------------------------------------------------------------


def test_search_tasks_returns_list_of_tasks(httpx_mock: HTTPXMock) -> None:
    """search_tasks() returns a list of Task instances for a matching query."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.search_tasks(project_id=1, query="test")
    assert len(tasks) == 1
    assert isinstance(tasks[0], Task)


def test_search_tasks_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """search_tasks() returns empty list when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.search_tasks(project_id=1, query="nope") == []


def test_search_tasks_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """search_tasks() returns empty list when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.tasks.search_tasks(project_id=1, query="nope") == []


def test_search_tasks_multiple_results(httpx_mock: HTTPXMock) -> None:
    """search_tasks() returns multiple Task instances from the API response."""
    task2 = dict(_TASK_DATA)
    task2["id"] = "2"
    task2["title"] = "Second Task"
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA, task2]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.tasks.search_tasks(project_id=1, query="task")
    assert len(tasks) == 2
    assert tasks[1].title == "Second Task"


# ---------------------------------------------------------------------------
# TasksResource accessor on KanboardClient
# ---------------------------------------------------------------------------


def test_tasks_resource_accessible_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient.tasks is a TasksResource instance."""
    from kanboard.resources.tasks import TasksResource

    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.tasks, TasksResource)
