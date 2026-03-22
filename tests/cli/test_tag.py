"""CLI tests for ``kanboard tag`` subcommands (US-014)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError
from kanboard.models import Tag
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_TAG_DATA: dict = {
    "id": "5",
    "name": "urgent",
    "project_id": "1",
    "color_id": "red",
}

_SAMPLE_TAG_DATA_2: dict = {
    **_SAMPLE_TAG_DATA,
    "id": "6",
    "name": "bug",
    "color_id": "orange",
}


def _make_tag(data: dict | None = None) -> Tag:
    """Build a Tag from sample data."""
    return Tag.from_api(data or _SAMPLE_TAG_DATA)


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
    """Return a MagicMock client with a tags resource."""
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
# tag list
# ===========================================================================


def test_tag_list_all_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list`` (no --project-id) calls get_all_tags and renders in table."""
    mock_client.tags.get_all_tags.return_value = [_make_tag()]
    result = _invoke(runner, mock_config, mock_client, ["tag", "list"])
    assert result.exit_code == 0
    assert "urgent" in result.output
    mock_client.tags.get_all_tags.assert_called_once_with()
    mock_client.tags.get_tags_by_project.assert_not_called()


def test_tag_list_by_project(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list --project-id`` calls get_tags_by_project."""
    mock_client.tags.get_tags_by_project.return_value = [_make_tag()]
    result = _invoke(runner, mock_config, mock_client, ["tag", "list", "--project-id", "1"])
    assert result.exit_code == 0
    assert "urgent" in result.output
    mock_client.tags.get_tags_by_project.assert_called_once_with(1)
    mock_client.tags.get_all_tags.assert_not_called()


def test_tag_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list --output json`` renders tags as a JSON array."""
    mock_client.tags.get_all_tags.return_value = [_make_tag()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "tag", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 5
    assert data[0]["name"] == "urgent"


def test_tag_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list --output csv`` renders tags as CSV with a header row."""
    mock_client.tags.get_all_tags.return_value = [_make_tag()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "tag", "list"])
    assert result.exit_code == 0
    assert "urgent" in result.output
    assert "id" in result.output  # header row


def test_tag_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list --output quiet`` prints only tag IDs."""
    mock_client.tags.get_all_tags.return_value = [
        _make_tag(),
        _make_tag(_SAMPLE_TAG_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "tag", "list"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "5" in lines
    assert "6" in lines


def test_tag_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list`` with no tags exits 0 cleanly."""
    mock_client.tags.get_all_tags.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["tag", "list"])
    assert result.exit_code == 0


def test_tag_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# tag get
# ===========================================================================


def test_tag_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag get`` shows task tags in table format."""
    mock_client.tags.get_task_tags.return_value = {"5": "urgent", "6": "bug"}
    result = _invoke(runner, mock_config, mock_client, ["tag", "get", "42"])
    assert result.exit_code == 0
    mock_client.tags.get_task_tags.assert_called_once_with(42)


def test_tag_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag get --output json`` renders the task tags as a JSON object."""
    mock_client.tags.get_task_tags.return_value = {"5": "urgent"}
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "tag", "get", "42"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["5"] == "urgent"


def test_tag_get_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag get`` with no tags assigned exits 0 cleanly."""
    mock_client.tags.get_task_tags.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["tag", "get", "42"])
    assert result.exit_code == 0


def test_tag_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# tag create
# ===========================================================================


def test_tag_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag create`` creates a tag and prints the new ID."""
    mock_client.tags.create_tag.return_value = 5
    result = _invoke(runner, mock_config, mock_client, ["tag", "create", "1", "urgent"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.tags.create_tag.assert_called_once_with(1, "urgent")


def test_tag_create_with_color_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag create`` with --color-id passes it to the SDK."""
    mock_client.tags.create_tag.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["tag", "create", "1", "bug", "--color-id", "orange"],
    )
    assert result.exit_code == 0
    mock_client.tags.create_tag.assert_called_once_with(1, "bug", color_id="orange")


def test_tag_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.tags.create_tag.side_effect = KanboardAPIError(
        "createTag failed", method="createTag", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["tag", "create", "1", "urgent"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_tag_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# tag update
# ===========================================================================


def test_tag_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag update`` updates a tag and prints a success message."""
    mock_client.tags.update_tag.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["tag", "update", "5", "critical"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.tags.update_tag.assert_called_once_with(5, "critical")


def test_tag_update_with_color_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag update`` with --color-id passes it to the SDK."""
    mock_client.tags.update_tag.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["tag", "update", "5", "urgent", "--color-id", "yellow"],
    )
    assert result.exit_code == 0
    mock_client.tags.update_tag.assert_called_once_with(5, "urgent", color_id="yellow")


def test_tag_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.tags.update_tag.side_effect = KanboardAPIError(
        "updateTag failed", method="updateTag", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["tag", "update", "5", "critical"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_tag_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# tag remove
# ===========================================================================


def test_tag_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag remove --yes`` removes without prompting."""
    mock_client.tags.remove_tag.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["tag", "remove", "5", "--yes"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.tags.remove_tag.assert_called_once_with(5)


def test_tag_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "remove", "5"], input="n\n")
    assert result.exit_code != 0
    mock_client.tags.remove_tag.assert_not_called()


def test_tag_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag remove`` without --yes and answering 'y' proceeds."""
    mock_client.tags.remove_tag.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["tag", "remove", "5"], input="y\n")
    assert result.exit_code == 0
    mock_client.tags.remove_tag.assert_called_once_with(5)


def test_tag_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "remove", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# tag set
# ===========================================================================


def test_tag_set_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag set`` assigns tags to a task and prints a success message."""
    mock_client.tags.set_task_tags.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["tag", "set", "1", "42", "urgent", "bug"])
    assert result.exit_code == 0
    assert "42" in result.output
    mock_client.tags.set_task_tags.assert_called_once_with(1, 42, ["urgent", "bug"])


def test_tag_set_single_tag(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag set`` with a single tag assigns it correctly."""
    mock_client.tags.set_task_tags.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["tag", "set", "1", "42", "urgent"])
    assert result.exit_code == 0
    mock_client.tags.set_task_tags.assert_called_once_with(1, 42, ["urgent"])


def test_tag_set_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag set`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.tags.set_task_tags.side_effect = KanboardAPIError(
        "setTaskTags failed", method="setTaskTags", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["tag", "set", "1", "42", "urgent"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_tag_set_requires_tags(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag set`` without any tag names exits non-zero (required argument)."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "set", "1", "42"])
    assert result.exit_code != 0


def test_tag_set_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``tag set --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["tag", "set", "--help"])
    assert result.exit_code == 0
