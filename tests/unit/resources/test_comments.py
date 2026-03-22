"""Unit tests for CommentsResource — all 5 comment API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Comment
from kanboard.resources.comments import CommentsResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMENT_DATA: dict = {
    "id": "10",
    "task_id": "42",
    "user_id": "3",
    "username": "alice",
    "name": "Alice",
    "comment": "This looks good!",
    "date_creation": "1711078800",
    "date_modification": "1711082400",
}

_COMMENT_DATA_2: dict = {
    "id": "11",
    "task_id": "42",
    "user_id": "5",
    "username": "bob",
    "name": "Bob",
    "comment": "Agreed.",
    "date_creation": "1711083000",
    "date_modification": "1711083000",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_comment
# ---------------------------------------------------------------------------


def test_create_comment_returns_int_id(httpx_mock: HTTPXMock) -> None:
    """create_comment() returns the integer ID of the new comment."""
    httpx_mock.add_response(json=_rpc_ok(10))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.create_comment(task_id=42, user_id=3, content="Hello!")
    assert result == 10
    assert isinstance(result, int)


def test_create_comment_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_comment() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to create comment"):
            client.comments.create_comment(task_id=42, user_id=3, content="Hello!")


def test_create_comment_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_comment() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError):
            client.comments.create_comment(task_id=42, user_id=3, content="Hello!")


def test_create_comment_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """create_comment() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.comments.create_comment(task_id=42, user_id=3, content="Hello!")


def test_create_comment_forwards_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_comment() accepts and forwards extra keyword arguments to the API."""
    httpx_mock.add_response(json=_rpc_ok(15))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.create_comment(
            task_id=42, user_id=3, content="With extra", reference="ref-123"
        )
    assert result == 15


# ---------------------------------------------------------------------------
# get_comment
# ---------------------------------------------------------------------------


def test_get_comment_returns_comment_model(httpx_mock: HTTPXMock) -> None:
    """get_comment() returns a Comment instance on success."""
    httpx_mock.add_response(json=_rpc_ok(_COMMENT_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.get_comment(10)
    assert isinstance(result, Comment)


def test_get_comment_fields_mapped_correctly(httpx_mock: HTTPXMock) -> None:
    """get_comment() maps API fields to Comment dataclass attributes."""
    httpx_mock.add_response(json=_rpc_ok(_COMMENT_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        c = client.comments.get_comment(10)
    assert c.id == 10
    assert c.task_id == 42
    assert c.user_id == 3
    assert c.username == "alice"
    assert c.name == "Alice"
    assert c.comment == "This looks good!"


def test_get_comment_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_comment() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.comments.get_comment(999)
    err = exc_info.value
    assert err.resource == "Comment"
    assert err.identifier == 999


def test_get_comment_not_found_message(httpx_mock: HTTPXMock) -> None:
    """get_comment() not-found message includes the comment ID."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(
            KanboardNotFoundError,
            match=r"Not found: Comment '999' does not exist",
        ):
            client.comments.get_comment(999)


def test_get_comment_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_comment() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Access denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Access denied"):
            client.comments.get_comment(10)


# ---------------------------------------------------------------------------
# get_all_comments
# ---------------------------------------------------------------------------


def test_get_all_comments_returns_list_of_comment_models(httpx_mock: HTTPXMock) -> None:
    """get_all_comments() returns a list of Comment instances on success."""
    httpx_mock.add_response(json=_rpc_ok([_COMMENT_DATA, _COMMENT_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.get_all_comments(42)
    assert len(result) == 2
    assert all(isinstance(c, Comment) for c in result)


def test_get_all_comments_fields_mapped(httpx_mock: HTTPXMock) -> None:
    """get_all_comments() maps fields for the first comment correctly."""
    httpx_mock.add_response(json=_rpc_ok([_COMMENT_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.get_all_comments(42)
    c = result[0]
    assert c.id == 10
    assert c.username == "alice"
    assert c.comment == "This looks good!"


def test_get_all_comments_returns_empty_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_comments() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.get_all_comments(42)
    assert result == []


def test_get_all_comments_returns_empty_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_comments() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.get_all_comments(42)
    assert result == []


def test_get_all_comments_returns_empty_on_empty_list(httpx_mock: HTTPXMock) -> None:
    """get_all_comments() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.get_all_comments(42)
    assert result == []


def test_get_all_comments_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_all_comments() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.comments.get_all_comments(42)


# ---------------------------------------------------------------------------
# update_comment
# ---------------------------------------------------------------------------


def test_update_comment_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_comment() returns True when the API returns a truthy value."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.update_comment(id=10, content="Updated text")
    assert result is True


def test_update_comment_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_comment() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to update comment 10"):
            client.comments.update_comment(id=10, content="Updated text")


def test_update_comment_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_comment() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Update failed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Update failed"):
            client.comments.update_comment(id=10, content="Any text")


# ---------------------------------------------------------------------------
# remove_comment
# ---------------------------------------------------------------------------


def test_remove_comment_returns_true(httpx_mock: HTTPXMock) -> None:
    """remove_comment() returns True when the API returns True."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.remove_comment(10)
    assert result is True


def test_remove_comment_returns_false(httpx_mock: HTTPXMock) -> None:
    """remove_comment() returns False when the API returns False (no raise)."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.comments.remove_comment(999)
    assert result is False


def test_remove_comment_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_comment() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32000, "Cannot delete"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Cannot delete"):
            client.comments.remove_comment(10)


# ---------------------------------------------------------------------------
# Client wiring / importability
# ---------------------------------------------------------------------------


def test_comments_resource_wired_on_client(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes a CommentsResource instance as .comments."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.comments, CommentsResource)


def test_comments_resource_importable_from_kanboard() -> None:
    """CommentsResource is importable directly from the kanboard package."""
    import kanboard

    assert hasattr(kanboard, "CommentsResource")
    assert kanboard.CommentsResource is CommentsResource
