"""Unit tests for UsersResource — all 10 user API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import User
from kanboard.resources.users import UsersResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_DATA: dict = {
    "id": "3",
    "username": "jdoe",
    "name": "John Doe",
    "email": "jdoe@example.com",
    "role": "app-user",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}

_USER_DATA_2: dict = {
    "id": "4",
    "username": "jsmith",
    "name": "Jane Smith",
    "email": "jsmith@example.com",
    "role": "app-manager",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "1",
    "avatar_path": "/avatars/jsmith.png",
    "timezone": "UTC",
    "language": "en_US",
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
# create_user
# ---------------------------------------------------------------------------


def test_create_user_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_user() returns the new user ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(3))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.create_user(username="jdoe", password="s3cr3t")
    assert result == 3
    assert isinstance(result, int)


def test_create_user_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_user() forwards optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.create_user(
            username="jdoe", password="s3cr3t", name="John Doe", email="jdoe@example.com"
        )
    assert result == 5


def test_create_user_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_user() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create user"):
            client.users.create_user(username="jdoe", password="s3cr3t")


def test_create_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.create_user(username="jdoe", password="s3cr3t")


# ---------------------------------------------------------------------------
# create_ldap_user
# ---------------------------------------------------------------------------


def test_create_ldap_user_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_ldap_user() returns the new user ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.create_ldap_user(username="ldapuser")
    assert result == 7
    assert isinstance(result, int)


def test_create_ldap_user_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_ldap_user() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create LDAP user"):
            client.users.create_ldap_user(username="ldapuser")


def test_create_ldap_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_ldap_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.create_ldap_user(username="ldapuser")


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


def test_get_user_returns_user_model(httpx_mock: HTTPXMock) -> None:
    """get_user() returns a User instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_USER_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_user(user_id=3)
    assert isinstance(result, User)


def test_get_user_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_user() maps all API fields to the User dataclass correctly."""
    httpx_mock.add_response(json=_rpc_ok(_USER_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_user(user_id=3)
    assert result.id == 3
    assert result.username == "jdoe"
    assert result.name == "John Doe"
    assert result.email == "jdoe@example.com"
    assert result.role == "app-user"
    assert result.is_active is True
    assert result.is_ldap_user is False
    assert result.notification_method == 0
    assert result.avatar_path is None
    assert result.timezone is None
    assert result.language is None


def test_get_user_optional_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_user() maps optional fields (avatar_path, timezone, language) correctly."""
    httpx_mock.add_response(json=_rpc_ok(_USER_DATA_2))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_user(user_id=4)
    assert result.avatar_path == "/avatars/jsmith.png"
    assert result.timezone == "UTC"
    assert result.language == "en_US"


def test_get_user_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_user() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="User"):
            client.users.get_user(user_id=999)


def test_get_user_not_found_error_attributes(httpx_mock: HTTPXMock) -> None:
    """get_user() KanboardNotFoundError carries correct resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.users.get_user(user_id=999)
    err = exc_info.value
    assert err.resource == "User"
    assert err.identifier == 999


def test_get_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.get_user(user_id=3)


# ---------------------------------------------------------------------------
# get_user_by_name
# ---------------------------------------------------------------------------


def test_get_user_by_name_returns_user_model(httpx_mock: HTTPXMock) -> None:
    """get_user_by_name() returns a User instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_USER_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_user_by_name(username="jdoe")
    assert isinstance(result, User)


def test_get_user_by_name_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_user_by_name() maps all API fields to the User dataclass correctly."""
    httpx_mock.add_response(json=_rpc_ok(_USER_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_user_by_name(username="jdoe")
    assert result.id == 3
    assert result.username == "jdoe"


def test_get_user_by_name_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_user_by_name() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="User"):
            client.users.get_user_by_name(username="nobody")


def test_get_user_by_name_not_found_error_attributes(httpx_mock: HTTPXMock) -> None:
    """get_user_by_name() KanboardNotFoundError carries correct resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.users.get_user_by_name(username="nobody")
    err = exc_info.value
    assert err.resource == "User"
    assert err.identifier == "nobody"


def test_get_user_by_name_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_user_by_name() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.get_user_by_name(username="jdoe")


# ---------------------------------------------------------------------------
# get_all_users
# ---------------------------------------------------------------------------


def test_get_all_users_returns_list_of_user_models(httpx_mock: HTTPXMock) -> None:
    """get_all_users() returns a list of User instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_USER_DATA, _USER_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_all_users()
    assert len(result) == 2
    assert all(isinstance(u, User) for u in result)


def test_get_all_users_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_all_users() maps API fields correctly for each User."""
    httpx_mock.add_response(json=_rpc_ok([_USER_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_all_users()
    user = result[0]
    assert user.id == 3
    assert user.username == "jdoe"
    assert user.email == "jdoe@example.com"


def test_get_all_users_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_users() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_all_users()
    assert result == []


def test_get_all_users_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_users() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_all_users()
    assert result == []


def test_get_all_users_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_users() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.get_all_users()
    assert result == []


def test_get_all_users_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_all_users() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.get_all_users()


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


def test_update_user_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_user() returns True when the API succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.update_user(id=3, name="John Updated")
    assert result is True


def test_update_user_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_user() forwards optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.update_user(id=3, email="new@example.com", role="app-admin")
    assert result is True


def test_update_user_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_user() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update user"):
            client.users.update_user(id=3)


def test_update_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """update_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.update_user(id=3)


# ---------------------------------------------------------------------------
# remove_user
# ---------------------------------------------------------------------------


def test_remove_user_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_user() returns True when the API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.remove_user(user_id=3)
    assert result is True


def test_remove_user_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """remove_user() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.remove_user(user_id=999)
    assert result is False


def test_remove_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """remove_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.remove_user(user_id=3)


# ---------------------------------------------------------------------------
# disable_user
# ---------------------------------------------------------------------------


def test_disable_user_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """disable_user() returns True when the API confirms the operation."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.disable_user(user_id=3)
    assert result is True


def test_disable_user_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """disable_user() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.disable_user(user_id=999)
    assert result is False


def test_disable_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """disable_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.disable_user(user_id=3)


# ---------------------------------------------------------------------------
# enable_user
# ---------------------------------------------------------------------------


def test_enable_user_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """enable_user() returns True when the API confirms the operation."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.enable_user(user_id=3)
    assert result is True


def test_enable_user_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """enable_user() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.enable_user(user_id=999)
    assert result is False


def test_enable_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """enable_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.enable_user(user_id=3)


# ---------------------------------------------------------------------------
# is_active_user
# ---------------------------------------------------------------------------


def test_is_active_user_returns_true_when_active(httpx_mock: HTTPXMock) -> None:
    """is_active_user() returns True when the user is active."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.is_active_user(user_id=3)
    assert result is True


def test_is_active_user_returns_false_when_inactive(httpx_mock: HTTPXMock) -> None:
    """is_active_user() returns False when the user is inactive."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.users.is_active_user(user_id=3)
    assert result is False


def test_is_active_user_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """is_active_user() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.users.is_active_user(user_id=3)


# ---------------------------------------------------------------------------
# Resource wiring and importability
# ---------------------------------------------------------------------------


def test_users_resource_is_wired_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes .users as a UsersResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.users, UsersResource)


def test_users_resource_importable_from_kanboard() -> None:
    """UsersResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "UsersResource")
    assert kanboard.UsersResource is UsersResource
