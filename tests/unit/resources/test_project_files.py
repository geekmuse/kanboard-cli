"""Unit tests for ProjectFilesResource — all 6 project file API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError, KanboardNotFoundError
from kanboard.models import ProjectFile
from kanboard.resources.project_files import ProjectFilesResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FILE_DATA: dict = {
    "id": "5",
    "name": "report.pdf",
    "path": "projects/5/report.pdf",
    "is_image": "0",
    "project_id": "1",
    "owner_id": "2",
    "date": "1711078800",
    "size": "204800",
    "username": "alice",
    "task_id": "0",
    "mime_type": "application/pdf",
}

_FILE_DATA_2: dict = {
    **_FILE_DATA,
    "id": "6",
    "name": "spec.md",
    "size": "1024",
    "mime_type": "text/markdown",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_project_file
# ---------------------------------------------------------------------------


def test_create_project_file_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_project_file() returns the integer ID of the new file."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.create_project_file(1, "report.pdf", "base64content==")
    assert result == 5
    assert isinstance(result, int)


def test_create_project_file_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_project_file() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create project file"):
            client.project_files.create_project_file(1, "report.pdf", "base64content==")


def test_create_project_file_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_project_file() raises KanboardAPIError when API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.project_files.create_project_file(1, "report.pdf", "base64content==")


def test_create_project_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """create_project_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.project_files.create_project_file(1, "report.pdf", "base64content==")


def test_create_project_file_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_project_file() accepts and forwards extra keyword arguments."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.create_project_file(
            1, "extra.txt", "base64==", extra_param="value"
        )
    assert result == 7


# ---------------------------------------------------------------------------
# get_all_project_files
# ---------------------------------------------------------------------------


def test_get_all_project_files_returns_list_of_models(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() returns a list of ProjectFile instances."""
    httpx_mock.add_response(json=_rpc_ok([_FILE_DATA, _FILE_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.get_all_project_files(1)
    assert len(result) == 2
    assert all(isinstance(f, ProjectFile) for f in result)


def test_get_all_project_files_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() maps fields correctly for the first file."""
    httpx_mock.add_response(json=_rpc_ok([_FILE_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.get_all_project_files(1)
    f = result[0]
    assert f.id == 5
    assert f.name == "report.pdf"
    assert f.size == 204800
    assert f.mime_type == "application/pdf"
    assert f.username == "alice"


def test_get_all_project_files_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.get_all_project_files(1)
    assert result == []


def test_get_all_project_files_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.get_all_project_files(1)
    assert result == []


def test_get_all_project_files_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() returns [] when API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.get_all_project_files(1)
    assert result == []


def test_get_all_project_files_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() propagates KanboardAPIError."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.project_files.get_all_project_files(1)


# ---------------------------------------------------------------------------
# get_project_file
# ---------------------------------------------------------------------------


def test_get_project_file_returns_model(httpx_mock: HTTPXMock) -> None:
    """get_project_file() returns a ProjectFile instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_FILE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.get_project_file(1, 5)
    assert isinstance(result, ProjectFile)


def test_get_project_file_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_project_file() maps API fields to ProjectFile dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok(_FILE_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        f = client.project_files.get_project_file(1, 5)
    assert f.id == 5
    assert f.name == "report.pdf"
    assert f.project_id == 1
    assert f.owner_id == 2
    assert f.is_image is False
    assert f.mime_type == "application/pdf"


def test_get_project_file_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_project_file() raises KanboardNotFoundError when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.project_files.get_project_file(1, 999)
    err = exc_info.value
    assert err.resource == "ProjectFile"
    assert err.identifier == 999


def test_get_project_file_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_project_file() raises KanboardNotFoundError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError):
            client.project_files.get_project_file(1, 999)


def test_get_project_file_not_found_message(httpx_mock: HTTPXMock) -> None:
    """get_project_file() not-found message includes the file ID."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(
            KanboardNotFoundError,
            match=r"Not found: ProjectFile '999' does not exist",
        ):
            client.project_files.get_project_file(1, 999)


def test_get_project_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_project_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.project_files.get_project_file(1, 5)


# ---------------------------------------------------------------------------
# download_project_file
# ---------------------------------------------------------------------------


def test_download_project_file_returns_base64_string(httpx_mock: HTTPXMock) -> None:
    """download_project_file() returns the base64-encoded content string."""
    httpx_mock.add_response(json=_rpc_ok("SGVsbG8gV29ybGQ="))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.download_project_file(1, 5)
    assert result == "SGVsbG8gV29ybGQ="
    assert isinstance(result, str)


def test_download_project_file_returns_empty_string_on_none(httpx_mock: HTTPXMock) -> None:
    """download_project_file() returns empty string when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.download_project_file(1, 5)
    assert result == ""


def test_download_project_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """download_project_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "File not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="File not found"):
            client.project_files.download_project_file(1, 999)


# ---------------------------------------------------------------------------
# remove_project_file
# ---------------------------------------------------------------------------


def test_remove_project_file_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_project_file() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.remove_project_file(1, 5)
    assert result is True


def test_remove_project_file_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_project_file() returns False when API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.remove_project_file(1, 999)
    assert result is False


def test_remove_project_file_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_project_file() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.project_files.remove_project_file(1, 5)


# ---------------------------------------------------------------------------
# remove_all_project_files
# ---------------------------------------------------------------------------


def test_remove_all_project_files_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_all_project_files() returns True when API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.remove_all_project_files(1)
    assert result is True


def test_remove_all_project_files_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_all_project_files() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.project_files.remove_all_project_files(1)
    assert result is False


def test_remove_all_project_files_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_all_project_files() propagates KanboardAPIError from a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.project_files.remove_all_project_files(1)


# ---------------------------------------------------------------------------
# Network failure tests
# ---------------------------------------------------------------------------


def test_create_project_file_network_failure(httpx_mock: HTTPXMock) -> None:
    """create_project_file() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_files.create_project_file(1, "f.pdf", "base64==")


def test_get_all_project_files_connection_error(httpx_mock: HTTPXMock) -> None:
    """get_all_project_files() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_files.get_all_project_files(1)


def test_download_project_file_connection_error(httpx_mock: HTTPXMock) -> None:
    """download_project_file() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.project_files.download_project_file(1, 5)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_project_files_resource_wired_on_client() -> None:
    """KanboardClient exposes a ProjectFilesResource instance as .project_files."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.project_files, ProjectFilesResource)


def test_project_files_resource_importable_from_kanboard() -> None:
    """ProjectFilesResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "ProjectFilesResource")
    assert kanboard.ProjectFilesResource is ProjectFilesResource
