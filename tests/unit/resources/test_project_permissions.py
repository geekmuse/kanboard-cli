"""Unit tests for ProjectPermissionsResource - all 9 project permission API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError
from kanboard.resources.project_permissions import ProjectPermissionsResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ===========================================================================
# get_project_users
# ===========================================================================


def test_get_project_users_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_project_users() returns a dict of user_id -> username."""
    httpx_mock.add_response(json=_rpc_ok({"1": "admin", "2": "alice"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_users(1)
    assert result == {"1": "admin", "2": "alice"}
    assert isinstance(result, dict)


def test_get_project_users_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_users() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_users(1)
    assert result == {}


def test_get_project_users_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_users() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_users(1)
    assert result == {}


def test_get_project_users_returns_empty_on_empty_dict(httpx_mock: HTTPXMock) -> None:
    """get_project_users() returns {} when API returns an empty dict."""
    httpx_mock.add_response(json=_rpc_ok({}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_users(1)
    assert result == {}


def test_get_project_users_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_project_users() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.project_permissions.get_project_users(1)


# ===========================================================================
# get_assignable_users
# ===========================================================================


def test_get_assignable_users_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() returns a dict of user_id -> username."""
    httpx_mock.add_response(json=_rpc_ok({"1": "admin", "3": "bob"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_assignable_users(1)
    assert result == {"1": "admin", "3": "bob"}
    assert isinstance(result, dict)


def test_get_assignable_users_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_assignable_users(1)
    assert result == {}


def test_get_assignable_users_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_assignable_users(1)
    assert result == {}


def test_get_assignable_users_returns_empty_on_empty_dict(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() returns {} when API returns empty dict."""
    httpx_mock.add_response(json=_rpc_ok({}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_assignable_users(1)
    assert result == {}


def test_get_assignable_users_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() forwards extra kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok({"0": "Unassigned", "1": "admin"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_assignable_users(1, prepend_unassigned=True)
    assert "0" in result
    assert result["0"] == "Unassigned"


def test_get_assignable_users_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.project_permissions.get_assignable_users(1)


# ===========================================================================
# get_project_user_role
# ===========================================================================


def test_get_project_user_role_returns_string(httpx_mock: HTTPXMock) -> None:
    """get_project_user_role() returns the role as a string."""
    httpx_mock.add_response(json=_rpc_ok("project-manager"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_user_role(1, 2)
    assert result == "project-manager"
    assert isinstance(result, str)


def test_get_project_user_role_returns_empty_on_empty_string(
    httpx_mock: HTTPXMock,
) -> None:
    """get_project_user_role() returns '' when API returns empty string."""
    httpx_mock.add_response(json=_rpc_ok(""))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_user_role(1, 2)
    assert result == ""


def test_get_project_user_role_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_user_role() returns '' when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_user_role(1, 2)
    assert result == ""


def test_get_project_user_role_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_user_role() returns '' when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.get_project_user_role(1, 2)
    assert result == ""


def test_get_project_user_role_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_project_user_role() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.project_permissions.get_project_user_role(1, 2)


# ===========================================================================
# add_project_user
# ===========================================================================


def test_add_project_user_returns_true(httpx_mock: HTTPXMock) -> None:
    """add_project_user() returns True when API confirms."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.add_project_user(1, 2)
    assert result is True


def test_add_project_user_with_role(httpx_mock: HTTPXMock) -> None:
    """add_project_user() accepts a role kwarg."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.add_project_user(1, 2, role="project-manager")
    assert result is True


def test_add_project_user_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """add_project_user() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to add user"):
            client.project_permissions.add_project_user(1, 2)


def test_add_project_user_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """add_project_user() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Internal error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Internal error"):
            client.project_permissions.add_project_user(1, 2)


# ===========================================================================
# remove_project_user
# ===========================================================================


def test_remove_project_user_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_project_user() returns True when API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.remove_project_user(1, 2)
    assert result is True


def test_remove_project_user_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_project_user() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.remove_project_user(1, 2)
    assert result is False


def test_remove_project_user_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_project_user() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot remove"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot remove"):
            client.project_permissions.remove_project_user(1, 2)


# ===========================================================================
# change_project_user_role
# ===========================================================================


def test_change_project_user_role_returns_true(httpx_mock: HTTPXMock) -> None:
    """change_project_user_role() returns True when API confirms."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.change_project_user_role(1, 2, "project-manager")
    assert result is True


def test_change_project_user_role_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """change_project_user_role() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to change role for user"):
            client.project_permissions.change_project_user_role(1, 2, "project-manager")


def test_change_project_user_role_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """change_project_user_role() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Invalid role"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Invalid role"):
            client.project_permissions.change_project_user_role(1, 2, "bad-role")


# ===========================================================================
# add_project_group
# ===========================================================================


def test_add_project_group_returns_true(httpx_mock: HTTPXMock) -> None:
    """add_project_group() returns True when API confirms."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.add_project_group(1, 5)
    assert result is True


def test_add_project_group_with_role(httpx_mock: HTTPXMock) -> None:
    """add_project_group() accepts a role kwarg."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.add_project_group(1, 5, role="project-viewer")
    assert result is True


def test_add_project_group_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """add_project_group() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to add group"):
            client.project_permissions.add_project_group(1, 5)


def test_add_project_group_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """add_project_group() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Internal error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Internal error"):
            client.project_permissions.add_project_group(1, 5)


# ===========================================================================
# remove_project_group
# ===========================================================================


def test_remove_project_group_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_project_group() returns True when API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.remove_project_group(1, 5)
    assert result is True


def test_remove_project_group_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_project_group() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.remove_project_group(1, 5)
    assert result is False


def test_remove_project_group_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_project_group() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot remove"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot remove"):
            client.project_permissions.remove_project_group(1, 5)


# ===========================================================================
# change_project_group_role
# ===========================================================================


def test_change_project_group_role_returns_true(httpx_mock: HTTPXMock) -> None:
    """change_project_group_role() returns True when API confirms."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_permissions.change_project_group_role(1, 5, "project-viewer")
    assert result is True


def test_change_project_group_role_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """change_project_group_role() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to change role for group"):
            client.project_permissions.change_project_group_role(1, 5, "project-viewer")


def test_change_project_group_role_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """change_project_group_role() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Invalid role"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Invalid role"):
            client.project_permissions.change_project_group_role(1, 5, "bad-role")


# ===========================================================================
# Network failure tests
# ===========================================================================


def test_get_project_users_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_project_users() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.get_project_users(1)


def test_get_assignable_users_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_assignable_users() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.get_assignable_users(1)


def test_get_project_user_role_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_project_user_role() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.get_project_user_role(1, 2)


def test_add_project_user_network_failure(httpx_mock: HTTPXMock) -> None:
    """add_project_user() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.add_project_user(1, 2)


def test_remove_project_user_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_project_user() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.remove_project_user(1, 2)


def test_change_project_user_role_network_failure(httpx_mock: HTTPXMock) -> None:
    """change_project_user_role() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.change_project_user_role(1, 2, "project-manager")


def test_add_project_group_network_failure(httpx_mock: HTTPXMock) -> None:
    """add_project_group() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.add_project_group(1, 5)


def test_remove_project_group_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_project_group() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.remove_project_group(1, 5)


def test_change_project_group_role_network_failure(httpx_mock: HTTPXMock) -> None:
    """change_project_group_role() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_permissions.change_project_group_role(1, 5, "project-viewer")


# ===========================================================================
# Client wiring / importability
# ===========================================================================


def test_project_permissions_resource_wired_on_client() -> None:
    """KanboardClient exposes a ProjectPermissionsResource as .project_permissions."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.project_permissions, ProjectPermissionsResource)


def test_project_permissions_resource_importable_from_kanboard() -> None:
    """ProjectPermissionsResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "ProjectPermissionsResource")
    assert kanboard.ProjectPermissionsResource is ProjectPermissionsResource
