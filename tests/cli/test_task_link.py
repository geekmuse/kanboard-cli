"""CLI tests for ``kanboard task-link`` subcommands (US-017)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import TaskLink
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_TL_DATA: dict = {
    "id": "7",
    "task_id": "10",
    "opposite_task_id": "20",
    "link_id": "1",
}

_SAMPLE_TL_DATA_2: dict = {
    "id": "8",
    "task_id": "10",
    "opposite_task_id": "30",
    "link_id": "2",
}


def _make_task_link(data: dict | None = None) -> TaskLink:
    """Build a TaskLink from sample data."""
    return TaskLink.from_api(data or _SAMPLE_TL_DATA)


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
    """Return a MagicMock client with a task_links resource."""
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
# task-link list
# ===========================================================================


def test_task_link_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list`` renders task links in table format."""
    mock_client.task_links.get_all_task_links.return_value = [_make_task_link()]
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "10"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.get_all_task_links.assert_called_once_with(10)


def test_task_link_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --output json`` renders task links as a JSON array."""
    mock_client.task_links.get_all_task_links.return_value = [
        _make_task_link(),
        _make_task_link(_SAMPLE_TL_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-link", "list", "10"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 7
    assert data[0]["task_id"] == 10


def test_task_link_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --output csv`` renders task links as CSV with a header row."""
    mock_client.task_links.get_all_task_links.return_value = [_make_task_link()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "task-link", "list", "10"]
    )
    assert result.exit_code == 0
    assert "id" in result.output  # header row
    assert "7" in result.output


def test_task_link_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --output quiet`` prints only task link IDs."""
    mock_client.task_links.get_all_task_links.return_value = [
        _make_task_link(),
        _make_task_link(_SAMPLE_TL_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "task-link", "list", "10"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "7" in lines
    assert "8" in lines


def test_task_link_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list`` with no links exits 0 cleanly."""
    mock_client.task_links.get_all_task_links.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "10"])
    assert result.exit_code == 0


def test_task_link_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on task-link list exits non-zero."""
    mock_client.task_links.get_all_task_links.side_effect = KanboardAPIError(
        "getAllTaskLinks failed", method="getAllTaskLinks", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "10"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link get
# ===========================================================================


def test_task_link_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get`` shows task link details in table format."""
    mock_client.task_links.get_task_link_by_id.return_value = _make_task_link()
    result = _invoke(runner, mock_config, mock_client, ["task-link", "get", "7"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.get_task_link_by_id.assert_called_once_with(7)


def test_task_link_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get --output json`` renders the task link as a JSON object."""
    mock_client.task_links.get_task_link_by_id.return_value = _make_task_link()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-link", "get", "7"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 7
    assert data["task_id"] == 10
    assert data["opposite_task_id"] == 20
    assert data["link_id"] == 1


def test_task_link_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get`` with unknown ID exits non-zero with an error message."""
    mock_client.task_links.get_task_link_by_id.side_effect = KanboardNotFoundError(
        "TaskLink 99 not found", resource="TaskLink", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["task-link", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link create
# ===========================================================================


def test_task_link_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` creates a task link and prints the new ID."""
    mock_client.task_links.create_task_link.return_value = 7
    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.create_task_link.assert_called_once_with(10, 20, 1)


def test_task_link_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.task_links.create_task_link.side_effect = KanboardAPIError(
        "createTaskLink failed", method="createTaskLink", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link update
# ===========================================================================


def test_task_link_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link update`` updates a task link and prints a success message."""
    mock_client.task_links.update_task_link.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-link", "update", "7", "10", "30", "2"]
    )
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.update_task_link.assert_called_once_with(7, 10, 30, 2)


def test_task_link_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.task_links.update_task_link.side_effect = KanboardAPIError(
        "updateTaskLink failed", method="updateTaskLink", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["task-link", "update", "7", "10", "30", "2"]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link remove
# ===========================================================================


def test_task_link_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove --yes`` removes without prompting."""
    mock_client.task_links.remove_task_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "7", "--yes"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.remove_task_link.assert_called_once_with(7)


def test_task_link_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "7"], input="n\n")
    assert result.exit_code != 0
    mock_client.task_links.remove_task_link.assert_not_called()


def test_task_link_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove`` without --yes and answering 'y' proceeds."""
    mock_client.task_links.remove_task_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "7"], input="y\n")
    assert result.exit_code == 0
    mock_client.task_links.remove_task_link.assert_called_once_with(7)


def test_task_link_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "--help"])
    assert result.exit_code == 0
