"""CLI tests for ``kanboard action`` subcommands (US-010)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError
from kanboard.models import Action
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_ACTION_DATA: dict = {
    "id": "1",
    "project_id": "2",
    "event_name": "task.move.column",
    "action_name": "\\TaskClose",
    "params": {"column_id": "5"},
}

_SAMPLE_ACTION_DATA_2: dict = {
    "id": "3",
    "project_id": "2",
    "event_name": "task.create",
    "action_name": "\\TaskAssignUser",
    "params": {"user_id": "10"},
}


def _make_action(data: dict | None = None) -> Action:
    """Build an Action from sample data."""
    return Action.from_api(data or _SAMPLE_ACTION_DATA)


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
    """Return a MagicMock client with an actions resource."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
    input: str | None = None,
) -> object:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args, input=input)


# ===========================================================================
# action list
# ===========================================================================


def test_action_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action list`` renders actions in table format."""
    mock_client.actions.get_actions.return_value = [
        _make_action(),
        _make_action(_SAMPLE_ACTION_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["action", "list", "2"])
    assert result.exit_code == 0
    assert "TaskClose" in result.output
    assert "TaskAssignUser" in result.output


def test_action_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action list`` renders actions in JSON format."""
    mock_client.actions.get_actions.return_value = [_make_action()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "action", "list", "2"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["action_name"] == "\\TaskClose"


def test_action_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action list`` renders actions in CSV format."""
    mock_client.actions.get_actions.return_value = [_make_action()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "action", "list", "2"])
    assert result.exit_code == 0
    assert "action_name" in result.output
    assert "TaskClose" in result.output


def test_action_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action list`` in quiet mode outputs IDs only."""
    mock_client.actions.get_actions.return_value = [_make_action()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "action", "list", "2"])
    assert result.exit_code == 0
    assert "1" in result.output


def test_action_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action list`` renders cleanly when no actions exist."""
    mock_client.actions.get_actions.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["action", "list", "2"])
    assert result.exit_code == 0


def test_action_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action list`` displays error on API failure."""
    mock_client.actions.get_actions.side_effect = KanboardAPIError(
        "Server error", method="getActions"
    )
    result = _invoke(runner, mock_config, mock_client, ["action", "list", "2"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# action available
# ===========================================================================


def test_action_available_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action available`` renders action types in table format."""
    mock_client.actions.get_available_actions.return_value = {
        "\\TaskClose": "Close a task",
        "\\TaskOpen": "Open a task",
    }
    result = _invoke(runner, mock_config, mock_client, ["action", "available"])
    assert result.exit_code == 0
    assert "TaskClose" in result.output
    assert "Close a task" in result.output


def test_action_available_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action available`` renders action types in JSON format."""
    mock_client.actions.get_available_actions.return_value = {
        "\\TaskClose": "Close a task",
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "action", "available"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["action"] == "\\TaskClose"


def test_action_available_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action available`` renders in CSV format."""
    mock_client.actions.get_available_actions.return_value = {
        "\\TaskClose": "Close a task",
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "action", "available"])
    assert result.exit_code == 0
    assert "action" in result.output
    assert "TaskClose" in result.output


def test_action_available_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action available`` renders in quiet mode."""
    mock_client.actions.get_available_actions.return_value = {
        "\\TaskClose": "Close a task",
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "action", "available"])
    assert result.exit_code == 0


def test_action_available_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action available`` renders cleanly when no actions exist."""
    mock_client.actions.get_available_actions.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["action", "available"])
    assert result.exit_code == 0


# ===========================================================================
# action events
# ===========================================================================


def test_action_events_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action events`` renders events in table format."""
    mock_client.actions.get_available_action_events.return_value = {
        "task.move.column": "Task moved to another column",
        "task.create": "Task creation",
    }
    result = _invoke(runner, mock_config, mock_client, ["action", "events"])
    assert result.exit_code == 0
    assert "task.move.column" in result.output
    assert "Task moved" in result.output


def test_action_events_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action events`` renders events in JSON format."""
    mock_client.actions.get_available_action_events.return_value = {
        "task.move.column": "Task moved to another column",
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "action", "events"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["event"] == "task.move.column"


def test_action_events_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action events`` renders cleanly when no events exist."""
    mock_client.actions.get_available_action_events.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["action", "events"])
    assert result.exit_code == 0


# ===========================================================================
# action compatible-events
# ===========================================================================


def test_action_compatible_events_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action compatible-events`` renders event list in table format."""
    mock_client.actions.get_compatible_action_events.return_value = [
        "task.move.column",
        "task.create",
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["action", "compatible-events", "\\TaskClose"]
    )
    assert result.exit_code == 0
    assert "task.move.column" in result.output
    assert "task.create" in result.output


def test_action_compatible_events_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action compatible-events`` renders in JSON format."""
    mock_client.actions.get_compatible_action_events.return_value = [
        "task.move.column",
    ]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "action", "compatible-events", "\\TaskClose"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["event"] == "task.move.column"


def test_action_compatible_events_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action compatible-events`` renders cleanly when no events are compatible."""
    mock_client.actions.get_compatible_action_events.return_value = []
    result = _invoke(
        runner, mock_config, mock_client, ["action", "compatible-events", "\\TaskClose"]
    )
    assert result.exit_code == 0


# ===========================================================================
# action create
# ===========================================================================


def test_action_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action create`` displays success message with ID."""
    mock_client.actions.create_action.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "action",
            "create",
            "2",
            "task.move.column",
            "\\TaskClose",
            "-p",
            "column_id=5",
        ],
    )
    assert result.exit_code == 0
    assert "Action #7 created" in result.output
    mock_client.actions.create_action.assert_called_once_with(
        2, "task.move.column", "\\TaskClose", {"column_id": "5"}
    )


def test_action_create_multiple_params(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action create`` handles multiple --param flags."""
    mock_client.actions.create_action.return_value = 10
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "action",
            "create",
            "2",
            "task.move.column",
            "\\TaskClose",
            "-p",
            "column_id=5",
            "-p",
            "color_id=red",
        ],
    )
    assert result.exit_code == 0
    assert "Action #10 created" in result.output
    mock_client.actions.create_action.assert_called_once_with(
        2,
        "task.move.column",
        "\\TaskClose",
        {"column_id": "5", "color_id": "red"},
    )


def test_action_create_no_params(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action create`` works with no --param flags (empty dict)."""
    mock_client.actions.create_action.return_value = 11
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["action", "create", "2", "task.move.column", "\\TaskClose"],
    )
    assert result.exit_code == 0
    assert "Action #11 created" in result.output
    mock_client.actions.create_action.assert_called_once_with(
        2, "task.move.column", "\\TaskClose", {}
    )


def test_action_create_invalid_param_format(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action create`` errors on invalid param format (missing =)."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "action",
            "create",
            "2",
            "task.move.column",
            "\\TaskClose",
            "-p",
            "bad_param",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid param format" in result.output


def test_action_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action create`` displays error on API failure."""
    mock_client.actions.create_action.side_effect = KanboardAPIError(
        "Failed to create action", method="createAction"
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "action",
            "create",
            "2",
            "task.move.column",
            "\\TaskClose",
            "-p",
            "column_id=5",
        ],
    )
    assert result.exit_code != 0
    assert "Failed to create action" in result.output


def test_action_create_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action create`` with --output json shows success in JSON."""
    mock_client.actions.create_action.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "--output",
            "json",
            "action",
            "create",
            "2",
            "task.move.column",
            "\\TaskClose",
            "-p",
            "column_id=5",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "Action #7 created" in data["message"]


# ===========================================================================
# action remove
# ===========================================================================


def test_action_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action remove`` with --yes removes without prompting."""
    mock_client.actions.remove_action.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["action", "remove", "5", "--yes"])
    assert result.exit_code == 0
    assert "Action #5 removed" in result.output
    mock_client.actions.remove_action.assert_called_once_with(5)


def test_action_remove_without_yes_confirmed(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action remove`` without --yes prompts and proceeds on 'y'."""
    mock_client.actions.remove_action.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["action", "remove", "5"], input="y\n")
    assert result.exit_code == 0
    assert "Action #5 removed" in result.output


def test_action_remove_without_yes_aborted(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action remove`` without --yes aborts on 'n'."""
    result = _invoke(runner, mock_config, mock_client, ["action", "remove", "5"], input="n\n")
    assert result.exit_code != 0


def test_action_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``action remove`` with --output json shows success in JSON."""
    mock_client.actions.remove_action.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "action", "remove", "5", "--yes"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "Action #5 removed" in data["message"]


# ===========================================================================
# Help output
# ===========================================================================


def test_action_help(runner: CliRunner) -> None:
    """``action --help`` shows available subcommands."""
    result = runner.invoke(cli, ["action", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "available" in result.output
    assert "events" in result.output
    assert "compatible-events" in result.output
    assert "create" in result.output
    assert "remove" in result.output
