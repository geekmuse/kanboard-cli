"""Unit tests for TagsResource — all 7 tag API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError
from kanboard.models import Tag
from kanboard.resources.tags import TagsResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TAG_DATA: dict = {
    "id": "3",
    "name": "urgent",
    "project_id": "1",
    "color_id": "red",
}

_TAG_DATA_2: dict = {
    "id": "4",
    "name": "backend",
    "project_id": "1",
    "color_id": "blue",
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
# get_all_tags
# ---------------------------------------------------------------------------


def test_get_all_tags_returns_list_of_tag_models(httpx_mock: HTTPXMock) -> None:
    """get_all_tags() returns a list of Tag instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_TAG_DATA, _TAG_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_all_tags()
    assert len(result) == 2
    assert all(isinstance(t, Tag) for t in result)


def test_get_all_tags_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_all_tags() maps API fields to Tag dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok([_TAG_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_all_tags()
    tag = result[0]
    assert tag.id == 3
    assert tag.name == "urgent"
    assert tag.project_id == 1
    assert tag.color_id == "red"


def test_get_all_tags_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_tags() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_all_tags()
    assert result == []


def test_get_all_tags_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_tags() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_all_tags()
    assert result == []


def test_get_all_tags_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_tags() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_all_tags()
    assert result == []


def test_get_all_tags_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_tags() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.tags.get_all_tags()


# ---------------------------------------------------------------------------
# get_tags_by_project
# ---------------------------------------------------------------------------


def test_get_tags_by_project_returns_list_of_tag_models(httpx_mock: HTTPXMock) -> None:
    """get_tags_by_project() returns a list of Tag instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_TAG_DATA, _TAG_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_tags_by_project(1)
    assert len(result) == 2
    assert all(isinstance(t, Tag) for t in result)


def test_get_tags_by_project_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_tags_by_project() maps fields for the first tag correctly."""
    httpx_mock.add_response(json=_rpc_ok([_TAG_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_tags_by_project(1)
    tag = result[0]
    assert tag.id == 3
    assert tag.name == "urgent"
    assert tag.project_id == 1
    assert tag.color_id == "red"


def test_get_tags_by_project_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_tags_by_project() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_tags_by_project(1)
    assert result == []


def test_get_tags_by_project_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_tags_by_project() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_tags_by_project(1)
    assert result == []


def test_get_tags_by_project_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_tags_by_project() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_tags_by_project(1)
    assert result == []


def test_get_tags_by_project_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_tags_by_project() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.tags.get_tags_by_project(1)


# ---------------------------------------------------------------------------
# create_tag
# ---------------------------------------------------------------------------


def test_create_tag_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_tag() returns the integer ID of the new tag."""
    httpx_mock.add_response(json=_rpc_ok(3))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.create_tag(project_id=1, tag="urgent")
    assert result == 3
    assert isinstance(result, int)


def test_create_tag_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_tag() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create tag"):
            client.tags.create_tag(project_id=1, tag="urgent")


def test_create_tag_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_tag() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.tags.create_tag(project_id=1, tag="urgent")


def test_create_tag_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """create_tag() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.tags.create_tag(project_id=1, tag="urgent")


def test_create_tag_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_tag() accepts and forwards extra keyword arguments to the API."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.create_tag(project_id=1, tag="backend", color_id="blue")
    assert result == 5


# ---------------------------------------------------------------------------
# update_tag
# ---------------------------------------------------------------------------


def test_update_tag_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_tag() returns True when the API returns a truthy value."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.update_tag(tag_id=3, tag="critical")
    assert result is True


def test_update_tag_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_tag() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update tag 3"):
            client.tags.update_tag(tag_id=3, tag="critical")


def test_update_tag_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """update_tag() accepts and forwards extra keyword arguments to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.update_tag(tag_id=3, tag="critical", color_id="orange")
    assert result is True


def test_update_tag_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_tag() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Update failed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Update failed"):
            client.tags.update_tag(tag_id=3, tag="critical")


# ---------------------------------------------------------------------------
# remove_tag
# ---------------------------------------------------------------------------


def test_remove_tag_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_tag() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.remove_tag(3)
    assert result is True


def test_remove_tag_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_tag() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.remove_tag(999)
    assert result is False


def test_remove_tag_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_tag() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.tags.remove_tag(3)


# ---------------------------------------------------------------------------
# set_task_tags
# ---------------------------------------------------------------------------


def test_set_task_tags_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """set_task_tags() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.set_task_tags(project_id=1, task_id=10, tags=["urgent", "backend"])
    assert result is True


def test_set_task_tags_returns_false_on_false(httpx_mock: HTTPXMock) -> None:
    """set_task_tags() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.set_task_tags(project_id=1, task_id=10, tags=[])
    assert result is False


def test_set_task_tags_accepts_empty_list(httpx_mock: HTTPXMock) -> None:
    """set_task_tags() accepts an empty tag list (clears task tags)."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.set_task_tags(project_id=1, task_id=10, tags=[])
    assert isinstance(result, bool)


def test_set_task_tags_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """set_task_tags() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Task not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Task not found"):
            client.tags.set_task_tags(project_id=1, task_id=10, tags=["urgent"])


# ---------------------------------------------------------------------------
# get_task_tags
# ---------------------------------------------------------------------------


def test_get_task_tags_returns_dict_on_success(httpx_mock: HTTPXMock) -> None:
    """get_task_tags() returns a dict mapping tag IDs to tag names."""
    httpx_mock.add_response(json=_rpc_ok({"3": "urgent", "4": "backend"}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_task_tags(10)
    assert isinstance(result, dict)
    assert result == {"3": "urgent", "4": "backend"}


def test_get_task_tags_returns_empty_dict_on_false(httpx_mock: HTTPXMock) -> None:
    """get_task_tags() returns {} when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_task_tags(10)
    assert result == {}


def test_get_task_tags_returns_empty_dict_on_none(httpx_mock: HTTPXMock) -> None:
    """get_task_tags() returns {} when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_task_tags(10)
    assert result == {}


def test_get_task_tags_returns_empty_dict_on_empty_dict(httpx_mock: HTTPXMock) -> None:
    """get_task_tags() returns {} when the API returns an empty dict."""
    httpx_mock.add_response(json=_rpc_ok({}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.tags.get_task_tags(10)
    assert result == {}


def test_get_task_tags_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_task_tags() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.tags.get_task_tags(10)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_tags_resource_wired_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes a TagsResource instance as .tags."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.tags, TagsResource)


def test_tags_resource_importable_from_kanboard() -> None:
    """TagsResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "TagsResource")
    assert kanboard.TagsResource is TagsResource
