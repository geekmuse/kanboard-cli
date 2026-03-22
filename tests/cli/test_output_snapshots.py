"""Snapshot-style CLI output tests — systematic cross-cutting format coverage (US-005).

Tests all four output formats (table, json, csv, quiet) for the major command
groups, plus error handling, empty results, and edge cases.

Focus: FORMAT CORRECTNESS across the codebase, not per-command business logic.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import (
    KanboardAPIError,
    KanboardAuthError,
    KanboardNotFoundError,
)
from kanboard.models import (
    Category,
    Column,
    Comment,
    Group,
    Link,
    Project,
    Subtask,
    Swimlane,
    Tag,
    Task,
    TaskLink,
    User,
)
from kanboard_cli.main import cli

# ===========================================================================
# Shared fixtures and helpers
# ===========================================================================


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def mock_config() -> KanboardConfig:
    """Return a minimal resolved config (table output default)."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock SDK client."""
    return MagicMock()


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
) -> Any:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args)


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------


def _project() -> Project:
    """Build a sample Project."""
    return Project.from_api(
        {
            "id": "1",
            "name": "Alpha Project",
            "description": "First project",
            "is_active": "1",
            "token": "abc123xyz",
            "last_modified": "1711000000",
            "is_public": "0",
            "is_private": False,
            "owner_id": "2",
            "identifier": "ALPHA",
            "start_date": None,
            "end_date": None,
            "url": "http://kanboard.test/board/1",
        }
    )


def _task() -> Task:
    """Build a sample Task."""
    return Task.from_api(
        {
            "id": "10",
            "title": "Implement login",
            "description": "Add SSO",
            "date_creation": "1711000000",
            "date_modification": "1711100000",
            "date_due": None,
            "date_completed": None,
            "date_moved": None,
            "color_id": "blue",
            "project_id": "1",
            "column_id": "2",
            "swimlane_id": "0",
            "owner_id": "3",
            "creator_id": "1",
            "category_id": "0",
            "is_active": "1",
            "priority": "1",
            "score": "3",
            "position": "2",
            "reference": "IMPL-001",
            "tags": ["auth"],
            "url": "http://kanboard.test/task/10",
        }
    )


def _column() -> Column:
    """Build a sample Column."""
    return Column.from_api(
        {
            "id": "3",
            "title": "In Progress",
            "project_id": "1",
            "task_limit": "5",
            "position": "2",
            "description": "Active work",
            "hide_in_dashboard": "0",
        }
    )


def _swimlane() -> Swimlane:
    """Build a sample Swimlane."""
    return Swimlane.from_api(
        {
            "id": "2",
            "name": "Backend",
            "project_id": "1",
            "position": "1",
            "is_active": "1",
            "description": "Server-side work",
        }
    )


def _comment() -> Comment:
    """Build a sample Comment."""
    return Comment.from_api(
        {
            "id": "7",
            "task_id": "10",
            "user_id": "1",
            "username": "alice",
            "name": "Alice Smith",
            "comment": "LGTM!",
            "date_creation": None,
            "date_modification": None,
        }
    )


def _user() -> User:
    """Build a sample User."""
    return User.from_api(
        {
            "id": "5",
            "username": "bob",
            "name": "Bob Jones",
            "email": "bob@example.com",
            "role": "app-user",
            "is_active": "1",
            "is_ldap_user": "0",
            "notification_method": "0",
            "avatar_path": None,
            "timezone": None,
            "language": None,
        }
    )


def _category() -> Category:
    """Build a sample Category."""
    return Category.from_api(
        {
            "id": "4",
            "name": "Feature",
            "project_id": "1",
            "color_id": "green",
        }
    )


def _subtask() -> Subtask:
    """Build a sample Subtask."""
    return Subtask.from_api(
        {
            "id": "9",
            "title": "Write unit tests",
            "task_id": "10",
            "user_id": "3",
            "status": "0",
            "time_estimated": "2.5",
            "time_spent": "0.5",
            "position": "1",
            "username": "carol",
            "name": "Carol White",
        }
    )


def _tag() -> Tag:
    """Build a sample Tag."""
    return Tag.from_api(
        {
            "id": "6",
            "name": "urgent",
            "project_id": "1",
            "color_id": "red",
        }
    )


def _group() -> Group:
    """Build a sample Group."""
    return Group.from_api(
        {
            "id": "2",
            "name": "Developers",
            "external_id": "dev-team",
        }
    )


def _link() -> Link:
    """Build a sample Link."""
    return Link.from_api(
        {
            "id": "1",
            "label": "blocks",
            "opposite_id": "2",
        }
    )


def _task_link() -> TaskLink:
    """Build a sample TaskLink."""
    return TaskLink.from_api(
        {
            "id": "11",
            "task_id": "10",
            "opposite_task_id": "20",
            "link_id": "1",
        }
    )


# ===========================================================================
# Section 1: Systematic format coverage — all 4 formats per major group
# ===========================================================================


# ---------------------------------------------------------------------------
# Project list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_project_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``project list`` exits 0 for all 4 output formats."""
    mock_client.projects.get_all_projects.return_value = [_project()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "project", "list"])
    assert result.exit_code == 0, result.output


def test_project_list_table_has_headers(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Table format shows column headers."""
    mock_client.projects.get_all_projects.return_value = [_project()]
    result = _invoke(runner, mock_config, mock_client, ["project", "list"])
    assert "id" in result.output
    assert "name" in result.output


def test_project_list_json_is_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON list output is a JSON array with correct data."""
    mock_client.projects.get_all_projects.return_value = [_project()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "project", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Alpha Project"
    assert data[0]["id"] == 1


def test_project_list_csv_has_header_and_values(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """CSV list output has header row and data row."""
    mock_client.projects.get_all_projects.return_value = [_project()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "project", "list"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert len(lines) >= 2  # header + at least one data row
    assert "name" in lines[0]  # header
    assert "Alpha Project" in result.output


def test_project_list_quiet_ids_only(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet list output contains only IDs, one per line."""
    p2 = Project.from_api({**_project().__dict__, "id": 2, "name": "Beta"})
    mock_client.projects.get_all_projects.return_value = [_project(), p2]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "project", "list"])
    assert result.exit_code == 0
    lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
    assert "1" in lines
    assert "2" in lines
    # Should NOT contain full project names
    assert "Alpha Project" not in result.output
    assert "Beta" not in result.output


def test_project_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON get output is a single JSON object, not an array."""
    mock_client.projects.get_project_by_id.return_value = _project()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "project", "get", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["name"] == "Alpha Project"


# ---------------------------------------------------------------------------
# Task list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_task_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``task list`` exits 0 for all 4 output formats."""
    mock_client.tasks.get_all_tasks.return_value = [_task()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "task", "list", "1"])
    assert result.exit_code == 0, result.output


def test_task_list_json_array_structure(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON task list is a valid array with correct fields."""
    mock_client.tasks.get_all_tasks.return_value = [_task()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "list", "1"])
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Implement login"
    assert data[0]["id"] == 10


def test_task_list_csv_header_and_value(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """CSV task list has header + data rows."""
    mock_client.tasks.get_all_tasks.return_value = [_task()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "task", "list", "1"])
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "title" in lines[0]
    assert "Implement login" in result.output


def test_task_list_quiet_only_ids(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet task list prints only IDs."""
    t2_data = {
        **{
            "id": "20",
            "title": "Write docs",
            "description": "",
            "date_creation": None,
            "date_modification": None,
            "date_due": None,
            "date_completed": None,
            "date_moved": None,
            "color_id": "green",
            "project_id": "1",
            "column_id": "1",
            "swimlane_id": "0",
            "owner_id": "0",
            "creator_id": "1",
            "category_id": "0",
            "is_active": "1",
            "priority": "0",
            "score": "0",
            "position": "1",
            "reference": "",
            "tags": [],
            "url": "",
        }
    }
    mock_client.tasks.get_all_tasks.return_value = [_task(), Task.from_api(t2_data)]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "task", "list", "1"])
    lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
    assert "10" in lines
    assert "20" in lines
    assert "Implement login" not in result.output


def test_task_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON task get is a single object."""
    mock_client.tasks.get_task.return_value = _task()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "get", "10"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["title"] == "Implement login"


# ---------------------------------------------------------------------------
# Column list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_column_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``column list`` exits 0 for all 4 output formats."""
    mock_client.columns.get_columns.return_value = [_column()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "column", "list", "1"])
    assert result.exit_code == 0, result.output


def test_column_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON column list is an array."""
    mock_client.columns.get_columns.return_value = [_column()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "column", "list", "1"])
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "In Progress"


def test_column_list_quiet_ids(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet column list prints only IDs."""
    mock_client.columns.get_columns.return_value = [_column()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "column", "list", "1"])
    lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
    assert "3" in lines
    assert "In Progress" not in result.output


def test_column_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON column get is a single object."""
    mock_client.columns.get_column.return_value = _column()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "column", "get", "3"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["title"] == "In Progress"


# ---------------------------------------------------------------------------
# Swimlane list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_swimlane_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``swimlane list`` exits 0 for all 4 output formats."""
    # Default list uses get_active_swimlanes (no --all flag)
    mock_client.swimlanes.get_active_swimlanes.return_value = [_swimlane()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "swimlane", "list", "1"])
    assert result.exit_code == 0, result.output


def test_swimlane_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON swimlane list is an array with name field."""
    mock_client.swimlanes.get_active_swimlanes.return_value = [_swimlane()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "swimlane", "list", "1"]
    )
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Backend"


def test_swimlane_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON swimlane get is a single object."""
    mock_client.swimlanes.get_swimlane.return_value = _swimlane()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "swimlane", "get", "2"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["name"] == "Backend"


# ---------------------------------------------------------------------------
# Comment list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_comment_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``comment list`` exits 0 for all 4 output formats."""
    mock_client.comments.get_all_comments.return_value = [_comment()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "comment", "list", "10"])
    assert result.exit_code == 0, result.output


def test_comment_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON comment list is an array with comment field."""
    mock_client.comments.get_all_comments.return_value = [_comment()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "comment", "list", "10"]
    )
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["comment"] == "LGTM!"
    assert data[0]["id"] == 7


def test_comment_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON comment get is a single object."""
    mock_client.comments.get_comment.return_value = _comment()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "comment", "get", "7"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["username"] == "alice"


def test_comment_list_quiet_ids(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet comment list prints only IDs."""
    mock_client.comments.get_all_comments.return_value = [_comment()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "comment", "list", "10"]
    )
    lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
    assert "7" in lines
    assert "LGTM!" not in result.output


# ---------------------------------------------------------------------------
# User list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_user_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``user list`` exits 0 for all 4 output formats."""
    mock_client.users.get_all_users.return_value = [_user()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "user", "list"])
    assert result.exit_code == 0, result.output


def test_user_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON user list is an array with username field."""
    mock_client.users.get_all_users.return_value = [_user()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "user", "list"])
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["username"] == "bob"
    assert data[0]["id"] == 5


def test_user_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON user get is a single object."""
    mock_client.users.get_user.return_value = _user()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "user", "get", "5"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["email"] == "bob@example.com"


def test_user_list_csv_header(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """CSV user list has header row with expected fields."""
    mock_client.users.get_all_users.return_value = [_user()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "user", "list"])
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "id" in lines[0]
    assert "bob" in result.output


# ---------------------------------------------------------------------------
# Category list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_category_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``category list`` exits 0 for all 4 output formats."""
    mock_client.categories.get_all_categories.return_value = [_category()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "category", "list", "1"])
    assert result.exit_code == 0, result.output


def test_category_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON category list is an array with name field."""
    mock_client.categories.get_all_categories.return_value = [_category()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "category", "list", "1"]
    )
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Feature"


def test_category_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON category get is a single object."""
    mock_client.categories.get_category.return_value = _category()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "category", "get", "4"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["name"] == "Feature"


# ---------------------------------------------------------------------------
# Subtask list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_subtask_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``subtask list`` exits 0 for all 4 output formats."""
    mock_client.subtasks.get_all_subtasks.return_value = [_subtask()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "subtask", "list", "10"])
    assert result.exit_code == 0, result.output


def test_subtask_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON subtask list is an array with title field."""
    mock_client.subtasks.get_all_subtasks.return_value = [_subtask()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "subtask", "list", "10"]
    )
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Write unit tests"
    assert data[0]["id"] == 9


def test_subtask_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON subtask get is a single object."""
    mock_client.subtasks.get_subtask.return_value = _subtask()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "subtask", "get", "9"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["title"] == "Write unit tests"


# ---------------------------------------------------------------------------
# Tag list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_tag_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``tag list`` exits 0 for all 4 output formats."""
    mock_client.tags.get_all_tags.return_value = [_tag()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "tag", "list"])
    assert result.exit_code == 0, result.output


def test_tag_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON tag list is an array."""
    mock_client.tags.get_all_tags.return_value = [_tag()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "tag", "list"])
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "urgent"


def test_tag_list_by_project_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list --project-id`` returns a JSON array."""
    mock_client.tags.get_tags_by_project.return_value = [_tag()]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "tag", "list", "--project-id", "1"],
    )
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "urgent"


# ---------------------------------------------------------------------------
# Group list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_group_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``group list`` exits 0 for all 4 output formats."""
    mock_client.groups.get_all_groups.return_value = [_group()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "group", "list"])
    assert result.exit_code == 0, result.output


def test_group_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON group list is an array."""
    mock_client.groups.get_all_groups.return_value = [_group()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "group", "list"])
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Developers"


def test_group_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON group get is a single object."""
    mock_client.groups.get_group.return_value = _group()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "group", "get", "2"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["name"] == "Developers"


# ---------------------------------------------------------------------------
# Link list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_link_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``link list`` exits 0 for all 4 output formats."""
    mock_client.links.get_all_links.return_value = [_link()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "link", "list"])
    assert result.exit_code == 0, result.output


def test_link_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON link list is an array."""
    mock_client.links.get_all_links.return_value = [_link()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "link", "list"])
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["label"] == "blocks"


def test_link_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON link get is a single object."""
    mock_client.links.get_link_by_id.return_value = _link()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "link", "get", "1"])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["label"] == "blocks"


# ---------------------------------------------------------------------------
# Task-link list — all 4 formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_task_link_list_all_formats(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
) -> None:
    """``task-link list`` exits 0 for all 4 output formats."""
    mock_client.task_links.get_all_task_links.return_value = [_task_link()]
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, "task-link", "list", "10"])
    assert result.exit_code == 0, result.output


def test_task_link_list_json_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON task-link list is an array."""
    mock_client.task_links.get_all_task_links.return_value = [_task_link()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-link", "list", "10"]
    )
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 11
    assert data[0]["task_id"] == 10


def test_task_link_get_json_is_object(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON task-link get is a single object."""
    mock_client.task_links.get_task_link_by_id.return_value = _task_link()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-link", "get", "11"]
    )
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["opposite_task_id"] == 20


# ===========================================================================
# Section 2: Error output tests — all 3 error types
# ===========================================================================


def test_error_not_found_displayed_correctly(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """KanboardNotFoundError produces a clear 'Not found' error message."""
    mock_client.projects.get_project_by_id.side_effect = KanboardNotFoundError(
        "Project 99 not found",
        resource="Project",
        identifier=99,
    )
    result = _invoke(runner, mock_config, mock_client, ["project", "get", "99"])
    assert result.exit_code != 0
    # Click renders ClickException messages with "Error: ..."
    assert "Error" in result.output
    # The not-found message includes resource type and identifier
    assert "Project" in result.output or "99" in result.output


def test_error_api_error_displayed_correctly(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """KanboardAPIError produces a clear 'API error' message with method info."""
    mock_client.tasks.get_all_tasks.side_effect = KanboardAPIError(
        "Internal server error",
        method="getAllTasks",
        code=-32603,
    )
    result = _invoke(runner, mock_config, mock_client, ["task", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output
    assert "Internal server error" in result.output


def test_error_auth_error_displayed_correctly(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """KanboardAuthError raised by resource produces a clear auth message."""
    mock_client.me.get_me.side_effect = KanboardAuthError(
        "User API authentication required",
        http_status=403,
    )
    result = _invoke(runner, mock_config, mock_client, ["me"])
    assert result.exit_code != 0
    assert "Error" in result.output
    # The auth error message should be visible
    assert "auth" in result.output.lower() or "403" in result.output


def test_error_not_found_in_json_mode(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """KanboardNotFoundError exits non-zero even in JSON output mode."""
    mock_client.tasks.get_task.side_effect = KanboardNotFoundError(
        "Task not found",
        resource="Task",
        identifier=999,
    )
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "get", "999"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_error_api_error_in_csv_mode(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """KanboardAPIError exits non-zero in CSV output mode."""
    mock_client.columns.get_columns.side_effect = KanboardAPIError(
        "getColumns failed",
        method="getColumns",
        code=None,
    )
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "column", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_error_not_found_in_quiet_mode(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """KanboardNotFoundError exits non-zero in quiet output mode."""
    mock_client.users.get_user.side_effect = KanboardNotFoundError(
        "User not found",
        resource="User",
        identifier=999,
    )
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "user", "get", "999"])
    assert result.exit_code != 0


# ===========================================================================
# Section 3: Empty result tests
# ===========================================================================


@pytest.mark.parametrize(
    "command,setup",
    [
        (
            ["project", "list"],
            lambda mc: mc.projects.get_all_projects.__setattr__("return_value", []),
        ),
        (
            ["task", "list", "1"],
            lambda mc: mc.tasks.get_all_tasks.__setattr__("return_value", []),
        ),
        (
            ["column", "list", "1"],
            lambda mc: mc.columns.get_columns.__setattr__("return_value", []),
        ),
        (
            ["swimlane", "list", "1"],
            lambda mc: mc.swimlanes.get_active_swimlanes.__setattr__("return_value", []),
        ),
        (
            ["comment", "list", "10"],
            lambda mc: mc.comments.get_all_comments.__setattr__("return_value", []),
        ),
        (
            ["user", "list"],
            lambda mc: mc.users.get_all_users.__setattr__("return_value", []),
        ),
        (
            ["category", "list", "1"],
            lambda mc: mc.categories.get_all_categories.__setattr__("return_value", []),
        ),
        (
            ["subtask", "list", "10"],
            lambda mc: mc.subtasks.get_all_subtasks.__setattr__("return_value", []),
        ),
        (
            ["tag", "list"],
            lambda mc: mc.tags.get_all_tags.__setattr__("return_value", []),
        ),
        (
            ["group", "list"],
            lambda mc: mc.groups.get_all_groups.__setattr__("return_value", []),
        ),
        (
            ["link", "list"],
            lambda mc: mc.links.get_all_links.__setattr__("return_value", []),
        ),
        (
            ["task-link", "list", "10"],
            lambda mc: mc.task_links.get_all_task_links.__setattr__("return_value", []),
        ),
    ],
)
def test_empty_list_exits_cleanly(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    command: list[str],
    setup: Any,
) -> None:
    """All list commands exit 0 cleanly when the SDK returns an empty list."""
    setup(mock_client)
    result = _invoke(runner, mock_config, mock_client, command)
    assert result.exit_code == 0, f"{command}: {result.output}"


@pytest.mark.parametrize(
    "fmt,command,setup",
    [
        (
            "json",
            ["project", "list"],
            lambda mc: mc.projects.get_all_projects.__setattr__("return_value", []),
        ),
        (
            "csv",
            ["project", "list"],
            lambda mc: mc.projects.get_all_projects.__setattr__("return_value", []),
        ),
        (
            "quiet",
            ["project", "list"],
            lambda mc: mc.projects.get_all_projects.__setattr__("return_value", []),
        ),
        (
            "json",
            ["task", "list", "1"],
            lambda mc: mc.tasks.get_all_tasks.__setattr__("return_value", []),
        ),
        (
            "json",
            ["comment", "list", "10"],
            lambda mc: mc.comments.get_all_comments.__setattr__("return_value", []),
        ),
        (
            "json",
            ["user", "list"],
            lambda mc: mc.users.get_all_users.__setattr__("return_value", []),
        ),
    ],
)
def test_empty_list_all_formats_exits_cleanly(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    fmt: str,
    command: list[str],
    setup: Any,
) -> None:
    """Empty list exits 0 for all output formats."""
    setup(mock_client)
    result = _invoke(runner, mock_config, mock_client, ["--output", fmt, *command])
    assert result.exit_code == 0, f"{fmt} {command}: {result.output}"


def test_empty_json_list_is_array(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Empty list in JSON format produces a valid empty JSON array []."""
    mock_client.projects.get_all_projects.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "project", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == []


def test_empty_quiet_produces_no_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Empty list in quiet mode produces no output lines."""
    mock_client.projects.get_all_projects.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "project", "list"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert lines == []


# ===========================================================================
# Section 4: Edge case tests
# ===========================================================================


def test_edge_case_very_long_field_values_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Table format handles very long field values without crashing."""
    long_name = "A" * 300
    p = Project.from_api(
        {
            "id": "1",
            "name": long_name,
            "description": "B" * 500,
            "is_active": "1",
            "token": "tok",
            "last_modified": None,
            "is_public": "0",
            "is_private": False,
            "owner_id": "1",
            "identifier": "",
            "start_date": None,
            "end_date": None,
            "url": "",
        }
    )
    mock_client.projects.get_all_projects.return_value = [p]
    result = _invoke(runner, mock_config, mock_client, ["project", "list"])
    assert result.exit_code == 0


def test_edge_case_very_long_field_values_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON format preserves very long field values in full."""
    long_name = "A" * 300
    p = Project.from_api(
        {
            "id": "1",
            "name": long_name,
            "description": "",
            "is_active": "1",
            "token": "tok",
            "last_modified": None,
            "is_public": "0",
            "is_private": False,
            "owner_id": "1",
            "identifier": "",
            "start_date": None,
            "end_date": None,
            "url": "",
        }
    )
    mock_client.projects.get_all_projects.return_value = [p]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "project", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["name"] == long_name


def test_edge_case_none_fields_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """None optional fields appear in JSON output and do not crash."""
    u = User.from_api(
        {
            "id": "7",
            "username": "niluser",
            "name": "Nil User",
            "email": "",
            "role": "app-user",
            "is_active": "1",
            "is_ldap_user": "0",
            "notification_method": "0",
            "avatar_path": None,  # explicitly None
            "timezone": None,
            "language": None,
        }
    )
    mock_client.users.get_user.return_value = u
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "user", "get", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["avatar_path"] is None
    assert data["timezone"] is None
    assert data["language"] is None


def test_edge_case_none_fields_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Table format renders None optional fields as empty string without crashing."""
    u = User.from_api(
        {
            "id": "7",
            "username": "niluser",
            "name": "",
            "email": "",
            "role": "app-user",
            "is_active": "1",
            "is_ldap_user": "0",
            "notification_method": "0",
            "avatar_path": None,
            "timezone": None,
            "language": None,
        }
    )
    mock_client.users.get_all_users.return_value = [u]
    result = _invoke(runner, mock_config, mock_client, ["user", "list"])
    assert result.exit_code == 0
    # None fields should render as empty, not "None"
    assert "None" not in result.output


def test_edge_case_csv_special_chars_comma(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """CSV output properly quotes field values containing commas."""
    c = Comment.from_api(
        {
            "id": "1",
            "task_id": "10",
            "user_id": "1",
            "username": "alice",
            "name": "Smith, Alice",  # name with comma
            "comment": "Fixed it, works now.",
            "date_creation": None,
            "date_modification": None,
        }
    )
    mock_client.comments.get_all_comments.return_value = [c]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "comment", "list", "10"])
    assert result.exit_code == 0
    # Parse the CSV to verify it's structurally valid
    reader = csv.DictReader(io.StringIO(result.output))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["name"] == "Smith, Alice"


def test_edge_case_csv_special_chars_quotes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """CSV output properly escapes field values containing double-quotes."""
    c = Comment.from_api(
        {
            "id": "2",
            "task_id": "10",
            "user_id": "1",
            "username": "bob",
            "name": "Bob",
            "comment": 'He said "LGTM" and merged.',
            "date_creation": None,
            "date_modification": None,
        }
    )
    mock_client.comments.get_all_comments.return_value = [c]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "comment", "list", "10"])
    assert result.exit_code == 0
    reader = csv.DictReader(io.StringIO(result.output))
    rows = list(reader)
    assert rows[0]["comment"] == 'He said "LGTM" and merged.'


def test_edge_case_csv_special_chars_newline(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """CSV output properly handles field values containing newlines."""
    t = Task.from_api(
        {
            "id": "5",
            "title": "Multi-line\ntask title",
            "description": "Line one\nLine two",
            "date_creation": None,
            "date_modification": None,
            "date_due": None,
            "date_completed": None,
            "date_moved": None,
            "color_id": "green",
            "project_id": "1",
            "column_id": "1",
            "swimlane_id": "0",
            "owner_id": "0",
            "creator_id": "1",
            "category_id": "0",
            "is_active": "1",
            "priority": "0",
            "score": "0",
            "position": "1",
            "reference": "",
            "tags": [],
            "url": "",
        }
    )
    mock_client.tasks.get_all_tasks.return_value = [t]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "task", "list", "1"])
    assert result.exit_code == 0
    # The CSV must still parse as valid CSV despite the embedded newline
    reader = csv.DictReader(io.StringIO(result.output))
    rows = list(reader)
    assert len(rows) == 1
    assert "Multi-line" in rows[0]["title"]


def test_edge_case_special_chars_in_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON output correctly encodes special characters (Unicode, HTML entities)."""
    c = Comment.from_api(
        {
            "id": "3",
            "task_id": "10",
            "user_id": "1",
            "username": "user",
            "name": "Ünïcödé Üsér",
            "comment": "This & that <b>test</b> → done",
            "date_creation": None,
            "date_modification": None,
        }
    )
    mock_client.comments.get_comment.return_value = c
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "comment", "get", "3"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Ünïcödé Üsér"
    assert data["comment"] == "This & that <b>test</b> → done"


def test_edge_case_datetime_field_in_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """JSON output serialises datetime fields as ISO-8601 strings."""
    # Task with a non-None date_creation (Unix timestamp → datetime)
    t = Task.from_api(
        {
            "id": "50",
            "title": "Datetime test",
            "description": "",
            "date_creation": "1711000000",
            "date_modification": "1711100000",
            "date_due": None,
            "date_completed": None,
            "date_moved": None,
            "color_id": "red",
            "project_id": "1",
            "column_id": "1",
            "swimlane_id": "0",
            "owner_id": "1",
            "creator_id": "1",
            "category_id": "0",
            "is_active": "1",
            "priority": "0",
            "score": "0",
            "position": "1",
            "reference": "",
            "tags": [],
            "url": "",
        }
    )
    mock_client.tasks.get_task.return_value = t
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "get", "50"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # date_creation should be a non-null ISO-8601 string
    assert isinstance(data["date_creation"], str)
    assert "T" in data["date_creation"]  # ISO-8601 datetime has 'T' separator
    # date_due is None → should remain null in JSON
    assert data["date_due"] is None


# ===========================================================================
# Section 5: Quiet mode — IDs-only verification
# ===========================================================================


def test_quiet_multiple_items_one_id_per_line(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet mode prints exactly one ID per line for multiple results."""
    c1 = Comment.from_api(
        {
            "id": "1",
            "task_id": "10",
            "user_id": "1",
            "username": "u",
            "name": "User",
            "comment": "a",
            "date_creation": None,
            "date_modification": None,
        }
    )
    c2 = Comment.from_api(
        {
            "id": "2",
            "task_id": "10",
            "user_id": "2",
            "username": "v",
            "name": "Other",
            "comment": "b",
            "date_creation": None,
            "date_modification": None,
        }
    )
    c3 = Comment.from_api(
        {
            "id": "3",
            "task_id": "10",
            "user_id": "3",
            "username": "w",
            "name": "Third",
            "comment": "c",
            "date_creation": None,
            "date_modification": None,
        }
    )
    mock_client.comments.get_all_comments.return_value = [c1, c2, c3]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "comment", "list", "10"]
    )
    assert result.exit_code == 0
    lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
    assert lines == ["1", "2", "3"]


def test_quiet_no_column_headers(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet mode does not print column headers."""
    mock_client.users.get_all_users.return_value = [_user()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "user", "list"])
    assert result.exit_code == 0
    # Headers like "username", "email", "role" should NOT appear
    for header in ("username", "email", "role", "name"):
        assert header not in result.output


def test_quiet_single_item(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """Quiet mode for a single item prints exactly one ID line."""
    mock_client.groups.get_all_groups.return_value = [_group()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "group", "list"])
    assert result.exit_code == 0
    lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
    assert lines == ["2"]
