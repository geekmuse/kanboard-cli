"""Unit tests for TaskFilesResource — all 6 task file API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError, KanboardNotFoundError
from kanboard.models import TaskFile
from kanboard.resources.task_files import TaskFilesResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FILE_DATA: dict = {
    "id": "10",
    "name": "screenshot.png",
    "path": "tasks/42/screenshot.png",
    "is_image": "1",
    "task_id": "42",
    "date": "1711078800",
    "size": "102400",
    "username": "bob",
    "user_id": "3",
    "project_id": "1",
    "mime_type": "image/png",
}

_FILE_DATA_2: dict = {
    **_FILE_DATA,
    "id": "11",
    "name": "notes.txt",
    "is_image": "0",
    "size": "512",
    "mime_type": "text/plain",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_task_file
# ---------------------------------------------------------------------------


def test_create_task_file_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_task_file() returns the integer ID of the new file."""
    httpx_mock.add_response(json=_rpc_ok(10))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.create_task_file(1, 42, "screenshot.png", "base64content==")
    assert result == 10
    assert isinstance(result, int)


def test_create_task_file_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_task_file() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create task file"):
            client.task_files.create_task_file(1, 42, "screenshot.png", "base64content==")


def test_create_task_file_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_task_file() raises KanboardAPIError when API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.task_files.create_task_file(1, 42, "screenshot.png", "base64content==")


def test_create_task_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """create_task_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.task_files.create_task_file(1, 42, "screenshot.png", "base64content==")


def test_create_task_file_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_task_file() accepts and forwards extra keyword arguments."""
    httpx_mock.add_response(json=_rpc_ok(12))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.create_task_file(
            1, 42, "extra.txt", "base64==", extra_param="value"
        )
    assert result == 12


# ---------------------------------------------------------------------------
# get_all_task_files
# ---------------------------------------------------------------------------


def test_get_all_task_files_returns_list_of_models(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() returns a list of TaskFile instances."""
    httpx_mock.add_response(json=_rpc_ok([_FILE_DATA, _FILE_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.get_all_task_files(42)
    assert len(result) == 2
    assert all(isinstance(f, TaskFile) for f in result)


def test_get_all_task_files_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() maps fields correctly for the first file."""
    httpx_mock.add_response(json=_rpc_ok([_FILE_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.get_all_task_files(42)
    f = result[0]
    assert f.id == 10
    assert f.name == "screenshot.png"
    assert f.size == 102400
    assert f.mime_type == "image/png"
    assert f.username == "bob"
    assert f.task_id == 42
    assert f.project_id == 1
    assert f.user_id == 3
    assert f.is_image is True


def test_get_all_task_files_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.get_all_task_files(42)
    assert result == []


def test_get_all_task_files_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.get_all_task_files(42)
    assert result == []


def test_get_all_task_files_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() returns [] when API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.get_all_task_files(42)
    assert result == []


def test_get_all_task_files_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.task_files.get_all_task_files(42)


# ---------------------------------------------------------------------------
# get_task_file
# ---------------------------------------------------------------------------


def test_get_task_file_returns_model(httpx_mock: HTTPXMock) -> None:
    """get_task_file() returns a TaskFile instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_FILE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.get_task_file(10)
    assert isinstance(result, TaskFile)


def test_get_task_file_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_task_file() maps API fields to TaskFile dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok(_FILE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        f = client.task_files.get_task_file(10)
    assert f.id == 10
    assert f.name == "screenshot.png"
    assert f.task_id == 42
    assert f.project_id == 1
    assert f.user_id == 3
    assert f.is_image is True
    assert f.mime_type == "image/png"


def test_get_task_file_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_file() raises KanboardNotFoundError when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.task_files.get_task_file(999)
    err = exc_info.value
    assert err.resource == "TaskFile"
    assert err.identifier == 999


def test_get_task_file_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_task_file() raises KanboardNotFoundError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError):
            client.task_files.get_task_file(999)


def test_get_task_file_not_found_message(httpx_mock: HTTPXMock) -> None:
    """get_task_file() not-found message includes the file ID."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(
            KanboardNotFoundError,
            match=r"Not found: TaskFile '999' does not exist",
        ):
            client.task_files.get_task_file(999)


def test_get_task_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_task_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.task_files.get_task_file(10)


# ---------------------------------------------------------------------------
# download_task_file
# ---------------------------------------------------------------------------


def test_download_task_file_returns_base64_string(httpx_mock: HTTPXMock) -> None:
    """download_task_file() returns the base64-encoded content string."""
    httpx_mock.add_response(json=_rpc_ok("SGVsbG8gV29ybGQ="))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.download_task_file(10)
    assert result == "SGVsbG8gV29ybGQ="
    assert isinstance(result, str)


def test_download_task_file_returns_empty_string_on_none(httpx_mock: HTTPXMock) -> None:
    """download_task_file() returns empty string when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.download_task_file(10)
    assert result == ""


def test_download_task_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """download_task_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "File not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="File not found"):
            client.task_files.download_task_file(999)


# ---------------------------------------------------------------------------
# remove_task_file
# ---------------------------------------------------------------------------


def test_remove_task_file_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_task_file() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.remove_task_file(10)
    assert result is True


def test_remove_task_file_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_task_file() returns False when API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.remove_task_file(999)
    assert result is False


def test_remove_task_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_task_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.task_files.remove_task_file(10)


# ---------------------------------------------------------------------------
# remove_all_task_files
# ---------------------------------------------------------------------------


def test_remove_all_task_files_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_all_task_files() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.remove_all_task_files(42)
    assert result is True


def test_remove_all_task_files_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_all_task_files() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.task_files.remove_all_task_files(42)
    assert result is False


def test_remove_all_task_files_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_all_task_files() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.task_files.remove_all_task_files(42)


# ---------------------------------------------------------------------------
# Network failure tests
# ---------------------------------------------------------------------------


def test_create_task_file_network_failure(httpx_mock: HTTPXMock) -> None:
    """create_task_file() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_files.create_task_file(1, 42, "f.pdf", "base64==")


def test_get_all_task_files_connection_error(httpx_mock: HTTPXMock) -> None:
    """get_all_task_files() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_files.get_all_task_files(42)


def test_download_task_file_connection_error(httpx_mock: HTTPXMock) -> None:
    """download_task_file() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_files.download_task_file(10)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_task_files_resource_wired_on_client() -> None:
    """KanboardClient exposes a TaskFilesResource instance as .task_files."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.task_files, TaskFilesResource)


def test_task_files_resource_importable_from_kanboard() -> None:
    """TaskFilesResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "TaskFilesResource")
    assert kanboard.TaskFilesResource is TaskFilesResource
