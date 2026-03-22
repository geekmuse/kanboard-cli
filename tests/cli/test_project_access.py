"""CLI tests for ``kanboard project-access`` subcommands (US-006)."""

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
    """Return a MagicMock client with a project_permissions resource."""
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
# project-access list
# ===========================================================================


def test_list_table(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``project-access list`` renders project users in table format."""
    mock_client.project_permissions.get_project_users.return_value = {
        "1": "admin",
        "2": "alice",
    }
    result = _invoke(runner, mock_config, mock_client, ["project-access", "list", "1"])
    assert result.exit_code == 0
    assert "admin" in result.output
    assert "alice" in result.output
    mock_client.project_permissions.get_project_users.assert_called_once_with(1)


def test_list_json(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``project-access list --output json`` renders as JSON array."""
    mock_client.project_permissions.get_project_users.return_value = {
        "1": "admin",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project-access", "list", "1"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["user_id"] == "1"
    assert data[0]["username"] == "admin"


def test_list_csv(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``project-access list --output csv`` renders as CSV."""
    mock_client.project_permissions.get_project_users.return_value = {
        "1": "admin",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "project-access", "list", "1"]
    )
    assert result.exit_code == 0
    assert "user_id" in result.output
    assert "username" in result.output
    assert "admin" in result.output


def test_list_quiet(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``project-access list --output quiet`` outputs nothing (no id field)."""
    mock_client.project_permissions.get_project_users.return_value = {
        "1": "admin",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "project-access", "list", "1"]
    )
    assert result.exit_code == 0


def test_list_empty(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``project-access list`` with no users exits 0 cleanly."""
    mock_client.project_permissions.get_project_users.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["project-access", "list", "1"])
    assert result.exit_code == 0


def test_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on project-access list exits non-zero."""
    mock_client.project_permissions.get_project_users.side_effect = KanboardAPIError(
        "getProjectUsers failed", method="getProjectUsers", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project-access", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_list_help(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``project-access list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-access assignable
# ===========================================================================


def test_assignable_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access assignable`` renders assignable users in table format."""
    mock_client.project_permissions.get_assignable_users.return_value = {
        "1": "admin",
        "3": "bob",
    }
    result = _invoke(runner, mock_config, mock_client, ["project-access", "assignable", "1"])
    assert result.exit_code == 0
    assert "admin" in result.output
    assert "bob" in result.output
    mock_client.project_permissions.get_assignable_users.assert_called_once_with(1)


def test_assignable_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access assignable --output json`` renders as JSON."""
    mock_client.project_permissions.get_assignable_users.return_value = {
        "1": "admin",
    }
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "assignable", "1"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["user_id"] == "1"


def test_assignable_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access assignable --output csv`` renders as CSV."""
    mock_client.project_permissions.get_assignable_users.return_value = {
        "1": "admin",
    }
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "csv", "project-access", "assignable", "1"],
    )
    assert result.exit_code == 0
    assert "user_id" in result.output
    assert "admin" in result.output


def test_assignable_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access assignable`` with empty result exits 0."""
    mock_client.project_permissions.get_assignable_users.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["project-access", "assignable", "1"])
    assert result.exit_code == 0


def test_assignable_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access assignable --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "assignable", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-access add-user
# ===========================================================================


def test_add_user_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-user`` adds a user and confirms."""
    mock_client.project_permissions.add_project_user.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["project-access", "add-user", "1", "42"])
    assert result.exit_code == 0
    assert "42" in result.output
    mock_client.project_permissions.add_project_user.assert_called_once_with(1, 42)


def test_add_user_with_role(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-user --role`` passes role kwarg."""
    mock_client.project_permissions.add_project_user.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "add-user", "1", "42", "--role", "project-manager"],
    )
    assert result.exit_code == 0
    mock_client.project_permissions.add_project_user.assert_called_once_with(
        1, 42, role="project-manager"
    )


def test_add_user_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-user --output json`` renders confirmation as JSON."""
    mock_client.project_permissions.add_project_user.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "add-user", "1", "42"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_add_user_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-user`` exits non-zero on API error."""
    mock_client.project_permissions.add_project_user.side_effect = KanboardAPIError(
        "Failed to add user", method="addProjectUser", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project-access", "add-user", "1", "42"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_add_user_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-user --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "add-user", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-access add-group
# ===========================================================================


def test_add_group_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-group`` adds a group and confirms."""
    mock_client.project_permissions.add_project_group.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["project-access", "add-group", "1", "5"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.project_permissions.add_project_group.assert_called_once_with(1, 5)


def test_add_group_with_role(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-group --role`` passes role kwarg."""
    mock_client.project_permissions.add_project_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "add-group", "1", "5", "--role", "project-viewer"],
    )
    assert result.exit_code == 0
    mock_client.project_permissions.add_project_group.assert_called_once_with(
        1, 5, role="project-viewer"
    )


def test_add_group_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-group --output json`` renders JSON confirmation."""
    mock_client.project_permissions.add_project_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "add-group", "1", "5"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_add_group_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-group`` exits non-zero on API error."""
    mock_client.project_permissions.add_project_group.side_effect = KanboardAPIError(
        "Failed to add group", method="addProjectGroup", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project-access", "add-group", "1", "5"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_add_group_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access add-group --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "add-group", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-access remove-user
# ===========================================================================


def test_remove_user_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-user --yes`` removes without prompting."""
    mock_client.project_permissions.remove_project_user.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "remove-user", "1", "42", "--yes"],
    )
    assert result.exit_code == 0
    assert "42" in result.output
    mock_client.project_permissions.remove_project_user.assert_called_once_with(1, 42)


def test_remove_user_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-user`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "remove-user", "1", "42"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_client.project_permissions.remove_project_user.assert_not_called()


def test_remove_user_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-user`` answering 'y' interactively proceeds."""
    mock_client.project_permissions.remove_project_user.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "remove-user", "1", "42"],
        input="y\n",
    )
    assert result.exit_code == 0
    mock_client.project_permissions.remove_project_user.assert_called_once_with(1, 42)


def test_remove_user_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-user --output json`` renders JSON."""
    mock_client.project_permissions.remove_project_user.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "remove-user", "1", "42", "--yes"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_remove_user_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-user --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "remove-user", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-access remove-group
# ===========================================================================


def test_remove_group_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-group --yes`` removes without prompting."""
    mock_client.project_permissions.remove_project_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "remove-group", "1", "5", "--yes"],
    )
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.project_permissions.remove_project_group.assert_called_once_with(1, 5)


def test_remove_group_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-group`` without --yes and 'n' aborts."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "remove-group", "1", "5"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_client.project_permissions.remove_project_group.assert_not_called()


def test_remove_group_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-group`` answering 'y' proceeds."""
    mock_client.project_permissions.remove_project_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "remove-group", "1", "5"],
        input="y\n",
    )
    assert result.exit_code == 0
    mock_client.project_permissions.remove_project_group.assert_called_once_with(1, 5)


def test_remove_group_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-group --output json`` renders JSON."""
    mock_client.project_permissions.remove_project_group.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "remove-group", "1", "5", "--yes"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_remove_group_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access remove-group --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "remove-group", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-access set-user-role
# ===========================================================================


def test_set_user_role_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-user-role`` changes role and confirms."""
    mock_client.project_permissions.change_project_user_role.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "set-user-role", "1", "42", "project-manager"],
    )
    assert result.exit_code == 0
    assert "project-manager" in result.output
    mock_client.project_permissions.change_project_user_role.assert_called_once_with(
        1, 42, "project-manager"
    )


def test_set_user_role_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-user-role --output json`` renders JSON."""
    mock_client.project_permissions.change_project_user_role.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "set-user-role", "1", "42", "project-manager"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_set_user_role_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-user-role`` exits non-zero on API error."""
    mock_client.project_permissions.change_project_user_role.side_effect = KanboardAPIError(
        "Failed to change role", method="changeProjectUserRole", code=None
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "set-user-role", "1", "42", "project-manager"],
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_set_user_role_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-user-role --help`` exits cleanly."""
    result = _invoke(
        runner, mock_config, mock_client, ["project-access", "set-user-role", "--help"]
    )
    assert result.exit_code == 0


# ===========================================================================
# project-access set-group-role
# ===========================================================================


def test_set_group_role_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-group-role`` changes role and confirms."""
    mock_client.project_permissions.change_project_group_role.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "set-group-role", "1", "5", "project-viewer"],
    )
    assert result.exit_code == 0
    assert "project-viewer" in result.output
    mock_client.project_permissions.change_project_group_role.assert_called_once_with(
        1, 5, "project-viewer"
    )


def test_set_group_role_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-group-role --output json`` renders JSON."""
    mock_client.project_permissions.change_project_group_role.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "set-group-role", "1", "5", "project-viewer"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_set_group_role_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-group-role`` exits non-zero on API error."""
    mock_client.project_permissions.change_project_group_role.side_effect = KanboardAPIError(
        "Failed to change role", method="changeProjectGroupRole", code=None
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-access", "set-group-role", "1", "5", "project-viewer"],
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_set_group_role_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access set-group-role --help`` exits cleanly."""
    result = _invoke(
        runner, mock_config, mock_client, ["project-access", "set-group-role", "--help"]
    )
    assert result.exit_code == 0


# ===========================================================================
# project-access user-role
# ===========================================================================


def test_user_role_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access user-role`` shows the role in table format."""
    mock_client.project_permissions.get_project_user_role.return_value = "project-manager"
    result = _invoke(runner, mock_config, mock_client, ["project-access", "user-role", "1", "42"])
    assert result.exit_code == 0
    assert "project-manager" in result.output
    mock_client.project_permissions.get_project_user_role.assert_called_once_with(1, 42)


def test_user_role_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access user-role --output json`` renders as JSON."""
    mock_client.project_permissions.get_project_user_role.return_value = "project-manager"
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "project-access", "user-role", "1", "42"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["user_id"] == "42"
    assert data["role"] == "project-manager"


def test_user_role_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access user-role --output csv`` renders as CSV."""
    mock_client.project_permissions.get_project_user_role.return_value = "project-manager"
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "csv", "project-access", "user-role", "1", "42"],
    )
    assert result.exit_code == 0
    assert "user_id" in result.output
    assert "role" in result.output
    assert "project-manager" in result.output


def test_user_role_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access user-role`` with empty role exits 0."""
    mock_client.project_permissions.get_project_user_role.return_value = ""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "user-role", "1", "42"])
    assert result.exit_code == 0


def test_user_role_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-access user-role --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-access", "user-role", "--help"])
    assert result.exit_code == 0
