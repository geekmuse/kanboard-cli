"""CLI tests for ``kanboard group member`` subcommands (US-008)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError
from kanboard.models import Group, User
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

_SAMPLE_USER_DATA: dict = {
    "id": "10",
    "username": "alice",
    "name": "Alice Smith",
    "email": "alice@example.com",
    "role": "app-user",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}

_SAMPLE_USER_DATA_2: dict = {
    "id": "20",
    "username": "bob",
    "name": "Bob Jones",
    "email": "bob@example.com",
    "role": "app-admin",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}


def _make_group(data: dict | None = None) -> Group:
    """Build a Group from sample data."""
    return Group.from_api(data or _SAMPLE_GROUP_DATA)


def _make_user(data: dict | None = None) -> User:
    """Build a User from sample data."""
    return User.from_api(data or _SAMPLE_USER_DATA)


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
    """Return a MagicMock client with a group_members resource."""
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
# group member list
# ===========================================================================


def test_member_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member list`` renders members in table format."""
    mock_client.group_members.get_group_members.return_value = [_make_user()]
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "list", "1"])
    assert result.exit_code == 0
    assert "alice" in result.output
    mock_client.group_members.get_group_members.assert_called_once_with(1)


def test_member_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member list --output json`` renders members as JSON."""
    mock_client.group_members.get_group_members.return_value = [_make_user()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "group", "member", "list", "1"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["username"] == "alice"


def test_member_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member list --output csv`` renders members as CSV."""
    mock_client.group_members.get_group_members.return_value = [_make_user()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "group", "member", "list", "1"]
    )
    assert result.exit_code == 0
    assert "username" in result.output
    assert "alice" in result.output


def test_member_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member list --output quiet`` renders only IDs."""
    mock_client.group_members.get_group_members.return_value = [_make_user()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "group", "member", "list", "1"]
    )
    assert result.exit_code == 0
    assert "10" in result.output


def test_member_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member list`` renders cleanly when no members exist."""
    mock_client.group_members.get_group_members.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "list", "1"])
    assert result.exit_code == 0


def test_member_list_multiple(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member list`` renders multiple members."""
    mock_client.group_members.get_group_members.return_value = [
        _make_user(),
        _make_user(_SAMPLE_USER_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "list", "1"])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "bob" in result.output


# ===========================================================================
# group member groups
# ===========================================================================


def test_member_groups_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member groups`` renders groups in table format."""
    mock_client.group_members.get_member_groups.return_value = [_make_group()]
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "groups", "10"])
    assert result.exit_code == 0
    assert "Developers" in result.output
    mock_client.group_members.get_member_groups.assert_called_once_with(10)


def test_member_groups_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member groups --output json`` renders groups as JSON."""
    mock_client.group_members.get_member_groups.return_value = [_make_group()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "group", "member", "groups", "10"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Developers"


def test_member_groups_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member groups --output csv`` renders groups as CSV."""
    mock_client.group_members.get_member_groups.return_value = [_make_group()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "group", "member", "groups", "10"]
    )
    assert result.exit_code == 0
    assert "name" in result.output
    assert "Developers" in result.output


def test_member_groups_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member groups --output quiet`` renders only IDs."""
    mock_client.group_members.get_member_groups.return_value = [_make_group()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "group", "member", "groups", "10"]
    )
    assert result.exit_code == 0
    assert "1" in result.output


def test_member_groups_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member groups`` renders cleanly when user has no groups."""
    mock_client.group_members.get_member_groups.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "groups", "10"])
    assert result.exit_code == 0


def test_member_groups_multiple(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member groups`` renders multiple groups."""
    mock_client.group_members.get_member_groups.return_value = [
        _make_group(),
        _make_group(_SAMPLE_GROUP_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "groups", "10"])
    assert result.exit_code == 0
    assert "Developers" in result.output
    assert "Designers" in result.output


# ===========================================================================
# group member add
# ===========================================================================


def test_member_add_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member add`` adds a member and shows success message."""
    mock_client.group_members.add_group_member.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "add", "1", "10"])
    assert result.exit_code == 0
    assert "#10" in result.output
    assert "#1" in result.output
    mock_client.group_members.add_group_member.assert_called_once_with(1, 10)


def test_member_add_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member add --output json`` returns JSON success message."""
    mock_client.group_members.add_group_member.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "member", "add", "1", "10"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "added" in data["message"]


def test_member_add_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member add`` shows error on API failure."""
    mock_client.group_members.add_group_member.side_effect = KanboardAPIError(
        "Failed to add user", method="addGroupMember"
    )
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "add", "1", "10"])
    assert result.exit_code != 0


# ===========================================================================
# group member remove
# ===========================================================================


def test_member_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member remove --yes`` removes without prompt."""
    mock_client.group_members.remove_group_member.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["group", "member", "remove", "1", "10", "--yes"]
    )
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.group_members.remove_group_member.assert_called_once_with(1, 10)


def test_member_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member remove`` without --yes prompts and aborts on 'n'."""
    result = _invoke(
        runner, mock_config, mock_client, ["group", "member", "remove", "1", "10"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.group_members.remove_group_member.assert_not_called()


def test_member_remove_without_yes_confirms(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member remove`` without --yes prompts and proceeds on 'y'."""
    mock_client.group_members.remove_group_member.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["group", "member", "remove", "1", "10"], input="y\n"
    )
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.group_members.remove_group_member.assert_called_once_with(1, 10)


def test_member_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member remove --output json --yes`` returns JSON success message."""
    mock_client.group_members.remove_group_member.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "member", "remove", "1", "10", "--yes"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "removed" in data["message"]


# ===========================================================================
# group member check
# ===========================================================================


def test_member_check_is_member(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member check`` shows True when user is a member."""
    mock_client.group_members.is_group_member.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "check", "1", "10"])
    assert result.exit_code == 0
    mock_client.group_members.is_group_member.assert_called_once_with(1, 10)


def test_member_check_not_member(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member check`` shows False when user is not a member."""
    mock_client.group_members.is_group_member.return_value = False
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "check", "1", "10"])
    assert result.exit_code == 0


def test_member_check_json_is_member(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member check --output json`` returns JSON with is_member=True."""
    mock_client.group_members.is_group_member.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "member", "check", "1", "10"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["is_member"] is True
    assert data["group_id"] == 1
    assert data["user_id"] == 10


def test_member_check_json_not_member(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member check --output json`` returns JSON with is_member=False."""
    mock_client.group_members.is_group_member.return_value = False
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "group", "member", "check", "1", "10"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["is_member"] is False


# ===========================================================================
# help output
# ===========================================================================


def test_group_member_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group member --help`` shows available subcommands."""
    result = _invoke(runner, mock_config, mock_client, ["group", "member", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "groups" in result.output
    assert "add" in result.output
    assert "remove" in result.output
    assert "check" in result.output


def test_group_help_includes_member(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``group --help`` includes the member sub-group."""
    result = _invoke(runner, mock_config, mock_client, ["group", "--help"])
    assert result.exit_code == 0
    assert "member" in result.output
