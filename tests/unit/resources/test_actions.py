"""Unit tests for ActionsResource - all 6 automatic-action API methods."""

from __future__ import annotations

import httpx as httpx_lib
import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError
from kanboard.models import Action
from kanboard.resources.actions import ActionsResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTION_DATA: dict = {
    "id": "1",
    "project_id": "2",
    "event_name": "task.move.column",
    "action_name": "\\TaskClose",
    "params": {"column_id": "5"},
}

_ACTION_DATA_2: dict = {
    "id": "3",
    "project_id": "2",
    "event_name": "task.create",
    "action_name": "\\TaskAssignUser",
    "params": {"user_id": "10"},
}


def _rpc_ok(result: object, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


# ===========================================================================
# get_available_actions
# ===========================================================================


def test_get_available_actions_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_available_actions() returns a dict of action types."""
    httpx_mock.add_response(
        json=_rpc_ok({"\\TaskClose": "Close a task", "\\TaskOpen": "Open a task"})
    )
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_available_actions()
    assert result == {"\\TaskClose": "Close a task", "\\TaskOpen": "Open a task"}


def test_get_available_actions_empty_false(httpx_mock: HTTPXMock) -> None:
    """get_available_actions() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_available_actions()
    assert result == {}


def test_get_available_actions_empty_none(httpx_mock: HTTPXMock) -> None:
    """get_available_actions() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_available_actions()
    assert result == {}


def test_get_available_actions_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_available_actions() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.actions.get_available_actions()


# ===========================================================================
# get_available_action_events
# ===========================================================================


def test_get_available_action_events_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_available_action_events() returns a dict of event types."""
    httpx_mock.add_response(
        json=_rpc_ok(
            {
                "task.move.column": "Task moved to another column",
                "task.create": "Task creation",
            }
        )
    )
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_available_action_events()
    assert result == {
        "task.move.column": "Task moved to another column",
        "task.create": "Task creation",
    }


def test_get_available_action_events_empty_false(httpx_mock: HTTPXMock) -> None:
    """get_available_action_events() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_available_action_events()
    assert result == {}


def test_get_available_action_events_empty_none(httpx_mock: HTTPXMock) -> None:
    """get_available_action_events() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_available_action_events()
    assert result == {}


def test_get_available_action_events_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_available_action_events() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.actions.get_available_action_events()


# ===========================================================================
# get_compatible_action_events
# ===========================================================================


def test_get_compatible_action_events_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_compatible_action_events() returns a list of event names."""
    httpx_mock.add_response(json=_rpc_ok(["task.move.column", "task.create"]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_compatible_action_events("\\TaskClose")
    assert result == ["task.move.column", "task.create"]


def test_get_compatible_action_events_returns_dict_list(httpx_mock: HTTPXMock) -> None:
    """get_compatible_action_events() handles dict-keyed result from API."""
    httpx_mock.add_response(
        json=_rpc_ok({"task.move.column": "Move column", "task.create": "Create"})
    )
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_compatible_action_events("\\TaskClose")
    # dict is truthy, list() on dict yields keys
    assert "task.move.column" in result
    assert "task.create" in result


def test_get_compatible_action_events_empty_false(httpx_mock: HTTPXMock) -> None:
    """get_compatible_action_events() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_compatible_action_events("\\TaskClose")
    assert result == []


def test_get_compatible_action_events_empty_none(httpx_mock: HTTPXMock) -> None:
    """get_compatible_action_events() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_compatible_action_events("\\TaskClose")
    assert result == []


def test_get_compatible_action_events_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_compatible_action_events() returns [] when API returns []."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_compatible_action_events("\\TaskClose")
    assert result == []


def test_get_compatible_action_events_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_compatible_action_events() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.actions.get_compatible_action_events("\\TaskClose")


# ===========================================================================
# get_actions
# ===========================================================================


def test_get_actions_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_actions() returns a list of Action instances."""
    httpx_mock.add_response(json=_rpc_ok([_ACTION_DATA, _ACTION_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_actions(2)
    assert len(result) == 2
    assert isinstance(result[0], Action)
    assert result[0].id == 1
    assert result[0].project_id == 2
    assert result[0].event_name == "task.move.column"
    assert result[0].action_name == "\\TaskClose"
    assert result[0].params == {"column_id": "5"}
    assert result[1].id == 3


def test_get_actions_single(httpx_mock: HTTPXMock) -> None:
    """get_actions() works with a single item."""
    httpx_mock.add_response(json=_rpc_ok([_ACTION_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_actions(2)
    assert len(result) == 1
    assert result[0].action_name == "\\TaskClose"


def test_get_actions_empty_false(httpx_mock: HTTPXMock) -> None:
    """get_actions() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_actions(2)
    assert result == []


def test_get_actions_empty_none(httpx_mock: HTTPXMock) -> None:
    """get_actions() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_actions(2)
    assert result == []


def test_get_actions_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_actions() returns [] when API returns []."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.get_actions(2)
    assert result == []


def test_get_actions_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_actions() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.actions.get_actions(2)


# ===========================================================================
# create_action
# ===========================================================================


def test_create_action_returns_id(httpx_mock: HTTPXMock) -> None:
    """create_action() returns the new action ID."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.create_action(
            project_id=2,
            event_name="task.move.column",
            action_name="\\TaskClose",
            params={"column_id": "5"},
        )
    assert result == 7


def test_create_action_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_action() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create action"):
            client.actions.create_action(
                project_id=2,
                event_name="task.move.column",
                action_name="\\TaskClose",
                params={"column_id": "5"},
            )


def test_create_action_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_action() raises KanboardAPIError when API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create action"):
            client.actions.create_action(
                project_id=2,
                event_name="task.move.column",
                action_name="\\TaskClose",
                params={"column_id": "5"},
            )


def test_create_action_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_action() raises KanboardAPIError on RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32602, "Invalid params"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Invalid params"):
            client.actions.create_action(
                project_id=2,
                event_name="task.move.column",
                action_name="\\TaskClose",
                params={"column_id": "5"},
            )


def test_create_action_network_failure(httpx_mock: HTTPXMock) -> None:
    """create_action() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.actions.create_action(
                project_id=2,
                event_name="task.move.column",
                action_name="\\TaskClose",
                params={"column_id": "5"},
            )


# ===========================================================================
# remove_action
# ===========================================================================


def test_remove_action_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_action() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.remove_action(1)
    assert result is True


def test_remove_action_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_action() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.actions.remove_action(999)
    assert result is False


def test_remove_action_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_action() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.actions.remove_action(1)


# ===========================================================================
# Client wiring
# ===========================================================================


def test_client_has_actions_attribute(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes an .actions attribute of the correct type."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert hasattr(client, "actions")
        assert isinstance(client.actions, ActionsResource)


# ===========================================================================
# Package importability
# ===========================================================================


def test_actions_resource_importable_from_package() -> None:
    """ActionsResource is importable from the top-level kanboard package."""
    from kanboard import ActionsResource as Imported

    assert Imported is ActionsResource
