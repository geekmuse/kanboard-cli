"""Unit tests for MeResource — authenticated user endpoints.

Covers:
- App auth mode: every method raises KanboardAuthError with a clear message.
- User auth mode: methods make real API calls (verified via pytest-httpx).
- auth_mode property on KanboardClient.
"""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAuthError
from kanboard.resources.me import MeResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"
_USERNAME = "admin"
_PASSWORD = "secret"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _app_client() -> KanboardClient:
    """Return a client using application API token auth (default)."""
    return KanboardClient(_URL, _TOKEN)


def _user_client() -> KanboardClient:
    """Return a client using User API authentication."""
    return KanboardClient(
        _URL,
        auth_mode="user",
        username=_USERNAME,
        password=_PASSWORD,
    )


def _rpc_response(result: object, req_id: int = 1) -> dict:
    """Build a minimal JSON-RPC 2.0 success response dict."""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _mock_post(httpx_mock: HTTPXMock, result: object) -> None:
    """Register a single successful JSON-RPC POST response."""
    httpx_mock.add_response(
        method="POST",
        url=_URL,
        json=_rpc_response(result),
    )


# ===========================================================================
# KanboardClient.auth_mode property
# ===========================================================================


def test_auth_mode_default_is_app() -> None:
    """auth_mode defaults to 'app'."""
    with _app_client() as client:
        assert client.auth_mode == "app"


def test_auth_mode_user_is_stored() -> None:
    """auth_mode='user' is stored and accessible via property."""
    with _user_client() as client:
        assert client.auth_mode == "user"


# ===========================================================================
# App auth mode — every method raises KanboardAuthError
# ===========================================================================


def test_get_me_raises_auth_error_with_app_auth() -> None:
    """get_me() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_me()


def test_get_my_dashboard_raises_auth_error_with_app_auth() -> None:
    """get_my_dashboard() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_dashboard()


def test_get_my_activity_stream_raises_auth_error_with_app_auth() -> None:
    """get_my_activity_stream() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_activity_stream()


def test_create_my_private_project_raises_auth_error_with_app_auth() -> None:
    """create_my_private_project() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.create_my_private_project("Test Project")


def test_create_my_private_project_kwargs_raises_auth_error_with_app_auth() -> None:
    """create_my_private_project() raises KanboardAuthError even with extra kwargs."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.create_my_private_project("Test", description="desc")


def test_get_my_projects_list_raises_auth_error_with_app_auth() -> None:
    """get_my_projects_list() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_projects_list()


def test_get_my_overdue_tasks_raises_auth_error_with_app_auth() -> None:
    """get_my_overdue_tasks() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_overdue_tasks()


def test_get_my_projects_raises_auth_error_with_app_auth() -> None:
    """get_my_projects() raises KanboardAuthError when using app auth."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_projects()


# ===========================================================================
# App auth error message quality
# ===========================================================================


def test_app_auth_error_mentions_auth_mode() -> None:
    """Error message mentions how to switch to user auth mode."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="auth_mode"):
            client.me.get_me()


def test_app_auth_error_mentions_username_password() -> None:
    """Error message mentions username + password requirement."""
    with _app_client() as client:
        with pytest.raises(KanboardAuthError, match="username"):
            client.me.get_me()


# ===========================================================================
# User auth mode — actual API calls
# ===========================================================================

_USER_DATA = {
    "id": "1",
    "username": "admin",
    "name": "Admin User",
    "email": "admin@example.com",
    "role": "app-admin",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}


def test_get_me_returns_user_model(httpx_mock: HTTPXMock) -> None:
    """get_me() returns a User model when user auth is active."""
    _mock_post(httpx_mock, _USER_DATA)
    with _user_client() as client:
        user = client.me.get_me()
    assert user.username == "admin"
    assert user.id == 1
    assert user.role == "app-admin"


def test_get_me_sends_correct_method(httpx_mock: HTTPXMock) -> None:
    """get_me() calls the getMe JSON-RPC method."""
    _mock_post(httpx_mock, _USER_DATA)
    with _user_client() as client:
        client.me.get_me()
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "getMe"


def test_get_my_dashboard_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_my_dashboard() returns a dict when user auth is active."""
    dashboard = {"projects": [], "tasks": [], "subtasks": []}
    _mock_post(httpx_mock, dashboard)
    with _user_client() as client:
        result = client.me.get_my_dashboard()
    assert isinstance(result, dict)
    assert "projects" in result


def test_get_my_dashboard_sends_correct_method(httpx_mock: HTTPXMock) -> None:
    """get_my_dashboard() calls the getMyDashboard JSON-RPC method."""
    _mock_post(httpx_mock, {"projects": [], "tasks": [], "subtasks": []})
    with _user_client() as client:
        client.me.get_my_dashboard()
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "getMyDashboard"


def test_get_my_activity_stream_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_my_activity_stream() returns a list when user auth is active."""
    _mock_post(httpx_mock, [{"event_name": "task.open", "task_id": 1}])
    with _user_client() as client:
        result = client.me.get_my_activity_stream()
    assert isinstance(result, list)
    assert result[0]["event_name"] == "task.open"


def test_get_my_activity_stream_sends_correct_method(httpx_mock: HTTPXMock) -> None:
    """get_my_activity_stream() calls the getMyActivityStream JSON-RPC method."""
    _mock_post(httpx_mock, [])
    with _user_client() as client:
        client.me.get_my_activity_stream()
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "getMyActivityStream"


def test_get_my_activity_stream_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_my_activity_stream() returns [] when API returns None."""
    _mock_post(httpx_mock, None)
    with _user_client() as client:
        result = client.me.get_my_activity_stream()
    assert result == []


def test_create_my_private_project_returns_id(httpx_mock: HTTPXMock) -> None:
    """create_my_private_project() returns the new project ID."""
    _mock_post(httpx_mock, 42)
    with _user_client() as client:
        project_id = client.me.create_my_private_project("My Private Project")
    assert project_id == 42


def test_create_my_private_project_sends_name(httpx_mock: HTTPXMock) -> None:
    """create_my_private_project() sends the name as a JSON-RPC param."""
    _mock_post(httpx_mock, 42)
    with _user_client() as client:
        client.me.create_my_private_project("My Private Project")
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "createMyPrivateProject"
    assert body["params"]["name"] == "My Private Project"


def test_create_my_private_project_sends_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_my_private_project() forwards extra kwargs as params."""
    _mock_post(httpx_mock, 7)
    with _user_client() as client:
        client.me.create_my_private_project("Project", description="A desc")
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["params"]["description"] == "A desc"


def test_get_my_projects_list_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_my_projects_list() returns a dict when user auth is active."""
    _mock_post(httpx_mock, {"1": "My Project", "2": "Another"})
    with _user_client() as client:
        result = client.me.get_my_projects_list()
    assert result == {"1": "My Project", "2": "Another"}


def test_get_my_projects_list_sends_correct_method(httpx_mock: HTTPXMock) -> None:
    """get_my_projects_list() calls the getMyProjectsList JSON-RPC method."""
    _mock_post(httpx_mock, {})
    with _user_client() as client:
        client.me.get_my_projects_list()
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "getMyProjectsList"


def test_get_my_overdue_tasks_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_my_overdue_tasks() returns a list when user auth is active."""
    _mock_post(httpx_mock, [{"id": "3", "title": "Late task"}])
    with _user_client() as client:
        result = client.me.get_my_overdue_tasks()
    assert isinstance(result, list)
    assert result[0]["title"] == "Late task"


def test_get_my_overdue_tasks_sends_correct_method(httpx_mock: HTTPXMock) -> None:
    """get_my_overdue_tasks() calls the getMyOverdueTasks JSON-RPC method."""
    _mock_post(httpx_mock, [])
    with _user_client() as client:
        client.me.get_my_overdue_tasks()
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "getMyOverdueTasks"


def test_get_my_overdue_tasks_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_my_overdue_tasks() returns [] when API returns None."""
    _mock_post(httpx_mock, None)
    with _user_client() as client:
        result = client.me.get_my_overdue_tasks()
    assert result == []


def test_get_my_projects_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_my_projects() returns a list when user auth is active."""
    _mock_post(httpx_mock, [{"id": "1", "name": "Alpha"}])
    with _user_client() as client:
        result = client.me.get_my_projects()
    assert isinstance(result, list)
    assert result[0]["name"] == "Alpha"


def test_get_my_projects_sends_correct_method(httpx_mock: HTTPXMock) -> None:
    """get_my_projects() calls the getMyProjects JSON-RPC method."""
    _mock_post(httpx_mock, [])
    with _user_client() as client:
        client.me.get_my_projects()
    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body["method"] == "getMyProjects"


def test_get_my_projects_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_my_projects() returns [] when API returns None."""
    _mock_post(httpx_mock, None)
    with _user_client() as client:
        result = client.me.get_my_projects()
    assert result == []


# ===========================================================================
# Client wiring
# ===========================================================================


def test_client_has_me_resource() -> None:
    """KanboardClient exposes a ``me`` attribute of type MeResource."""
    with _app_client() as client:
        assert hasattr(client, "me")
        assert isinstance(client.me, MeResource)


# ===========================================================================
# Package-level import
# ===========================================================================


def test_me_resource_importable_from_package() -> None:
    """MeResource is importable from the top-level kanboard package."""
    from kanboard import MeResource as ImportedMeResource

    assert ImportedMeResource is MeResource
