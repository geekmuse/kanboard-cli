"""Unit tests for LinksResource — all 7 link-type API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Link
from kanboard.resources.links import LinksResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LINK_DATA: dict = {
    "id": "1",
    "label": "blocks",
    "opposite_id": "2",
}

_LINK_DATA_2: dict = {
    "id": "2",
    "label": "is blocked by",
    "opposite_id": "1",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


# ---------------------------------------------------------------------------
# get_all_links
# ---------------------------------------------------------------------------


def test_get_all_links_returns_list_of_link_models(httpx_mock: HTTPXMock) -> None:
    """get_all_links() returns a list of Link instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_LINK_DATA, _LINK_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_all_links()
    assert len(result) == 2
    assert all(isinstance(link, Link) for link in result)


def test_get_all_links_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_all_links() maps API fields correctly for each Link."""
    httpx_mock.add_response(json=_rpc_ok([_LINK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_all_links()
    link = result[0]
    assert link.id == 1
    assert link.label == "blocks"
    assert link.opposite_id == 2


def test_get_all_links_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_links() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_all_links()
    assert result == []


def test_get_all_links_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_links() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_all_links()
    assert result == []


def test_get_all_links_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_links() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_all_links()
    assert result == []


def test_get_all_links_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_all_links() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.get_all_links()


# ---------------------------------------------------------------------------
# get_opposite_link_id
# ---------------------------------------------------------------------------


def test_get_opposite_link_id_returns_int(httpx_mock: HTTPXMock) -> None:
    """get_opposite_link_id() returns the opposite link ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(2))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_opposite_link_id(link_id=1)
    assert result == 2
    assert isinstance(result, int)


def test_get_opposite_link_id_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """get_opposite_link_id() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to get opposite link ID"):
            client.links.get_opposite_link_id(link_id=999)


def test_get_opposite_link_id_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """get_opposite_link_id() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to get opposite link ID"):
            client.links.get_opposite_link_id(link_id=999)


def test_get_opposite_link_id_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_opposite_link_id() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.get_opposite_link_id(link_id=1)


# ---------------------------------------------------------------------------
# get_link_by_label
# ---------------------------------------------------------------------------


def test_get_link_by_label_returns_link_model(httpx_mock: HTTPXMock) -> None:
    """get_link_by_label() returns a Link instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_link_by_label(label="blocks")
    assert isinstance(result, Link)


def test_get_link_by_label_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_link_by_label() maps all API fields to the Link dataclass correctly."""
    httpx_mock.add_response(json=_rpc_ok(_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_link_by_label(label="blocks")
    assert result.id == 1
    assert result.label == "blocks"
    assert result.opposite_id == 2


def test_get_link_by_label_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_link_by_label() raises KanboardNotFoundError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Link"):
            client.links.get_link_by_label(label="nonexistent")


def test_get_link_by_label_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_link_by_label() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Link"):
            client.links.get_link_by_label(label="nonexistent")


def test_get_link_by_label_not_found_error_attributes(httpx_mock: HTTPXMock) -> None:
    """get_link_by_label() KanboardNotFoundError carries correct resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.links.get_link_by_label(label="nonexistent")
    err = exc_info.value
    assert err.resource == "Link"
    assert err.identifier == "nonexistent"


def test_get_link_by_label_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_link_by_label() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.get_link_by_label(label="blocks")


# ---------------------------------------------------------------------------
# get_link_by_id
# ---------------------------------------------------------------------------


def test_get_link_by_id_returns_link_model(httpx_mock: HTTPXMock) -> None:
    """get_link_by_id() returns a Link instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_link_by_id(link_id=1)
    assert isinstance(result, Link)


def test_get_link_by_id_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_link_by_id() maps all API fields to the Link dataclass correctly."""
    httpx_mock.add_response(json=_rpc_ok(_LINK_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.get_link_by_id(link_id=1)
    assert result.id == 1
    assert result.label == "blocks"
    assert result.opposite_id == 2


def test_get_link_by_id_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_link_by_id() raises KanboardNotFoundError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Link"):
            client.links.get_link_by_id(link_id=999)


def test_get_link_by_id_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_link_by_id() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError, match="Link"):
            client.links.get_link_by_id(link_id=999)


def test_get_link_by_id_not_found_error_attributes(httpx_mock: HTTPXMock) -> None:
    """get_link_by_id() KanboardNotFoundError carries correct resource and identifier."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.links.get_link_by_id(link_id=999)
    err = exc_info.value
    assert err.resource == "Link"
    assert err.identifier == 999


def test_get_link_by_id_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """get_link_by_id() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.get_link_by_id(link_id=1)


# ---------------------------------------------------------------------------
# create_link
# ---------------------------------------------------------------------------


def test_create_link_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_link() returns the new link type ID as an int."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.create_link(label="depends on")
    assert result == 5
    assert isinstance(result, int)


def test_create_link_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_link() forwards optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok(6))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.create_link(label="depends on", opposite_label="is a dependency of")
    assert result == 6


def test_create_link_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_link() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create link"):
            client.links.create_link(label="depends on")


def test_create_link_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_link() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create link"):
            client.links.create_link(label="depends on")


def test_create_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_link() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.create_link(label="depends on")


# ---------------------------------------------------------------------------
# update_link
# ---------------------------------------------------------------------------


def test_update_link_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_link() returns True when the API succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.update_link(link_id=1, opposite_link_id=2, label="blocks")
    assert result is True


def test_update_link_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_link() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update link"):
            client.links.update_link(link_id=99, opposite_link_id=100, label="blocks")


def test_update_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """update_link() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.update_link(link_id=1, opposite_link_id=2, label="blocks")


# ---------------------------------------------------------------------------
# remove_link
# ---------------------------------------------------------------------------


def test_remove_link_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_link() returns True when the API confirms removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.remove_link(link_id=1)
    assert result is True


def test_remove_link_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """remove_link() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.links.remove_link(link_id=999)
    assert result is False


def test_remove_link_raises_on_rpc_error(httpx_mock: HTTPXMock) -> None:
    """remove_link() raises KanboardAPIError on an RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32600, "Invalid request"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.links.remove_link(link_id=1)


# ---------------------------------------------------------------------------
# Resource wiring and importability
# ---------------------------------------------------------------------------


def test_links_resource_is_wired_on_client() -> None:
    """KanboardClient exposes .links as a LinksResource instance."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.links, LinksResource)


def test_links_resource_importable_from_kanboard() -> None:
    """LinksResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "LinksResource")
    assert kanboard.LinksResource is LinksResource
