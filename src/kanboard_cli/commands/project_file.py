"""Project file CLI commands — project-level file management for Kanboard.

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
# project-file command group
# ---------------------------------------------------------------------------


@click.group(name="project-file")
def project_file() -> None:
    """Manage files attached to projects."""


# ---------------------------------------------------------------------------
# project-file list
# ---------------------------------------------------------------------------


@project_file.command("list")
@click.argument("project_id", type=int)
@click.pass_context
def project_file_list(ctx: click.Context, project_id: int) -> None:
    r"""List all files attached to PROJECT_ID.

    \b
    Examples:
        kanboard project-file list 1
        kanboard --output json project-file list 1
    """
    app: AppContext = ctx.obj
    try:
        files = app.client.project_files.get_all_project_files(project_id)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(files, app.output, columns=_LIST_COLUMNS)


# ---------------------------------------------------------------------------
# project-file get
# ---------------------------------------------------------------------------


@project_file.command("get")
@click.argument("project_id", type=int)
@click.argument("file_id", type=int)
@click.pass_context
def project_file_get(ctx: click.Context, project_id: int, file_id: int) -> None:
    r"""Show details for FILE_ID in PROJECT_ID.

    \b
    Examples:
        kanboard project-file get 1 5
        kanboard --output json project-file get 1 5
    """
    app: AppContext = ctx.obj
    try:
        pf = app.client.project_files.get_project_file(project_id, file_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    format_output(pf, app.output)


# ---------------------------------------------------------------------------
# project-file upload
# ---------------------------------------------------------------------------


@project_file.command("upload")
@click.argument("project_id", type=int)
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def project_file_upload(ctx: click.Context, project_id: int, filepath: str) -> None:
    r"""Upload FILEPATH to PROJECT_ID.

    Reads the file, base64-encodes its content, and creates a project file
    with the original filename.

    \b
    Examples:
        kanboard project-file upload 1 ./report.pdf
        kanboard --output json project-file upload 1 ./spec.md
    """
    app: AppContext = ctx.obj
    path = pathlib.Path(filepath)
    filename = path.name
    blob = base64.b64encode(path.read_bytes()).decode("utf-8")
    try:
        new_id = app.client.project_files.create_project_file(project_id, filename, blob)
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    format_success(f"File '{filename}' uploaded as project file #{new_id}.", app.output)


# ---------------------------------------------------------------------------
# project-file download
# ---------------------------------------------------------------------------


@project_file.command("download")
@click.argument("project_id", type=int)
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
def project_file_download(
    ctx: click.Context,
    project_id: int,
    file_id: int,
    output_path: str | None,
) -> None:
    r"""Download FILE_ID from PROJECT_ID and write to disk.

    Decodes the base64-encoded content returned by the API and writes the
    binary data to PATH (or the file's original name when omitted).

    \b
    Examples:
        kanboard project-file download 1 5
        kanboard project-file download 1 5 --output /tmp/report.pdf
    """
    app: AppContext = ctx.obj
    try:
        # Fetch metadata to determine the original filename.
        pf = app.client.project_files.get_project_file(project_id, file_id)
        b64 = app.client.project_files.download_project_file(project_id, file_id)
    except KanboardNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    except KanboardAPIError as exc:
        raise click.ClickException(str(exc)) from exc

    dest = pathlib.Path(output_path) if output_path else pathlib.Path(pf.name)
    dest.write_bytes(base64.b64decode(b64))
    format_success(f"File #{file_id} downloaded to '{dest}'.", app.output)


# ---------------------------------------------------------------------------
# project-file remove
# ---------------------------------------------------------------------------


@project_file.command("remove")
@click.argument("project_id", type=int)
@click.argument("file_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def project_file_remove(
    ctx: click.Context,
    project_id: int,
    file_id: int,
    yes: bool,
) -> None:
    r"""Permanently delete FILE_ID from PROJECT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard project-file remove 1 5 --yes
    """
    if not yes:
        click.confirm(
            f"Delete project file #{file_id} from project {project_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.project_files.remove_project_file(project_id, file_id)
    format_success(f"Project file #{file_id} removed.", app.output)


# ---------------------------------------------------------------------------
# project-file remove-all
# ---------------------------------------------------------------------------


@project_file.command("remove-all")
@click.argument("project_id", type=int)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without an interactive prompt.",
)
@click.pass_context
def project_file_remove_all(
    ctx: click.Context,
    project_id: int,
    yes: bool,
) -> None:
    r"""Permanently delete ALL files from PROJECT_ID.

    Requires ``--yes`` to confirm (or interactive prompt).

    \b
    Examples:
        kanboard project-file remove-all 1 --yes
    """
    if not yes:
        click.confirm(
            f"Delete ALL files from project {project_id}? This cannot be undone.",
            abort=True,
        )
    app: AppContext = ctx.obj
    app.client.project_files.remove_all_project_files(project_id)
    format_success(f"All files removed from project {project_id}.", app.output)
