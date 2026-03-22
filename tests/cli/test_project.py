"""CLI tests for ``kanboard project`` subcommands (US-012)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Project
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_PROJECT_DATA: dict = {
    "id": "1",
    "name": "Main Project",
    "description": "The main project",
    "is_active": "1",
    "token": "abc123",
    "last_modified": "1711000000",
    "is_public": "0",
    "is_private": False,
    "owner_id": "2",
    "identifier": "MAIN",
    "start_date": None,
    "end_date": None,
    "url": "http://kanboard.test/board/1",
}

_SAMPLE_PROJECT_DATA_2: dict = {
    **_SAMPLE_PROJECT_DATA,
    "id": "2",
    "name": "Second Project",
    "identifier": "SEC",
}


def _make_project(data: dict | None = None) -> Project:
    """Build a Project from sample data."""
    return Project.from_api(data or _SAMPLE_PROJECT_DATA)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def mock_config() -> KanboardConfig:
    """Return a minimal resolved config."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock client with a projects resource."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
) -> object:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args)


# ===========================================================================
# project list
# ===========================================================================


def test_project_list_table_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project list`` renders projects in table format by default."""
    mock_client.projects.get_all_projects.return_value = [_make_project()]
    result = _invoke(runner, mock_config, mock_client, ["project", "list"])
    assert result.exit_code == 0
    assert "id" in result.output
    assert "name" in result.output
    mock_client.projects.get_all_projects.assert_called_once_with()


def test_project_list_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project list`` renders projects as a JSON array with data values."""
    mock_client.projects.get_all_projects.return_value = [_make_project()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "project", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Main Project"


def test_project_list_csv_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project list`` renders projects as CSV with data values."""
    mock_client.projects.get_all_projects.return_value = [_make_project()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "project", "list"])
    assert result.exit_code == 0
    assert "Main Project" in result.output
    assert "name" in result.output  # header row


def test_project_list_quiet_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project list --output quiet`` prints only IDs."""
    mock_client.projects.get_all_projects.return_value = [
        _make_project(),
        _make_project(_SAMPLE_PROJECT_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "project", "list"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "1" in lines
    assert "2" in lines


def test_project_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project list`` with no results exits 0 cleanly."""
    mock_client.projects.get_all_projects.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["project", "list"])
    assert result.exit_code == 0


def test_project_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error exits non-zero with a message."""
    mock_client.projects.get_all_projects.side_effect = KanboardAPIError(
        "Server error", method="getAllProjects", code=-1
    )
    result = _invoke(runner, mock_config, mock_client, ["project", "list"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# project get
# ===========================================================================


def test_project_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project get`` exits 0 in table format and calls get_project_by_id."""
    mock_client.projects.get_project_by_id.return_value = _make_project()
    result = _invoke(runner, mock_config, mock_client, ["project", "get", "1"])
    assert result.exit_code == 0
    mock_client.projects.get_project_by_id.assert_called_once_with(1)


def test_project_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project get`` with --output json renders a single JSON object."""
    mock_client.projects.get_project_by_id.return_value = _make_project()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "project", "get", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["name"] == "Main Project"
    assert data["id"] == 1


def test_project_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project get`` with unknown ID exits non-zero with an error."""
    mock_client.projects.get_project_by_id.side_effect = KanboardNotFoundError(
        "Project not found",
        method="getProjectById",
        code=None,
        resource="Project",
        identifier="99",
    )
    result = _invoke(runner, mock_config, mock_client, ["project", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# project create
# ===========================================================================


def test_project_create_minimal(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project create`` with only name creates a project and prints its ID."""
    mock_client.projects.create_project.return_value = 3
    result = _invoke(runner, mock_config, mock_client, ["project", "create", "My Project"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.projects.create_project.assert_called_once_with("My Project")


def test_project_create_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project create`` passes all supplied options to the SDK."""
    mock_client.projects.create_project.return_value = 4
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "project",
            "create",
            "Sprint 1",
            "--description",
            "First sprint",
            "--owner-id",
            "2",
            "--identifier",
            "SP1",
            "--start-date",
            "2025-01-01",
            "--end-date",
            "2025-03-31",
        ],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.projects.create_project.call_args
    assert kwargs["description"] == "First sprint"
    assert kwargs["owner_id"] == 2
    assert kwargs["identifier"] == "SP1"
    assert kwargs["start_date"] == "2025-01-01"
    assert kwargs["end_date"] == "2025-03-31"


def test_project_create_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project create --output json`` emits JSON success object."""
    mock_client.projects.create_project.return_value = 5
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project", "create", "My Project"],
    )
    assert result.exit_code == 0
    assert '"status"' in result.output
    assert '"ok"' in result.output


def test_project_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on create exits non-zero."""
    mock_client.projects.create_project.side_effect = KanboardAPIError(
        "createProject failed", method="createProject", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project", "create", "Bad"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# project update
# ===========================================================================


def test_project_update_with_name(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project update --name`` updates the name."""
    mock_client.projects.update_project.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project", "update", "1", "--name", "Renamed"]
    )
    assert result.exit_code == 0
    assert "updated" in result.output
    mock_client.projects.update_project.assert_called_once_with(1, name="Renamed")


def test_project_update_multiple_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project update`` passes only supplied options to the SDK."""
    mock_client.projects.update_project.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "project",
            "update",
            "1",
            "--description",
            "New desc",
            "--owner-id",
            "3",
            "--identifier",
            "NEW",
        ],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.projects.update_project.call_args
    assert kwargs["description"] == "New desc"
    assert kwargs["owner_id"] == 3
    assert kwargs["identifier"] == "NEW"
    assert "name" not in kwargs


def test_project_update_no_options_is_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project update`` with no options exits non-zero with a usage error."""
    result = _invoke(runner, mock_config, mock_client, ["project", "update", "1"])
    assert result.exit_code != 0
    mock_client.projects.update_project.assert_not_called()


def test_project_update_json_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project update`` with --output json emits JSON success."""
    mock_client.projects.update_project.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project", "update", "1", "--name", "X"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


def test_project_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on update exits non-zero."""
    mock_client.projects.update_project.side_effect = KanboardAPIError(
        "updateProject failed", method="updateProject", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project", "update", "1", "--name", "Fail"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# project remove
# ===========================================================================


def test_project_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project remove --yes`` deletes without prompting."""
    mock_client.projects.remove_project.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["project", "remove", "1", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.projects.remove_project.assert_called_once_with(1)


def test_project_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project remove`` without --yes and declining aborts; SDK not called."""
    result = _invoke(runner, mock_config, mock_client, ["project", "remove", "1"])
    assert result.exit_code != 0
    mock_client.projects.remove_project.assert_not_called()


def test_project_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project remove`` with interactive 'y' answer removes the project."""
    mock_client.projects.remove_project.return_value = True
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["project", "remove", "1"], input="y\n")
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.projects.remove_project.assert_called_once_with(1)


def test_project_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project remove --yes --output json`` emits JSON success."""
    mock_client.projects.remove_project.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project", "remove", "1", "--yes"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# project enable / disable
# ===========================================================================


def test_project_enable(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project enable`` calls enable_project and prints confirmation."""
    mock_client.projects.enable_project.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["project", "enable", "1"])
    assert result.exit_code == 0
    assert "enabled" in result.output
    mock_client.projects.enable_project.assert_called_once_with(1)


def test_project_disable(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project disable`` calls disable_project and prints confirmation."""
    mock_client.projects.disable_project.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["project", "disable", "1"])
    assert result.exit_code == 0
    assert "disabled" in result.output
    mock_client.projects.disable_project.assert_called_once_with(1)


def test_project_enable_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project enable --output json`` emits JSON success."""
    mock_client.projects.enable_project.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project", "enable", "1"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


def test_project_disable_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project disable --output json`` emits JSON success."""
    mock_client.projects.disable_project.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project", "disable", "1"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# project activity
# ===========================================================================


def test_project_activity_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project activity`` exits 0 and calls get_project_activity."""
    mock_client.projects.get_project_activity.return_value = [
        {"id": 1, "event_name": "task.create", "author_name": "Alice"}
    ]
    result = _invoke(runner, mock_config, mock_client, ["project", "activity", "1"])
    assert result.exit_code == 0
    mock_client.projects.get_project_activity.assert_called_once_with(1)


def test_project_activity_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project activity --output json`` renders a JSON array with event data."""
    mock_client.projects.get_project_activity.return_value = [
        {"id": 1, "event_name": "task.create", "author_name": "Alice"}
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project", "activity", "1"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["event_name"] == "task.create"


def test_project_activity_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project activity`` with no events exits 0."""
    mock_client.projects.get_project_activity.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["project", "activity", "1"])
    assert result.exit_code == 0


def test_project_activity_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project activity --output csv`` renders CSV rows."""
    mock_client.projects.get_project_activity.return_value = [
        {"id": 2, "event_name": "task.close", "author_name": "Bob"}
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "project", "activity", "1"]
    )
    assert result.exit_code == 0
    assert "task.close" in result.output


def test_project_activity_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on activity exits non-zero."""
    mock_client.projects.get_project_activity.side_effect = KanboardAPIError(
        "getProjectActivity failed", method="getProjectActivity", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project", "activity", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# --help smoke tests
# ===========================================================================


@pytest.mark.parametrize(
    "subcommand",
    ["list", "get", "create", "update", "remove", "enable", "disable", "activity"],
)
def test_project_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Every project subcommand must respond to --help with exit 0."""
    from kanboard.exceptions import KanboardConfigError

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("x", field="url"),
    ):
        result = runner.invoke(cli, ["project", subcommand, "--help"])
    assert result.exit_code == 0, (
        f"'project {subcommand} --help' exited {result.exit_code}: {result.output}"
    )
