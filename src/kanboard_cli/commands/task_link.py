"""Task link CLI commands — internal task-to-task link management for Kanboard.

Subcommands: list, get, create, update, remove.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "task_id", "opposite_task_id", "link_id"]
# Fields rendered when --with-project is active.
_LIST_COLUMNS_WITH_PROJECT = [*_LIST_COLUMNS, "opposite_project"]


# ---------------------------------------------------------------------------
# Task-link command group
# ---------------------------------------------------------------------------


@click.group(name="task-link")
def task_link() -> None:
    """Manage links between tasks."""


# ---------------------------------------------------------------------------
# task-link list
# ---------------------------------------------------------------------------


@task_link.command("list")
@click.argument("task_id", type=int)
@click.option(
    "--with-project",
    is_flag=True,
    default=False,
    help=(
        "Enrich each link with the opposite task's project name. "
        "Slower for tasks with many links (one extra API call per link)."
    ),
)
@click.pass_context
def task_link_list(ctx: click.Context, task_id: int, with_project: bool) -> None:
    r"""List all task links for TASK_ID.

    Use ``--with-project`` to include the opposite task's project name in the
    output.  This requires one additional ``getTask`` API call per link, so it
    may be slower for tasks with many links.

    \b
    Examples:
        kanboard task-link list 42
        kanboard task-link list 42 --with-project
        kanboard --output json task-link list 42
    """
    app: AppContext = ctx.obj
    try:
        links = app.client.task_links.get_all_task_links(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc

    if with_project:
        project_cache: dict[int, str] = {}
        rows: list[dict] = []
        for link in links:
            row = dataclasses.asdict(link)
            opp_task = app.client.tasks.get_task(link.opposite_task_id)
            pid = opp_task.project_id
            if pid not in project_cache:
                proj = app.client.projects.get_project_by_id(pid)
                project_cache[pid] = proj.name
            row["opposite_project"] = project_cache[pid]
            rows.append(row)
        format_output(rows, app.output, columns=_LIST_COLUMNS_WITH_PROJECT)
    else:
        format_output(links, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task-link get
# ---------------------------------------------------------------------------


@task_link.command("get")
@click.argument("task_link_id", type=int)
@click.pass_context
def task_link_get(ctx: click.Context, task_link_id: int) -> None:
    r"""Show details for task link TASK_LINK_ID.

    \b
    Examples:
        kanboard task-link get 7
        kanboard --output json task-link get 7
    """
    app: AppContext = ctx.obj
    try:
        tl = app.client.task_links.get_task_link_by_id(task_link_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(tl, app.output)


# ---------------------------------------------------------------------------
# task-link create
# ---------------------------------------------------------------------------


@task_link.command("create")
@click.argument("task_id", type=int)
@click.argument("opposite_task_id", type=int)
@click.argument("link_id", type=int)
@click.pass_context
def task_link_create(
    ctx: click.Context,
    task_id: int,
    opposite_task_id: int,
    link_id: int,
) -> None:
    r"""Create a task link from TASK_ID to OPPOSITE_TASK_ID using LINK_ID.

    After a successful creation, if the two tasks belong to different projects,
    an informational cross-project dependency message is displayed.

    \b
    Examples:
        kanboard task-link create 10 20 1
    """
    app: AppContext = ctx.obj
    try:
        new_id = app.client.task_links.create_task_link(task_id, opposite_task_id, link_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Task link #{new_id} created.", app.output)

    # Cross-project context enrichment — only on success, best-effort.
    # Fetching tasks here avoids latency on any error path above.
    try:
        task = app.client.tasks.get_task(task_id)
        opp_task = app.client.tasks.get_task(opposite_task_id)
        if task.project_id != opp_task.project_id:
            task_proj = app.client.projects.get_project_by_id(task.project_id)
            opp_proj = app.client.projects.get_project_by_id(opp_task.project_id)
            click.echo(
                f"\u2139 Cross-project dependency: Task #{task_id} ({task_proj.name})"
                f" is blocked by Task #{opposite_task_id} ({opp_proj.name})"
            )
    except Exception:
        pass  # Best-effort — enrichment failure must not obscure the success


# ---------------------------------------------------------------------------
# task-link update
# ---------------------------------------------------------------------------


@task_link.command("update")
@click.argument("task_link_id", type=int)
@click.argument("task_id", type=int)
@click.argument("opposite_task_id", type=int)
@click.argument("link_id", type=int)
@click.pass_context
def task_link_update(
    ctx: click.Context,
    task_link_id: int,
    task_id: int,
    opposite_task_id: int,
    link_id: int,
) -> None:
    r"""Update task link TASK_LINK_ID with new TASK_ID, OPPOSITE_TASK_ID, and LINK_ID.

    \b
    Examples:
        kanboard task-link update 7 10 30 2
    """
    app: AppContext = ctx.obj
    try:
        app.client.task_links.update_task_link(task_link_id, task_id, opposite_task_id, link_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"Task link #{task_link_id} updated.", app.output)


# ---------------------------------------------------------------------------
# task-link remove
# ---------------------------------------------------------------------------


@task_link.command("remove")
@click.argument("task_link_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def task_link_remove(ctx: click.Context, task_link_id: int, yes: bool) -> None:
    r"""Permanently delete task link TASK_LINK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard task-link remove 7 --yes
    """
    if not yes:
        click.confirm(
            f"Delete task link #{task_link_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.task_links.remove_task_link(task_link_id)
    format_success(f"Task link #{task_link_id} removed.", app.output)
