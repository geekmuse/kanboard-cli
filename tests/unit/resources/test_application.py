"""Unit tests for ApplicationResource - all 7 application info API methods."""

from __future__ import annotations

import httpx as httpx_lib
import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardConnectionError
from kanboard.resources.application import ApplicationResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rpc_ok(result: object, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


# ===========================================================================
# get_version
# ===========================================================================


def test_get_version_returns_string(httpx_mock: HTTPXMock) -> None:
    """get_version() returns the version string from the API."""
    httpx_mock.add_response(json=_rpc_ok("1.2.30"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_version()
    assert result == "1.2.30"


def test_get_version_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_version() returns empty string when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_version()
    assert result == ""


def test_get_version_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_version() returns empty string when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_version()
    assert result == ""


def test_get_version_empty_on_empty_string(httpx_mock: HTTPXMock) -> None:
    """get_version() returns empty string when API returns empty string."""
    httpx_mock.add_response(json=_rpc_ok(""))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_version()
    assert result == ""


def test_get_version_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_version() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_version()


# ===========================================================================
# get_timezone
# ===========================================================================


def test_get_timezone_returns_string(httpx_mock: HTTPXMock) -> None:
    """get_timezone() returns the timezone string from the API."""
    httpx_mock.add_response(json=_rpc_ok("America/New_York"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_timezone()
    assert result == "America/New_York"


def test_get_timezone_utc(httpx_mock: HTTPXMock) -> None:
    """get_timezone() handles UTC timezone."""
    httpx_mock.add_response(json=_rpc_ok("UTC"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_timezone()
    assert result == "UTC"


def test_get_timezone_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_timezone() returns empty string when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_timezone()
    assert result == ""


def test_get_timezone_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_timezone() returns empty string when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_timezone()
    assert result == ""


def test_get_timezone_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_timezone() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_timezone()


# ===========================================================================
# get_default_task_colors
# ===========================================================================


def test_get_default_task_colors_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_default_task_colors() returns a dict of colour definitions."""
    colors = {
        "yellow": {"name": "Yellow", "background": "#fdf8cd"},
        "blue": {"name": "Blue", "background": "#dce5f1"},
    }
    httpx_mock.add_response(json=_rpc_ok(colors))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_default_task_colors()
    assert result == colors


def test_get_default_task_colors_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_default_task_colors() returns empty dict when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_default_task_colors()
    assert result == {}


def test_get_default_task_colors_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_default_task_colors() returns empty dict when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_default_task_colors()
    assert result == {}


def test_get_default_task_colors_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_default_task_colors() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_default_task_colors()


# ===========================================================================
# get_default_task_color
# ===========================================================================


def test_get_default_task_color_returns_string(httpx_mock: HTTPXMock) -> None:
    """get_default_task_color() returns the default colour identifier."""
    httpx_mock.add_response(json=_rpc_ok("yellow"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_default_task_color()
    assert result == "yellow"


def test_get_default_task_color_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_default_task_color() returns empty string when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_default_task_color()
    assert result == ""


def test_get_default_task_color_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_default_task_color() returns empty string when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_default_task_color()
    assert result == ""


def test_get_default_task_color_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_default_task_color() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_default_task_color()


# ===========================================================================
# get_color_list
# ===========================================================================


def test_get_color_list_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_color_list() returns a dict mapping IDs to labels."""
    color_list = {"yellow": "Yellow", "blue": "Blue", "green": "Green"}
    httpx_mock.add_response(json=_rpc_ok(color_list))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_color_list()
    assert result == color_list


def test_get_color_list_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_color_list() returns empty dict when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_color_list()
    assert result == {}


def test_get_color_list_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_color_list() returns empty dict when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_color_list()
    assert result == {}


def test_get_color_list_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_color_list() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_color_list()


# ===========================================================================
# get_application_roles
# ===========================================================================


def test_get_application_roles_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_application_roles() returns a dict mapping role IDs to labels."""
    roles = {"app-admin": "Administrator", "app-manager": "Manager", "app-user": "User"}
    httpx_mock.add_response(json=_rpc_ok(roles))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_application_roles()
    assert result == roles


def test_get_application_roles_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_application_roles() returns empty dict when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_application_roles()
    assert result == {}


def test_get_application_roles_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_application_roles() returns empty dict when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_application_roles()
    assert result == {}


def test_get_application_roles_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_application_roles() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_application_roles()


# ===========================================================================
# get_project_roles
# ===========================================================================


def test_get_project_roles_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_project_roles() returns a dict mapping role IDs to labels."""
    roles = {"project-manager": "Project Manager", "project-member": "Project Member"}
    httpx_mock.add_response(json=_rpc_ok(roles))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_project_roles()
    assert result == roles


def test_get_project_roles_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_roles() returns empty dict when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_project_roles()
    assert result == {}


def test_get_project_roles_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_roles() returns empty dict when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.application.get_project_roles()
    assert result == {}


def test_get_project_roles_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_project_roles() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.application.get_project_roles()


# ===========================================================================
# Client wiring
# ===========================================================================


def test_client_has_application_attribute(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes a .application attribute of the correct type."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert hasattr(client, "application")
        assert isinstance(client.application, ApplicationResource)


# ===========================================================================
# Package importability
# ===========================================================================


def test_application_resource_importable_from_package() -> None:
    """ApplicationResource is importable from the top-level kanboard package."""
    from kanboard import ApplicationResource as Imported

    assert Imported is ApplicationResource
