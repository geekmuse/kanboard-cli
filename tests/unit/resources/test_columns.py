"""Unit tests for ColumnsResource — all 6 column API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Column
from kanboard.resources.columns import ColumnsResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COLUMN_DATA: dict = {
    "id": "3",
    "title": "In Progress",
    "project_id": "1",
    "task_limit": "5",
    "position": "2",
    "description": "Work in flight",
    "hide_in_dashboard": "0",
}

_COLUMN_DATA_2: dict = {
    "id": "4",
    "title": "Done",
    "project_id": "1",
    "task_limit": "0",
    "position": "3",
    "description": "",
    "hide_in_dashboard": "0",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# get_columns
# ---------------------------------------------------------------------------


def test_get_columns_returns_list_of_column_models(httpx_mock: HTTPXMock) -> None:
    """get_columns() returns a list of Column instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_COLUMN_DATA, _COLUMN_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.get_columns(1)
    assert len(result) == 2
    assert all(isinstance(c, Column) for c in result)


def test_get_columns_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_columns() maps API fields to Column dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok([_COLUMN_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.get_columns(1)
    col = result[0]
    assert col.id == 3
    assert col.title == "In Progress"
    assert col.project_id == 1
    assert col.task_limit == 5
    assert col.position == 2
    assert col.description == "Work in flight"
    assert col.hide_in_dashboard is False


def test_get_columns_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_columns() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.get_columns(99)
    assert result == []


def test_get_columns_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_columns() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.get_columns(99)
    assert result == []


def test_get_columns_returns_empty_list_on_empty_array(httpx_mock: HTTPXMock) -> None:
    """get_columns() returns [] when the API returns an empty array."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.get_columns(99)
    assert result == []


def test_get_columns_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_columns() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.columns.get_columns(1)


# ---------------------------------------------------------------------------
# get_column
# ---------------------------------------------------------------------------


def test_get_column_returns_column_model(httpx_mock: HTTPXMock) -> None:
    """get_column() returns a Column instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_COLUMN_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.get_column(3)
    assert isinstance(result, Column)
    assert result.id == 3
    assert result.title == "In Progress"


def test_get_column_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_column() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Column '99' does not exist"):
            client.columns.get_column(99)


def test_get_column_not_found_carries_resource_info(httpx_mock: HTTPXMock) -> None:
    """get_column() KanboardNotFoundError carries resource and identifier attributes."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.columns.get_column(42)
    err = exc_info.value
    assert err.resource == "Column"
    assert err.identifier == 42


def test_get_column_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_column() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.columns.get_column(3)


# ---------------------------------------------------------------------------
# change_column_position
# ---------------------------------------------------------------------------


def test_change_column_position_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """change_column_position() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.change_column_position(1, 3, 2)
    assert result is True


def test_change_column_position_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """change_column_position() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.change_column_position(1, 99, 5)
    assert result is False


def test_change_column_position_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """change_column_position() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Position conflict"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Position conflict"):
            client.columns.change_column_position(1, 3, 2)


# ---------------------------------------------------------------------------
# update_column
# ---------------------------------------------------------------------------


def test_update_column_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_column() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.update_column(3, "New Title")
    assert result is True


def test_update_column_accepts_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_column() forwards kwargs (task_limit, description) to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.update_column(3, "Review", task_limit=3, description="QA")
    assert result is True


def test_update_column_raises_api_error_on_false(httpx_mock: HTTPXMock) -> None:
    """update_column() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update column 3"):
            client.columns.update_column(3, "Bad Title")


def test_update_column_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """update_column() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.columns.update_column(3, "Title")


# ---------------------------------------------------------------------------
# add_column
# ---------------------------------------------------------------------------


def test_add_column_returns_new_column_id(httpx_mock: HTTPXMock) -> None:
    """add_column() returns the integer ID of the newly created column."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.add_column(1, "New Column")
    assert result == 7


def test_add_column_accepts_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """add_column() forwards kwargs (task_limit, description) to the API."""
    httpx_mock.add_response(json=_rpc_ok(8))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.add_column(1, "QA", task_limit=2, description="Quality checks")
    assert result == 8


def test_add_column_raises_api_error_on_false(httpx_mock: HTTPXMock) -> None:
    """add_column() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to add column"):
            client.columns.add_column(1, "Bad Column")


def test_add_column_raises_api_error_on_zero(httpx_mock: HTTPXMock) -> None:
    """add_column() raises KanboardAPIError when the API returns 0 (falsy)."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.columns.add_column(1, "Zero ID Column")


def test_add_column_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """add_column() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Project not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Project not found"):
            client.columns.add_column(99, "Column")


# ---------------------------------------------------------------------------
# remove_column
# ---------------------------------------------------------------------------


def test_remove_column_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_column() returns True when the API confirms deletion."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.remove_column(3)
    assert result is True


def test_remove_column_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """remove_column() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.columns.remove_column(99)
    assert result is False


def test_remove_column_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_column() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Column has tasks"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Column has tasks"):
            client.columns.remove_column(3)


# ---------------------------------------------------------------------------
# ColumnsResource accessor and importability
# ---------------------------------------------------------------------------


def test_columns_resource_accessible_on_client() -> None:
    """KanboardClient.columns is a ColumnsResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.columns, ColumnsResource)


def test_columns_resource_importable_from_kanboard() -> None:
    """ColumnsResource is importable directly from the kanboard package."""
    import kanboard

    assert kanboard.ColumnsResource is ColumnsResource
