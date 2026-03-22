"""CLI tests for ``kanboard subtask`` subcommands (US-015)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Subtask
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_SUBTASK_DATA: dict = {
    "id": "10",
    "title": "Write unit tests",
    "task_id": "42",
    "user_id": "3",
    "status": "0",
    "time_estimated": "2.0",
    "time_spent": "0.5",
    "position": "1",
    "username": "jdoe",
    "name": "John Doe",
}

_SAMPLE_SUBTASK_DATA_2: dict = {
    **_SAMPLE_SUBTASK_DATA,
    "id": "11",
    "title": "Review pull request",
    "status": "1",
}


def _make_subtask(data: dict | None = None) -> Subtask:
    """Build a Subtask from sample data."""
    return Subtask.from_api(data or _SAMPLE_SUBTASK_DATA)


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
    """Return a MagicMock client with a subtasks resource."""
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
# subtask list
# ===========================================================================


def test_subtask_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask list`` renders subtasks in table format."""
    mock_client.subtasks.get_all_subtasks.return_value = [_make_subtask()]
    result = _invoke(runner, mock_config, mock_client, ["subtask", "list", "42"])
    assert result.exit_code == 0
    assert "10" in result.output  # id is always short and not wrapped
    mock_client.subtasks.get_all_subtasks.assert_called_once_with(42)


def test_subtask_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask list --output json`` renders subtasks as a JSON array."""
    mock_client.subtasks.get_all_subtasks.return_value = [_make_subtask()]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "subtask", "list", "42"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 10
    assert data[0]["title"] == "Write unit tests"


def test_subtask_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask list --output csv`` renders subtasks as CSV with a header row."""
    mock_client.subtasks.get_all_subtasks.return_value = [_make_subtask()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "subtask", "list", "42"])
    assert result.exit_code == 0
    assert "Write unit tests" in result.output
    assert "id" in result.output  # header row


def test_subtask_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask list --output quiet`` prints only subtask IDs."""
    mock_client.subtasks.get_all_subtasks.return_value = [
        _make_subtask(),
        _make_subtask(_SAMPLE_SUBTASK_DATA_2),
    ]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "quiet", "subtask", "list", "42"],
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "10" in lines
    assert "11" in lines


def test_subtask_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask list`` with no subtasks exits 0 cleanly."""
    mock_client.subtasks.get_all_subtasks.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["subtask", "list", "42"])
    assert result.exit_code == 0


def test_subtask_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on subtask list exits non-zero."""
    mock_client.subtasks.get_all_subtasks.side_effect = KanboardAPIError(
        "getAllSubtasks failed", method="getAllSubtasks", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["subtask", "list", "42"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_subtask_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["subtask", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# subtask get
# ===========================================================================


def test_subtask_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask get`` shows subtask details in table format."""
    mock_client.subtasks.get_subtask.return_value = _make_subtask()
    result = _invoke(runner, mock_config, mock_client, ["subtask", "get", "10"])
    assert result.exit_code == 0
    assert "jdoe" in result.output  # username field is short and not wrapped
    mock_client.subtasks.get_subtask.assert_called_once_with(10)


def test_subtask_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask get --output json`` renders the subtask as a JSON object."""
    mock_client.subtasks.get_subtask.return_value = _make_subtask()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "subtask", "get", "10"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 10
    assert data["title"] == "Write unit tests"


def test_subtask_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask get`` with unknown ID exits non-zero with an error message."""
    mock_client.subtasks.get_subtask.side_effect = KanboardNotFoundError(
        "Subtask 99 not found", resource="Subtask", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["subtask", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_subtask_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["subtask", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# subtask create
# ===========================================================================


def test_subtask_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask create`` creates a subtask and prints the new ID."""
    mock_client.subtasks.create_subtask.return_value = 10
    result = _invoke(
        runner, mock_config, mock_client, ["subtask", "create", "42", "Write unit tests"]
    )
    assert result.exit_code == 0
    assert "10" in result.output
    mock_client.subtasks.create_subtask.assert_called_once_with(42, "Write unit tests")


def test_subtask_create_with_user_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask create --user-id`` passes it to the SDK."""
    mock_client.subtasks.create_subtask.return_value = 11
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["subtask", "create", "42", "Review PR", "--user-id", "3"],
    )
    assert result.exit_code == 0
    mock_client.subtasks.create_subtask.assert_called_once_with(42, "Review PR", user_id=3)


def test_subtask_create_with_time_estimated(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask create --time-estimated`` passes it to the SDK."""
    mock_client.subtasks.create_subtask.return_value = 12
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["subtask", "create", "42", "Deploy", "--time-estimated", "1.5"],
    )
    assert result.exit_code == 0
    mock_client.subtasks.create_subtask.assert_called_once_with(42, "Deploy", time_estimated=1.5)


def test_subtask_create_with_status(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask create --status`` passes it to the SDK."""
    mock_client.subtasks.create_subtask.return_value = 13
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["subtask", "create", "42", "Draft doc", "--status", "0"],
    )
    assert result.exit_code == 0
    mock_client.subtasks.create_subtask.assert_called_once_with(42, "Draft doc", status=0)


def test_subtask_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.subtasks.create_subtask.side_effect = KanboardAPIError(
        "createSubtask failed", method="createSubtask", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["subtask", "create", "42", "Bad subtask"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_subtask_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["subtask", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# subtask update
# ===========================================================================


def test_subtask_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask update`` updates a subtask and prints a success message."""
    mock_client.subtasks.update_subtask.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["subtask", "update", "10", "42", "--title", "Revised"]
    )
    assert result.exit_code == 0
    assert "10" in result.output
    mock_client.subtasks.update_subtask.assert_called_once_with(10, 42, title="Revised")


def test_subtask_update_with_status(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask update --status`` passes status to the SDK."""
    mock_client.subtasks.update_subtask.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["subtask", "update", "10", "42", "--status", "1"],
    )
    assert result.exit_code == 0
    mock_client.subtasks.update_subtask.assert_called_once_with(10, 42, status=1)


def test_subtask_update_with_time_spent(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask update --time-spent`` passes time_spent to the SDK."""
    mock_client.subtasks.update_subtask.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["subtask", "update", "10", "42", "--time-spent", "2.0"],
    )
    assert result.exit_code == 0
    mock_client.subtasks.update_subtask.assert_called_once_with(10, 42, time_spent=2.0)


def test_subtask_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.subtasks.update_subtask.side_effect = KanboardAPIError(
        "updateSubtask failed", method="updateSubtask", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["subtask", "update", "10", "42", "--title", "X"]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_subtask_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["subtask", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# subtask remove
# ===========================================================================


def test_subtask_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask remove --yes`` removes without prompting."""
    mock_client.subtasks.remove_subtask.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["subtask", "remove", "10", "--yes"])
    assert result.exit_code == 0
    assert "10" in result.output
    mock_client.subtasks.remove_subtask.assert_called_once_with(10)


def test_subtask_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["subtask", "remove", "10"], input="n\n")
    assert result.exit_code != 0
    mock_client.subtasks.remove_subtask.assert_not_called()


def test_subtask_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask remove`` without --yes and answering 'y' proceeds."""
    mock_client.subtasks.remove_subtask.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["subtask", "remove", "10"], input="y\n")
    assert result.exit_code == 0
    mock_client.subtasks.remove_subtask.assert_called_once_with(10)


def test_subtask_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``subtask remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["subtask", "remove", "--help"])
    assert result.exit_code == 0
