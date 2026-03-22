"""CLI tests for ``kanboard me`` subcommands (US-012).

All commands raise KanboardAuthError because User API auth is not yet
implemented.  Tests verify the error message is displayed clearly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAuthError
from kanboard_cli.main import cli

_AUTH_MSG = (
    "The 'me' endpoints require User API authentication "
    "(username + password). JSON-RPC API token auth is not supported "
    "for these methods. User API auth will be available in a future release."
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
    """Return a minimal resolved config."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
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


def test_me_default_mentions_json_rpc(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``kanboard me`` error mentions JSON-RPC token is not supported."""
    result = _invoke(runner, mock_config, mock_client, ["me"])
    assert "JSON-RPC API token" in result.output


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
# Error message quality
# ===========================================================================


def test_all_commands_mention_future_release(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """All commands mention the feature will be available in a future release."""
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
        assert "future release" in result.output, (
            f"Command {cmd!r} did not mention 'future release'"
        )
