"""Config management CLI commands.

Subcommands: init, show, path, profiles, test.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import tomli_w

from kanboard.config import CONFIG_DIR, CONFIG_FILE
from kanboard.exceptions import (
    KanboardAPIError,
    KanboardAuthError,
    KanboardConnectionError,
)
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _mask_token(token: str) -> str:
    """Return *token* with all but the last 4 characters replaced by stars.

    Args:
        token: The raw API token string.

    Returns:
        A masked representation like ``****abcd``.  Tokens shorter than
        5 characters are replaced entirely by ``****``.
    """
    if len(token) <= 4:
        return "****"
    return f"****{token[-4:]}"


def _read_raw_config(path: Path) -> dict[str, Any]:
    """Load *path* as TOML, returning an empty dict when the file is absent.

    Args:
        path: Filesystem path to the TOML configuration file.

    Returns:
        Parsed TOML data, or an empty dict if *path* does not exist.
    """
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}


# ---------------------------------------------------------------------------
# Config command group
# ---------------------------------------------------------------------------


@click.group(name="config")
def config_cmd() -> None:
    """Manage the Kanboard CLI configuration file."""


# ---------------------------------------------------------------------------
# config init
# ---------------------------------------------------------------------------


@config_cmd.command("init")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing configuration file.",
)
@click.pass_context
def config_init(ctx: click.Context, force: bool) -> None:
    r"""Create the configuration file interactively.

    Prompts for the Kanboard URL and API token, then writes
    ``~/.config/kanboard/config.toml``.  Aborts if the file already
    exists unless ``--force`` is supplied.

    \b
    Examples:
        kanboard config init
        kanboard config init --force
    """
    if CONFIG_FILE.exists() and not force:
        raise click.ClickException(
            f"Config file already exists: {CONFIG_FILE}\nUse --force to overwrite."
        )

    url: str = click.prompt("Kanboard URL", default="http://localhost/jsonrpc.php")
    token: str = click.prompt("API token", hide_input=True)

    data: dict[str, Any] = {
        "settings": {"default_profile": "default"},
        "profiles": {
            "default": {
                "url": url,
                "token": token,
            }
        },
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode())

    app_ctx: AppContext = ctx.obj
    format_success(f"Config written to {CONFIG_FILE}", app_ctx.output)


# ---------------------------------------------------------------------------
# config show
# ---------------------------------------------------------------------------


@config_cmd.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    r"""Display the current configuration with tokens masked.

    Prints the active URL, masked token (``****<last4>``), profile name,
    and output format from the resolved configuration.

    \b
    Examples:
        kanboard config show
        kanboard --output json config show
    """
    app_ctx: AppContext = ctx.obj
    if app_ctx.config is None:
        raise click.ClickException(
            "No configuration found. Run 'kanboard config init' to create one."
        )
    cfg = app_ctx.config
    rows: list[dict[str, str]] = [
        {"key": "url", "value": cfg.url},
        {"key": "token", "value": _mask_token(cfg.token)},
        {"key": "profile", "value": cfg.profile},
        {"key": "output_format", "value": cfg.output_format},
    ]
    format_output(rows, app_ctx.output, columns=["key", "value"])


# ---------------------------------------------------------------------------
# config path
# ---------------------------------------------------------------------------


@config_cmd.command("path")
def config_path() -> None:
    r"""Print the path to the configuration file.

    \b
    Examples:
        kanboard config path
    """
    click.echo(CONFIG_FILE)


# ---------------------------------------------------------------------------
# config profiles
# ---------------------------------------------------------------------------


@config_cmd.command("profiles")
@click.pass_context
def config_profiles(ctx: click.Context) -> None:
    r"""List all profile names defined in the configuration file.

    Reads the ``[profiles]`` section of ``~/.config/kanboard/config.toml``
    and prints every profile name.

    \b
    Examples:
        kanboard config profiles
        kanboard --output json config profiles
    """
    app_ctx: AppContext = ctx.obj
    raw = _read_raw_config(CONFIG_FILE)
    profile_names = list(raw.get("profiles", {}).keys())
    rows: list[dict[str, str]] = [{"profile": name} for name in profile_names]
    format_output(rows, app_ctx.output, columns=["profile"])


# ---------------------------------------------------------------------------
# config test
# ---------------------------------------------------------------------------


@config_cmd.command("test")
@click.pass_context
def config_test(ctx: click.Context) -> None:
    r"""Test connectivity to the configured Kanboard server.

    Calls ``getVersion`` on the server and prints the version string on
    success.  Exits non-zero with a descriptive error when the connection
    or authentication fails.

    \b
    Examples:
        kanboard config test
        kanboard --output json config test
    """
    app_ctx: AppContext = ctx.obj
    if app_ctx.client is None:
        raise click.ClickException(
            "No configuration found. Run 'kanboard config init' to create one."
        )
    try:
        version = app_ctx.client.application.get_version()
    except (KanboardConnectionError, KanboardAuthError, KanboardAPIError) as exc:
        raise click.ClickException(f"Connection failed: {exc}") from exc

    format_output(
        [{"key": "server_version", "value": version}],
        app_ctx.output,
        columns=["key", "value"],
    )
