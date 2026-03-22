"""CLI tests for ``kanboard project-meta`` subcommands (US-003)."""

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
    """Return a MagicMock client with a project_metadata resource."""
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
# project-meta list
# ===========================================================================


def test_project_meta_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta list`` renders metadata in table format."""
    mock_client.project_metadata.get_project_metadata.return_value = {
        "owner": "alice",
        "priority": "high",
    }
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "list", "1"])
    assert result.exit_code == 0
    assert "owner" in result.output
    assert "alice" in result.output
    mock_client.project_metadata.get_project_metadata.assert_called_once_with(1)


def test_project_meta_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta list --output json`` renders metadata as a JSON array."""
    mock_client.project_metadata.get_project_metadata.return_value = {
        "owner": "alice",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project-meta", "list", "1"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["key"] == "owner"
    assert data[0]["value"] == "alice"


def test_project_meta_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta list --output csv`` renders metadata as CSV."""
    mock_client.project_metadata.get_project_metadata.return_value = {
        "owner": "alice",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "project-meta", "list", "1"]
    )
    assert result.exit_code == 0
    assert "key" in result.output  # header row
    assert "owner" in result.output
    assert "alice" in result.output


def test_project_meta_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta list --output quiet`` outputs nothing (no id field)."""
    mock_client.project_metadata.get_project_metadata.return_value = {
        "owner": "alice",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "project-meta", "list", "1"]
    )
    assert result.exit_code == 0


def test_project_meta_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta list`` with no metadata exits 0 cleanly."""
    mock_client.project_metadata.get_project_metadata.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "list", "1"])
    assert result.exit_code == 0


def test_project_meta_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on project-meta list exits non-zero."""
    mock_client.project_metadata.get_project_metadata.side_effect = KanboardAPIError(
        "getProjectMetadata failed", method="getProjectMetadata", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_project_meta_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-meta get
# ===========================================================================


def test_project_meta_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta get`` shows the metadata value in table format."""
    mock_client.project_metadata.get_project_metadata_by_name.return_value = "alice"
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "get", "1", "owner"])
    assert result.exit_code == 0
    assert "owner" in result.output
    assert "alice" in result.output
    mock_client.project_metadata.get_project_metadata_by_name.assert_called_once_with(1, "owner")


def test_project_meta_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta get --output json`` renders the value as a JSON object."""
    mock_client.project_metadata.get_project_metadata_by_name.return_value = "alice"
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-meta", "get", "1", "owner"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["key"] == "owner"
    assert data["value"] == "alice"


def test_project_meta_get_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta get --output csv`` renders as CSV."""
    mock_client.project_metadata.get_project_metadata_by_name.return_value = "alice"
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "csv", "project-meta", "get", "1", "owner"],
    )
    assert result.exit_code == 0
    assert "key" in result.output
    assert "owner" in result.output


def test_project_meta_get_empty_value(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta get`` with missing key returns empty value cleanly."""
    mock_client.project_metadata.get_project_metadata_by_name.return_value = ""
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "get", "1", "missing"])
    assert result.exit_code == 0


def test_project_meta_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-meta set
# ===========================================================================


def test_project_meta_set_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta set`` saves metadata and confirms."""
    mock_client.project_metadata.save_project_metadata.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project-meta", "set", "1", "owner", "alice"]
    )
    assert result.exit_code == 0
    assert "owner" in result.output
    mock_client.project_metadata.save_project_metadata.assert_called_once_with(
        1, {"owner": "alice"}
    )


def test_project_meta_set_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta set --output json`` renders confirmation as JSON."""
    mock_client.project_metadata.save_project_metadata.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-meta", "set", "1", "owner", "alice"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_project_meta_set_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta set`` exits non-zero on API error."""
    mock_client.project_metadata.save_project_metadata.side_effect = KanboardAPIError(
        "Failed to save metadata", method="saveProjectMetadata", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["project-meta", "set", "1", "owner", "alice"]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_project_meta_set_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta set --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "set", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-meta remove
# ===========================================================================


def test_project_meta_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta remove --yes`` removes without prompting."""
    mock_client.project_metadata.remove_project_metadata.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project-meta", "remove", "1", "owner", "--yes"]
    )
    assert result.exit_code == 0
    assert "owner" in result.output
    mock_client.project_metadata.remove_project_metadata.assert_called_once_with(1, "owner")


def test_project_meta_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta remove`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-meta", "remove", "1", "owner"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_client.project_metadata.remove_project_metadata.assert_not_called()


def test_project_meta_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta remove`` without --yes and answering 'y' proceeds."""
    mock_client.project_metadata.remove_project_metadata.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-meta", "remove", "1", "owner"],
        input="y\n",
    )
    assert result.exit_code == 0
    mock_client.project_metadata.remove_project_metadata.assert_called_once_with(1, "owner")


def test_project_meta_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-meta remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-meta", "remove", "--help"])
    assert result.exit_code == 0
