"""CLI tests for ``kanboard task-meta`` subcommands (US-004)."""

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
    """Return a MagicMock client with a task_metadata resource."""
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
# task-meta list
# ===========================================================================


def test_task_meta_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta list`` renders metadata in table format."""
    mock_client.task_metadata.get_task_metadata.return_value = {
        "priority": "high",
        "reviewer": "bob",
    }
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "list", "42"])
    assert result.exit_code == 0
    assert "priority" in result.output
    assert "high" in result.output
    mock_client.task_metadata.get_task_metadata.assert_called_once_with(42)


def test_task_meta_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta list --output json`` renders metadata as a JSON array."""
    mock_client.task_metadata.get_task_metadata.return_value = {
        "priority": "high",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-meta", "list", "42"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["key"] == "priority"
    assert data[0]["value"] == "high"


def test_task_meta_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta list --output csv`` renders metadata as CSV."""
    mock_client.task_metadata.get_task_metadata.return_value = {
        "priority": "high",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "task-meta", "list", "42"]
    )
    assert result.exit_code == 0
    assert "key" in result.output  # header row
    assert "priority" in result.output
    assert "high" in result.output


def test_task_meta_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta list --output quiet`` outputs nothing (no id field)."""
    mock_client.task_metadata.get_task_metadata.return_value = {
        "priority": "high",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "task-meta", "list", "42"]
    )
    assert result.exit_code == 0


def test_task_meta_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta list`` with no metadata exits 0 cleanly."""
    mock_client.task_metadata.get_task_metadata.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "list", "42"])
    assert result.exit_code == 0


def test_task_meta_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on task-meta list exits non-zero."""
    mock_client.task_metadata.get_task_metadata.side_effect = KanboardAPIError(
        "getTaskMetadata failed", method="getTaskMetadata", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "list", "42"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_meta_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-meta get
# ===========================================================================


def test_task_meta_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta get`` shows the metadata value in table format."""
    mock_client.task_metadata.get_task_metadata_by_name.return_value = "high"
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "get", "42", "priority"])
    assert result.exit_code == 0
    assert "priority" in result.output
    assert "high" in result.output
    mock_client.task_metadata.get_task_metadata_by_name.assert_called_once_with(42, "priority")


def test_task_meta_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta get --output json`` renders the value as a JSON object."""
    mock_client.task_metadata.get_task_metadata_by_name.return_value = "high"
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "task-meta", "get", "42", "priority"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["key"] == "priority"
    assert data["value"] == "high"


def test_task_meta_get_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta get --output csv`` renders as CSV."""
    mock_client.task_metadata.get_task_metadata_by_name.return_value = "high"
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "csv", "task-meta", "get", "42", "priority"],
    )
    assert result.exit_code == 0
    assert "key" in result.output
    assert "priority" in result.output


def test_task_meta_get_empty_value(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta get`` with missing key returns empty value cleanly."""
    mock_client.task_metadata.get_task_metadata_by_name.return_value = ""
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "get", "42", "missing"])
    assert result.exit_code == 0


def test_task_meta_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-meta set
# ===========================================================================


def test_task_meta_set_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta set`` saves metadata and confirms."""
    mock_client.task_metadata.save_task_metadata.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-meta", "set", "42", "priority", "high"]
    )
    assert result.exit_code == 0
    assert "priority" in result.output
    mock_client.task_metadata.save_task_metadata.assert_called_once_with(42, {"priority": "high"})


def test_task_meta_set_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta set --output json`` renders confirmation as JSON."""
    mock_client.task_metadata.save_task_metadata.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "task-meta", "set", "42", "priority", "high"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_task_meta_set_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta set`` exits non-zero on API error."""
    mock_client.task_metadata.save_task_metadata.side_effect = KanboardAPIError(
        "Failed to save metadata", method="saveTaskMetadata", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["task-meta", "set", "42", "priority", "high"]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_meta_set_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta set --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "set", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-meta remove
# ===========================================================================


def test_task_meta_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta remove --yes`` removes without prompting."""
    mock_client.task_metadata.remove_task_metadata.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-meta", "remove", "42", "priority", "--yes"]
    )
    assert result.exit_code == 0
    assert "priority" in result.output
    mock_client.task_metadata.remove_task_metadata.assert_called_once_with(42, "priority")


def test_task_meta_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta remove`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task-meta", "remove", "42", "priority"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_client.task_metadata.remove_task_metadata.assert_not_called()


def test_task_meta_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta remove`` without --yes and answering 'y' proceeds."""
    mock_client.task_metadata.remove_task_metadata.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task-meta", "remove", "42", "priority"],
        input="y\n",
    )
    assert result.exit_code == 0
    mock_client.task_metadata.remove_task_metadata.assert_called_once_with(42, "priority")


def test_task_meta_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-meta remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-meta", "remove", "--help"])
    assert result.exit_code == 0
