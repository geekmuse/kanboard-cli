"""Unit tests for MeResource - all 7 "me" API methods.

All methods raise KanboardAuthError because User API auth is not yet
implemented.  Tests verify the error is raised with a clear message.
"""

from __future__ import annotations

import pytest

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAuthError
from kanboard.resources.me import MeResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"


# ===========================================================================
# get_me
# ===========================================================================


def test_get_me_raises_auth_error() -> None:
    """get_me() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_me()


# ===========================================================================
# get_my_dashboard
# ===========================================================================


def test_get_my_dashboard_raises_auth_error() -> None:
    """get_my_dashboard() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_dashboard()


# ===========================================================================
# get_my_activity_stream
# ===========================================================================


def test_get_my_activity_stream_raises_auth_error() -> None:
    """get_my_activity_stream() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_activity_stream()


# ===========================================================================
# create_my_private_project
# ===========================================================================


def test_create_my_private_project_raises_auth_error() -> None:
    """create_my_private_project() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.create_my_private_project("Test Project")


def test_create_my_private_project_with_kwargs_raises_auth_error() -> None:
    """create_my_private_project() raises KanboardAuthError even with kwargs."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.create_my_private_project("Test", description="desc")


# ===========================================================================
# get_my_projects_list
# ===========================================================================


def test_get_my_projects_list_raises_auth_error() -> None:
    """get_my_projects_list() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_projects_list()


# ===========================================================================
# get_my_overdue_tasks
# ===========================================================================


def test_get_my_overdue_tasks_raises_auth_error() -> None:
    """get_my_overdue_tasks() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_overdue_tasks()


# ===========================================================================
# get_my_projects
# ===========================================================================


def test_get_my_projects_raises_auth_error() -> None:
    """get_my_projects() raises KanboardAuthError with a clear message."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="User API authentication"):
            client.me.get_my_projects()


# ===========================================================================
# Client wiring
# ===========================================================================


def test_client_has_me_resource() -> None:
    """KanboardClient exposes a ``me`` attribute of type MeResource."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert hasattr(client, "me")
        assert isinstance(client.me, MeResource)


# ===========================================================================
# Package-level import
# ===========================================================================


def test_me_resource_importable_from_package() -> None:
    """MeResource is importable from the top-level kanboard package."""
    from kanboard import MeResource as ImportedMeResource

    assert ImportedMeResource is MeResource


# ===========================================================================
# Error message quality
# ===========================================================================


def test_auth_error_mentions_json_rpc() -> None:
    """The auth error message mentions JSON-RPC token auth is not supported."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="JSON-RPC API token"):
            client.me.get_me()


def test_auth_error_mentions_future_release() -> None:
    """The auth error message mentions future availability."""
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAuthError, match="future release"):
            client.me.get_me()
