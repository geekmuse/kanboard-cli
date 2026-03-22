"""Board CLI commands — board layout viewing for Kanboard projects.

Subcommands: show.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError
from kanboard_cli.formatters import format_output

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Top-level column fields to render in table / CSV mode.
# The nested ``swimlanes`` key is intentionally excluded from table output;
# use ``--output json`` to see the full nested structure.
_BOARD_COLUMNS = ["id", "title", "position", "task_limit", "description"]


# ---------------------------------------------------------------------------
# Board command group
# ---------------------------------------------------------------------------


@click.group()
def board() -> None:
    """View and navigate project boards."""


# ---------------------------------------------------------------------------
# board show
# ---------------------------------------------------------------------------


@board.command("show")
@click.argument("project_id", type=int)
@click.pass_context
def board_show(ctx: click.Context, project_id: int) -> None:
    r"""Display the board layout for PROJECT_ID.

    In table and CSV mode the top-level column fields (id, title, position,
    task_limit, description) are shown.  Use ``--output json`` for the full
    nested structure including swimlanes and tasks.

    \b
    Examples:
        kanboard board show 1
        kanboard --output json board show 1
    """
    app: AppContext = ctx.obj
    try:
        board_data = app.client.board.get_board(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(board_data, app.output, columns=_BOARD_COLUMNS)
