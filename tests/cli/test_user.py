"""CLI tests for ``kanboard user`` subcommands (US-016)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import User
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_USER_DATA: dict = {
    "id": "3",
    "username": "jdoe",
    "name": "John Doe",
    "email": "jdoe@example.com",
    "role": "app-user",
    "is_active": "1",
    "is_ldap_user": "0",
    "notification_method": "0",
    "avatar_path": None,
    "timezone": None,
    "language": None,
}

_SAMPLE_USER_DATA_2: dict = {
    **_SAMPLE_USER_DATA,
    "id": "4",
    "username": "jsmith",
    "name": "Jane Smith",
    "email": "jsmith@example.com",
}


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
    """Return a MagicMock client with a users resource."""
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
# user list
# ===========================================================================


def test_user_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user list`` renders users in table format."""
    mock_client.users.get_all_users.return_value = [_make_user()]
    result = _invoke(runner, mock_config, mock_client, ["user", "list"])
    assert result.exit_code == 0
    assert "jdoe" in result.output
    mock_client.users.get_all_users.assert_called_once_with()


def test_user_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user list --output json`` renders users as a JSON array."""
    mock_client.users.get_all_users.return_value = [_make_user()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "user", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 3
    assert data[0]["username"] == "jdoe"


def test_user_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user list --output csv`` renders users as CSV with a header row."""
    mock_client.users.get_all_users.return_value = [_make_user()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "user", "list"])
    assert result.exit_code == 0
    assert "jdoe" in result.output
    assert "id" in result.output  # header row


def test_user_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user list --output quiet`` prints only user IDs."""
    mock_client.users.get_all_users.return_value = [
        _make_user(),
        _make_user(_SAMPLE_USER_DATA_2),
    ]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "user", "list"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "3" in lines
    assert "4" in lines


def test_user_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user list`` with no users exits 0 cleanly."""
    mock_client.users.get_all_users.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["user", "list"])
    assert result.exit_code == 0


def test_user_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on user list exits non-zero."""
    mock_client.users.get_all_users.side_effect = KanboardAPIError(
        "getAllUsers failed", method="getAllUsers", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["user", "list"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_user_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user get
# ===========================================================================


def test_user_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get`` shows user details in table format."""
    mock_client.users.get_user.return_value = _make_user()
    result = _invoke(runner, mock_config, mock_client, ["user", "get", "3"])
    assert result.exit_code == 0
    assert "jdoe" in result.output
    mock_client.users.get_user.assert_called_once_with(3)


def test_user_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get --output json`` renders the user as a JSON object."""
    mock_client.users.get_user.return_value = _make_user()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "user", "get", "3"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 3
    assert data["username"] == "jdoe"


def test_user_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get`` with unknown ID exits non-zero with an error message."""
    mock_client.users.get_user.side_effect = KanboardNotFoundError(
        "User 99 not found", resource="User", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["user", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_user_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user get-by-name
# ===========================================================================


def test_user_get_by_name_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get-by-name`` shows user details in table format."""
    mock_client.users.get_user_by_name.return_value = _make_user()
    result = _invoke(runner, mock_config, mock_client, ["user", "get-by-name", "jdoe"])
    assert result.exit_code == 0
    assert "jdoe" in result.output
    mock_client.users.get_user_by_name.assert_called_once_with("jdoe")


def test_user_get_by_name_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get-by-name --output json`` renders the user as JSON."""
    mock_client.users.get_user_by_name.return_value = _make_user()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "user", "get-by-name", "jdoe"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["username"] == "jdoe"


def test_user_get_by_name_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get-by-name`` exits non-zero for unknown username."""
    mock_client.users.get_user_by_name.side_effect = KanboardNotFoundError(
        "User 'unknown' not found", resource="User", identifier="unknown"
    )
    result = _invoke(runner, mock_config, mock_client, ["user", "get-by-name", "unknown"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_user_get_by_name_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user get-by-name --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "get-by-name", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user create
# ===========================================================================


def test_user_create_with_password_option(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user create`` with --password creates a user without prompting."""
    mock_client.users.create_user.return_value = 5
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["user", "create", "newuser", "--password", "s3cret"],
    )
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.users.create_user.assert_called_once_with("newuser", "s3cret")


def test_user_create_with_all_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user create`` passes all optional fields to the SDK."""
    mock_client.users.create_user.return_value = 6
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "user",
            "create",
            "jdoe",
            "--password",
            "pass123",
            "--name",
            "John Doe",
            "--email",
            "jdoe@example.com",
            "--role",
            "app-admin",
        ],
    )
    assert result.exit_code == 0
    mock_client.users.create_user.assert_called_once_with(
        "jdoe", "pass123", name="John Doe", email="jdoe@example.com", role="app-admin"
    )


def test_user_create_password_prompt(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user create`` without --password prompts interactively."""
    mock_client.users.create_user.return_value = 7
    # Provide password twice — once for the prompt and once for confirmation.
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["user", "create", "prompted_user"],
        input="s3cret\ns3cret\n",
    )
    assert result.exit_code == 0
    mock_client.users.create_user.assert_called_once_with("prompted_user", "s3cret")


def test_user_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.users.create_user.side_effect = KanboardAPIError(
        "createUser failed", method="createUser", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["user", "create", "bad", "--password", "x"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_user_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user update
# ===========================================================================


def test_user_update_username(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user update --username`` updates the login name."""
    mock_client.users.update_user.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["user", "update", "3", "--username", "jdoe2"]
    )
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.users.update_user.assert_called_once_with(3, username="jdoe2")


def test_user_update_all_fields(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user update`` with all options passes them all to the SDK."""
    mock_client.users.update_user.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "user",
            "update",
            "3",
            "--name",
            "Jane Doe",
            "--email",
            "jane@example.com",
            "--role",
            "app-admin",
        ],
    )
    assert result.exit_code == 0
    mock_client.users.update_user.assert_called_once_with(
        3, name="Jane Doe", email="jane@example.com", role="app-admin"
    )


def test_user_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.users.update_user.side_effect = KanboardAPIError(
        "updateUser failed", method="updateUser", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["user", "update", "3", "--name", "X"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_user_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user remove
# ===========================================================================


def test_user_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user remove --yes`` removes without prompting."""
    mock_client.users.remove_user.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["user", "remove", "3", "--yes"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.users.remove_user.assert_called_once_with(3)


def test_user_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["user", "remove", "3"], input="n\n")
    assert result.exit_code != 0
    mock_client.users.remove_user.assert_not_called()


def test_user_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user remove`` without --yes and answering 'y' proceeds."""
    mock_client.users.remove_user.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["user", "remove", "3"], input="y\n")
    assert result.exit_code == 0
    mock_client.users.remove_user.assert_called_once_with(3)


def test_user_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "remove", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user enable
# ===========================================================================


def test_user_enable_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user enable`` enables a user and prints a success message."""
    mock_client.users.enable_user.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["user", "enable", "3"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.users.enable_user.assert_called_once_with(3)


def test_user_enable_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user enable --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "enable", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user disable
# ===========================================================================


def test_user_disable_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user disable`` disables a user and prints a success message."""
    mock_client.users.disable_user.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["user", "disable", "3"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.users.disable_user.assert_called_once_with(3)


def test_user_disable_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user disable --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "disable", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# user is-active
# ===========================================================================


def test_user_is_active_true(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user is-active`` reports an active user."""
    mock_client.users.is_active_user.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["user", "is-active", "3"])
    assert result.exit_code == 0
    assert "active" in result.output
    mock_client.users.is_active_user.assert_called_once_with(3)


def test_user_is_active_false(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user is-active`` reports an inactive user."""
    mock_client.users.is_active_user.return_value = False
    result = _invoke(runner, mock_config, mock_client, ["user", "is-active", "3"])
    assert result.exit_code == 0
    assert "inactive" in result.output


def test_user_is_active_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``user is-active --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["user", "is-active", "--help"])
    assert result.exit_code == 0
