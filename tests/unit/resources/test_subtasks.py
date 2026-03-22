"""Unit tests for SubtasksResource — all 5 subtask API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Subtask
from kanboard.resources.subtasks import SubtasksResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUBTASK_DATA: dict = {
    "id": "5",
    "title": "Write unit tests",
    "task_id": "42",
    "user_id": "2",
    "status": "1",
    "time_estimated": "3.5",
    "time_spent": "1.0",
    "position": "1",
    "username": "jdoe",
    "name": "John Doe",
}

_SUBTASK_DATA_2: dict = {
    "id": "6",
    "title": "Review PR",
    "task_id": "42",
    "user_id": "3",
    "status": "0",
    "time_estimated": "1.0",
    "time_spent": "0.0",
    "position": "2",
    "username": "jsmith",
    "name": "Jane Smith",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


# ---------------------------------------------------------------------------
# create_subtask
# ---------------------------------------------------------------------------


def test_create_subtask_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_subtask() returns the new subtask ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.create_subtask(task_id=42, title="Write unit tests")
    assert result == 5
    assert isinstance(result, int)


def test_create_subtask_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_subtask() forwards optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.create_subtask(
            task_id=42, title="Write tests", user_id=2, time_estimated=3.5, status=0
        )
    assert result == 7


def test_create_subtask_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_subtask() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create subtask"):
            client.subtasks.create_subtask(task_id=42, title="Fail task")


def test_create_subtask_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_subtask() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.subtasks.create_subtask(task_id=42, title="Error task")


# ---------------------------------------------------------------------------
# get_subtask
# ---------------------------------------------------------------------------


def test_get_subtask_returns_subtask_model(httpx_mock: HTTPXMock) -> None:
    """get_subtask() returns a Subtask instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_SUBTASK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_subtask(subtask_id=5)
    assert isinstance(result, Subtask)


def test_get_subtask_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_subtask() maps all API fields to the Subtask dataclass correctly."""
    httpx_mock.add_response(json=_rpc_ok(_SUBTASK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_subtask(subtask_id=5)
    assert result.id == 5
    assert result.title == "Write unit tests"
    assert result.task_id == 42
    assert result.user_id == 2
    assert result.status == 1
    assert result.time_estimated == 3.5
    assert result.time_spent == 1.0
    assert result.position == 1
    assert result.username == "jdoe"
    assert result.name == "John Doe"


def test_get_subtask_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_subtask() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Subtask"):
            client.subtasks.get_subtask(subtask_id=999)


def test_get_subtask_not_found_error_attributes(httpx_mock: HTTPXMock) -> None:
    """get_subtask() KanboardNotFoundError carries correct resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.subtasks.get_subtask(subtask_id=999)
    err = exc_info.value
    assert err.resource == "Subtask"
    assert err.identifier == 999


def test_get_subtask_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_subtask() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.subtasks.get_subtask(subtask_id=5)


# ---------------------------------------------------------------------------
# get_all_subtasks
# ---------------------------------------------------------------------------


def test_get_all_subtasks_returns_list_of_subtask_models(httpx_mock: HTTPXMock) -> None:
    """get_all_subtasks() returns a list of Subtask instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_SUBTASK_DATA, _SUBTASK_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_all_subtasks(task_id=42)
    assert len(result) == 2
    assert all(isinstance(s, Subtask) for s in result)


def test_get_all_subtasks_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_all_subtasks() maps API fields correctly for each Subtask."""
    httpx_mock.add_response(json=_rpc_ok([_SUBTASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_all_subtasks(task_id=42)
    subtask = result[0]
    assert subtask.id == 5
    assert subtask.title == "Write unit tests"
    assert subtask.task_id == 42


def test_get_all_subtasks_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_subtasks() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_all_subtasks(task_id=42)
    assert result == []


def test_get_all_subtasks_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_subtasks() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_all_subtasks(task_id=42)
    assert result == []


def test_get_all_subtasks_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_subtasks() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.get_all_subtasks(task_id=42)
    assert result == []


def test_get_all_subtasks_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_all_subtasks() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.subtasks.get_all_subtasks(task_id=42)


# ---------------------------------------------------------------------------
# update_subtask
# ---------------------------------------------------------------------------


def test_update_subtask_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_subtask() returns True when the API succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.update_subtask(id=5, task_id=42, title="Updated title")
    assert result is True


def test_update_subtask_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_subtask() forwards optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.update_subtask(id=5, task_id=42, status=2, time_spent=2.5)
    assert result is True


def test_update_subtask_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_subtask() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update subtask"):
            client.subtasks.update_subtask(id=5, task_id=42)


def test_update_subtask_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """update_subtask() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.subtasks.update_subtask(id=5, task_id=42)


# ---------------------------------------------------------------------------
# remove_subtask
# ---------------------------------------------------------------------------


def test_remove_subtask_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_subtask() returns True when the API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.remove_subtask(subtask_id=5)
    assert result is True


def test_remove_subtask_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """remove_subtask() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtasks.remove_subtask(subtask_id=999)
    assert result is False


def test_remove_subtask_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """remove_subtask() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.subtasks.remove_subtask(subtask_id=5)


# ---------------------------------------------------------------------------
# Resource wiring and importability
# ---------------------------------------------------------------------------


def test_subtasks_resource_is_wired_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes .subtasks as a SubtasksResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.subtasks, SubtasksResource)


def test_subtasks_resource_importable_from_kanboard() -> None:
    """SubtasksResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "SubtasksResource")
    assert kanboard.SubtasksResource is SubtasksResource
