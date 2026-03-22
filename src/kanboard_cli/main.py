"""Kanboard CLI — root command group and global options.

Entry point: ``kanboard_cli.main:cli``

All subcommands inherit the global options defined here and receive an
:class:`AppContext` instance via ``ctx.obj``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import click

from kanboard.client import KanboardClient
from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardConfigError
from kanboard_cli.commands.project import project
from kanboard_cli.commands.task import task

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
@click.pass_context
def cli(
    ctx: click.Context,
    url: str | None,
    token: str | None,
    profile: str | None,
    output: str,
    verbose: bool,
) -> None:
    r"""Kanboard CLI — manage your Kanboard instance from the terminal.

    Global options are inherited by every subcommand.  Set ``KANBOARD_URL``
    and ``KANBOARD_TOKEN`` environment variables (or configure a profile in
    ``~/.config/kanboard/config.toml``) to avoid repeating them on every
    invocation.

    \b
    Examples:
        kanboard project list
        kanboard task get 42
        kanboard task create 1 "Fix login bug" --due 2025-12-31
        kanboard --output json task list 1
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
        )
        app_ctx.config = config
        app_ctx.client = KanboardClient(url=config.url, token=config.token)
    except KanboardConfigError:
        # Config-less commands (e.g., ``kanboard config init``) handle missing
        # configuration themselves.  We silently absorb the error here so the
        # CLI stays usable even before a config file has been created.
        pass

    ctx.obj = app_ctx


# ---------------------------------------------------------------------------
# Stub command groups
# (Populated with real sub-commands in later user stories)
# ---------------------------------------------------------------------------


@click.group()
def board() -> None:
    """View and navigate project boards."""


@click.group()
def column() -> None:
    """Manage board columns."""


@click.group()
def swimlane() -> None:
    """Manage project swimlanes."""


@click.group()
def category() -> None:
    """Manage task categories."""


@click.group()
def comment() -> None:
    """Manage task comments."""


@click.group()
def subtask() -> None:
    """Manage task subtasks."""


@click.group()
def timer() -> None:
    """Start and stop subtask timers."""


@click.group()
def user() -> None:
    """Manage Kanboard users."""


@click.group()
def me() -> None:
    """Commands for the authenticated user."""


@click.group()
def tag() -> None:
    """Manage task tags."""


@click.group()
def link() -> None:
    """Manage link type definitions."""


@click.group(name="task-link")
def task_link() -> None:
    """Manage links between tasks."""


@click.group(name="external-link")
def external_link() -> None:
    """Manage external links on tasks."""


@click.group()
def group() -> None:
    """Manage Kanboard user groups."""


@click.group()
def action() -> None:
    """Manage automatic actions on projects."""


@click.group(name="project-file")
def project_file() -> None:
    """Manage files attached to projects."""


@click.group(name="task-file")
def task_file() -> None:
    """Manage files attached to tasks."""


@click.group(name="project-meta")
def project_meta() -> None:
    """Manage project metadata."""


@click.group(name="task-meta")
def task_meta() -> None:
    """Manage task metadata."""


@click.group(name="project-access")
def project_access() -> None:
    """Manage project user and group access."""


@click.group()
def app() -> None:
    """Application-level information and settings."""


@click.group(name="config")
def config_group() -> None:
    """Manage the Kanboard CLI configuration file."""


@click.group()
def workflow() -> None:
    """Run and manage workflow plugins."""


# ---------------------------------------------------------------------------
# Register all stub groups with the root CLI
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
cli.add_command(config_group)
cli.add_command(workflow)
