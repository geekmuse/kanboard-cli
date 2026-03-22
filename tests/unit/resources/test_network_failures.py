"""Network-failure tests for all Milestone 2 SDK resource modules.

Each test confirms that a KanboardConnectionError propagates correctly
when a transport-level error occurs while calling a representative method
on each M2 resource.  Error-handling at the transport layer is already
unit-tested in tests/unit/test_client.py; these tests exist to provide
explicit resource-level evidence that the error path is reachable and
correctly propagates for every resource.
"""

from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardConnectionError

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# BoardResource
# ---------------------------------------------------------------------------


def test_board_get_board_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """BoardResource.get_board() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.board.get_board(1)


# ---------------------------------------------------------------------------
# ColumnsResource
# ---------------------------------------------------------------------------


def test_columns_get_columns_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """ColumnsResource.get_columns() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.columns.get_columns(1)


def test_columns_get_column_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """ColumnsResource.get_column() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.columns.get_column(3)


# ---------------------------------------------------------------------------
# SwimlanesResource
# ---------------------------------------------------------------------------


def test_swimlanes_get_active_swimlanes_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """SwimlanesResource.get_active_swimlanes() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.swimlanes.get_active_swimlanes(1)


def test_swimlanes_get_swimlane_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """SwimlanesResource.get_swimlane() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.swimlanes.get_swimlane(1)


# ---------------------------------------------------------------------------
# CommentsResource
# ---------------------------------------------------------------------------


def test_comments_get_all_comments_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """CommentsResource.get_all_comments() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.comments.get_all_comments(10)


def test_comments_get_comment_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """CommentsResource.get_comment() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.comments.get_comment(5)


# ---------------------------------------------------------------------------
# CategoriesResource
# ---------------------------------------------------------------------------


def test_categories_get_all_categories_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """CategoriesResource.get_all_categories() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.categories.get_all_categories(1)


def test_categories_get_category_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """CategoriesResource.get_category() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.categories.get_category(7)


# ---------------------------------------------------------------------------
# TagsResource
# ---------------------------------------------------------------------------


def test_tags_get_all_tags_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """TagsResource.get_all_tags() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.tags.get_all_tags()


def test_tags_get_tags_by_project_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """TagsResource.get_tags_by_project() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.tags.get_tags_by_project(2)


# ---------------------------------------------------------------------------
# SubtasksResource
# ---------------------------------------------------------------------------


def test_subtasks_get_all_subtasks_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """SubtasksResource.get_all_subtasks() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.subtasks.get_all_subtasks(10)


def test_subtasks_get_subtask_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """SubtasksResource.get_subtask() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.subtasks.get_subtask(3)


# ---------------------------------------------------------------------------
# UsersResource
# ---------------------------------------------------------------------------


def test_users_get_all_users_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """UsersResource.get_all_users() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.users.get_all_users()


def test_users_get_user_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """UsersResource.get_user() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.users.get_user(1)


def test_users_create_user_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """UsersResource.create_user() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ConnectTimeout("Connect timeout"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.users.create_user("alice", "s3cr3t")


# ---------------------------------------------------------------------------
# LinksResource
# ---------------------------------------------------------------------------


def test_links_get_all_links_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """LinksResource.get_all_links() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.links.get_all_links()


def test_links_get_link_by_id_raises_on_network_failure(httpx_mock: HTTPXMock) -> None:
    """LinksResource.get_link_by_id() propagates KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.links.get_link_by_id(1)


# ---------------------------------------------------------------------------
# TaskLinksResource
# ---------------------------------------------------------------------------


def test_task_links_get_all_task_links_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """TaskLinksResource.get_all_task_links() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_links.get_all_task_links(10)


def test_task_links_get_task_link_by_id_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """TaskLinksResource.get_task_link_by_id() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ReadTimeout("Timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_links.get_task_link_by_id(5)


def test_task_links_create_task_link_raises_on_network_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """TaskLinksResource.create_task_link() propagates KanboardConnectionError."""
    httpx_mock.add_exception(httpx.ConnectTimeout("Connect timeout"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.task_links.create_task_link(1, 2, 1)
