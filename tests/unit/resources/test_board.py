"""Unit tests for BoardResource — getBoard API method."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError
from kanboard.resources.board import BoardResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BOARD_COLUMN: dict = {
    "id": "1",
    "title": "Backlog",
    "task_limit": "0",
    "position": "1",
    "swimlanes": [
        {
            "id": "0",
            "name": "Default swimlane",
            "tasks": [
                {
                    "id": "1",
                    "title": "Sample task",
                    "column_id": "1",
                    "swimlane_id": "0",
                }
            ],
        }
    ],
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# get_board — successful response
# ---------------------------------------------------------------------------


def test_get_board_returns_list_of_column_dicts(httpx_mock: HTTPXMock) -> None:
    """get_board() returns a list of column dicts on a successful API call."""
    httpx_mock.add_response(json=_rpc_ok([_BOARD_COLUMN]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.board.get_board(1)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Backlog"


def test_get_board_preserves_nested_structure(httpx_mock: HTTPXMock) -> None:
    """get_board() preserves the full nested column/swimlane/task structure."""
    httpx_mock.add_response(json=_rpc_ok([_BOARD_COLUMN]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.board.get_board(1)
    swimlanes = result[0]["swimlanes"]
    assert len(swimlanes) == 1
    assert swimlanes[0]["tasks"][0]["title"] == "Sample task"


def test_get_board_returns_multiple_columns(httpx_mock: HTTPXMock) -> None:
    """get_board() returns all columns when the board has multiple columns."""
    col2 = dict(_BOARD_COLUMN)
    col2["id"] = "2"
    col2["title"] = "In Progress"
    col2["position"] = "2"
    httpx_mock.add_response(json=_rpc_ok([_BOARD_COLUMN, col2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.board.get_board(1)
    assert len(result) == 2
    assert result[1]["title"] == "In Progress"


# ---------------------------------------------------------------------------
# get_board — empty / falsy board
# ---------------------------------------------------------------------------


def test_get_board_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_board() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.board.get_board(99)
    assert result == []


def test_get_board_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_board() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.board.get_board(99)
    assert result == []


def test_get_board_returns_empty_list_on_empty_array(httpx_mock: HTTPXMock) -> None:
    """get_board() returns [] when the API returns an empty array."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.board.get_board(99)
    assert result == []


# ---------------------------------------------------------------------------
# get_board — error responses
# ---------------------------------------------------------------------------


def test_get_board_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_board() raises KanboardAPIError when the API returns a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.board.get_board(1)


def test_get_board_raises_on_access_denied_error(httpx_mock: HTTPXMock) -> None:
    """get_board() raises KanboardAPIError on any API-level error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.board.get_board(1)


# ---------------------------------------------------------------------------
# BoardResource accessor on KanboardClient
# ---------------------------------------------------------------------------


def test_board_resource_accessible_on_client() -> None:
    """KanboardClient.board is a BoardResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.board, BoardResource)


def test_board_resource_importable_from_kanboard() -> None:
    """BoardResource is importable directly from the kanboard package."""
    import kanboard

    assert kanboard.BoardResource is BoardResource
