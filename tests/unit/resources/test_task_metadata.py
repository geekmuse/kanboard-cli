"""Unit tests for TaskMetadataResource - all 4 task metadata API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError
from kanboard.resources.task_metadata import TaskMetadataResource

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
# get_task_metadata
# ===========================================================================


def test_get_task_metadata_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() returns a dict of key-value pairs."""
    httpx_mock.add_response(json=_rpc_ok({"priority": "high", "reviewer": "bob"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata(42)
    assert result == {"priority": "high", "reviewer": "bob"}
    assert isinstance(result, dict)


def test_get_task_metadata_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata(42)
    assert result == {}


def test_get_task_metadata_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata(42)
    assert result == {}


def test_get_task_metadata_returns_empty_on_empty_dict(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() returns {} when API returns an empty dict."""
    httpx_mock.add_response(json=_rpc_ok({}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata(42)
    assert result == {}


def test_get_task_metadata_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() returns {} when API returns [] (Kanboard quirk)."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata(42)
    assert result == {}


def test_get_task_metadata_returns_empty_on_non_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() returns {} when API returns a non-empty list (unexpected)."""
    httpx_mock.add_response(json=_rpc_ok(["unexpected"]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata(42)
    assert result == {}


def test_get_task_metadata_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.task_metadata.get_task_metadata(42)


# ===========================================================================
# get_task_metadata_by_name
# ===========================================================================


def test_get_task_metadata_by_name_returns_string(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata_by_name() returns the metadata value as a string."""
    httpx_mock.add_response(json=_rpc_ok("high"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata_by_name(42, "priority")
    assert result == "high"
    assert isinstance(result, str)


def test_get_task_metadata_by_name_returns_empty_on_empty_string(
    httpx_mock: HTTPXMock,
) -> None:
    """get_task_metadata_by_name() returns '' when API returns empty string."""
    httpx_mock.add_response(json=_rpc_ok(""))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata_by_name(42, "missing")
    assert result == ""


def test_get_task_metadata_by_name_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata_by_name() returns '' when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata_by_name(42, "missing")
    assert result == ""


def test_get_task_metadata_by_name_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata_by_name() returns '' when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata_by_name(42, "missing")
    assert result == ""


def test_get_task_metadata_by_name_preserves_zero_value(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata_by_name() returns '0' when API returns 0 (not empty)."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.get_task_metadata_by_name(42, "count")
    assert result == "0"


def test_get_task_metadata_by_name_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata_by_name() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.task_metadata.get_task_metadata_by_name(42, "priority")


# ===========================================================================
# save_task_metadata
# ===========================================================================


def test_save_task_metadata_returns_true(httpx_mock: HTTPXMock) -> None:
    """save_task_metadata() returns True when API confirms save."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.save_task_metadata(42, {"priority": "high"})
    assert result is True


def test_save_task_metadata_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """save_task_metadata() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to save metadata"):
            client.task_metadata.save_task_metadata(42, {"priority": "high"})


def test_save_task_metadata_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """save_task_metadata() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Internal error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Internal error"):
            client.task_metadata.save_task_metadata(42, {"k": "v"})


def test_save_task_metadata_multiple_keys(httpx_mock: HTTPXMock) -> None:
    """save_task_metadata() accepts multiple key-value pairs."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.save_task_metadata(
            42, {"priority": "high", "reviewer": "bob"}
        )
    assert result is True


# ===========================================================================
# remove_task_metadata
# ===========================================================================


def test_remove_task_metadata_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_task_metadata() returns True when API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.remove_task_metadata(42, "priority")
    assert result is True


def test_remove_task_metadata_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_task_metadata() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_metadata.remove_task_metadata(42, "missing")
    assert result is False


def test_remove_task_metadata_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_task_metadata() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.task_metadata.remove_task_metadata(42, "priority")


# ===========================================================================
# Network failure tests
# ===========================================================================


def test_get_task_metadata_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_metadata.get_task_metadata(42)


def test_get_task_metadata_by_name_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_task_metadata_by_name() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_metadata.get_task_metadata_by_name(42, "priority")


def test_save_task_metadata_network_failure(httpx_mock: HTTPXMock) -> None:
    """save_task_metadata() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_metadata.save_task_metadata(42, {"k": "v"})


def test_remove_task_metadata_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_task_metadata() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_metadata.remove_task_metadata(42, "priority")


# ===========================================================================
# Client wiring / importability
# ===========================================================================


def test_task_metadata_resource_wired_on_client() -> None:
    """KanboardClient exposes a TaskMetadataResource as .task_metadata."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.task_metadata, TaskMetadataResource)


def test_task_metadata_resource_importable_from_kanboard() -> None:
    """TaskMetadataResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "TaskMetadataResource")
    assert kanboard.TaskMetadataResource is TaskMetadataResource
