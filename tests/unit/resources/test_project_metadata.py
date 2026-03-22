"""Unit tests for ProjectMetadataResource — all 4 project metadata API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError
from kanboard.resources.project_metadata import ProjectMetadataResource

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
# get_project_metadata
# ===========================================================================


def test_get_project_metadata_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata() returns a dict of key-value pairs."""
    httpx_mock.add_response(json=_rpc_ok({"owner": "alice", "priority": "high"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata(1)
    assert result == {"owner": "alice", "priority": "high"}
    assert isinstance(result, dict)


def test_get_project_metadata_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata(1)
    assert result == {}


def test_get_project_metadata_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata(1)
    assert result == {}


def test_get_project_metadata_returns_empty_on_empty_dict(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata() returns {} when API returns an empty dict."""
    httpx_mock.add_response(json=_rpc_ok({}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata(1)
    assert result == {}


def test_get_project_metadata_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.project_metadata.get_project_metadata(1)


# ===========================================================================
# get_project_metadata_by_name
# ===========================================================================


def test_get_project_metadata_by_name_returns_string(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata_by_name() returns the metadata value as a string."""
    httpx_mock.add_response(json=_rpc_ok("alice"))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata_by_name(1, "owner")
    assert result == "alice"
    assert isinstance(result, str)


def test_get_project_metadata_by_name_returns_empty_on_empty_string(
    httpx_mock: HTTPXMock,
) -> None:
    """get_project_metadata_by_name() returns '' when API returns empty string."""
    httpx_mock.add_response(json=_rpc_ok(""))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata_by_name(1, "missing")
    assert result == ""


def test_get_project_metadata_by_name_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata_by_name() returns '' when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata_by_name(1, "missing")
    assert result == ""


def test_get_project_metadata_by_name_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata_by_name() returns '' when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata_by_name(1, "missing")
    assert result == ""


def test_get_project_metadata_by_name_preserves_zero_value(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata_by_name() returns '0' when API returns 0 (not empty)."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.get_project_metadata_by_name(1, "count")
    assert result == "0"


def test_get_project_metadata_by_name_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata_by_name() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.project_metadata.get_project_metadata_by_name(1, "owner")


# ===========================================================================
# save_project_metadata
# ===========================================================================


def test_save_project_metadata_returns_true(httpx_mock: HTTPXMock) -> None:
    """save_project_metadata() returns True when API confirms save."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.save_project_metadata(1, {"owner": "alice"})
    assert result is True


def test_save_project_metadata_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """save_project_metadata() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to save metadata"):
            client.project_metadata.save_project_metadata(1, {"owner": "alice"})


def test_save_project_metadata_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """save_project_metadata() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Internal error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Internal error"):
            client.project_metadata.save_project_metadata(1, {"k": "v"})


def test_save_project_metadata_multiple_keys(httpx_mock: HTTPXMock) -> None:
    """save_project_metadata() accepts multiple key-value pairs."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.save_project_metadata(
            1, {"owner": "alice", "priority": "high"}
        )
    assert result is True


# ===========================================================================
# remove_project_metadata
# ===========================================================================


def test_remove_project_metadata_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_project_metadata() returns True when API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.remove_project_metadata(1, "owner")
    assert result is True


def test_remove_project_metadata_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_project_metadata() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_metadata.remove_project_metadata(1, "missing")
    assert result is False


def test_remove_project_metadata_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_project_metadata() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.project_metadata.remove_project_metadata(1, "owner")


# ===========================================================================
# Network failure tests
# ===========================================================================


def test_get_project_metadata_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_metadata.get_project_metadata(1)


def test_get_project_metadata_by_name_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_project_metadata_by_name() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_metadata.get_project_metadata_by_name(1, "owner")


def test_save_project_metadata_network_failure(httpx_mock: HTTPXMock) -> None:
    """save_project_metadata() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_metadata.save_project_metadata(1, {"k": "v"})


def test_remove_project_metadata_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_project_metadata() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_metadata.remove_project_metadata(1, "owner")


# ===========================================================================
# Client wiring / importability
# ===========================================================================


def test_project_metadata_resource_wired_on_client() -> None:
    """KanboardClient exposes a ProjectMetadataResource as .project_metadata."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.project_metadata, ProjectMetadataResource)


def test_project_metadata_resource_importable_from_kanboard() -> None:
    """ProjectMetadataResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "ProjectMetadataResource")
    assert kanboard.ProjectMetadataResource is ProjectMetadataResource
