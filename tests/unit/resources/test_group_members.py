"""Unit tests for GroupMembersResource - all 5 group member API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError
from kanboard.models import Group, User
from kanboard.resources.group_members import GroupMembersResource

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

_USER_DATA: dict = {
    "id": "10",
    "username": "alice",
    "name": "Alice Smith",
    "email": "alice@example.com",
    "role": "app-user",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}

_USER_DATA_2: dict = {
    "id": "20",
    "username": "bob",
    "name": "Bob Jones",
    "email": "bob@example.com",
    "role": "app-admin",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# get_member_groups
# ---------------------------------------------------------------------------


def test_get_member_groups_returns_list_of_groups(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() returns a list of Group instances."""
    httpx_mock.add_response(json=_rpc_ok([_GROUP_DATA, _GROUP_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_member_groups(10)
    assert len(result) == 2
    assert all(isinstance(g, Group) for g in result)


def test_get_member_groups_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() maps fields correctly."""
    httpx_mock.add_response(json=_rpc_ok([_GROUP_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_member_groups(10)
    g = result[0]
    assert g.id == 1
    assert g.name == "Developers"
    assert g.external_id == ""


def test_get_member_groups_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_member_groups(10)
    assert result == []


def test_get_member_groups_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_member_groups(10)
    assert result == []


def test_get_member_groups_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() returns [] when API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_member_groups(10)
    assert result == []


def test_get_member_groups_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.group_members.get_member_groups(10)


# ---------------------------------------------------------------------------
# get_group_members
# ---------------------------------------------------------------------------


def test_get_group_members_returns_list_of_users(httpx_mock: HTTPXMock) -> None:
    """get_group_members() returns a list of User instances."""
    httpx_mock.add_response(json=_rpc_ok([_USER_DATA, _USER_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_group_members(1)
    assert len(result) == 2
    assert all(isinstance(u, User) for u in result)


def test_get_group_members_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_group_members() maps fields correctly."""
    httpx_mock.add_response(json=_rpc_ok([_USER_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_group_members(1)
    u = result[0]
    assert u.id == 10
    assert u.username == "alice"
    assert u.name == "Alice Smith"
    assert u.email == "alice@example.com"
    assert u.role == "app-user"


def test_get_group_members_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_group_members() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_group_members(1)
    assert result == []


def test_get_group_members_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_group_members() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_group_members(1)
    assert result == []


def test_get_group_members_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_group_members() returns [] when API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.get_group_members(1)
    assert result == []


def test_get_group_members_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_group_members() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.group_members.get_group_members(1)


# ---------------------------------------------------------------------------
# add_group_member
# ---------------------------------------------------------------------------


def test_add_group_member_returns_true(httpx_mock: HTTPXMock) -> None:
    """add_group_member() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.add_group_member(1, 10)
    assert result is True


def test_add_group_member_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """add_group_member() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to add user 10 to group 1"):
            client.group_members.add_group_member(1, 10)


def test_add_group_member_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """add_group_member() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.group_members.add_group_member(1, 10)


# ---------------------------------------------------------------------------
# remove_group_member
# ---------------------------------------------------------------------------


def test_remove_group_member_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_group_member() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.remove_group_member(1, 10)
    assert result is True


def test_remove_group_member_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_group_member() returns False when API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.remove_group_member(1, 10)
    assert result is False


def test_remove_group_member_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_group_member() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot remove"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot remove"):
            client.group_members.remove_group_member(1, 10)


# ---------------------------------------------------------------------------
# is_group_member
# ---------------------------------------------------------------------------


def test_is_group_member_returns_true(httpx_mock: HTTPXMock) -> None:
    """is_group_member() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.is_group_member(1, 10)
    assert result is True


def test_is_group_member_returns_false(httpx_mock: HTTPXMock) -> None:
    """is_group_member() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.group_members.is_group_member(1, 10)
    assert result is False


def test_is_group_member_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """is_group_member() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.group_members.is_group_member(1, 10)


# ---------------------------------------------------------------------------
# Network failure tests
# ---------------------------------------------------------------------------


def test_get_member_groups_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_member_groups() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.group_members.get_member_groups(10)


def test_get_group_members_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_group_members() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.group_members.get_group_members(1)


def test_add_group_member_network_failure(httpx_mock: HTTPXMock) -> None:
    """add_group_member() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.group_members.add_group_member(1, 10)


def test_remove_group_member_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_group_member() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.group_members.remove_group_member(1, 10)


def test_is_group_member_network_failure(httpx_mock: HTTPXMock) -> None:
    """is_group_member() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.group_members.is_group_member(1, 10)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_group_members_resource_wired_on_client() -> None:
    """KanboardClient exposes a GroupMembersResource as .group_members."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.group_members, GroupMembersResource)


def test_group_members_resource_importable_from_kanboard() -> None:
    """GroupMembersResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "GroupMembersResource")
    assert kanboard.GroupMembersResource is GroupMembersResource
