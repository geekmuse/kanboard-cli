"""Unit tests for ProjectsResource — all 14 project API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Project

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_DATA: dict = {
    "id": "1",
    "name": "Test Project",
    "description": "A test project",
    "is_active": "1",
    "token": "abc123",
    "last_modified": "1711077600",
    "is_public": "0",
    "is_private": False,
    "owner_id": "1",
    "identifier": "PROJ",
    "start_date": None,
    "end_date": None,
    "url": "http://kanboard.test/?controller=BoardViewController&action=show&project_id=1",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------


def test_create_project_returns_new_id(httpx_mock: HTTPXMock) -> None:
    """create_project() returns the new project ID as an integer on success."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        project_id = client.projects.create_project("New Project")
    assert project_id == 5


def test_create_project_with_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_project() passes optional kwargs to the API call."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        project_id = client.projects.create_project(
            "New Project", description="desc", owner_id=2, identifier="NP"
        )
    assert project_id == 7


def test_create_project_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_project() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createProject"):
            client.projects.create_project("Duplicate Name")


def test_create_project_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_project() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createProject"):
            client.projects.create_project("Bad Project")


def test_create_project_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_project() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.projects.create_project("Blocked")


# ---------------------------------------------------------------------------
# get_project_by_id
# ---------------------------------------------------------------------------


def test_get_project_by_id_returns_project_instance(httpx_mock: HTTPXMock) -> None:
    """get_project_by_id() returns a populated Project dataclass for a valid ID."""
    httpx_mock.add_response(json=_rpc_ok(_PROJECT_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        project = client.projects.get_project_by_id(1)
    assert isinstance(project, Project)
    assert project.id == 1
    assert project.name == "Test Project"
    assert project.is_active is True


def test_get_project_by_id_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_by_id() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.projects.get_project_by_id(999)
    assert "999" in str(exc_info.value)


def test_get_project_by_id_not_found_identifies_resource(httpx_mock: HTTPXMock) -> None:
    """get_project_by_id() KanboardNotFoundError carries resource='Project'."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.projects.get_project_by_id(42)
    assert exc_info.value.resource == "Project"
    assert exc_info.value.identifier == "42"


# ---------------------------------------------------------------------------
# get_project_by_name
# ---------------------------------------------------------------------------


def test_get_project_by_name_returns_project(httpx_mock: HTTPXMock) -> None:
    """get_project_by_name() returns a Project for a valid name."""
    httpx_mock.add_response(json=_rpc_ok(_PROJECT_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        project = client.projects.get_project_by_name("Test Project")
    assert isinstance(project, Project)
    assert project.name == "Test Project"


def test_get_project_by_name_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_by_name() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.projects.get_project_by_name("Ghost Project")
    assert "Ghost Project" in str(exc_info.value)
    assert exc_info.value.identifier == "Ghost Project"
    assert exc_info.value.resource == "Project"


# ---------------------------------------------------------------------------
# get_project_by_identifier
# ---------------------------------------------------------------------------


def test_get_project_by_identifier_returns_project(httpx_mock: HTTPXMock) -> None:
    """get_project_by_identifier() returns a Project for a valid identifier."""
    httpx_mock.add_response(json=_rpc_ok(_PROJECT_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        project = client.projects.get_project_by_identifier("PROJ")
    assert isinstance(project, Project)
    assert project.identifier == "PROJ"


def test_get_project_by_identifier_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_by_identifier() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.projects.get_project_by_identifier("NOPE")
    assert "NOPE" in str(exc_info.value)
    assert exc_info.value.identifier == "NOPE"


# ---------------------------------------------------------------------------
# get_project_by_email
# ---------------------------------------------------------------------------


def test_get_project_by_email_returns_project(httpx_mock: HTTPXMock) -> None:
    """get_project_by_email() returns a Project for a valid email address."""
    httpx_mock.add_response(json=_rpc_ok(_PROJECT_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        project = client.projects.get_project_by_email("proj@kanboard.test")
    assert isinstance(project, Project)


def test_get_project_by_email_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_by_email() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.projects.get_project_by_email("ghost@kanboard.test")
    assert "ghost@kanboard.test" in str(exc_info.value)
    assert exc_info.value.identifier == "ghost@kanboard.test"


# ---------------------------------------------------------------------------
# get_all_projects
# ---------------------------------------------------------------------------


def test_get_all_projects_returns_list_of_projects(httpx_mock: HTTPXMock) -> None:
    """get_all_projects() returns a list of Project instances."""
    httpx_mock.add_response(json=_rpc_ok([_PROJECT_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        projects = client.projects.get_all_projects()
    assert len(projects) == 1
    assert isinstance(projects[0], Project)


def test_get_all_projects_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_projects() returns an empty list when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.get_all_projects() == []


def test_get_all_projects_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_projects() returns an empty list when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.get_all_projects() == []


def test_get_all_projects_multiple_results(httpx_mock: HTTPXMock) -> None:
    """get_all_projects() returns multiple Project instances from the API response."""
    proj2 = dict(_PROJECT_DATA)
    proj2["id"] = "2"
    proj2["name"] = "Second Project"
    httpx_mock.add_response(json=_rpc_ok([_PROJECT_DATA, proj2]))
    with KanboardClient(_URL, _TOKEN) as client:
        projects = client.projects.get_all_projects()
    assert len(projects) == 2
    assert projects[1].name == "Second Project"


# ---------------------------------------------------------------------------
# update_project
# ---------------------------------------------------------------------------


def test_update_project_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_project() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.projects.update_project(1, name="Renamed Project")
    assert result is True


def test_update_project_with_multiple_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_project() passes all kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.projects.update_project(1, name="New Name", description="New desc")
    assert result is True


def test_update_project_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_project() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="updateProject"):
            client.projects.update_project(999, name="Bad update")


# ---------------------------------------------------------------------------
# remove_project
# ---------------------------------------------------------------------------


def test_remove_project_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_project() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.remove_project(1) is True


def test_remove_project_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """remove_project() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.remove_project(1) is False


# ---------------------------------------------------------------------------
# enable_project
# ---------------------------------------------------------------------------


def test_enable_project_returns_true(httpx_mock: HTTPXMock) -> None:
    """enable_project() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.enable_project(1) is True


def test_enable_project_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """enable_project() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.enable_project(1) is False


# ---------------------------------------------------------------------------
# disable_project
# ---------------------------------------------------------------------------


def test_disable_project_returns_true(httpx_mock: HTTPXMock) -> None:
    """disable_project() returns True when the API signals success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.disable_project(1) is True


def test_disable_project_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """disable_project() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.disable_project(1) is False


# ---------------------------------------------------------------------------
# enable_project_public_access
# ---------------------------------------------------------------------------


def test_enable_project_public_access_returns_true(httpx_mock: HTTPXMock) -> None:
    """enable_project_public_access() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.enable_project_public_access(1) is True


def test_enable_project_public_access_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """enable_project_public_access() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.enable_project_public_access(1) is False


# ---------------------------------------------------------------------------
# disable_project_public_access
# ---------------------------------------------------------------------------


def test_disable_project_public_access_returns_true(httpx_mock: HTTPXMock) -> None:
    """disable_project_public_access() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.disable_project_public_access(1) is True


def test_disable_project_public_access_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """disable_project_public_access() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.disable_project_public_access(1) is False


# ---------------------------------------------------------------------------
# get_project_activity
# ---------------------------------------------------------------------------


def test_get_project_activity_returns_list_of_dicts(httpx_mock: HTTPXMock) -> None:
    """get_project_activity() returns a list of activity event dicts."""
    activity = [{"event_name": "task.create", "task_id": 1}]
    httpx_mock.add_response(json=_rpc_ok(activity))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.projects.get_project_activity(1)
    assert result == activity
    assert isinstance(result, list)


def test_get_project_activity_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_activity() returns an empty list when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.get_project_activity(1) == []


def test_get_project_activity_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_activity() returns an empty list when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.get_project_activity(1) == []


def test_get_project_activity_multiple_events(httpx_mock: HTTPXMock) -> None:
    """get_project_activity() returns all event dicts from the API response."""
    activities = [
        {"event_name": "task.create", "task_id": 1},
        {"event_name": "task.close", "task_id": 2},
    ]
    httpx_mock.add_response(json=_rpc_ok(activities))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.projects.get_project_activity(1)
    assert len(result) == 2
    assert result[1]["event_name"] == "task.close"


# ---------------------------------------------------------------------------
# get_project_activities
# ---------------------------------------------------------------------------


def test_get_project_activities_returns_list_of_dicts(httpx_mock: HTTPXMock) -> None:
    """get_project_activities() returns a list of activity event dicts."""
    activities = [{"event_name": "task.create", "project_id": 1}]
    httpx_mock.add_response(json=_rpc_ok(activities))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.projects.get_project_activities([1, 2])
    assert result == activities


def test_get_project_activities_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_activities() returns an empty list when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.get_project_activities([1]) == []


def test_get_project_activities_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_activities() returns an empty list when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.projects.get_project_activities([1, 2, 3]) == []


# ---------------------------------------------------------------------------
# ProjectsResource accessor on KanboardClient
# ---------------------------------------------------------------------------


def test_projects_resource_accessible_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient.projects is a ProjectsResource instance."""
    from kanboard.resources.projects import ProjectsResource

    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.projects, ProjectsResource)
