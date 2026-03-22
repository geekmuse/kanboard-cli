"""CLI tests for ``kanboard project-file`` subcommands (US-001)."""

from __future__ import annotations

import base64
import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import ProjectFile
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_FILE_DATA: dict = {
    "id": "5",
    "name": "report.pdf",
    "path": "projects/1/report.pdf",
    "is_image": "0",
    "project_id": "1",
    "owner_id": "2",
    "date": None,
    "size": "204800",
    "username": "alice",
    "task_id": "0",
    "mime_type": "application/pdf",
}

_SAMPLE_FILE_DATA_2: dict = {
    **_SAMPLE_FILE_DATA,
    "id": "6",
    "name": "spec.md",
    "size": "1024",
    "mime_type": "text/markdown",
}


def _make_pf(data: dict | None = None) -> ProjectFile:
    """Build a ProjectFile from sample data."""
    return ProjectFile.from_api(data or _SAMPLE_FILE_DATA)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def mock_config() -> KanboardConfig:
    """Return a minimal resolved config."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock client with a project_files resource."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
    input: str | None = None,
) -> object:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args, input=input)


# ===========================================================================
# project-file list
# ===========================================================================


def test_project_file_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file list`` renders files in table format."""
    mock_client.project_files.get_all_project_files.return_value = [_make_pf()]
    result = _invoke(runner, mock_config, mock_client, ["project-file", "list", "1"])
    assert result.exit_code == 0
    assert "report.pdf" in result.output
    mock_client.project_files.get_all_project_files.assert_called_once_with(1)


def test_project_file_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file list --output json`` renders files as a JSON array."""
    mock_client.project_files.get_all_project_files.return_value = [_make_pf()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project-file", "list", "1"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 5
    assert data[0]["name"] == "report.pdf"


def test_project_file_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file list --output csv`` renders files as CSV with a header row."""
    mock_client.project_files.get_all_project_files.return_value = [_make_pf()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "project-file", "list", "1"]
    )
    assert result.exit_code == 0
    assert "report.pdf" in result.output
    assert "id" in result.output  # header row


def test_project_file_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file list --output quiet`` prints only file IDs."""
    mock_client.project_files.get_all_project_files.return_value = [
        _make_pf(),
        _make_pf(_SAMPLE_FILE_DATA_2),
    ]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "quiet", "project-file", "list", "1"],
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "5" in lines
    assert "6" in lines


def test_project_file_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file list`` with no files exits 0 cleanly."""
    mock_client.project_files.get_all_project_files.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["project-file", "list", "1"])
    assert result.exit_code == 0


def test_project_file_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on project-file list exits non-zero."""
    mock_client.project_files.get_all_project_files.side_effect = KanboardAPIError(
        "getAllProjectFiles failed", method="getAllProjectFiles", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["project-file", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_project_file_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-file", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-file get
# ===========================================================================


def test_project_file_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file get`` shows file details in table format."""
    mock_client.project_files.get_project_file.return_value = _make_pf()
    result = _invoke(runner, mock_config, mock_client, ["project-file", "get", "1", "5"])
    assert result.exit_code == 0
    assert "rep" in result.output  # name may be truncated in narrow tables
    mock_client.project_files.get_project_file.assert_called_once_with(1, 5)


def test_project_file_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file get --output json`` renders the file as a JSON object."""
    mock_client.project_files.get_project_file.return_value = _make_pf()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "project-file", "get", "1", "5"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 5
    assert data["name"] == "report.pdf"


def test_project_file_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file get`` with unknown ID exits non-zero with an error message."""
    mock_client.project_files.get_project_file.side_effect = KanboardNotFoundError(
        "ProjectFile 99 not found", resource="ProjectFile", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["project-file", "get", "1", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_project_file_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-file", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-file upload
# ===========================================================================


def test_project_file_upload_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock, tmp_path: pathlib.Path
) -> None:
    """``project-file upload`` reads the file, base64-encodes it, and uploads."""
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"PDF content here")
    mock_client.project_files.create_project_file.return_value = 5

    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "upload", "1", str(test_file)]
    )
    assert result.exit_code == 0
    assert "5" in result.output

    expected_blob = base64.b64encode(b"PDF content here").decode("utf-8")
    mock_client.project_files.create_project_file.assert_called_once_with(
        1, "report.pdf", expected_blob
    )


def test_project_file_upload_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock, tmp_path: pathlib.Path
) -> None:
    """``project-file upload`` exits non-zero when SDK raises KanboardAPIError."""
    test_file = tmp_path / "report.pdf"
    test_file.write_bytes(b"PDF content here")
    mock_client.project_files.create_project_file.side_effect = KanboardAPIError(
        "createProjectFile failed", method="createProjectFile", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "upload", "1", str(test_file)]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_project_file_upload_missing_file(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file upload`` exits non-zero when file does not exist."""
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "upload", "1", "/nonexistent/file.pdf"]
    )
    assert result.exit_code != 0


def test_project_file_upload_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file upload --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-file", "upload", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-file download
# ===========================================================================


def test_project_file_download_default_path(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    """``project-file download`` writes decoded content to the file's original name."""
    file_content = b"Hello World"
    b64_content = base64.b64encode(file_content).decode("utf-8")
    mock_client.project_files.get_project_file.return_value = _make_pf()
    mock_client.project_files.download_project_file.return_value = b64_content

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = _invoke(runner, mock_config, mock_client, ["project-file", "download", "1", "5"])

    assert result.exit_code == 0
    assert "report.pdf" in result.output


def test_project_file_download_custom_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    """``project-file download --output PATH`` writes to the specified path."""
    file_content = b"Binary data"
    b64_content = base64.b64encode(file_content).decode("utf-8")
    mock_client.project_files.get_project_file.return_value = _make_pf()
    mock_client.project_files.download_project_file.return_value = b64_content
    dest = tmp_path / "output.bin"

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["project-file", "download", "1", "5", "--output", str(dest)],
    )
    assert result.exit_code == 0
    assert dest.read_bytes() == file_content


def test_project_file_download_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file download`` exits non-zero when file not found."""
    mock_client.project_files.get_project_file.side_effect = KanboardNotFoundError(
        "ProjectFile 99 not found", resource="ProjectFile", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["project-file", "download", "1", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_project_file_download_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file download --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-file", "download", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-file remove
# ===========================================================================


def test_project_file_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove --yes`` removes without prompting."""
    mock_client.project_files.remove_project_file.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "remove", "1", "5", "--yes"]
    )
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.project_files.remove_project_file.assert_called_once_with(1, 5)


def test_project_file_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "remove", "1", "5"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.project_files.remove_project_file.assert_not_called()


def test_project_file_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove`` without --yes and answering 'y' proceeds."""
    mock_client.project_files.remove_project_file.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "remove", "1", "5"], input="y\n"
    )
    assert result.exit_code == 0
    mock_client.project_files.remove_project_file.assert_called_once_with(1, 5)


def test_project_file_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-file", "remove", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# project-file remove-all
# ===========================================================================


def test_project_file_remove_all_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove-all --yes`` removes all without prompting."""
    mock_client.project_files.remove_all_project_files.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "remove-all", "1", "--yes"]
    )
    assert result.exit_code == 0
    assert "1" in result.output
    mock_client.project_files.remove_all_project_files.assert_called_once_with(1)


def test_project_file_remove_all_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove-all`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "remove-all", "1"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.project_files.remove_all_project_files.assert_not_called()


def test_project_file_remove_all_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove-all`` without --yes and answering 'y' proceeds."""
    mock_client.project_files.remove_all_project_files.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["project-file", "remove-all", "1"], input="y\n"
    )
    assert result.exit_code == 0
    mock_client.project_files.remove_all_project_files.assert_called_once_with(1)


def test_project_file_remove_all_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``project-file remove-all --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["project-file", "remove-all", "--help"])
    assert result.exit_code == 0
