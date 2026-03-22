"""CLI tests for ``kanboard group`` subcommands (US-007)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Group
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_GROUP_DATA: dict = {
    "id": "1",
    "name": "Developers",
    "external_id": "",
}

_SAMPLE_GROUP_DATA_2: dict = {
    "id": "2",
    "name": "Designers",
    "external_id": "ldap-456",
}


def _make_group(data: dict | None = None) -> Group:
    """Build a Group from sample data."""
    return Group.from_api(data or _SAMPLE_GROUP_DATA)


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
    """Return a MagicMock client with a groups resource."""
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
# group list
# ===========================================================================


def test_group_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group list`` renders groups in table format."""
    mock_client.groups.get_all_groups.return_value = [_make_group()]
    result = _invoke(runner, mock_config, mock_client, ["group", "list"])
    assert result.exit_code == 0
    assert "Developers" in result.output
    mock_client.groups.get_all_groups.assert_called_once()


def test_group_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group list --output json`` renders groups as a JSON array."""
    mock_client.groups.get_all_groups.return_value = [_make_group()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "group", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Developers"


def test_group_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group list --output csv`` renders groups as CSV."""
    mock_client.groups.get_all_groups.return_value = [_make_group()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "group", "list"])
    assert result.exit_code == 0
    assert "id" in result.output
    assert "Developers" in result.output


def test_group_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group list --output quiet`` renders only IDs."""
    mock_client.groups.get_all_groups.return_value = [_make_group()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "group", "list"])
    assert result.exit_code == 0
    assert "1" in result.output


def test_group_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group list`` renders cleanly when no groups exist."""
    mock_client.groups.get_all_groups.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["group", "list"])
    assert result.exit_code == 0


def test_group_list_multiple(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group list`` renders multiple groups."""
    mock_client.groups.get_all_groups.return_value = [
        _make_group(),
        _make_group(_SAMPLE_GROUP_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["group", "list"])
    assert result.exit_code == 0
    assert "Developers" in result.output
    assert "Designers" in result.output


# ===========================================================================
# group get
# ===========================================================================


def test_group_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group get`` renders a single group in table format."""
    mock_client.groups.get_group.return_value = _make_group()
    result = _invoke(runner, mock_config, mock_client, ["group", "get", "1"])
    assert result.exit_code == 0
    assert "Developers" in result.output
    mock_client.groups.get_group.assert_called_once_with(1)


def test_group_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group get --output json`` renders a single group as JSON."""
    mock_client.groups.get_group.return_value = _make_group()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "group", "get", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Developers"


def test_group_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group get`` shows error when group is not found."""
    mock_client.groups.get_group.side_effect = KanboardNotFoundError(
        "Group 999 not found", resource="Group", identifier=999
    )
    result = _invoke(runner, mock_config, mock_client, ["group", "get", "999"])
    assert result.exit_code != 0
    assert "999" in result.output


# ===========================================================================
# group create
# ===========================================================================


def test_group_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group create`` creates a group and shows success message."""
    mock_client.groups.create_group.return_value = 5
    result = _invoke(runner, mock_config, mock_client, ["group", "create", "Testers"])
    assert result.exit_code == 0
    assert "Testers" in result.output
    assert "#5" in result.output
    mock_client.groups.create_group.assert_called_once_with("Testers")


def test_group_create_with_external_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group create --external-id`` passes external_id kwarg."""
    mock_client.groups.create_group.return_value = 6
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["group", "create", "External", "--external-id", "ldap-123"],
    )
    assert result.exit_code == 0
    assert "#6" in result.output
    mock_client.groups.create_group.assert_called_once_with("External", external_id="ldap-123")


def test_group_create_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group create --output json`` returns JSON success message."""
    mock_client.groups.create_group.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "create", "NewGroup"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "NewGroup" in data["message"]


def test_group_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group create`` shows error on API failure."""
    mock_client.groups.create_group.side_effect = KanboardAPIError(
        "Failed to create group", method="createGroup"
    )
    result = _invoke(runner, mock_config, mock_client, ["group", "create", "BadGroup"])
    assert result.exit_code != 0


# ===========================================================================
# group update
# ===========================================================================


def test_group_update_name(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group update --name`` updates the group name."""
    mock_client.groups.update_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["group", "update", "1", "--name", "New Name"],
    )
    assert result.exit_code == 0
    assert "updated" in result.output
    mock_client.groups.update_group.assert_called_once_with(1, name="New Name")


def test_group_update_external_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group update --external-id`` updates the external ID."""
    mock_client.groups.update_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["group", "update", "1", "--external-id", "ext-99"],
    )
    assert result.exit_code == 0
    mock_client.groups.update_group.assert_called_once_with(1, external_id="ext-99")


def test_group_update_both(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group update --name --external-id`` updates both fields."""
    mock_client.groups.update_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["group", "update", "1", "--name", "N", "--external-id", "E"],
    )
    assert result.exit_code == 0
    mock_client.groups.update_group.assert_called_once_with(1, name="N", external_id="E")


def test_group_update_no_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group update`` with no options shows error."""
    result = _invoke(runner, mock_config, mock_client, ["group", "update", "1"])
    assert result.exit_code != 0
    assert "at least one" in result.output.lower()


def test_group_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group update`` shows error on API failure."""
    mock_client.groups.update_group.side_effect = KanboardAPIError(
        "Failed to update group", method="updateGroup"
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["group", "update", "1", "--name", "Fail"],
    )
    assert result.exit_code != 0


def test_group_update_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group update --output json`` returns JSON success message."""
    mock_client.groups.update_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "update", "1", "--name", "X"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "updated" in data["message"]


# ===========================================================================
# group remove
# ===========================================================================


def test_group_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group remove --yes`` deletes without prompt."""
    mock_client.groups.remove_group.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["group", "remove", "1", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.groups.remove_group.assert_called_once_with(1)


def test_group_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group remove`` without --yes prompts and aborts on 'n'."""
    result = _invoke(runner, mock_config, mock_client, ["group", "remove", "1"], input="n\n")
    assert result.exit_code != 0
    mock_client.groups.remove_group.assert_not_called()


def test_group_remove_without_yes_confirms(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group remove`` without --yes prompts and proceeds on 'y'."""
    mock_client.groups.remove_group.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["group", "remove", "1"], input="y\n")
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.groups.remove_group.assert_called_once_with(1)


def test_group_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group remove --output json --yes`` returns JSON success message."""
    mock_client.groups.remove_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "remove", "1", "--yes"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "removed" in data["message"]


# ===========================================================================
# help output
# ===========================================================================


def test_group_help(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``group --help`` shows available subcommands."""
    result = _invoke(runner, mock_config, mock_client, ["group", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "create" in result.output
    assert "update" in result.output
    assert "remove" in result.output
