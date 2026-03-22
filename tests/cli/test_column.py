"""CLI tests for ``kanboard column`` subcommands (US-011)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Column
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_COLUMN_DATA: dict = {
    "id": "1",
    "title": "Backlog",
    "project_id": "1",
    "task_limit": "0",
    "position": "1",
    "description": "Initial backlog column",
    "hide_in_dashboard": "0",
}

_SAMPLE_COLUMN_DATA_2: dict = {
    **_SAMPLE_COLUMN_DATA,
    "id": "2",
    "title": "In Progress",
    "position": "2",
}


def _make_column(data: dict | None = None) -> Column:
    """Build a Column from sample data."""
    return Column.from_api(data or _SAMPLE_COLUMN_DATA)


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
    """Return a MagicMock client with a columns resource."""
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
# column list
# ===========================================================================


def test_column_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column list`` renders columns in table format."""
    mock_client.columns.get_columns.return_value = [_make_column()]
    result = _invoke(runner, mock_config, mock_client, ["column", "list", "1"])
    assert result.exit_code == 0
    assert "Backlog" in result.output
    mock_client.columns.get_columns.assert_called_once_with(1)


def test_column_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column list --output json`` renders columns as a JSON array."""
    mock_client.columns.get_columns.return_value = [_make_column()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "column", "list", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Backlog"
    assert data[0]["id"] == 1


def test_column_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column list --output csv`` renders columns as CSV with header."""
    mock_client.columns.get_columns.return_value = [_make_column()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "column", "list", "1"])
    assert result.exit_code == 0
    assert "Backlog" in result.output
    assert "title" in result.output  # header row


def test_column_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column list --output quiet`` prints only column IDs."""
    mock_client.columns.get_columns.return_value = [
        _make_column(),
        _make_column(_SAMPLE_COLUMN_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "column", "list", "1"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "1" in lines
    assert "2" in lines


def test_column_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column list`` with no columns exits 0 cleanly."""
    mock_client.columns.get_columns.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["column", "list", "1"])
    assert result.exit_code == 0


def test_column_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on column list exits non-zero."""
    mock_client.columns.get_columns.side_effect = KanboardAPIError(
        "getColumns failed", method="getColumns", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["column", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# column get
# ===========================================================================


def test_column_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column get`` exits 0 in table format and calls get_column."""
    mock_client.columns.get_column.return_value = _make_column()
    result = _invoke(runner, mock_config, mock_client, ["column", "get", "1"])
    assert result.exit_code == 0
    mock_client.columns.get_column.assert_called_once_with(1)


def test_column_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column get --output json`` renders a single JSON object."""
    mock_client.columns.get_column.return_value = _make_column()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "column", "get", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["title"] == "Backlog"
    assert data["id"] == 1


def test_column_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column get`` with unknown ID exits non-zero."""
    mock_client.columns.get_column.side_effect = KanboardNotFoundError(
        "Column 99 not found",
        method="getColumn",
        code=None,
        resource="Column",
        identifier=99,
    )
    result = _invoke(runner, mock_config, mock_client, ["column", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# column add
# ===========================================================================


def test_column_add_minimal(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column add`` with project_id and title creates a column."""
    mock_client.columns.add_column.return_value = 3
    result = _invoke(runner, mock_config, mock_client, ["column", "add", "1", "In Review"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.columns.add_column.assert_called_once_with(1, "In Review")


def test_column_add_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column add`` passes task-limit and description options to the SDK."""
    mock_client.columns.add_column.return_value = 4
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "column",
            "add",
            "1",
            "Done",
            "--task-limit",
            "20",
            "--description",
            "Completed tasks",
        ],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.columns.add_column.call_args
    assert kwargs["task_limit"] == 20
    assert kwargs["description"] == "Completed tasks"


def test_column_add_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column add --output json`` emits JSON success object."""
    mock_client.columns.add_column.return_value = 5
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "column", "add", "1", "Archived"],
    )
    assert result.exit_code == 0
    assert '"status"' in result.output
    assert '"ok"' in result.output


def test_column_add_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on column add exits non-zero."""
    mock_client.columns.add_column.side_effect = KanboardAPIError(
        "addColumn failed", method="addColumn", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["column", "add", "1", "Bad"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# column update
# ===========================================================================


def test_column_update_title_only(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column update`` with just a title calls update_column with that title."""
    mock_client.columns.update_column.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["column", "update", "1", "Renamed Column"])
    assert result.exit_code == 0
    assert "updated" in result.output
    mock_client.columns.update_column.assert_called_once_with(1, "Renamed Column")


def test_column_update_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column update`` passes task-limit and description options to the SDK."""
    mock_client.columns.update_column.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "column",
            "update",
            "1",
            "WIP",
            "--task-limit",
            "10",
            "--description",
            "Work in progress",
        ],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.columns.update_column.call_args
    assert kwargs["task_limit"] == 10
    assert kwargs["description"] == "Work in progress"


def test_column_update_json_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column update --output json`` emits JSON success."""
    mock_client.columns.update_column.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "column", "update", "1", "X"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


def test_column_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on update exits non-zero."""
    mock_client.columns.update_column.side_effect = KanboardAPIError(
        "updateColumn failed", method="updateColumn", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["column", "update", "1", "Fail"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# column remove
# ===========================================================================


def test_column_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column remove --yes`` deletes without prompting."""
    mock_client.columns.remove_column.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["column", "remove", "1", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.columns.remove_column.assert_called_once_with(1)


def test_column_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column remove`` without --yes and declining aborts; SDK not called."""
    result = _invoke(runner, mock_config, mock_client, ["column", "remove", "1"])
    assert result.exit_code != 0
    mock_client.columns.remove_column.assert_not_called()


def test_column_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column remove`` with interactive 'y' answer removes the column."""
    mock_client.columns.remove_column.return_value = True
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["column", "remove", "1"], input="y\n")
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.columns.remove_column.assert_called_once_with(1)


def test_column_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column remove --yes --output json`` emits JSON success."""
    mock_client.columns.remove_column.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "column", "remove", "1", "--yes"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# column move
# ===========================================================================


def test_column_move(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column move`` calls change_column_position and prints confirmation."""
    mock_client.columns.change_column_position.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["column", "move", "1", "5", "3"])
    assert result.exit_code == 0
    assert "moved" in result.output
    mock_client.columns.change_column_position.assert_called_once_with(1, 5, 3)


def test_column_move_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``column move --output json`` emits JSON success."""
    mock_client.columns.change_column_position.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "column", "move", "1", "2", "1"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# --help smoke tests
# ===========================================================================


@pytest.mark.parametrize("subcommand", ["list", "get", "add", "update", "remove", "move"])
def test_column_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Every column subcommand must respond to --help with exit 0."""
    from kanboard.exceptions import KanboardConfigError

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("x", field="url"),
    ):
        result = runner.invoke(cli, ["column", subcommand, "--help"])
    assert result.exit_code == 0, (
        f"'column {subcommand} --help' exited {result.exit_code}: {result.output}"
    )
