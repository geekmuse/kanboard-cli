"""Task file CLI commands — task-level file management for Kanboard.

Subcommands: list, get, upload, download, remove, remove-all.
"""

from __future__ import annotations

import base64
import pathlib
from typing import TYPE_CHECKING

import click

from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard_cli.formatters import format_output, format_success

if TYPE_CHECKING:
    from kanboard_cli.main import AppContext

# Default fields rendered in list / table output.
_LIST_COLUMNS = ["id", "name", "size", "mime_type", "username", "date"]


# ---------------------------------------------------------------------------
# task-file command group
# ---------------------------------------------------------------------------


@click.group(name="task-file")
def task_file() -> None:
    """Manage files attached to tasks."""


# ---------------------------------------------------------------------------
# task-file list
# ---------------------------------------------------------------------------


@task_file.command("list")
@click.argument("task_id", type=int)
@click.pass_context
def task_file_list(ctx: click.Context, task_id: int) -> None:
    r"""List all files attached to TASK_ID.

    \b
    Examples:
        kanboard task-file list 42
        kanboard --output json task-file list 42
    """
    app: AppContext = ctx.obj
    try:
        files = app.client.task_files.get_all_task_files(task_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(files, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# task-file get
# ---------------------------------------------------------------------------


@task_file.command("get")
@click.argument("file_id", type=int)
@click.pass_context
def task_file_get(ctx: click.Context, file_id: int) -> None:
    r"""Show details for FILE_ID.

    \b
    Examples:
        kanboard task-file get 5
        kanboard --output json task-file get 5
    """
    app: AppContext = ctx.obj
    try:
        tf = app.client.task_files.get_task_file(file_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(tf, app.output)


# ---------------------------------------------------------------------------
# task-file upload
# ---------------------------------------------------------------------------


@task_file.command("upload")
@click.argument("project_id", type=int)
@click.argument("task_id", type=int)
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def task_file_upload(
    ctx: click.Context,
    project_id: int,
    task_id: int,
    filepath: str,
) -> None:
    r"""Upload FILEPATH to TASK_ID in PROJECT_ID.

    Reads the file, base64-encodes its content, and creates a task file
    with the original filename.

    \b
    Examples:
        kanboard task-file upload 1 42 ./report.pdf
        kanboard --output json task-file upload 1 42 ./spec.md
    """
    app: AppContext = ctx.obj
    path = pathlib.Path(filepath)
    filename = path.name
    blob = base64.b64encode(path.read_bytes()).decode("utf-8")
    try:
        new_id = app.client.task_files.create_task_file(project_id, task_id, filename, blob)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"File '{filename}' uploaded as task file #{new_id}.", app.output)


# ---------------------------------------------------------------------------
# task-file download
# ---------------------------------------------------------------------------


@task_file.command("download")
@click.argument("file_id", type=int)
@click.option(
    "--output",
    "output_path",
    default=None,
    metavar="PATH",
    help=(
        "Destination path to write the downloaded file.  "
        "Defaults to the file's original name in the current directory."
    ),
)
@click.pass_context
def task_file_download(
    ctx: click.Context,
    file_id: int,
    output_path: str | None,
) -> None:
    r"""Download FILE_ID and write to disk.

    Decodes the base64-encoded content returned by the API and writes the
    binary data to PATH (or the file's original name when omitted).

    \b
    Examples:
        kanboard task-file download 5
        kanboard task-file download 5 --output /tmp/report.pdf
    """
    app: AppContext = ctx.obj
    try:
        tf = app.client.task_files.get_task_file(file_id)
        b64 = app.client.task_files.download_task_file(file_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc

    dest = pathlib.Path(output_path) if output_path else pathlib.Path(tf.name)
    dest.write_bytes(base64.b64decode(b64))
    format_success(f"File #{file_id} downloaded to '{dest}'.", app.output)


# ---------------------------------------------------------------------------
# task-file remove
# ---------------------------------------------------------------------------


@task_file.command("remove")
@click.argument("file_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def task_file_remove(
    ctx: click.Context,
    file_id: int,
    yes: bool,
) -> None:
    r"""Permanently delete FILE_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard task-file remove 5 --yes
    """
    if not yes:
        click.confirm(
            f"Delete task file #{file_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.task_files.remove_task_file(file_id)
    format_success(f"Task file #{file_id} removed.", app.output)


# ---------------------------------------------------------------------------
# task-file remove-all
# ---------------------------------------------------------------------------


@task_file.command("remove-all")
@click.argument("task_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def task_file_remove_all(
    ctx: click.Context,
    task_id: int,
    yes: bool,
) -> None:
    r"""Permanently delete ALL files from TASK_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard task-file remove-all 42 --yes
    """
    if not yes:
        click.confirm(
            f"Delete ALL files from task {task_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.task_files.remove_all_task_files(task_id)
    format_success(f"All files removed from task {task_id}.", app.output)
