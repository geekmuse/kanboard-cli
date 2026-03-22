"""Unit tests for GroupsResource - all 5 group API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError, KanboardNotFoundError
from kanboard.models import Group
from kanboard.resources.groups import GroupsResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GROUP_DATA: dict = {
    "id": "1",
    "name": "Developers",
    "external_id": "",
}

_GROUP_DATA_2: dict = {
    "id": "2",
    "name": "Designers",
    "external_id": "ldap-456",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_group
# ---------------------------------------------------------------------------


def test_create_group_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_group() returns the integer ID of the new group."""
    httpx_mock.add_response(json=_rpc_ok(1))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.create_group("Developers")
    assert result == 1
    assert isinstance(result, int)


def test_create_group_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_group() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create group"):
            client.groups.create_group("Developers")


def test_create_group_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_group() raises KanboardAPIError when API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.groups.create_group("Developers")


def test_create_group_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """create_group() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.groups.create_group("Developers")


def test_create_group_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_group() accepts and forwards extra keyword arguments."""
    httpx_mock.add_response(json=_rpc_ok(3))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.create_group("External", external_id="ldap-123")
    assert result == 3


# ---------------------------------------------------------------------------
# get_group
# ---------------------------------------------------------------------------


def test_get_group_returns_model(httpx_mock: HTTPXMock) -> None:
    """get_group() returns a Group instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_GROUP_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.get_group(1)
    assert isinstance(result, Group)


def test_get_group_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_group() maps API fields to Group dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok(_GROUP_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        g = client.groups.get_group(1)
    assert g.id == 1
    assert g.name == "Developers"
    assert g.external_id == ""


def test_get_group_with_external_id(httpx_mock: HTTPXMock) -> None:
    """get_group() correctly maps external_id field."""
    httpx_mock.add_response(json=_rpc_ok(_GROUP_DATA_2))
    with KanboardClient(_URL, _TOKEN) as client:
        g = client.groups.get_group(2)
    assert g.id == 2
    assert g.name == "Designers"
    assert g.external_id == "ldap-456"


def test_get_group_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_group() raises KanboardNotFoundError when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.groups.get_group(999)
    err = exc_info.value
    assert err.resource == "Group"
    assert err.identifier == 999


def test_get_group_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_group() raises KanboardNotFoundError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError):
            client.groups.get_group(999)


def test_get_group_not_found_message(httpx_mock: HTTPXMock) -> None:
    """get_group() not-found message includes the group ID."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(
            KanboardNotFoundError,
            match=r"Not found: Group '999' does not exist",
        ):
            client.groups.get_group(999)


def test_get_group_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_group() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.groups.get_group(1)


# ---------------------------------------------------------------------------
# get_all_groups
# ---------------------------------------------------------------------------


def test_get_all_groups_returns_list_of_models(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() returns a list of Group instances."""
    httpx_mock.add_response(json=_rpc_ok([_GROUP_DATA, _GROUP_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.get_all_groups()
    assert len(result) == 2
    assert all(isinstance(g, Group) for g in result)


def test_get_all_groups_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() maps fields correctly for the first group."""
    httpx_mock.add_response(json=_rpc_ok([_GROUP_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.get_all_groups()
    g = result[0]
    assert g.id == 1
    assert g.name == "Developers"


def test_get_all_groups_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.get_all_groups()
    assert result == []


def test_get_all_groups_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.get_all_groups()
    assert result == []


def test_get_all_groups_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() returns [] when API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.get_all_groups()
    assert result == []


def test_get_all_groups_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.groups.get_all_groups()


# ---------------------------------------------------------------------------
# update_group
# ---------------------------------------------------------------------------


def test_update_group_returns_true(httpx_mock: HTTPXMock) -> None:
    """update_group() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.update_group(1, name="New Name")
    assert result is True


def test_update_group_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_group() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update group"):
            client.groups.update_group(1, name="New Name")


def test_update_group_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_group() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Group not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Group not found"):
            client.groups.update_group(999, name="New Name")


def test_update_group_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_group() forwards keyword arguments to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.update_group(1, name="New", external_id="ext-1")
    assert result is True


# ---------------------------------------------------------------------------
# remove_group
# ---------------------------------------------------------------------------


def test_remove_group_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_group() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.remove_group(1)
    assert result is True


def test_remove_group_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_group() returns False when API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.groups.remove_group(999)
    assert result is False


def test_remove_group_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_group() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.groups.remove_group(1)


# ---------------------------------------------------------------------------
# Network failure tests
# ---------------------------------------------------------------------------


def test_create_group_network_failure(httpx_mock: HTTPXMock) -> None:
    """create_group() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.groups.create_group("Developers")


def test_get_group_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_group() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.groups.get_group(1)


def test_get_all_groups_connection_error(httpx_mock: HTTPXMock) -> None:
    """get_all_groups() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.groups.get_all_groups()


def test_update_group_network_failure(httpx_mock: HTTPXMock) -> None:
    """update_group() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.groups.update_group(1, name="New")


def test_remove_group_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_group() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.groups.remove_group(1)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_groups_resource_wired_on_client() -> None:
    """KanboardClient exposes a GroupsResource instance as .groups."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.groups, GroupsResource)


def test_groups_resource_importable_from_kanboard() -> None:
    """GroupsResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "GroupsResource")
    assert kanboard.GroupsResource is GroupsResource
