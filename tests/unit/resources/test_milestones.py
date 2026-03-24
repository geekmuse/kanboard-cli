"""Unit tests for MilestonesResource — all 10 milestone plugin API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import PluginMilestone, PluginMilestoneProgress

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MILESTONE_DATA: dict = {
    "id": "1",
    "portfolio_id": "2",
    "name": "v1.0 Release",
    "description": "First release milestone",
    "target_date": "1711077600",
    "status": "0",
    "color_id": "blue",
    "owner_id": "3",
    "created_at": "1711000000",
    "updated_at": "1711010000",
}

_MILESTONE_DATA_2: dict = {
    "id": "2",
    "portfolio_id": "2",
    "name": "v2.0 Release",
    "description": "",
    "target_date": "0",
    "status": "1",
    "color_id": "",
    "owner_id": "1",
    "created_at": "1711020000",
    "updated_at": "1711030000",
}

_TASK_DATA: dict = {
    "id": "10",
    "title": "Implement feature",
    "project_id": "5",
}

_PROGRESS_DATA: dict = {
    "milestone_id": "1",
    "total": "8",
    "completed": "5",
    "percent": "62.5",
    "is_at_risk": True,
    "is_overdue": False,
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_milestone
# ---------------------------------------------------------------------------


def test_create_milestone_returns_new_id(httpx_mock: HTTPXMock) -> None:
    """create_milestone() returns the new milestone ID as an integer on success."""
    httpx_mock.add_response(json=_rpc_ok(1))
    with KanboardClient(_URL, _TOKEN) as client:
        milestone_id = client.milestones.create_milestone(portfolio_id=2, name="v1.0")
    assert milestone_id == 1


def test_create_milestone_with_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_milestone() passes optional kwargs to the API call."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        milestone_id = client.milestones.create_milestone(
            portfolio_id=2,
            name="v2.0",
            description="Second release",
            target_date="2026-06-30",
            color_id="red",
        )
    assert milestone_id == 7


def test_create_milestone_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_milestone() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createMilestone"):
            client.milestones.create_milestone(portfolio_id=99, name="Duplicate")


def test_create_milestone_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_milestone() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createMilestone"):
            client.milestones.create_milestone(portfolio_id=99, name="Bad")


def test_create_milestone_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_milestone() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.milestones.create_milestone(portfolio_id=1, name="Blocked")


# ---------------------------------------------------------------------------
# get_milestone
# ---------------------------------------------------------------------------


def test_get_milestone_returns_plugin_milestone_instance(httpx_mock: HTTPXMock) -> None:
    """get_milestone() returns a populated PluginMilestone dataclass for a valid ID."""
    httpx_mock.add_response(json=_rpc_ok(_MILESTONE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        milestone = client.milestones.get_milestone(1)
    assert isinstance(milestone, PluginMilestone)
    assert milestone.id == 1
    assert milestone.portfolio_id == 2
    assert milestone.name == "v1.0 Release"
    assert milestone.owner_id == 3


def test_get_milestone_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_milestone() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.milestones.get_milestone(999)
    assert "999" in str(exc_info.value)


def test_get_milestone_not_found_identifies_resource(httpx_mock: HTTPXMock) -> None:
    """get_milestone() KanboardNotFoundError carries resource='PluginMilestone'."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.milestones.get_milestone(42)
    assert exc_info.value.resource == "PluginMilestone"


def test_get_milestone_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_milestone() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.milestones.get_milestone(1)


# ---------------------------------------------------------------------------
# get_portfolio_milestones
# ---------------------------------------------------------------------------


def test_get_portfolio_milestones_returns_list_of_plugin_milestones(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_milestones() returns a list of PluginMilestone instances."""
    httpx_mock.add_response(json=_rpc_ok([_MILESTONE_DATA, _MILESTONE_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        milestones = client.milestones.get_portfolio_milestones(2)
    assert len(milestones) == 2
    assert all(isinstance(m, PluginMilestone) for m in milestones)
    assert milestones[0].name == "v1.0 Release"
    assert milestones[1].name == "v2.0 Release"


def test_get_portfolio_milestones_returns_empty_list_on_false(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_milestones() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_portfolio_milestones(99)
    assert result == []


def test_get_portfolio_milestones_returns_empty_list_on_none(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_milestones() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_portfolio_milestones(99)
    assert result == []


def test_get_portfolio_milestones_returns_empty_list_on_empty_array(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_milestones() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_portfolio_milestones(2)
    assert result == []


# ---------------------------------------------------------------------------
# update_milestone
# ---------------------------------------------------------------------------


def test_update_milestone_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_milestone() returns True when the update succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.update_milestone(1, name="v1.1 Release")
    assert result is True


def test_update_milestone_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_milestone() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="updateMilestone"):
            client.milestones.update_milestone(999, name="Ghost")


def test_update_milestone_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_milestone() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.milestones.update_milestone(1, name="Blocked")


# ---------------------------------------------------------------------------
# remove_milestone
# ---------------------------------------------------------------------------


def test_remove_milestone_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_milestone() returns True when deletion succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.remove_milestone(1)
    assert result is True


def test_remove_milestone_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """remove_milestone() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.remove_milestone(999)
    assert result is False


def test_remove_milestone_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_milestone() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.milestones.remove_milestone(1)


# ---------------------------------------------------------------------------
# add_task_to_milestone
# ---------------------------------------------------------------------------


def test_add_task_to_milestone_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """add_task_to_milestone() returns True when the task is added."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.add_task_to_milestone(1, 10)
    assert result is True


def test_add_task_to_milestone_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """add_task_to_milestone() passes optional kwargs to the API call."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.add_task_to_milestone(1, 10, sort_order=1)
    assert result is True


def test_add_task_to_milestone_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """add_task_to_milestone() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="addTaskToMilestone"):
            client.milestones.add_task_to_milestone(1, 999)


def test_add_task_to_milestone_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """add_task_to_milestone() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.milestones.add_task_to_milestone(1, 10)


# ---------------------------------------------------------------------------
# remove_task_from_milestone
# ---------------------------------------------------------------------------


def test_remove_task_from_milestone_returns_true_on_success(
    httpx_mock: HTTPXMock,
) -> None:
    """remove_task_from_milestone() returns True on successful removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.remove_task_from_milestone(1, 10)
    assert result is True


def test_remove_task_from_milestone_returns_false_on_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """remove_task_from_milestone() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.remove_task_from_milestone(1, 999)
    assert result is False


def test_remove_task_from_milestone_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_task_from_milestone() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.milestones.remove_task_from_milestone(1, 10)


# ---------------------------------------------------------------------------
# get_milestone_tasks
# ---------------------------------------------------------------------------


def test_get_milestone_tasks_returns_list_of_dicts(httpx_mock: HTTPXMock) -> None:
    """get_milestone_tasks() returns a list of task dicts."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.milestones.get_milestone_tasks(1)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Implement feature"


def test_get_milestone_tasks_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_milestone_tasks() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_milestone_tasks(1)
    assert result == []


def test_get_milestone_tasks_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_milestone_tasks() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_milestone_tasks(1)
    assert result == []


def test_get_milestone_tasks_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_milestone_tasks() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Plugin error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Plugin error"):
            client.milestones.get_milestone_tasks(1)


# ---------------------------------------------------------------------------
# get_task_milestones
# ---------------------------------------------------------------------------


def test_get_task_milestones_returns_list_of_plugin_milestones(
    httpx_mock: HTTPXMock,
) -> None:
    """get_task_milestones() returns a list of PluginMilestone instances."""
    httpx_mock.add_response(json=_rpc_ok([_MILESTONE_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        milestones = client.milestones.get_task_milestones(10)
    assert len(milestones) == 1
    assert isinstance(milestones[0], PluginMilestone)
    assert milestones[0].id == 1


def test_get_task_milestones_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_task_milestones() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_task_milestones(99)
    assert result == []


def test_get_task_milestones_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_milestones() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.milestones.get_task_milestones(99)
    assert result == []


# ---------------------------------------------------------------------------
# get_milestone_progress
# ---------------------------------------------------------------------------


def test_get_milestone_progress_returns_plugin_milestone_progress(
    httpx_mock: HTTPXMock,
) -> None:
    """get_milestone_progress() returns a PluginMilestoneProgress for a valid ID."""
    httpx_mock.add_response(json=_rpc_ok(_PROGRESS_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        progress = client.milestones.get_milestone_progress(1)
    assert isinstance(progress, PluginMilestoneProgress)
    assert progress.milestone_id == 1
    assert progress.total == 8
    assert progress.completed == 5
    assert progress.percent == pytest.approx(62.5)
    assert progress.is_at_risk is True
    assert progress.is_overdue is False


def test_get_milestone_progress_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_milestone_progress() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.milestones.get_milestone_progress(999)
    assert "999" in str(exc_info.value)


def test_get_milestone_progress_not_found_identifies_resource(
    httpx_mock: HTTPXMock,
) -> None:
    """get_milestone_progress() KanboardNotFoundError carries resource='PluginMilestoneProgress'."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.milestones.get_milestone_progress(42)
    assert exc_info.value.resource == "PluginMilestoneProgress"


def test_get_milestone_progress_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_milestone_progress() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Plugin not installed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Plugin not installed"):
            client.milestones.get_milestone_progress(1)


# ---------------------------------------------------------------------------
# MilestonesResource is importable from kanboard package
# ---------------------------------------------------------------------------


def test_milestones_resource_importable_from_kanboard_package() -> None:
    """MilestonesResource is accessible in the kanboard package __all__."""
    import kanboard

    assert hasattr(kanboard, "MilestonesResource")
    assert "MilestonesResource" in kanboard.__all__


def test_milestones_resource_accessible_on_client(httpx_mock: HTTPXMock) -> None:
    """client.milestones is an instance of MilestonesResource."""
    from kanboard.resources.milestones import MilestonesResource

    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.milestones, MilestonesResource)
