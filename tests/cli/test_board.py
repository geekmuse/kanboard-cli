"""CLI tests for ``kanboard board`` subcommands (US-011)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_SAMPLE_COLUMN_DICT: dict = {
    "id": "1",
    "title": "Backlog",
    "position": "1",
    "task_limit": "0",
    "description": "Tasks not yet started",
    "hide_in_dashboard": "0",
    "swimlanes": [
        {
            "id": "1",
            "name": "Default",
            "tasks": [
                {"id": "10", "title": "Fix login bug"},
            ],
        }
    ],
}

_SAMPLE_BOARD: list[dict] = [_SAMPLE_COLUMN_DICT]


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
    """Return a MagicMock client with a board resource."""
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
# board show
# ===========================================================================


def test_board_show_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``board show`` renders board columns in table format."""
    mock_client.board.get_board.return_value = _SAMPLE_BOARD
    result = _invoke(runner, mock_config, mock_client, ["board", "show", "1"])
    assert result.exit_code == 0
    assert "Backlog" in result.output
    mock_client.board.get_board.assert_called_once_with(1)


def test_board_show_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``board show --output json`` renders full nested structure."""
    mock_client.board.get_board.return_value = _SAMPLE_BOARD
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "board", "show", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Backlog"
    # Full nested structure should be present in JSON mode
    assert "swimlanes" in data[0]


def test_board_show_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``board show --output csv`` renders top-level column fields as CSV."""
    mock_client.board.get_board.return_value = _SAMPLE_BOARD
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "board", "show", "1"])
    assert result.exit_code == 0
    assert "Backlog" in result.output
    assert "title" in result.output  # header row


def test_board_show_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``board show --output quiet`` prints only column IDs."""
    mock_client.board.get_board.return_value = _SAMPLE_BOARD
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "board", "show", "1"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "1" in lines


def test_board_show_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``board show`` with an empty board exits 0 cleanly."""
    mock_client.board.get_board.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["board", "show", "1"])
    assert result.exit_code == 0


def test_board_show_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on board show exits non-zero with an error message."""
    mock_client.board.get_board.side_effect = KanboardAPIError(
        "getBoard failed", method="getBoard", code=-1
    )
    result = _invoke(runner, mock_config, mock_client, ["board", "show", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# --help smoke tests
# ===========================================================================


@pytest.mark.parametrize("subcommand", ["show"])
def test_board_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Every board subcommand must respond to --help with exit 0."""
    from kanboard.exceptions import KanboardConfigError

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("x", field="url"),
    ):
        result = runner.invoke(cli, ["board", subcommand, "--help"])
    assert result.exit_code == 0, (
        f"'board {subcommand} --help' exited {result.exit_code}: {result.output}"
    )
