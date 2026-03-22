"""CLI tests for ``kanboard swimlane`` subcommands (US-012)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Swimlane
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_SWIMLANE_DATA: dict = {
    "id": "3",
    "name": "Default",
    "project_id": "1",
    "position": "1",
    "is_active": "1",
    "description": "Default swimlane",
}

_SAMPLE_SWIMLANE_DATA_2: dict = {
    **_SAMPLE_SWIMLANE_DATA,
    "id": "4",
    "name": "High Priority",
    "position": "2",
}


def _make_swimlane(data: dict | None = None) -> Swimlane:
    """Build a Swimlane from sample data."""
    return Swimlane.from_api(data or _SAMPLE_SWIMLANE_DATA)


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
    """Return a MagicMock client with a swimlanes resource."""
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
# swimlane list
# ===========================================================================


def test_swimlane_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane list`` renders active swimlanes in table format."""
    mock_client.swimlanes.get_active_swimlanes.return_value = [_make_swimlane()]
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "list", "1"])
    assert result.exit_code == 0
    assert "Default" in result.output
    mock_client.swimlanes.get_active_swimlanes.assert_called_once_with(1)


def test_swimlane_list_all_flag(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane list --all`` calls get_all_swimlanes instead."""
    mock_client.swimlanes.get_all_swimlanes.return_value = [
        _make_swimlane(),
        _make_swimlane(_SAMPLE_SWIMLANE_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "list", "1", "--all"])
    assert result.exit_code == 0
    mock_client.swimlanes.get_all_swimlanes.assert_called_once_with(1)
    mock_client.swimlanes.get_active_swimlanes.assert_not_called()


def test_swimlane_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane list --output json`` renders swimlanes as a JSON array."""
    mock_client.swimlanes.get_active_swimlanes.return_value = [_make_swimlane()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "swimlane", "list", "1"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Default"
    assert data[0]["id"] == 3


def test_swimlane_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane list --output csv`` renders swimlanes as CSV with a header row."""
    mock_client.swimlanes.get_active_swimlanes.return_value = [_make_swimlane()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "swimlane", "list", "1"])
    assert result.exit_code == 0
    assert "Default" in result.output
    assert "name" in result.output  # header row


def test_swimlane_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane list --output quiet`` prints only swimlane IDs."""
    mock_client.swimlanes.get_active_swimlanes.return_value = [
        _make_swimlane(),
        _make_swimlane(_SAMPLE_SWIMLANE_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "swimlane", "list", "1"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "3" in lines
    assert "4" in lines


def test_swimlane_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane list`` with no swimlanes exits 0 cleanly."""
    mock_client.swimlanes.get_active_swimlanes.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "list", "1"])
    assert result.exit_code == 0


def test_swimlane_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on swimlane list exits non-zero."""
    mock_client.swimlanes.get_active_swimlanes.side_effect = KanboardAPIError(
        "getActiveSwimlanes failed", method="getActiveSwimlanes", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# swimlane get
# ===========================================================================


def test_swimlane_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane get`` exits 0 in table format and calls get_swimlane."""
    mock_client.swimlanes.get_swimlane.return_value = _make_swimlane()
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "get", "3"])
    assert result.exit_code == 0
    mock_client.swimlanes.get_swimlane.assert_called_once_with(3)


def test_swimlane_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane get --output json`` renders a single JSON object."""
    mock_client.swimlanes.get_swimlane.return_value = _make_swimlane()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "swimlane", "get", "3"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["name"] == "Default"
    assert data["id"] == 3


def test_swimlane_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane get`` with unknown ID exits non-zero."""
    mock_client.swimlanes.get_swimlane.side_effect = KanboardNotFoundError(
        "Swimlane 99 not found",
        method="getSwimlane",
        code=None,
        resource="Swimlane",
        identifier=99,
    )
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# swimlane get-by-name
# ===========================================================================


def test_swimlane_get_by_name_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane get-by-name`` exits 0 and calls get_swimlane_by_name."""
    mock_client.swimlanes.get_swimlane_by_name.return_value = _make_swimlane()
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "get-by-name", "1", "Default"])
    assert result.exit_code == 0
    mock_client.swimlanes.get_swimlane_by_name.assert_called_once_with(1, "Default")


def test_swimlane_get_by_name_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane get-by-name --output json`` renders a single JSON object."""
    mock_client.swimlanes.get_swimlane_by_name.return_value = _make_swimlane()
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "swimlane", "get-by-name", "1", "Default"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Default"


def test_swimlane_get_by_name_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane get-by-name`` with unknown name exits non-zero."""
    mock_client.swimlanes.get_swimlane_by_name.side_effect = KanboardNotFoundError(
        "Swimlane 'Unknown' not found in project 1",
        method="getSwimlaneByName",
        code=None,
        resource="Swimlane",
        identifier="Unknown",
    )
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "get-by-name", "1", "Unknown"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# swimlane add
# ===========================================================================


def test_swimlane_add_minimal(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane add`` with project_id and name creates a swimlane."""
    mock_client.swimlanes.add_swimlane.return_value = 5
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "add", "1", "High Priority"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.swimlanes.add_swimlane.assert_called_once_with(1, "High Priority")


def test_swimlane_add_with_description(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane add --description`` passes description kwarg to the SDK."""
    mock_client.swimlanes.add_swimlane.return_value = 6
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["swimlane", "add", "1", "Low Priority", "--description", "Non-urgent work"],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.swimlanes.add_swimlane.call_args
    assert kwargs["description"] == "Non-urgent work"


def test_swimlane_add_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane add --output json`` emits JSON success object."""
    mock_client.swimlanes.add_swimlane.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "swimlane", "add", "1", "Archive"],
    )
    assert result.exit_code == 0
    assert '"status"' in result.output
    assert '"ok"' in result.output


def test_swimlane_add_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on swimlane add exits non-zero."""
    mock_client.swimlanes.add_swimlane.side_effect = KanboardAPIError(
        "addSwimlane failed", method="addSwimlane", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "add", "1", "Bad"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# swimlane update
# ===========================================================================


def test_swimlane_update_name_only(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane update`` with required args calls update_swimlane."""
    mock_client.swimlanes.update_swimlane.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["swimlane", "update", "1", "3", "Renamed Lane"]
    )
    assert result.exit_code == 0
    assert "updated" in result.output
    mock_client.swimlanes.update_swimlane.assert_called_once_with(1, 3, "Renamed Lane")


def test_swimlane_update_with_description(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane update --description`` passes description kwarg to the SDK."""
    mock_client.swimlanes.update_swimlane.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["swimlane", "update", "1", "3", "Critical Path", "--description", "Top priority"],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.swimlanes.update_swimlane.call_args
    assert kwargs["description"] == "Top priority"


def test_swimlane_update_json_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane update --output json`` emits JSON success."""
    mock_client.swimlanes.update_swimlane.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "swimlane", "update", "1", "3", "X"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


def test_swimlane_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on update exits non-zero."""
    mock_client.swimlanes.update_swimlane.side_effect = KanboardAPIError(
        "updateSwimlane failed", method="updateSwimlane", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "update", "1", "3", "Fail"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# swimlane remove
# ===========================================================================


def test_swimlane_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane remove --yes`` deletes without prompting."""
    mock_client.swimlanes.remove_swimlane.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "remove", "1", "3", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.swimlanes.remove_swimlane.assert_called_once_with(1, 3)


def test_swimlane_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane remove`` without --yes and declining aborts; SDK not called."""
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "remove", "1", "3"])
    assert result.exit_code != 0
    mock_client.swimlanes.remove_swimlane.assert_not_called()


def test_swimlane_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane remove`` with interactive 'y' answer removes the swimlane."""
    mock_client.swimlanes.remove_swimlane.return_value = True
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["swimlane", "remove", "1", "3"], input="y\n")
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.swimlanes.remove_swimlane.assert_called_once_with(1, 3)


def test_swimlane_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane remove --yes --output json`` emits JSON success."""
    mock_client.swimlanes.remove_swimlane.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "swimlane", "remove", "1", "3", "--yes"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# swimlane enable
# ===========================================================================


def test_swimlane_enable(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane enable`` calls enable_swimlane and prints confirmation."""
    mock_client.swimlanes.enable_swimlane.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "enable", "1", "3"])
    assert result.exit_code == 0
    assert "enabled" in result.output
    mock_client.swimlanes.enable_swimlane.assert_called_once_with(1, 3)


def test_swimlane_enable_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane enable --output json`` emits JSON success."""
    mock_client.swimlanes.enable_swimlane.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "swimlane", "enable", "1", "3"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# swimlane disable
# ===========================================================================


def test_swimlane_disable(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane disable`` calls disable_swimlane and prints confirmation."""
    mock_client.swimlanes.disable_swimlane.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "disable", "1", "3"])
    assert result.exit_code == 0
    assert "disabled" in result.output
    mock_client.swimlanes.disable_swimlane.assert_called_once_with(1, 3)


def test_swimlane_disable_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane disable --output json`` emits JSON success."""
    mock_client.swimlanes.disable_swimlane.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "swimlane", "disable", "1", "3"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# swimlane move
# ===========================================================================


def test_swimlane_move(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane move`` calls change_swimlane_position and prints confirmation."""
    mock_client.swimlanes.change_swimlane_position.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["swimlane", "move", "1", "3", "2"])
    assert result.exit_code == 0
    assert "moved" in result.output
    mock_client.swimlanes.change_swimlane_position.assert_called_once_with(1, 3, 2)


def test_swimlane_move_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``swimlane move --output json`` emits JSON success."""
    mock_client.swimlanes.change_swimlane_position.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "swimlane", "move", "1", "3", "1"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# --help smoke tests
# ===========================================================================


@pytest.mark.parametrize(
    "subcommand",
    ["list", "get", "get-by-name", "add", "update", "remove", "enable", "disable", "move"],
)
def test_swimlane_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Every swimlane subcommand must respond to --help with exit 0."""
    from kanboard.exceptions import KanboardConfigError

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("x", field="url"),
    ):
        result = runner.invoke(cli, ["swimlane", subcommand, "--help"])
    assert result.exit_code == 0, (
        f"'swimlane {subcommand} --help' exited {result.exit_code}: {result.output}"
    )
