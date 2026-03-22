"""CLI tests for ``kanboard link`` subcommands (US-017)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Link
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_LINK_DATA: dict = {
    "id": "1",
    "label": "blocks",
    "opposite_id": "2",
}

_SAMPLE_LINK_DATA_2: dict = {
    "id": "2",
    "label": "is blocked by",
    "opposite_id": "1",
}


def _make_link(data: dict | None = None) -> Link:
    """Build a Link from sample data."""
    return Link.from_api(data or _SAMPLE_LINK_DATA)


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
    """Return a MagicMock client with a links resource."""
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
# link list
# ===========================================================================


def test_link_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link list`` renders link types in table format."""
    mock_client.links.get_all_links.return_value = [_make_link()]
    result = _invoke(runner, mock_config, mock_client, ["link", "list"])
    assert result.exit_code == 0
    assert "blocks" in result.output
    mock_client.links.get_all_links.assert_called_once_with()


def test_link_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link list --output json`` renders link types as a JSON array."""
    mock_client.links.get_all_links.return_value = [_make_link(), _make_link(_SAMPLE_LINK_DATA_2)]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "link", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 1
    assert data[0]["label"] == "blocks"


def test_link_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link list --output csv`` renders link types as CSV with a header row."""
    mock_client.links.get_all_links.return_value = [_make_link()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "link", "list"])
    assert result.exit_code == 0
    assert "blocks" in result.output
    assert "id" in result.output  # header row


def test_link_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link list --output quiet`` prints only link type IDs."""
    mock_client.links.get_all_links.return_value = [
        _make_link(),
        _make_link(_SAMPLE_LINK_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "link", "list"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "1" in lines
    assert "2" in lines


def test_link_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link list`` with no link types exits 0 cleanly."""
    mock_client.links.get_all_links.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["link", "list"])
    assert result.exit_code == 0


def test_link_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on link list exits non-zero."""
    mock_client.links.get_all_links.side_effect = KanboardAPIError(
        "getAllLinks failed", method="getAllLinks", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["link", "list"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_link_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["link", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# link get
# ===========================================================================


def test_link_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get`` shows link type details in table format."""
    mock_client.links.get_link_by_id.return_value = _make_link()
    result = _invoke(runner, mock_config, mock_client, ["link", "get", "1"])
    assert result.exit_code == 0
    assert "blocks" in result.output
    mock_client.links.get_link_by_id.assert_called_once_with(1)


def test_link_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get --output json`` renders the link type as a JSON object."""
    mock_client.links.get_link_by_id.return_value = _make_link()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "link", "get", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 1
    assert data["label"] == "blocks"


def test_link_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get`` with unknown ID exits non-zero with an error message."""
    mock_client.links.get_link_by_id.side_effect = KanboardNotFoundError(
        "Link 99 not found", resource="Link", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["link", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_link_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["link", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# link get-by-label
# ===========================================================================


def test_link_get_by_label_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get-by-label`` shows link type details in table format."""
    mock_client.links.get_link_by_label.return_value = _make_link()
    result = _invoke(runner, mock_config, mock_client, ["link", "get-by-label", "blocks"])
    assert result.exit_code == 0
    assert "blocks" in result.output
    mock_client.links.get_link_by_label.assert_called_once_with("blocks")


def test_link_get_by_label_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get-by-label --output json`` renders the link type as JSON."""
    mock_client.links.get_link_by_label.return_value = _make_link()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "link", "get-by-label", "blocks"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["label"] == "blocks"


def test_link_get_by_label_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get-by-label`` exits non-zero for unknown label."""
    mock_client.links.get_link_by_label.side_effect = KanboardNotFoundError(
        "Link with label 'unknown' not found", resource="Link", identifier="unknown"
    )
    result = _invoke(runner, mock_config, mock_client, ["link", "get-by-label", "unknown"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_link_get_by_label_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link get-by-label --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["link", "get-by-label", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# link create
# ===========================================================================


def test_link_create_label_only(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link create <label>`` creates a link type without an opposite label."""
    mock_client.links.create_link.return_value = 5
    result = _invoke(runner, mock_config, mock_client, ["link", "create", "duplicates"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.links.create_link.assert_called_once_with("duplicates")


def test_link_create_with_opposite_label(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link create`` with --opposite-label passes it to the SDK."""
    mock_client.links.create_link.return_value = 6
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["link", "create", "blocks", "--opposite-label", "is blocked by"],
    )
    assert result.exit_code == 0
    assert "6" in result.output
    mock_client.links.create_link.assert_called_once_with("blocks", opposite_label="is blocked by")


def test_link_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.links.create_link.side_effect = KanboardAPIError(
        "createLink failed", method="createLink", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["link", "create", "bad"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_link_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["link", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# link update
# ===========================================================================


def test_link_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link update`` updates the link type and prints a success message."""
    mock_client.links.update_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["link", "update", "1", "2", "blocks"])
    assert result.exit_code == 0
    assert "1" in result.output
    mock_client.links.update_link.assert_called_once_with(1, 2, "blocks")


def test_link_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.links.update_link.side_effect = KanboardAPIError(
        "updateLink failed", method="updateLink", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["link", "update", "1", "2", "blocks"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_link_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["link", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# link remove
# ===========================================================================


def test_link_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link remove --yes`` removes without prompting."""
    mock_client.links.remove_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["link", "remove", "5", "--yes"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.links.remove_link.assert_called_once_with(5)


def test_link_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["link", "remove", "5"], input="n\n")
    assert result.exit_code != 0
    mock_client.links.remove_link.assert_not_called()


def test_link_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link remove`` without --yes and answering 'y' proceeds."""
    mock_client.links.remove_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["link", "remove", "5"], input="y\n")
    assert result.exit_code == 0
    mock_client.links.remove_link.assert_called_once_with(5)


def test_link_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``link remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["link", "remove", "--help"])
    assert result.exit_code == 0
