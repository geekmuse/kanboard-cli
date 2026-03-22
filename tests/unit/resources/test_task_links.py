"""Unit tests for TaskLinksResource — all 5 internal task-link API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import TaskLink
from kanboard.resources.task_links import TaskLinksResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TASK_LINK_DATA: dict = {
    "id": "1",
    "task_id": "10",
    "opposite_task_id": "20",
    "link_id": "2",
}

_TASK_LINK_DATA_2: dict = {
    "id": "2",
    "task_id": "10",
    "opposite_task_id": "30",
    "link_id": "3",
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
# create_task_link
# ---------------------------------------------------------------------------


def test_create_task_link_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_task_link() returns the new task link ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.create_task_link(task_id=10, opposite_task_id=20, link_id=1)
    assert result == 5
    assert isinstance(result, int)


def test_create_task_link_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_task_link() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create task link"):
            client.task_links.create_task_link(task_id=10, opposite_task_id=20, link_id=1)


def test_create_task_link_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_task_link() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create task link"):
            client.task_links.create_task_link(task_id=10, opposite_task_id=20, link_id=1)


def test_create_task_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_task_link() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.task_links.create_task_link(task_id=10, opposite_task_id=20, link_id=1)


# ---------------------------------------------------------------------------
# update_task_link
# ---------------------------------------------------------------------------


def test_update_task_link_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_task_link() returns True when the API succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.update_task_link(
            task_link_id=1, task_id=10, opposite_task_id=20, link_id=1
        )
    assert result is True


def test_update_task_link_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_task_link() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update task link"):
            client.task_links.update_task_link(
                task_link_id=99, task_id=10, opposite_task_id=20, link_id=1
            )


def test_update_task_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """update_task_link() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.task_links.update_task_link(
                task_link_id=1, task_id=10, opposite_task_id=20, link_id=1
            )


# ---------------------------------------------------------------------------
# get_task_link_by_id
# ---------------------------------------------------------------------------


def test_get_task_link_by_id_returns_task_link_model(httpx_mock: HTTPXMock) -> None:
    """get_task_link_by_id() returns a TaskLink instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_TASK_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_task_link_by_id(task_link_id=1)
    assert isinstance(result, TaskLink)


def test_get_task_link_by_id_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_task_link_by_id() maps all API fields to the TaskLink dataclass correctly."""
    httpx_mock.add_response(json=_rpc_ok(_TASK_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_task_link_by_id(task_link_id=1)
    assert result.id == 1
    assert result.task_id == 10
    assert result.opposite_task_id == 20
    assert result.link_id == 2


def test_get_task_link_by_id_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_task_link_by_id() raises KanboardNotFoundError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="TaskLink"):
            client.task_links.get_task_link_by_id(task_link_id=999)


def test_get_task_link_by_id_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_link_by_id() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="TaskLink"):
            client.task_links.get_task_link_by_id(task_link_id=999)


def test_get_task_link_by_id_not_found_error_attributes(httpx_mock: HTTPXMock) -> None:
    """get_task_link_by_id() KanboardNotFoundError carries correct resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.task_links.get_task_link_by_id(task_link_id=999)
    err = exc_info.value
    assert err.resource == "TaskLink"
    assert err.identifier == 999


def test_get_task_link_by_id_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_task_link_by_id() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.task_links.get_task_link_by_id(task_link_id=1)


# ---------------------------------------------------------------------------
# get_all_task_links
# ---------------------------------------------------------------------------


def test_get_all_task_links_returns_list_of_task_link_models(
    httpx_mock: HTTPXMock,
) -> None:
    """get_all_task_links() returns a list of TaskLink instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_LINK_DATA, _TASK_LINK_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_all_task_links(task_id=10)
    assert len(result) == 2
    assert all(isinstance(tl, TaskLink) for tl in result)


def test_get_all_task_links_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_all_task_links() maps API fields correctly for each TaskLink."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_LINK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_all_task_links(task_id=10)
    tl = result[0]
    assert tl.id == 1
    assert tl.task_id == 10
    assert tl.opposite_task_id == 20
    assert tl.link_id == 2


def test_get_all_task_links_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_task_links() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_all_task_links(task_id=10)
    assert result == []


def test_get_all_task_links_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_task_links() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_all_task_links(task_id=10)
    assert result == []


def test_get_all_task_links_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_task_links() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.get_all_task_links(task_id=10)
    assert result == []


def test_get_all_task_links_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_all_task_links() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.task_links.get_all_task_links(task_id=10)


# ---------------------------------------------------------------------------
# remove_task_link
# ---------------------------------------------------------------------------


def test_remove_task_link_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_task_link() returns True when the API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.remove_task_link(task_link_id=1)
    assert result is True


def test_remove_task_link_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """remove_task_link() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_links.remove_task_link(task_link_id=999)
    assert result is False


def test_remove_task_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """remove_task_link() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.task_links.remove_task_link(task_link_id=1)


# ---------------------------------------------------------------------------
# Resource wiring and importability
# ---------------------------------------------------------------------------


def test_task_links_resource_is_wired_on_client() -> None:
    """KanboardClient exposes .task_links as a TaskLinksResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.task_links, TaskLinksResource)


def test_task_links_resource_importable_from_kanboard() -> None:
    """TaskLinksResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "TaskLinksResource")
    assert kanboard.TaskLinksResource is TaskLinksResource
