"""Unit tests for CategoriesResource — all 5 category API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Category
from kanboard.resources.categories import CategoriesResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATEGORY_DATA: dict = {
    "id": "5",
    "name": "Bug",
    "project_id": "1",
    "color_id": "red",
}

_CATEGORY_DATA_2: dict = {
    "id": "6",
    "name": "Feature",
    "project_id": "1",
    "color_id": "blue",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_category
# ---------------------------------------------------------------------------


def test_create_category_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_category() returns the integer ID of the new category."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.create_category(project_id=1, name="Bug")
    assert result == 5
    assert isinstance(result, int)


def test_create_category_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_category() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create category"):
            client.categories.create_category(project_id=1, name="Bug")


def test_create_category_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_category() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.categories.create_category(project_id=1, name="Bug")


def test_create_category_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """create_category() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.categories.create_category(project_id=1, name="Bug")


def test_create_category_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_category() accepts and forwards extra keyword arguments to the API."""
    httpx_mock.add_response(json=_rpc_ok(7))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.create_category(project_id=1, name="Feature", color_id="blue")
    assert result == 7


# ---------------------------------------------------------------------------
# get_category
# ---------------------------------------------------------------------------


def test_get_category_returns_category_model(httpx_mock: HTTPXMock) -> None:
    """get_category() returns a Category instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_CATEGORY_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.get_category(5)
    assert isinstance(result, Category)


def test_get_category_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_category() maps API fields to Category dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok(_CATEGORY_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        cat = client.categories.get_category(5)
    assert cat.id == 5
    assert cat.name == "Bug"
    assert cat.project_id == 1
    assert cat.color_id == "red"


def test_get_category_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_category() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.categories.get_category(999)
    err = exc_info.value
    assert err.resource == "Category"
    assert err.identifier == 999


def test_get_category_not_found_message(httpx_mock: HTTPXMock) -> None:
    """get_category() not-found message includes the category ID."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(
            KanboardNotFoundError,
            match=r"Not found: Category '999' does not exist",
        ):
            client.categories.get_category(999)


def test_get_category_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_category() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.categories.get_category(5)


# ---------------------------------------------------------------------------
# get_all_categories
# ---------------------------------------------------------------------------


def test_get_all_categories_returns_list_of_category_models(httpx_mock: HTTPXMock) -> None:
    """get_all_categories() returns a list of Category instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_CATEGORY_DATA, _CATEGORY_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.get_all_categories(1)
    assert len(result) == 2
    assert all(isinstance(cat, Category) for cat in result)


def test_get_all_categories_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_all_categories() maps fields for the first category correctly."""
    httpx_mock.add_response(json=_rpc_ok([_CATEGORY_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.get_all_categories(1)
    cat = result[0]
    assert cat.id == 5
    assert cat.name == "Bug"
    assert cat.color_id == "red"


def test_get_all_categories_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_categories() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.get_all_categories(1)
    assert result == []


def test_get_all_categories_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_categories() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.get_all_categories(1)
    assert result == []


def test_get_all_categories_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_categories() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.get_all_categories(1)
    assert result == []


def test_get_all_categories_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_categories() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.categories.get_all_categories(1)


# ---------------------------------------------------------------------------
# update_category
# ---------------------------------------------------------------------------


def test_update_category_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_category() returns True when the API returns a truthy value."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.update_category(id=5, name="Defect")
    assert result is True


def test_update_category_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_category() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update category 5"):
            client.categories.update_category(id=5, name="Defect")


def test_update_category_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_category() accepts and forwards extra keyword arguments to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.update_category(id=5, name="Defect", color_id="green")
    assert result is True


def test_update_category_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_category() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Update failed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Update failed"):
            client.categories.update_category(id=5, name="Defect")


# ---------------------------------------------------------------------------
# remove_category
# ---------------------------------------------------------------------------


def test_remove_category_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_category() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.remove_category(5)
    assert result is True


def test_remove_category_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_category() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.categories.remove_category(999)
    assert result is False


def test_remove_category_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_category() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.categories.remove_category(5)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_categories_resource_wired_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes a CategoriesResource instance as .categories."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.categories, CategoriesResource)


def test_categories_resource_importable_from_kanboard() -> None:
    """CategoriesResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "CategoriesResource")
    assert kanboard.CategoriesResource is CategoriesResource
