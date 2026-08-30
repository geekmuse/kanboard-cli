"""Security regression tests for downloaded file handling."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import click
import pytest

from kanboard_cli.downloads import write_download


@pytest.mark.parametrize(
    "name",
    ["../secret", "../../.bashrc", "/tmp/owned", r"..\secret", r"C:\owned", ".", ".."],
)
def test_default_download_rejects_unsafe_remote_names(tmp_path: Path, name: str) -> None:
    """Server-controlled default filenames cannot escape the current directory."""
    old_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(click.ClickException, match="unsafe download filename"):
            write_download(base64.b64encode(b"data").decode(), name, None)
    finally:
        os.chdir(old_cwd)


def test_download_rejects_invalid_base64(tmp_path: Path) -> None:
    """Malformed server content is rejected without creating a file."""
    destination = tmp_path / "result.bin"
    with pytest.raises(click.ClickException, match="invalid base64"):
        write_download("not!base64", "result.bin", str(destination))
    assert not destination.exists()


def test_download_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    """Downloads never overwrite an existing destination."""
    destination = tmp_path / "existing.txt"
    destination.write_text("original")
    with pytest.raises(click.ClickException, match="Refusing to overwrite"):
        write_download(base64.b64encode(b"replacement").decode(), "existing.txt", str(destination))
    assert destination.read_text() == "original"


def test_download_refuses_symlink_destination(tmp_path: Path) -> None:
    """Downloads cannot follow a destination symlink."""
    target = tmp_path / "target.txt"
    target.write_text("original")
    link = tmp_path / "download.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")
    with pytest.raises(click.ClickException):
        write_download(base64.b64encode(b"replacement").decode(), "download.txt", str(link))
    assert target.read_text() == "original"


def test_download_is_owner_only(tmp_path: Path) -> None:
    """Downloaded files are created with owner-only permissions."""
    destination = tmp_path / "private.bin"
    write_download(base64.b64encode(b"secret").decode(), "private.bin", str(destination))
    assert destination.read_bytes() == b"secret"
    assert destination.stat().st_mode & 0o777 == 0o600
