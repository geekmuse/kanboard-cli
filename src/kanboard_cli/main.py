"""Kanboard CLI — root command group and global options.

Entry point: ``kanboard_cli.main:cli``

All subcommands inherit the global options defined here and receive an
:class:`AppContext` instance via ``ctx.obj``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

import click

try:
    _VERSION = _pkg_version("kanboard-cli")
except PackageNotFoundError:
    _VERSION = "0.0.0+dev"

from kanboard.client import KanboardClient
from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardConfigError
from kanboard_cli.commands.action import action
from kanboard_cli.commands.app_info import app
from kanboard_cli.commands.board import board
from kanboard_cli.commands.category import category
from kanboard_cli.commands.column import column
from kanboard_cli.commands.comment import comment
from kanboard_cli.commands.completion import completion_cmd
from kanboard_cli.commands.config_cmd import config_cmd
from kanboard_cli.commands.external_link import external_link
from kanboard_cli.commands.group import group
from kanboard_cli.commands.link import link
from kanboard_cli.commands.me import me
from kanboard_cli.commands.project import project
from kanboard_cli.commands.project_access import project_access
from kanboard_cli.commands.project_file import project_file
from kanboard_cli.commands.project_meta import project_meta
from kanboard_cli.commands.subtask import subtask
from kanboard_cli.commands.swimlane import swimlane
from kanboard_cli.commands.tag import tag
from kanboard_cli.commands.task import task
from kanboard_cli.commands.task_file import task_file
from kanboard_cli.commands.task_link import task_link
from kanboard_cli.commands.task_meta import task_meta
from kanboard_cli.commands.timer import timer
from kanboard_cli.commands.user import user
from kanboard_cli.workflow_loader import discover_workflows

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared application context
# ---------------------------------------------------------------------------


@dataclass
class AppContext:
    """Shared application context propagated to every subcommand via ``ctx.obj``.

    Attributes:
        config: The resolved :class:`~kanboard.config.KanboardConfig`, or
            ``None`` when configuration could not be resolved (e.g., running
            ``kanboard config init`` before any config exists).
        client: A ready-to-use :class:`~kanboard.client.KanboardClient`, or
            ``None`` when *config* is ``None``.
        output: The active output format (``table``, ``json``, ``csv``, or
            ``quiet``).
        verbose: Whether debug-level logging is enabled.
    """

    config: KanboardConfig | None = None
    client: KanboardClient | None = None
    output: str = "table"
    verbose: bool = False


# ---------------------------------------------------------------------------
# Root CLI group
# ---------------------------------------------------------------------------


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120},
)
@click.version_option(version=_VERSION, prog_name="kanboard")
@click.option(
    "--url",
    envvar="KANBOARD_URL",
    default=None,
    metavar="URL",
    help="Kanboard JSON-RPC endpoint URL (overrides config file and KANBOARD_URL env var).",
)
@click.option(
    "--token",
    envvar="KANBOARD_TOKEN",
    default=None,
    metavar="TOKEN",
    help="Kanboard API token (overrides config file and KANBOARD_TOKEN env var).",
)
@click.option(
    "--profile",
    envvar="KANBOARD_PROFILE",
    default=None,
    metavar="PROFILE",
    help="Config profile name (overrides settings.default_profile in config file).",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["table", "json", "csv", "quiet"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG-level logging.",
)
@click.option(
    "--auth-mode",
    "auth_mode",
    envvar="KANBOARD_AUTH_MODE",
    type=click.Choice(["app", "user"], case_sensitive=False),
    default=None,
    help=(
        "Authentication mode: 'app' (API token, default) or 'user' "
        "(username + password, required for 'me' commands)."
    ),
)
@click.pass_context
def cli(
    ctx: click.Context,
    url: str | None,
    token: str | None,
    profile: str | None,
    output: str,
    verbose: bool,
    auth_mode: str | None,
) -> None:
    r"""Kanboard CLI — manage your Kanboard instance from the terminal.

    Global options are inherited by every subcommand.  Set ``KANBOARD_URL``
    and ``KANBOARD_TOKEN`` environment variables (or configure a profile in
    ``~/.config/kanboard/config.toml``) to avoid repeating them on every
    invocation.

    For 'me' commands, use ``--auth-mode user`` with ``KANBOARD_USERNAME``
    and ``KANBOARD_PASSWORD`` environment variables.

    \b
    Examples:
        kanboard project list
        kanboard task get 42
        kanboard task create 1 "Fix login bug" --due 2025-12-31
        kanboard --output json task list 1
        kanboard --auth-mode user me
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    app_ctx = AppContext(output=output, verbose=verbose)

    try:
        config = KanboardConfig.resolve(
            url=url,
            token=token,
            profile=profile,
            output_format=output,
            auth_mode=auth_mode,
        )
        app_ctx.config = config
        app_ctx.client = KanboardClient(
            url=config.url,
            token=config.token,
            auth_mode=config.auth_mode,
            username=config.username,
            password=config.password,
        )
    except KanboardConfigError:
        # Config-less commands (e.g., ``kanboard config init``) handle missing
        # configuration themselves.  We silently absorb the error here so the
        # CLI stays usable even before a config file has been created.
        pass

    ctx.obj = app_ctx


@click.group(name="workflow")
def workflow() -> None:
    """Run and manage workflow plugins."""


@workflow.command(name="list")
@click.pass_context
def workflow_list(ctx: click.Context) -> None:
    """List all discovered workflow plugins."""
    from kanboard_cli.formatters import format_output

    app_ctx: AppContext = ctx.obj
    workflows = discover_workflows()
    data = [{"name": wf.name, "description": wf.description} for wf in workflows]
    format_output(data, app_ctx.output, columns=["name", "description"])


# ---------------------------------------------------------------------------
# Register all command groups with the root CLI
# ---------------------------------------------------------------------------

cli.add_command(task)
cli.add_command(project)
cli.add_command(board)
cli.add_command(column)
cli.add_command(swimlane)
cli.add_command(category)
cli.add_command(comment)
cli.add_command(subtask)
cli.add_command(timer)
cli.add_command(user)
cli.add_command(me)
cli.add_command(tag)
cli.add_command(link)
cli.add_command(task_link)
cli.add_command(external_link)
cli.add_command(group)
cli.add_command(action)
cli.add_command(project_file)
cli.add_command(task_file)
cli.add_command(project_meta)
cli.add_command(task_meta)
cli.add_command(project_access)
cli.add_command(app)
cli.add_command(completion_cmd)
cli.add_command(config_cmd)
cli.add_command(workflow)

# ---------------------------------------------------------------------------
# Discover and register workflow plugins
# ---------------------------------------------------------------------------

for _wf in discover_workflows():
    try:
        _wf.register_commands(cli)
    except Exception:
        logger.warning(
            "Failed to register commands for workflow '%s'",
            _wf.name,
            exc_info=True,
        )
