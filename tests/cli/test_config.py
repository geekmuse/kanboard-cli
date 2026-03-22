"""CLI tests for ``kanboard config`` subcommands (US-001)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import CONFIG_FILE, KanboardConfig
from kanboard.exceptions import (
    KanboardAPIError,
    KanboardConfigError,
    KanboardConnectionError,
)
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
        token="my-secret-token",
        profile="default",
        output_format="table",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock KanboardClient."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig | None,
    mock_client: MagicMock | None,
    args: list[str],
) -> object:
    """Invoke CLI with optionally patched config and client.

    When *mock_config* and *mock_client* are ``None`` the config resolution
    is made to raise :class:`~kanboard.exceptions.KanboardConfigError` so the
    CLI proceeds in config-less mode (``ctx.obj.config is None``).
    """
    if mock_config is not None and mock_client is not None:
        with (
            patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
            patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
        ):
            return runner.invoke(cli, args)
    else:
        with patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            side_effect=KanboardConfigError("no config", field="url"),
        ):
            return runner.invoke(cli, args)


# ===========================================================================
# config --help
# ===========================================================================


def test_config_help(runner: CliRunner) -> None:
    """``config --help`` shows all five subcommands."""
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    for sub in ("init", "show", "path", "profiles", "test"):
        assert sub in result.output


# ===========================================================================
# config path
# ===========================================================================


def test_config_path(runner: CliRunner) -> None:
    """``config path`` prints the config file path."""
    result = runner.invoke(cli, ["config", "path"])
    assert result.exit_code == 0
    assert str(CONFIG_FILE) in result.output


# ===========================================================================
# config init
# ===========================================================================


def test_config_init_creates_file(runner: CliRunner, tmp_path: Path) -> None:
    """``config init`` creates the config file with the prompted URL and token."""
    config_dir = tmp_path / ".config" / "kanboard"
    config_file = config_dir / "config.toml"

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_DIR", config_dir),
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            side_effect=KanboardConfigError("no config", field="url"),
        ),
    ):
        result = runner.invoke(
            cli,
            ["config", "init"],
            input="http://my.server/jsonrpc.php\nmysecrettoken\n",
        )

    assert result.exit_code == 0, result.output
    assert config_file.exists()
    with config_file.open("rb") as fh:
        data = tomllib.load(fh)
    assert data["profiles"]["default"]["url"] == "http://my.server/jsonrpc.php"
    assert data["profiles"]["default"]["token"] == "mysecrettoken"
    assert data["settings"]["default_profile"] == "default"


def test_config_init_creates_directory(runner: CliRunner, tmp_path: Path) -> None:
    """``config init`` creates the config directory when it does not exist."""
    config_dir = tmp_path / "nested" / "config" / "kanboard"
    config_file = config_dir / "config.toml"
    assert not config_dir.exists()

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_DIR", config_dir),
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            side_effect=KanboardConfigError("no config", field="url"),
        ),
    ):
        result = runner.invoke(
            cli,
            ["config", "init"],
            input="http://localhost/jsonrpc.php\ntoken123\n",
        )

    assert result.exit_code == 0, result.output
    assert config_dir.exists()
    assert config_file.exists()


def test_config_init_no_overwrite_without_force(runner: CliRunner, tmp_path: Path) -> None:
    """``config init`` refuses to overwrite an existing config without ``--force``."""
    config_dir = tmp_path / ".config" / "kanboard"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("existing = true")

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_DIR", config_dir),
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            side_effect=KanboardConfigError("no config", field="url"),
        ),
    ):
        result = runner.invoke(cli, ["config", "init"])

    assert result.exit_code != 0
    assert "already exists" in result.output or "--force" in result.output


def test_config_init_force_overwrites(runner: CliRunner, tmp_path: Path) -> None:
    """``config init --force`` replaces an existing config file."""
    config_dir = tmp_path / ".config" / "kanboard"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("old = true")

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_DIR", config_dir),
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            side_effect=KanboardConfigError("no config", field="url"),
        ),
    ):
        result = runner.invoke(
            cli,
            ["config", "init", "--force"],
            input="http://new.server/jsonrpc.php\nnewtoken\n",
        )

    assert result.exit_code == 0, result.output
    with config_file.open("rb") as fh:
        data = tomllib.load(fh)
    assert data["profiles"]["default"]["url"] == "http://new.server/jsonrpc.php"
    assert data["profiles"]["default"]["token"] == "newtoken"


def test_config_init_success_message(runner: CliRunner, tmp_path: Path) -> None:
    """``config init`` prints a success message after writing."""
    config_dir = tmp_path / ".config" / "kanboard"
    config_file = config_dir / "config.toml"

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_DIR", config_dir),
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch(
            "kanboard_cli.main.KanboardConfig.resolve",
            side_effect=KanboardConfigError("no config", field="url"),
        ),
    ):
        result = runner.invoke(
            cli,
            ["config", "init"],
            input="http://localhost/jsonrpc.php\ntoken\n",
        )

    assert result.exit_code == 0, result.output
    assert "Config written" in result.output


# ===========================================================================
# config show
# ===========================================================================


def test_config_show_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config show`` renders config in table format with token masked."""
    result = _invoke(runner, mock_config, mock_client, ["config", "show"])
    assert result.exit_code == 0
    assert "url" in result.output
    assert "http://kanboard.test/jsonrpc.php" in result.output
    # Token must be masked — raw value must not appear
    assert "my-secret-token" not in result.output
    # Last 4 chars of "my-secret-token" should be visible
    assert "oken" in result.output


def test_config_show_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config show`` renders in JSON format."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "config", "show"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    keys = {row["key"] for row in data}
    assert {"url", "token", "profile", "output_format"} <= keys
    token_row = next(r for r in data if r["key"] == "token")
    assert "my-secret-token" not in token_row["value"]
    assert token_row["value"].startswith("****")


def test_config_show_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config show`` renders in CSV format."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "config", "show"])
    assert result.exit_code == 0
    assert "key" in result.output
    assert "value" in result.output
    assert "url" in result.output


def test_config_show_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config show`` in quiet mode exits successfully."""
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "config", "show"])
    assert result.exit_code == 0


def test_config_show_no_config(runner: CliRunner) -> None:
    """``config show`` reports a clear error when no config is available."""
    result = _invoke(runner, None, None, ["config", "show"])
    assert result.exit_code != 0
    assert "No configuration" in result.output


def test_config_show_masks_short_token(runner: CliRunner, mock_client: MagicMock) -> None:
    """``config show`` masks tokens shorter than 5 characters as ``****``."""
    cfg = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="abc",
        profile="default",
        output_format="table",
    )
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=cfg),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "abc" not in result.output
    assert "****" in result.output


# ===========================================================================
# config profiles
# ===========================================================================


def test_config_profiles_table(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    tmp_path: Path,
) -> None:
    """``config profiles`` lists all profile names from the config file."""
    toml_content = (
        b"[profiles.default]\n"
        b'url = "http://localhost/jsonrpc.php"\n'
        b'token = "abc"\n'
        b"[profiles.work]\n"
        b'url = "https://work.example.com/jsonrpc.php"\n'
        b'token = "def"\n'
    )
    config_file = tmp_path / "config.toml"
    config_file.write_bytes(toml_content)

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["config", "profiles"])

    assert result.exit_code == 0
    assert "default" in result.output
    assert "work" in result.output


def test_config_profiles_json(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    tmp_path: Path,
) -> None:
    """``config profiles`` renders in JSON format."""
    toml_content = b'[profiles.default]\nurl = "http://localhost/jsonrpc.php"\ntoken = "abc"\n'
    config_file = tmp_path / "config.toml"
    config_file.write_bytes(toml_content)

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["--output", "json", "config", "profiles"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert any(r["profile"] == "default" for r in data)


def test_config_profiles_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config profiles`` handles a config file with no profiles cleanly."""
    with (
        patch(
            "kanboard_cli.commands.config_cmd._read_raw_config",
            return_value={},
        ),
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["config", "profiles"])
    assert result.exit_code == 0


def test_config_profiles_missing_file(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock, tmp_path: Path
) -> None:
    """``config profiles`` handles a missing config file cleanly."""
    config_file = tmp_path / "nonexistent.toml"

    with (
        patch("kanboard_cli.commands.config_cmd.CONFIG_FILE", config_file),
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["config", "profiles"])

    assert result.exit_code == 0


# ===========================================================================
# config test
# ===========================================================================


def test_config_test_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config test`` shows the server version on success."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["config", "test"])
    assert result.exit_code == 0
    assert "1.2.30" in result.output


def test_config_test_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config test`` renders in JSON format."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "config", "test"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["key"] == "server_version"
    assert data[0]["value"] == "1.2.30"


def test_config_test_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config test`` renders in CSV format."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "config", "test"])
    assert result.exit_code == 0
    assert "server_version" in result.output
    assert "1.2.30" in result.output


def test_config_test_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config test`` in quiet mode exits successfully."""
    mock_client.application.get_version.return_value = "1.2.30"
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "config", "test"])
    assert result.exit_code == 0


def test_config_test_connection_failure(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config test`` reports a clear error when the connection fails."""
    mock_client.application.get_version.side_effect = KanboardConnectionError(
        "Connection refused", url="http://kanboard.test/jsonrpc.php"
    )
    result = _invoke(runner, mock_config, mock_client, ["config", "test"])
    assert result.exit_code != 0
    assert "Connection failed" in result.output


def test_config_test_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``config test`` reports a clear error on API failure."""
    mock_client.application.get_version.side_effect = KanboardAPIError(
        "Unauthorized", method="getVersion"
    )
    result = _invoke(runner, mock_config, mock_client, ["config", "test"])
    assert result.exit_code != 0
    assert "Connection failed" in result.output


def test_config_test_no_config(runner: CliRunner) -> None:
    """``config test`` reports a clear error when no config is available."""
    result = _invoke(runner, None, None, ["config", "test"])
    assert result.exit_code != 0
    assert "No configuration" in result.output
