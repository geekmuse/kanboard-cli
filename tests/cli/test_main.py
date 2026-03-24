"""Tests for the root CLI group and global options (US-009)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardConfigError
from kanboard_cli.main import AppContext, cli


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def mock_config() -> KanboardConfig:
    """Return a minimal resolved config for tests."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token-abc",
        profile="default",
        output_format="table",
    )


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------


def test_help_exits_zero(runner: CliRunner) -> None:
    """``kanboard --help`` must exit 0."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0


def test_help_shows_global_options(runner: CliRunner) -> None:
    """``--help`` output lists all global options."""
    result = runner.invoke(cli, ["--help"])
    assert "--url" in result.output
    assert "--token" in result.output
    assert "--profile" in result.output
    assert "--output" in result.output
    assert "--verbose" in result.output


def test_help_shows_command_groups(runner: CliRunner) -> None:
    """``--help`` output lists all registered command groups."""
    result = runner.invoke(cli, ["--help"])
    expected_groups = [
        "task",
        "project",
        "board",
        "column",
        "swimlane",
        "category",
        "comment",
        "subtask",
        "timer",
        "user",
        "me",
        "tag",
        "link",
        "task-link",
        "external-link",
        "group",
        "action",
        "project-file",
        "task-file",
        "project-meta",
        "task-meta",
        "project-access",
        "app",
        "config",
        "workflow",
    ]
    for name in expected_groups:
        assert name in result.output, f"Expected command group '{name}' in --help output"


def test_short_help_flag(runner: CliRunner) -> None:
    """-h must work as a shortcut for --help."""
    result = runner.invoke(cli, ["-h"])
    assert result.exit_code == 0
    assert "--url" in result.output


# ---------------------------------------------------------------------------
# Output choice option
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["table", "json", "csv", "quiet"])
def test_output_choice_valid(runner: CliRunner, fmt: str, mock_config: KanboardConfig) -> None:
    """--output accepts all valid format choices."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["--output", fmt, "--help"])
    assert result.exit_code == 0


def test_output_choice_invalid(runner: CliRunner) -> None:
    """--output rejects unknown formats."""
    # Invoke a real subcommand so Click validates options (--help short-circuits validation).
    result = runner.invoke(cli, ["--output", "yaml", "task", "--help"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_output_short_flag(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """-o is accepted as shorthand for --output."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["-o", "json", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# ctx.obj population — happy path
# ---------------------------------------------------------------------------


def test_ctx_obj_populated_on_success(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """When config resolves, ctx.obj has config and client set."""
    mock_client = MagicMock()
    captured: list[AppContext] = []

    import click

    @cli.command("_test_ctx")
    @click.pass_context
    def _test_ctx(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["_test_ctx"])

    cli.commands.pop("_test_ctx", None)  # cleanup

    assert result.exit_code == 0
    assert len(captured) == 1
    ctx_obj = captured[0]
    assert isinstance(ctx_obj, AppContext)
    assert ctx_obj.config is mock_config
    assert ctx_obj.client is mock_client


def test_ctx_obj_output_default(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """ctx.obj.output defaults to 'table'."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_out")
    @click.pass_context
    def _test_out(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["_test_out"])

    cli.commands.pop("_test_out", None)

    assert result.exit_code == 0
    assert captured[0].output == "table"


def test_ctx_obj_output_custom(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """ctx.obj.output reflects --output value."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_custom_out")
    @click.pass_context
    def _test_custom_out(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["--output", "json", "_test_custom_out"])

    cli.commands.pop("_test_custom_out", None)

    assert result.exit_code == 0
    assert captured[0].output == "json"


def test_ctx_obj_verbose_false_by_default(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """ctx.obj.verbose is False unless --verbose is given."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_verbose_off")
    @click.pass_context
    def _test_verbose_off(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["_test_verbose_off"])

    cli.commands.pop("_test_verbose_off", None)

    assert result.exit_code == 0
    assert captured[0].verbose is False


def test_ctx_obj_verbose_enabled(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """ctx.obj.verbose is True when --verbose / -v is given."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_verbose_on")
    @click.pass_context
    def _test_verbose_on(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["-v", "_test_verbose_on"])

    cli.commands.pop("_test_verbose_on", None)

    assert result.exit_code == 0
    assert captured[0].verbose is True


# ---------------------------------------------------------------------------
# ctx.obj — config-less (KanboardConfigError absorbed)
# ---------------------------------------------------------------------------


def test_ctx_obj_none_on_config_error(runner: CliRunner) -> None:
    """When KanboardConfigError is raised, ctx.obj.config and .client are None."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_no_cfg")
    @click.pass_context
    def _test_no_cfg(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("url missing", field="url"),
    ):
        result = runner.invoke(cli, ["_test_no_cfg"])

    cli.commands.pop("_test_no_cfg", None)

    assert result.exit_code == 0
    ctx_obj = captured[0]
    assert isinstance(ctx_obj, AppContext)
    assert ctx_obj.config is None
    assert ctx_obj.client is None


# ---------------------------------------------------------------------------
# Stub subcommand --help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "subcommand",
    [
        "task",
        "project",
        "board",
        "column",
        "swimlane",
        "category",
        "comment",
        "subtask",
        "timer",
        "user",
        "me",
        "tag",
        "link",
        "task-link",
        "external-link",
        "group",
        "action",
        "project-file",
        "task-file",
        "project-meta",
        "task-meta",
        "project-access",
        "app",
        "config",
        "workflow",
    ],
)
def test_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Every stub command group must respond to --help."""
    err = KanboardConfigError("x", field="url")
    with patch("kanboard_cli.main.KanboardConfig.resolve", side_effect=err):
        result = runner.invoke(cli, [subcommand, "--help"])
    assert result.exit_code == 0, (
        f"'{subcommand} --help' exited {result.exit_code}: {result.output}"
    )


# ---------------------------------------------------------------------------
# AppContext dataclass
# ---------------------------------------------------------------------------


def test_app_context_defaults() -> None:
    """AppContext defaults are correct."""
    ctx = AppContext()
    assert ctx.config is None
    assert ctx.client is None
    assert ctx.output == "table"
    assert ctx.verbose is False


def test_app_context_fields() -> None:
    """AppContext stores provided values correctly."""
    cfg = MagicMock(spec=KanboardConfig)
    client = MagicMock()
    ctx = AppContext(config=cfg, client=client, output="json", verbose=True)
    assert ctx.config is cfg
    assert ctx.client is client
    assert ctx.output == "json"
    assert ctx.verbose is True


# ---------------------------------------------------------------------------
# --portfolio-backend global option (US-007)
# ---------------------------------------------------------------------------


def test_help_shows_portfolio_backend_option(runner: CliRunner) -> None:
    """``kanboard --help`` output shows the ``--portfolio-backend`` option."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--portfolio-backend" in result.output


@pytest.mark.parametrize("backend", ["local", "remote"])
def test_portfolio_backend_choice_valid(
    runner: CliRunner, mock_config: KanboardConfig, backend: str
) -> None:
    """``--portfolio-backend`` accepts both valid choices and passes them to resolve."""
    import click

    captured: list[AppContext] = []
    cmd_name = f"_test_pb_valid_{backend}"

    @cli.command(cmd_name)
    @click.pass_context
    def _cmd(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    resolved = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="tok",
        profile="default",
        output_format="table",
        portfolio_backend=backend,
    )
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=resolved) as mock_resolve,
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["--portfolio-backend", backend, cmd_name])

    cli.commands.pop(cmd_name, None)

    assert result.exit_code == 0
    mock_resolve.assert_called_once()
    _, kwargs = mock_resolve.call_args
    assert kwargs["cli_portfolio_backend"] == backend
    assert captured[0].config.portfolio_backend == backend


def test_portfolio_backend_choice_invalid(runner: CliRunner) -> None:
    """``--portfolio-backend`` rejects unknown values."""
    result = runner.invoke(cli, ["--portfolio-backend", "file", "task", "--help"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_portfolio_backend_none_by_default(runner: CliRunner, mock_config: KanboardConfig) -> None:
    """When ``--portfolio-backend`` is omitted, None is passed as cli_portfolio_backend."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_pb_default")
    @click.pass_context
    def _test_pb_default(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config) as mock_resolve,
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["_test_pb_default"])

    cli.commands.pop("_test_pb_default", None)

    assert result.exit_code == 0
    _, kwargs = mock_resolve.call_args
    assert kwargs.get("cli_portfolio_backend") is None


def test_portfolio_backend_remote_passed_to_resolve(
    runner: CliRunner, mock_config: KanboardConfig
) -> None:
    """``--portfolio-backend remote`` passes ``cli_portfolio_backend='remote'`` to resolve."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_pb_remote")
    @click.pass_context
    def _test_pb_remote(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    remote_config = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="tok",
        profile="default",
        output_format="table",
        portfolio_backend="remote",
    )
    with (
        patch(
            "kanboard_cli.main.KanboardConfig.resolve", return_value=remote_config
        ) as mock_resolve,
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["--portfolio-backend", "remote", "_test_pb_remote"])

    cli.commands.pop("_test_pb_remote", None)

    assert result.exit_code == 0
    _, kwargs = mock_resolve.call_args
    assert kwargs["cli_portfolio_backend"] == "remote"
    assert captured[0].config.portfolio_backend == "remote"


def test_portfolio_backend_local_passed_to_resolve(
    runner: CliRunner, mock_config: KanboardConfig
) -> None:
    """``--portfolio-backend local`` passes ``cli_portfolio_backend='local'`` to resolve."""
    captured: list[AppContext] = []

    import click

    @cli.command("_test_pb_local")
    @click.pass_context
    def _test_pb_local(ctx: click.Context) -> None:
        captured.append(ctx.obj)

    local_config = KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="tok",
        profile="default",
        output_format="table",
        portfolio_backend="local",
    )
    with (
        patch(
            "kanboard_cli.main.KanboardConfig.resolve", return_value=local_config
        ) as mock_resolve,
        patch("kanboard_cli.main.KanboardClient"),
    ):
        result = runner.invoke(cli, ["--portfolio-backend", "local", "_test_pb_local"])

    cli.commands.pop("_test_pb_local", None)

    assert result.exit_code == 0
    _, kwargs = mock_resolve.call_args
    assert kwargs["cli_portfolio_backend"] == "local"
    assert captured[0].config.portfolio_backend == "local"
