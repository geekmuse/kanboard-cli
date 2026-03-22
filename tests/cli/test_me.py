"""CLI tests for ``kanboard me`` subcommands.

Covers:
- App auth mode: all commands display a clear KanboardAuthError message.
- User auth mode (--auth-mode user): commands succeed with mocked SDK.
- --auth-mode flag wiring (CLI → config → client).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAuthError
from kanboard.models import User
from kanboard_cli.main import cli

_AUTH_MSG = (
    "The 'me' endpoints require User API authentication "
    "(username + password). Application API token auth is not supported "
    "for these methods."
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def mock_config() -> KanboardConfig:
    """Return a minimal resolved config (app auth mode)."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
        auth_mode="app",
    )


@pytest.fixture()
def mock_config_user_auth() -> KanboardConfig:
    """Return a resolved config for user auth mode."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="",
        profile="default",
        output_format="table",
        auth_mode="user",
        username="admin",
        password="secret",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock client with a me resource that raises KanboardAuthError."""
    client = MagicMock()
    client.me.get_me.side_effect = KanboardAuthError(_AUTH_MSG)
    client.me.get_my_dashboard.side_effect = KanboardAuthError(_AUTH_MSG)
    client.me.get_my_activity_stream.side_effect = KanboardAuthError(_AUTH_MSG)
    client.me.get_my_projects.side_effect = KanboardAuthError(_AUTH_MSG)
    client.me.get_my_overdue_tasks.side_effect = KanboardAuthError(_AUTH_MSG)
    client.me.create_my_private_project.side_effect = KanboardAuthError(_AUTH_MSG)
    client.me.get_my_projects_list.side_effect = KanboardAuthError(_AUTH_MSG)
    return client


_SAMPLE_USER = User(
    id=1,
    username="admin",
    name="Admin User",
    email="admin@example.com",
    role="app-admin",
    is_active=True,
    is_ldap_user=False,
    notification_method=0,
    avatar_path=None,
    timezone=None,
    language=None,
)


@pytest.fixture()
def mock_client_user_auth() -> MagicMock:
    """Return a MagicMock client configured for successful user auth responses."""
    client = MagicMock()
    client.me.get_me.return_value = _SAMPLE_USER
    client.me.get_my_dashboard.return_value = {"projects": [], "tasks": [], "subtasks": []}
    client.me.get_my_activity_stream.return_value = [{"event_name": "task.open"}]
    client.me.get_my_projects.return_value = [{"id": "1", "name": "Alpha"}]
    client.me.get_my_overdue_tasks.return_value = [{"id": "3", "title": "Late task"}]
    client.me.create_my_private_project.return_value = 42
    client.me.get_my_projects_list.return_value = {"1": "Alpha"}
    return client


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


def _invoke_user(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
    args: list[str],
    input: str | None = None,
) -> object:
    """Invoke the CLI with user auth mode patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config_user_auth),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client_user_auth),
    ):
        return runner.invoke(cli, args, input=input)


# ===========================================================================
# kanboard me (default - show current user)
# ===========================================================================


def test_me_default_shows_auth_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me`` (no subcommand) displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["me"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_default_mentions_app_api_token(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me`` error mentions Application API token is not supported."""
    result = _invoke(runner, mock_config, mock_client, ["me"])
    assert "Application API token" in result.output


# ===========================================================================
# kanboard me dashboard
# ===========================================================================


def test_me_dashboard_shows_auth_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me dashboard`` displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["me", "dashboard"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


# ===========================================================================
# kanboard me activity
# ===========================================================================


def test_me_activity_shows_auth_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me activity`` displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["me", "activity"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


# ===========================================================================
# kanboard me projects
# ===========================================================================


def test_me_projects_shows_auth_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me projects`` displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["me", "projects"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


# ===========================================================================
# kanboard me overdue
# ===========================================================================


def test_me_overdue_shows_auth_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me overdue`` displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["me", "overdue"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


# ===========================================================================
# kanboard me create-project
# ===========================================================================


def test_me_create_project_shows_auth_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me create-project`` displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["me", "create-project", "Test"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_create_project_with_description(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me create-project`` with --description still raises auth error."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["me", "create-project", "Test", "--description", "A desc"],
    )
    assert result.exit_code != 0
    assert "User API authentication" in result.output


# ===========================================================================
# Help output
# ===========================================================================


def test_me_help(runner: CliRunner) -> None:
    """``kanboard me --help`` shows available subcommands."""
    result = runner.invoke(cli, ["me", "--help"])
    assert result.exit_code == 0
    assert "dashboard" in result.output
    assert "activity" in result.output
    assert "projects" in result.output
    assert "overdue" in result.output
    assert "create-project" in result.output


def test_me_dashboard_help(runner: CliRunner) -> None:
    """``kanboard me dashboard --help`` shows usage."""
    result = runner.invoke(cli, ["me", "dashboard", "--help"])
    assert result.exit_code == 0
    assert "dashboard" in result.output.lower()


def test_me_create_project_help(runner: CliRunner) -> None:
    """``kanboard me create-project --help`` shows NAME argument."""
    result = runner.invoke(cli, ["me", "create-project", "--help"])
    assert result.exit_code == 0
    assert "NAME" in result.output


# ===========================================================================
# Output format tests — verify auth error surfaces with all formats
# ===========================================================================


def test_me_default_json_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output json me`` still displays auth error."""
    mock_config = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="json",
    )
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "me"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_default_csv_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output csv me`` still displays auth error."""
    mock_config = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="csv",
    )
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "me"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_default_quiet_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output quiet me`` still displays auth error."""
    mock_config = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="quiet",
    )
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "me"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_dashboard_json_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output json me dashboard`` still displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "me", "dashboard"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_projects_csv_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output csv me projects`` still displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "me", "projects"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_overdue_quiet_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output quiet me overdue`` still displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "me", "overdue"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_activity_json_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output json me activity`` still displays auth error."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "me", "activity"])
    assert result.exit_code != 0
    assert "User API authentication" in result.output


def test_me_create_project_json_format(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard --output json me create-project`` still displays auth error."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "me", "create-project", "Test"],
    )
    assert result.exit_code != 0
    assert "User API authentication" in result.output


# ===========================================================================
# Error message quality
# ===========================================================================


def test_all_commands_mention_user_api_authentication(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """All app-auth commands mention User API authentication requirement."""
    commands = [
        ["me"],
        ["me", "dashboard"],
        ["me", "activity"],
        ["me", "projects"],
        ["me", "overdue"],
        ["me", "create-project", "Test"],
    ]
    for cmd in commands:
        result = _invoke(runner, mock_config, mock_client, cmd)
        assert "User API authentication" in result.output, (
            f"Command {cmd!r} did not mention 'User API authentication'"
        )


# ===========================================================================
# User auth mode — successful command invocations
# ===========================================================================


def test_me_default_user_auth_success(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me`` with user auth succeeds and shows user info."""
    result = _invoke_user(runner, mock_config_user_auth, mock_client_user_auth, ["me"])
    assert result.exit_code == 0
    assert "admin" in result.output


def test_me_dashboard_user_auth_success(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me dashboard`` with user auth exits 0."""
    result = _invoke_user(runner, mock_config_user_auth, mock_client_user_auth, ["me", "dashboard"])
    assert result.exit_code == 0


def test_me_activity_user_auth_success(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me activity`` with user auth exits 0."""
    result = _invoke_user(runner, mock_config_user_auth, mock_client_user_auth, ["me", "activity"])
    assert result.exit_code == 0


def test_me_projects_user_auth_success(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me projects`` with user auth exits 0."""
    result = _invoke_user(runner, mock_config_user_auth, mock_client_user_auth, ["me", "projects"])
    assert result.exit_code == 0


def test_me_overdue_user_auth_success(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me overdue`` with user auth exits 0."""
    result = _invoke_user(runner, mock_config_user_auth, mock_client_user_auth, ["me", "overdue"])
    assert result.exit_code == 0


def test_me_create_project_user_auth_success(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me create-project`` with user auth succeeds and prints ID."""
    result = _invoke_user(
        runner,
        mock_config_user_auth,
        mock_client_user_auth,
        ["me", "create-project", "My Private"],
    )
    assert result.exit_code == 0
    assert "42" in result.output


def test_me_create_project_user_auth_with_description(
    runner: CliRunner,
    mock_config_user_auth: KanboardConfig,
    mock_client_user_auth: MagicMock,
) -> None:
    """``kanboard me create-project --description`` with user auth succeeds."""
    result = _invoke_user(
        runner,
        mock_config_user_auth,
        mock_client_user_auth,
        ["me", "create-project", "My Private", "--description", "A desc"],
    )
    assert result.exit_code == 0
    assert "42" in result.output


# ===========================================================================
# --auth-mode flag wiring
# ===========================================================================


def test_auth_mode_flag_passed_to_config_resolve(runner: CliRunner) -> None:
    """--auth-mode user is forwarded to KanboardConfig.resolve()."""
    with patch("kanboard_cli.main.KanboardConfig.resolve") as mock_resolve:
        mock_resolve.side_effect = Exception("stop")
        runner.invoke(cli, ["--auth-mode", "user", "me"])
    call_kwargs = mock_resolve.call_args.kwargs
    assert call_kwargs.get("auth_mode") == "user"


def test_auth_mode_app_is_default_in_cli(runner: CliRunner) -> None:
    """Omitting --auth-mode passes None to KanboardConfig.resolve()."""
    with patch("kanboard_cli.main.KanboardConfig.resolve") as mock_resolve:
        mock_resolve.side_effect = Exception("stop")
        runner.invoke(cli, ["me"])
    call_kwargs = mock_resolve.call_args.kwargs
    # No explicit --auth-mode → None passed, config uses its own default
    assert call_kwargs.get("auth_mode") is None


def test_auth_mode_choice_validated(runner: CliRunner) -> None:
    """--auth-mode with invalid value is rejected by Click."""
    result = runner.invoke(cli, ["--auth-mode", "invalid", "me"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output or "invalid" in result.output.lower()
