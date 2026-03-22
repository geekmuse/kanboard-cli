"""CLI tests for ``kanboard app`` subcommands (US-013)."""

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
    """Return a MagicMock client with an application resource."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
) -> object:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args)


# ===========================================================================
# app version
# ===========================================================================


def test_app_version_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app version`` shows version in table format."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["app", "version"])
    assert result.exit_code == 0
    assert "1.2.30" in result.output


def test_app_version_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app version`` renders in JSON format."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "app", "version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["key"] == "version"
    assert data[0]["value"] == "1.2.30"


def test_app_version_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app version`` renders in CSV format."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "app", "version"])
    assert result.exit_code == 0
    assert "key" in result.output
    assert "value" in result.output
    assert "1.2.30" in result.output


def test_app_version_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app version`` renders in quiet mode."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "app", "version"])
    assert result.exit_code == 0


def test_app_version_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app version`` displays error on API failure."""
    mock_client.application.get_version.side_effect = KanboardAPIError(
        "Server error", method="getVersion"
    )
    result = _invoke(runner, mock_config, mock_client, ["app", "version"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# app timezone
# ===========================================================================


def test_app_timezone_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app timezone`` shows timezone in table format."""
    mock_client.application.get_timezone.return_value = "UTC"
    result = _invoke(runner, mock_config, mock_client, ["app", "timezone"])
    assert result.exit_code == 0
    assert "UTC" in result.output


def test_app_timezone_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app timezone`` renders in JSON format."""
    mock_client.application.get_timezone.return_value = "America/New_York"
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "app", "timezone"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["key"] == "timezone"
    assert data[0]["value"] == "America/New_York"


def test_app_timezone_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app timezone`` renders in CSV format."""
    mock_client.application.get_timezone.return_value = "UTC"
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "app", "timezone"])
    assert result.exit_code == 0
    assert "timezone" in result.output
    assert "UTC" in result.output


def test_app_timezone_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app timezone`` renders in quiet mode."""
    mock_client.application.get_timezone.return_value = "UTC"
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "app", "timezone"])
    assert result.exit_code == 0


def test_app_timezone_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app timezone`` displays error on API failure."""
    mock_client.application.get_timezone.side_effect = KanboardAPIError(
        "Server error", method="getTimezone"
    )
    result = _invoke(runner, mock_config, mock_client, ["app", "timezone"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# app colors
# ===========================================================================


def test_app_colors_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app colors`` shows colour definitions in table format."""
    mock_client.application.get_default_task_colors.return_value = {
        "yellow": {"name": "Yellow", "background": "#fdf8cd"},
        "blue": {"name": "Blue", "background": "#dce5f1"},
    }
    result = _invoke(runner, mock_config, mock_client, ["app", "colors"])
    assert result.exit_code == 0
    assert "yellow" in result.output
    assert "blue" in result.output


def test_app_colors_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app colors`` renders in JSON format."""
    mock_client.application.get_default_task_colors.return_value = {
        "yellow": {"name": "Yellow"},
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "app", "colors"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["color_id"] == "yellow"


def test_app_colors_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app colors`` renders in CSV format."""
    mock_client.application.get_default_task_colors.return_value = {
        "yellow": {"name": "Yellow"},
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "app", "colors"])
    assert result.exit_code == 0
    assert "color_id" in result.output
    assert "yellow" in result.output


def test_app_colors_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app colors`` renders in quiet mode."""
    mock_client.application.get_default_task_colors.return_value = {"yellow": {"name": "Yellow"}}
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "app", "colors"])
    assert result.exit_code == 0


def test_app_colors_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app colors`` handles empty response cleanly."""
    mock_client.application.get_default_task_colors.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["app", "colors"])
    assert result.exit_code == 0


def test_app_colors_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app colors`` displays error on API failure."""
    mock_client.application.get_default_task_colors.side_effect = KanboardAPIError(
        "Server error", method="getDefaultTaskColors"
    )
    result = _invoke(runner, mock_config, mock_client, ["app", "colors"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# app default-color
# ===========================================================================


def test_app_default_color_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app default-color`` shows default colour in table format."""
    mock_client.application.get_default_task_color.return_value = "yellow"
    result = _invoke(runner, mock_config, mock_client, ["app", "default-color"])
    assert result.exit_code == 0
    assert "yellow" in result.output


def test_app_default_color_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app default-color`` renders in JSON format."""
    mock_client.application.get_default_task_color.return_value = "yellow"
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "app", "default-color"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["key"] == "default_color"
    assert data[0]["value"] == "yellow"


def test_app_default_color_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app default-color`` renders in CSV format."""
    mock_client.application.get_default_task_color.return_value = "yellow"
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "app", "default-color"])
    assert result.exit_code == 0
    assert "default_color" in result.output
    assert "yellow" in result.output


def test_app_default_color_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app default-color`` renders in quiet mode."""
    mock_client.application.get_default_task_color.return_value = "yellow"
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "app", "default-color"]
    )
    assert result.exit_code == 0


def test_app_default_color_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app default-color`` displays error on API failure."""
    mock_client.application.get_default_task_color.side_effect = KanboardAPIError(
        "Server error", method="getDefaultTaskColor"
    )
    result = _invoke(runner, mock_config, mock_client, ["app", "default-color"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# app roles
# ===========================================================================


def test_app_roles_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app roles`` shows roles in table format."""
    mock_client.application.get_application_roles.return_value = {
        "app-admin": "Administrator",
        "app-user": "User",
    }
    mock_client.application.get_project_roles.return_value = {
        "project-manager": "Project Manager",
    }
    result = _invoke(runner, mock_config, mock_client, ["app", "roles"])
    assert result.exit_code == 0
    assert "app-admin" in result.output or "Administrator" in result.output
    assert "project-manager" in result.output or "Project Manager" in result.output


def test_app_roles_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app roles`` renders in JSON format."""
    mock_client.application.get_application_roles.return_value = {
        "app-admin": "Administrator",
    }
    mock_client.application.get_project_roles.return_value = {
        "project-manager": "Project Manager",
    }
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "app", "roles"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    scopes = [r["scope"] for r in data]
    assert "application" in scopes
    assert "project" in scopes


def test_app_roles_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app roles`` renders in CSV format."""
    mock_client.application.get_application_roles.return_value = {
        "app-admin": "Administrator",
    }
    mock_client.application.get_project_roles.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "app", "roles"])
    assert result.exit_code == 0
    assert "scope" in result.output
    assert "role_id" in result.output


def test_app_roles_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app roles`` renders in quiet mode."""
    mock_client.application.get_application_roles.return_value = {"app-admin": "Admin"}
    mock_client.application.get_project_roles.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "app", "roles"])
    assert result.exit_code == 0


def test_app_roles_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app roles`` handles empty response cleanly."""
    mock_client.application.get_application_roles.return_value = {}
    mock_client.application.get_project_roles.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["app", "roles"])
    assert result.exit_code == 0


def test_app_roles_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``app roles`` displays error on API failure."""
    mock_client.application.get_application_roles.side_effect = KanboardAPIError(
        "Server error", method="getApplicationRoles"
    )
    result = _invoke(runner, mock_config, mock_client, ["app", "roles"])
    assert result.exit_code != 0
    assert "Server error" in result.output


# ===========================================================================
# Help output
# ===========================================================================


def test_app_help(runner: CliRunner) -> None:
    """``app --help`` shows available subcommands."""
    result = runner.invoke(cli, ["app", "--help"])
    assert result.exit_code == 0
    assert "version" in result.output
    assert "timezone" in result.output
    assert "colors" in result.output
    assert "default-color" in result.output
    assert "roles" in result.output
