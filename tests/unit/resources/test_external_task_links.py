"""Unit tests for ExternalTaskLinksResource - all 7 external-task-link API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import (
    KanboardAPIError,
    KanboardConnectionError,
    KanboardNotFoundError,
)
from kanboard.models import ExternalTaskLink
from kanboard.resources.external_task_links import ExternalTaskLinksResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXT_LINK_DATA: dict = {
    "id": "1",
    "task_id": "10",
    "url": "https://github.com/org/repo/issues/1",
    "title": "GitHub Issue #1",
    "link_type": "weblink",
    "dependency": "related",
}

_EXT_LINK_DATA_2: dict = {
    "id": "2",
    "task_id": "10",
    "url": "https://docs.example.com/spec",
    "title": "Specification",
    "link_type": "weblink",
    "dependency": "blocked",
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
# get_external_task_link_types
# ===========================================================================


def test_get_external_task_link_types_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_types() returns a dict of provider types."""
    httpx_mock.add_response(json=_rpc_ok({"weblink": "Web Link", "attachment": "Attachment"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_types()
    assert result == {"weblink": "Web Link", "attachment": "Attachment"}


def test_get_external_task_link_types_empty(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_types() returns {} when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_types()
    assert result == {}


def test_get_external_task_link_types_none(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_types() returns {} when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_types()
    assert result == {}


def test_get_external_task_link_types_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_types() raises KanboardAPIError on RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.external_task_links.get_external_task_link_types()


# ===========================================================================
# get_external_task_link_provider_dependencies
# ===========================================================================


def test_get_provider_dependencies_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_provider_dependencies() returns a dict."""
    httpx_mock.add_response(
        json=_rpc_ok({"related": "Related", "blocked": "Blocked", "child": "Child"})
    )
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_provider_dependencies("weblink")
    assert result == {"related": "Related", "blocked": "Blocked", "child": "Child"}


def test_get_provider_dependencies_empty(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_provider_dependencies() returns {} on False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_provider_dependencies("unknown")
    assert result == {}


def test_get_provider_dependencies_none(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_provider_dependencies() returns {} on None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_provider_dependencies("unknown")
    assert result == {}


# ===========================================================================
# create_external_task_link
# ===========================================================================


def test_create_external_task_link_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_external_task_link() returns the new link ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.create_external_task_link(
            task_id=10, url="https://example.com", dependency="related"
        )
    assert result == 5
    assert isinstance(result, int)


def test_create_external_task_link_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_external_task_link() passes optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.create_external_task_link(
            task_id=10,
            url="https://example.com",
            dependency="related",
            type="weblink",
            title="My Link",
        )
    assert result == 7


def test_create_external_task_link_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_external_task_link() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create external task link"):
            client.external_task_links.create_external_task_link(
                task_id=10, url="https://example.com", dependency="related"
            )


def test_create_external_task_link_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_external_task_link() raises KanboardAPIError when API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create external task link"):
            client.external_task_links.create_external_task_link(
                task_id=10, url="https://example.com", dependency="related"
            )


def test_create_external_task_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_external_task_link() raises KanboardAPIError on RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid params"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Invalid params"):
            client.external_task_links.create_external_task_link(
                task_id=10, url="https://example.com", dependency="related"
            )


# ===========================================================================
# update_external_task_link
# ===========================================================================


def test_update_external_task_link_returns_true(httpx_mock: HTTPXMock) -> None:
    """update_external_task_link() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.update_external_task_link(
            task_id=10, link_id=1, title="Updated", url="https://new.example.com"
        )
    assert result is True


def test_update_external_task_link_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_external_task_link() passes optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.update_external_task_link(
            task_id=10,
            link_id=1,
            title="Updated",
            url="https://new.example.com",
            dependency="blocked",
        )
    assert result is True


def test_update_external_task_link_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_external_task_link() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update external task link"):
            client.external_task_links.update_external_task_link(
                task_id=10, link_id=1, title="Updated", url="https://new.example.com"
            )


def test_update_external_task_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """update_external_task_link() raises KanboardAPIError on RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Update failed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Update failed"):
            client.external_task_links.update_external_task_link(
                task_id=10, link_id=1, title="Updated", url="https://new.example.com"
            )


# ===========================================================================
# get_external_task_link_by_id
# ===========================================================================


def test_get_external_task_link_by_id_returns_model(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_by_id() returns an ExternalTaskLink model."""
    httpx_mock.add_response(json=_rpc_ok(_EXT_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_external_task_link_by_id(task_id=10, link_id=1)
    assert isinstance(result, ExternalTaskLink)
    assert result.id == 1
    assert result.task_id == 10
    assert result.url == "https://github.com/org/repo/issues/1"
    assert result.title == "GitHub Issue #1"
    assert result.link_type == "weblink"
    assert result.dependency == "related"


def test_get_external_task_link_by_id_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_by_id() raises KanboardNotFoundError on False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.external_task_links.get_external_task_link_by_id(task_id=10, link_id=99)
    err = exc_info.value
    assert err.resource == "ExternalTaskLink"
    assert err.identifier == 99


def test_get_external_task_link_by_id_raises_on_none(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_by_id() raises KanboardNotFoundError on None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.external_task_links.get_external_task_link_by_id(task_id=10, link_id=99)
    err = exc_info.value
    assert err.resource == "ExternalTaskLink"
    assert err.identifier == 99


def test_get_external_task_link_by_id_not_found_message(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_by_id() not-found message includes the link ID."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(
            KanboardNotFoundError,
            match=r"Not found: ExternalTaskLink '99' does not exist",
        ):
            client.external_task_links.get_external_task_link_by_id(task_id=10, link_id=99)


def test_get_external_task_link_by_id_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_by_id() raises KanboardAPIError on RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Not found"):
            client.external_task_links.get_external_task_link_by_id(task_id=10, link_id=99)


# ===========================================================================
# get_all_external_task_links
# ===========================================================================


def test_get_all_external_task_links_returns_list(httpx_mock: HTTPXMock) -> None:
    """get_all_external_task_links() returns a list of ExternalTaskLink models."""
    httpx_mock.add_response(json=_rpc_ok([_EXT_LINK_DATA, _EXT_LINK_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_all_external_task_links(task_id=10)
    assert len(result) == 2
    assert all(isinstance(el, ExternalTaskLink) for el in result)
    assert result[0].id == 1
    assert result[1].id == 2


def test_get_all_external_task_links_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_external_task_links() returns [] when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_all_external_task_links(task_id=10)
    assert result == []


def test_get_all_external_task_links_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_external_task_links() returns [] when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_all_external_task_links(task_id=10)
    assert result == []


def test_get_all_external_task_links_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_external_task_links() returns [] when API returns []."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_all_external_task_links(task_id=10)
    assert result == []


def test_get_all_external_task_links_single_item(httpx_mock: HTTPXMock) -> None:
    """get_all_external_task_links() correctly handles a single-item list."""
    httpx_mock.add_response(json=_rpc_ok([_EXT_LINK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.get_all_external_task_links(task_id=10)
    assert len(result) == 1
    assert result[0].url == "https://github.com/org/repo/issues/1"


# ===========================================================================
# remove_external_task_link
# ===========================================================================


def test_remove_external_task_link_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_external_task_link() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.remove_external_task_link(task_id=10, link_id=1)
    assert result is True


def test_remove_external_task_link_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_external_task_link() returns False when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.external_task_links.remove_external_task_link(task_id=10, link_id=99)
    assert result is False


# ===========================================================================
# Client wiring & import tests
# ===========================================================================


def test_client_has_external_task_links_attribute(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes an external_task_links resource attribute."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert hasattr(client, "external_task_links")
        assert isinstance(client.external_task_links, ExternalTaskLinksResource)


def test_external_task_links_resource_importable() -> None:
    """ExternalTaskLinksResource is importable from the kanboard package."""
    from kanboard import ExternalTaskLinksResource as Imported

    assert Imported is ExternalTaskLinksResource


# ===========================================================================
# Network failure tests
# ===========================================================================


def test_get_external_task_link_types_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_external_task_link_types() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.external_task_links.get_external_task_link_types()


def test_create_external_task_link_network_failure(httpx_mock: HTTPXMock) -> None:
    """create_external_task_link() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.external_task_links.create_external_task_link(
                task_id=10, url="https://example.com", dependency="related"
            )


def test_get_all_external_task_links_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_all_external_task_links() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.external_task_links.get_all_external_task_links(task_id=10)


def test_remove_external_task_link_network_failure(httpx_mock: HTTPXMock) -> None:
    """remove_external_task_link() raises KanboardConnectionError on network failure."""
    import httpx as httpx_lib

    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.external_task_links.remove_external_task_link(task_id=10, link_id=1)
