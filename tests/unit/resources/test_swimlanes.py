"""Unit tests for SwimlanesResource — all 11 swimlane API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Swimlane
from kanboard.resources.swimlanes import SwimlanesResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SWIMLANE_DATA: dict = {
    "id": "2",
    "name": "Feature Lane",
    "project_id": "1",
    "position": "1",
    "is_active": "1",
    "description": "Active feature work",
}

_SWIMLANE_DATA_2: dict = {
    "id": "3",
    "name": "Bug Lane",
    "project_id": "1",
    "position": "2",
    "is_active": "0",
    "description": "Bug fixes",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# get_active_swimlanes
# ---------------------------------------------------------------------------


def test_get_active_swimlanes_returns_list_of_swimlane_models(httpx_mock: HTTPXMock) -> None:
    """get_active_swimlanes() returns a list of Swimlane instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_SWIMLANE_DATA, _SWIMLANE_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_active_swimlanes(1)
    assert len(result) == 2
    assert all(isinstance(s, Swimlane) for s in result)


def test_get_active_swimlanes_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_active_swimlanes() maps API fields to Swimlane dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok([_SWIMLANE_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_active_swimlanes(1)
    lane = result[0]
    assert lane.id == 2
    assert lane.name == "Feature Lane"
    assert lane.project_id == 1
    assert lane.position == 1
    assert lane.is_active is True
    assert lane.description == "Active feature work"


def test_get_active_swimlanes_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_active_swimlanes() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_active_swimlanes(99)
    assert result == []


def test_get_active_swimlanes_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_active_swimlanes() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_active_swimlanes(99)
    assert result == []


def test_get_active_swimlanes_returns_empty_list_on_empty_array(httpx_mock: HTTPXMock) -> None:
    """get_active_swimlanes() returns [] when the API returns an empty array."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_active_swimlanes(99)
    assert result == []


def test_get_active_swimlanes_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_active_swimlanes() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.swimlanes.get_active_swimlanes(1)


# ---------------------------------------------------------------------------
# get_all_swimlanes
# ---------------------------------------------------------------------------


def test_get_all_swimlanes_returns_list_of_swimlane_models(httpx_mock: HTTPXMock) -> None:
    """get_all_swimlanes() returns a list of Swimlane instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_SWIMLANE_DATA, _SWIMLANE_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_all_swimlanes(1)
    assert len(result) == 2
    assert all(isinstance(s, Swimlane) for s in result)


def test_get_all_swimlanes_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_swimlanes() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_all_swimlanes(99)
    assert result == []


def test_get_all_swimlanes_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_swimlanes() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_all_swimlanes(99)
    assert result == []


def test_get_all_swimlanes_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_swimlanes() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.swimlanes.get_all_swimlanes(1)


# ---------------------------------------------------------------------------
# get_swimlane
# ---------------------------------------------------------------------------


def test_get_swimlane_returns_swimlane_model(httpx_mock: HTTPXMock) -> None:
    """get_swimlane() returns a Swimlane instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_SWIMLANE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_swimlane(2)
    assert isinstance(result, Swimlane)
    assert result.id == 2
    assert result.name == "Feature Lane"


def test_get_swimlane_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_swimlane() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Swimlane '99' does not exist"):
            client.swimlanes.get_swimlane(99)


def test_get_swimlane_not_found_carries_resource_info(httpx_mock: HTTPXMock) -> None:
    """get_swimlane() KanboardNotFoundError carries resource and identifier attributes."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.swimlanes.get_swimlane(42)
    err = exc_info.value
    assert err.resource == "Swimlane"
    assert err.identifier == 42


def test_get_swimlane_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_swimlane() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.swimlanes.get_swimlane(2)


# ---------------------------------------------------------------------------
# get_swimlane_by_id
# ---------------------------------------------------------------------------


def test_get_swimlane_by_id_returns_swimlane_model(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_id() returns a Swimlane instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_SWIMLANE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_swimlane_by_id(2)
    assert isinstance(result, Swimlane)
    assert result.id == 2


def test_get_swimlane_by_id_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_id() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Swimlane '77' does not exist"):
            client.swimlanes.get_swimlane_by_id(77)


def test_get_swimlane_by_id_not_found_carries_resource_info(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_id() KanboardNotFoundError carries resource and identifier attributes."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.swimlanes.get_swimlane_by_id(55)
    err = exc_info.value
    assert err.resource == "Swimlane"
    assert err.identifier == 55


def test_get_swimlane_by_id_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_id() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Not permitted"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Not permitted"):
            client.swimlanes.get_swimlane_by_id(2)


# ---------------------------------------------------------------------------
# get_swimlane_by_name
# ---------------------------------------------------------------------------


def test_get_swimlane_by_name_returns_swimlane_model(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_name() returns a Swimlane instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_SWIMLANE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.get_swimlane_by_name(1, "Feature Lane")
    assert isinstance(result, Swimlane)
    assert result.name == "Feature Lane"


def test_get_swimlane_by_name_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_name() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Swimlane 'Ghost Lane' does not exist"):
            client.swimlanes.get_swimlane_by_name(1, "Ghost Lane")


def test_get_swimlane_by_name_not_found_carries_resource_info(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_name() KanboardNotFoundError carries resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.swimlanes.get_swimlane_by_name(1, "Missing")
    err = exc_info.value
    assert err.resource == "Swimlane"
    assert err.identifier == "Missing"


def test_get_swimlane_by_name_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_swimlane_by_name() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Project not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Project not found"):
            client.swimlanes.get_swimlane_by_name(99, "Lane")


# ---------------------------------------------------------------------------
# change_swimlane_position
# ---------------------------------------------------------------------------


def test_change_swimlane_position_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """change_swimlane_position() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.change_swimlane_position(1, 2, 3)
    assert result is True


def test_change_swimlane_position_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """change_swimlane_position() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.change_swimlane_position(1, 99, 5)
    assert result is False


def test_change_swimlane_position_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """change_swimlane_position() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Position conflict"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Position conflict"):
            client.swimlanes.change_swimlane_position(1, 2, 99)


# ---------------------------------------------------------------------------
# update_swimlane
# ---------------------------------------------------------------------------


def test_update_swimlane_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_swimlane() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.update_swimlane(1, 2, "Renamed Lane")
    assert result is True


def test_update_swimlane_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """update_swimlane() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.update_swimlane(1, 99, "No Lane")
    assert result is False


def test_update_swimlane_accepts_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_swimlane() forwards kwargs (description) to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.update_swimlane(1, 2, "Sprint Lane", description="Sprint work")
    assert result is True


def test_update_swimlane_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_swimlane() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.swimlanes.update_swimlane(1, 2, "Lane")


# ---------------------------------------------------------------------------
# add_swimlane
# ---------------------------------------------------------------------------


def test_add_swimlane_returns_new_swimlane_id(httpx_mock: HTTPXMock) -> None:
    """add_swimlane() returns the integer ID of the newly created swimlane."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.add_swimlane(1, "New Lane")
    assert result == 5


def test_add_swimlane_accepts_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """add_swimlane() forwards kwargs (description) to the API."""
    httpx_mock.add_response(json=_rpc_ok(6))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.add_swimlane(1, "Sprint", description="Sprint swimlane")
    assert result == 6


def test_add_swimlane_raises_api_error_on_false(httpx_mock: HTTPXMock) -> None:
    """add_swimlane() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to add swimlane"):
            client.swimlanes.add_swimlane(1, "Bad Lane")


def test_add_swimlane_raises_api_error_on_zero(httpx_mock: HTTPXMock) -> None:
    """add_swimlane() raises KanboardAPIError when the API returns 0 (falsy)."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.swimlanes.add_swimlane(1, "Zero ID Lane")


def test_add_swimlane_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """add_swimlane() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Project not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Project not found"):
            client.swimlanes.add_swimlane(99, "Lane")


# ---------------------------------------------------------------------------
# remove_swimlane
# ---------------------------------------------------------------------------


def test_remove_swimlane_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_swimlane() returns True when the API confirms deletion."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.remove_swimlane(1, 2)
    assert result is True


def test_remove_swimlane_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """remove_swimlane() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.remove_swimlane(1, 99)
    assert result is False


def test_remove_swimlane_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_swimlane() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Swimlane has tasks"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Swimlane has tasks"):
            client.swimlanes.remove_swimlane(1, 2)


# ---------------------------------------------------------------------------
# disable_swimlane
# ---------------------------------------------------------------------------


def test_disable_swimlane_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """disable_swimlane() returns True when the API confirms the operation."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.disable_swimlane(1, 2)
    assert result is True


def test_disable_swimlane_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """disable_swimlane() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.disable_swimlane(1, 99)
    assert result is False


def test_disable_swimlane_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """disable_swimlane() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Operation not allowed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Operation not allowed"):
            client.swimlanes.disable_swimlane(1, 2)


# ---------------------------------------------------------------------------
# enable_swimlane
# ---------------------------------------------------------------------------


def test_enable_swimlane_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """enable_swimlane() returns True when the API confirms the operation."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.enable_swimlane(1, 2)
    assert result is True


def test_enable_swimlane_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """enable_swimlane() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.swimlanes.enable_swimlane(1, 99)
    assert result is False


def test_enable_swimlane_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """enable_swimlane() raises KanboardAPIError on a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Enable failed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Enable failed"):
            client.swimlanes.enable_swimlane(1, 2)


# ---------------------------------------------------------------------------
# SwimlanesResource accessor and importability
# ---------------------------------------------------------------------------


def test_swimlanes_resource_accessible_on_client() -> None:
    """KanboardClient.swimlanes is a SwimlanesResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.swimlanes, SwimlanesResource)


def test_swimlanes_resource_importable_from_kanboard() -> None:
    """SwimlanesResource is importable directly from the kanboard package."""
    import kanboard

    assert kanboard.SwimlanesResource is SwimlanesResource
