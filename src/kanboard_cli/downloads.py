"""Secure helpers for writing files downloaded from Kanboard."""

from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

import click


def _safe_remote_filename(name: str) -> str:
    """Validate a server-controlled filename used as a local default.

    Args:
        name: Filename returned by the Kanboard API.

    Returns:
        A simple filename with no directory components.

    Raises:
        click.ClickException: If *name* is empty, absolute, or contains path
            separators, traversal components, NULs, or control characters.
    """
    if not name or name in {".", ".."} or "\x00" in name:
        raise click.ClickException("Server returned an unsafe download filename.")
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise click.ClickException("Server returned an unsafe download filename.")

    posix = PurePosixPath(name)
    windows = PureWindowsPath(name)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or len(posix.parts) != 1
        or len(windows.parts) != 1
        or posix.name != name
        or windows.name != name
    ):
        raise click.ClickException("Server returned an unsafe download filename.")
    return name


def write_download(encoded: str, remote_name: str, output_path: str | None) -> Path:
    """Decode and exclusively write a downloaded file.

    The server-controlled filename is accepted only when it is a simple
    basename. Existing files and symlinks are never overwritten.

    Args:
        encoded: Strict RFC 4648 base64-encoded file content.
        remote_name: Original filename returned by Kanboard.
        output_path: User-selected destination, or ``None`` to use
            *remote_name* in the current directory.

    Returns:
        The destination path.

    Raises:
        click.ClickException: If the filename or content is invalid, the
            destination exists, or the file cannot be written safely.
    """
    destination = Path(output_path) if output_path else Path(_safe_remote_filename(remote_name))
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise click.ClickException("Server returned invalid base64 file content.") from exc

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(destination, flags, 0o600)
    except FileExistsError as exc:
        raise click.ClickException(
            f"Refusing to overwrite existing destination: {destination}"
        ) from exc
    except OSError as exc:
        raise click.ClickException(f"Unable to write download to {destination}: {exc}") from exc

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
    except OSError as exc:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise click.ClickException(f"Unable to write download to {destination}: {exc}") from exc

    return destination
