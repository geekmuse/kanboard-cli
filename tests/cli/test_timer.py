"""CLI tests for ``kanboard timer`` subcommands (US-011)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError
from kanboard_cli.main import cli

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
    """Return a MagicMock client with a subtask_time_tracking resource."""
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
# timer status
# ===========================================================================


def test_timer_status_running_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` shows running=True in table format."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["timer", "status", "7"])
    assert result.exit_code == 0
    assert "True" in result.output
    assert "7" in result.output


def test_timer_status_not_running_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` shows running=False in table format."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = False
    result = _invoke(runner, mock_config, mock_client, ["timer", "status", "7"])
    assert result.exit_code == 0
    assert "False" in result.output


def test_timer_status_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` renders in JSON format."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "timer", "status", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["running"] == "True"
    assert data[0]["subtask_id"] == "7"


def test_timer_status_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` renders in CSV format."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "timer", "status", "7"])
    assert result.exit_code == 0
    assert "subtask_id" in result.output
    assert "running" in result.output
    assert "True" in result.output


def test_timer_status_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` renders in quiet mode."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "timer", "status", "7"]
    )
    assert result.exit_code == 0


def test_timer_status_with_user_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` passes --user-id to the SDK."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["timer", "status", "7", "--user-id", "1"])
    assert result.exit_code == 0
    mock_client.subtask_time_tracking.has_subtask_timer.assert_called_once_with(7, user_id=1)


def test_timer_status_not_running_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` shows running=False in JSON format."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = False
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "timer", "status", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["running"] == "False"


def test_timer_status_not_running_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` shows running=False in CSV format."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = False
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "timer", "status", "7"])
    assert result.exit_code == 0
    assert "False" in result.output


def test_timer_status_not_running_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` renders cleanly in quiet mode when not running."""
    mock_client.subtask_time_tracking.has_subtask_timer.return_value = False
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "timer", "status", "7"]
    )
    assert result.exit_code == 0


def test_timer_status_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer status`` displays error on API failure."""
    mock_client.subtask_time_tracking.has_subtask_timer.side_effect = KanboardAPIError(
        "Server error", method="hasSubtaskTimer"
    )
    result = _invoke(runner, mock_config, mock_client, ["timer", "status", "7"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# timer start
# ===========================================================================


def test_timer_start_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer start`` displays success message."""
    mock_client.subtask_time_tracking.set_subtask_start_time.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["timer", "start", "7"])
    assert result.exit_code == 0
    assert "Timer started for subtask #7" in result.output


def test_timer_start_with_user_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer start`` passes --user-id to the SDK."""
    mock_client.subtask_time_tracking.set_subtask_start_time.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["timer", "start", "7", "--user-id", "1"])
    assert result.exit_code == 0
    mock_client.subtask_time_tracking.set_subtask_start_time.assert_called_once_with(7, user_id=1)


def test_timer_start_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer start`` with --output json shows success in JSON."""
    mock_client.subtask_time_tracking.set_subtask_start_time.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "timer", "start", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "Timer started for subtask #7" in data["message"]


def test_timer_start_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer start`` displays error on API failure."""
    mock_client.subtask_time_tracking.set_subtask_start_time.side_effect = KanboardAPIError(
        "Failed to start timer", method="setSubtaskStartTime"
    )
    result = _invoke(runner, mock_config, mock_client, ["timer", "start", "7"])
    assert result.exit_code != 0
    assert "Failed to start timer" in result.output


# ===========================================================================
# timer stop
# ===========================================================================


def test_timer_stop_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer stop`` displays success message."""
    mock_client.subtask_time_tracking.set_subtask_end_time.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["timer", "stop", "7"])
    assert result.exit_code == 0
    assert "Timer stopped for subtask #7" in result.output


def test_timer_stop_with_user_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer stop`` passes --user-id to the SDK."""
    mock_client.subtask_time_tracking.set_subtask_end_time.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["timer", "stop", "7", "--user-id", "1"])
    assert result.exit_code == 0
    mock_client.subtask_time_tracking.set_subtask_end_time.assert_called_once_with(7, user_id=1)


def test_timer_stop_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer stop`` with --output json shows success in JSON."""
    mock_client.subtask_time_tracking.set_subtask_end_time.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "timer", "stop", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "Timer stopped for subtask #7" in data["message"]


def test_timer_stop_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer stop`` displays error on API failure."""
    mock_client.subtask_time_tracking.set_subtask_end_time.side_effect = KanboardAPIError(
        "Failed to stop timer", method="setSubtaskEndTime"
    )
    result = _invoke(runner, mock_config, mock_client, ["timer", "stop", "7"])
    assert result.exit_code != 0
    assert "Failed to stop timer" in result.output


# ===========================================================================
# timer spent
# ===========================================================================


def test_timer_spent_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` shows hours in table format."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 1.5
    result = _invoke(runner, mock_config, mock_client, ["timer", "spent", "7"])
    assert result.exit_code == 0
    assert "1.5" in result.output
    assert "7" in result.output


def test_timer_spent_zero(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` shows 0.0 when no time tracked."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 0.0
    result = _invoke(runner, mock_config, mock_client, ["timer", "spent", "7"])
    assert result.exit_code == 0
    assert "0.0" in result.output


def test_timer_spent_zero_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` shows 0.0 in JSON format when no time tracked."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 0.0
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "timer", "spent", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["hours_spent"] == "0.0"


def test_timer_spent_zero_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` shows 0.0 in CSV format when no time tracked."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 0.0
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "timer", "spent", "7"])
    assert result.exit_code == 0
    assert "0.0" in result.output


def test_timer_spent_zero_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` renders cleanly in quiet mode when zero time tracked."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 0.0
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "timer", "spent", "7"])
    assert result.exit_code == 0


def test_timer_spent_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` renders in JSON format."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 2.25
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "timer", "spent", "7"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["hours_spent"] == "2.25"
    assert data[0]["subtask_id"] == "7"


def test_timer_spent_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` renders in CSV format."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 1.5
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "timer", "spent", "7"])
    assert result.exit_code == 0
    assert "subtask_id" in result.output
    assert "hours_spent" in result.output
    assert "1.5" in result.output


def test_timer_spent_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` renders in quiet mode."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 1.5
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "timer", "spent", "7"])
    assert result.exit_code == 0


def test_timer_spent_with_user_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` passes --user-id to the SDK."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.return_value = 1.5
    result = _invoke(runner, mock_config, mock_client, ["timer", "spent", "7", "--user-id", "1"])
    assert result.exit_code == 0
    mock_client.subtask_time_tracking.get_subtask_time_spent.assert_called_once_with(7, user_id=1)


def test_timer_spent_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``timer spent`` displays error on API failure."""
    mock_client.subtask_time_tracking.get_subtask_time_spent.side_effect = KanboardAPIError(
        "Server error", method="getSubtaskTimeSpent"
    )
    result = _invoke(runner, mock_config, mock_client, ["timer", "spent", "7"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# Help output
# ===========================================================================


def test_timer_help(runner: CliRunner) -> None:
    """``timer --help`` shows available subcommands."""
    result = runner.invoke(cli, ["timer", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "start" in result.output
    assert "stop" in result.output
    assert "spent" in result.output
