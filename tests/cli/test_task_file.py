"""CLI tests for ``kanboard task-file`` subcommands (US-002)."""

from __future__ import annotations

import base64
import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import TaskFile
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_FILE_DATA: dict = {
    "id": "10",
    "name": "screenshot.png",
    "path": "tasks/42/screenshot.png",
    "is_image": "1",
    "task_id": "42",
    "date": None,
    "size": "102400",
    "username": "bob",
    "user_id": "3",
    "project_id": "1",
    "mime_type": "image/png",
}

_SAMPLE_FILE_DATA_2: dict = {
    **_SAMPLE_FILE_DATA,
    "id": "11",
    "name": "notes.txt",
    "is_image": "0",
    "size": "512",
    "mime_type": "text/plain",
}


def _make_tf(data: dict | None = None) -> TaskFile:
    """Build a TaskFile from sample data."""
    return TaskFile.from_api(data or _SAMPLE_FILE_DATA)


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
    """Return a MagicMock client with a task_files resource."""
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
# task-file list
# ===========================================================================


def test_task_file_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file list`` renders files in table format."""
    mock_client.task_files.get_all_task_files.return_value = [_make_tf()]
    result = _invoke(runner, mock_config, mock_client, ["task-file", "list", "42"])
    assert result.exit_code == 0
    assert "screenshot.png" in result.output
    mock_client.task_files.get_all_task_files.assert_called_once_with(42)


def test_task_file_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file list --output json`` renders files as a JSON array."""
    mock_client.task_files.get_all_task_files.return_value = [_make_tf()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-file", "list", "42"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 10
    assert data[0]["name"] == "screenshot.png"


def test_task_file_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file list --output csv`` renders files as CSV with a header row."""
    mock_client.task_files.get_all_task_files.return_value = [_make_tf()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "task-file", "list", "42"]
    )
    assert result.exit_code == 0
    assert "screenshot.png" in result.output
    assert "id" in result.output  # header row


def test_task_file_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file list --output quiet`` prints only file IDs."""
    mock_client.task_files.get_all_task_files.return_value = [
        _make_tf(),
        _make_tf(_SAMPLE_FILE_DATA_2),
    ]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "quiet", "task-file", "list", "42"],
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "10" in lines
    assert "11" in lines


def test_task_file_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file list`` with no files exits 0 cleanly."""
    mock_client.task_files.get_all_task_files.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["task-file", "list", "42"])
    assert result.exit_code == 0


def test_task_file_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on task-file list exits non-zero."""
    mock_client.task_files.get_all_task_files.side_effect = KanboardAPIError(
        "getAllTaskFiles failed", method="getAllTaskFiles", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task-file", "list", "42"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_file_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-file", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-file get
# ===========================================================================


def test_task_file_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file get`` shows file details in table format."""
    mock_client.task_files.get_task_file.return_value = _make_tf()
    result = _invoke(runner, mock_config, mock_client, ["task-file", "get", "10"])
    assert result.exit_code == 0
    assert "scr" in result.output  # name may be truncated in narrow tables
    mock_client.task_files.get_task_file.assert_called_once_with(10)


def test_task_file_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file get --output json`` renders the file as a JSON object."""
    mock_client.task_files.get_task_file.return_value = _make_tf()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-file", "get", "10"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 10
    assert data["name"] == "screenshot.png"


def test_task_file_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file get`` with unknown ID exits non-zero with an error message."""
    mock_client.task_files.get_task_file.side_effect = KanboardNotFoundError(
        "TaskFile 99 not found", resource="TaskFile", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["task-file", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_file_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-file", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-file upload
# ===========================================================================


def test_task_file_upload_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock, tmp_path: pathlib.Path
) -> None:
    """``task-file upload`` reads the file, base64-encodes it, and uploads."""
    test_file = tmp_path / "screenshot.png"
    test_file.write_bytes(b"PNG content here")
    mock_client.task_files.create_task_file.return_value = 10

    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "upload", "1", "42", str(test_file)]
    )
    assert result.exit_code == 0
    assert "10" in result.output

    expected_blob = base64.b64encode(b"PNG content here").decode("utf-8")
    mock_client.task_files.create_task_file.assert_called_once_with(
        1, 42, "screenshot.png", expected_blob
    )


def test_task_file_upload_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock, tmp_path: pathlib.Path
) -> None:
    """``task-file upload`` exits non-zero when SDK raises KanboardAPIError."""
    test_file = tmp_path / "screenshot.png"
    test_file.write_bytes(b"PNG content here")
    mock_client.task_files.create_task_file.side_effect = KanboardAPIError(
        "createTaskFile failed", method="createTaskFile", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "upload", "1", "42", str(test_file)]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_file_upload_missing_file(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file upload`` exits non-zero when file does not exist."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task-file", "upload", "1", "42", "/nonexistent/file.pdf"],
    )
    assert result.exit_code != 0


def test_task_file_upload_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file upload --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-file", "upload", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-file download
# ===========================================================================


def test_task_file_download_default_path(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    """``task-file download`` writes decoded content to the file's original name."""
    file_content = b"Hello World"
    b64_content = base64.b64encode(file_content).decode("utf-8")
    mock_client.task_files.get_task_file.return_value = _make_tf()
    mock_client.task_files.download_task_file.return_value = b64_content

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = _invoke(runner, mock_config, mock_client, ["task-file", "download", "10"])

    assert result.exit_code == 0
    assert "screenshot.png" in result.output


def test_task_file_download_custom_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    """``task-file download --output PATH`` writes to the specified path."""
    file_content = b"Binary data"
    b64_content = base64.b64encode(file_content).decode("utf-8")
    mock_client.task_files.get_task_file.return_value = _make_tf()
    mock_client.task_files.download_task_file.return_value = b64_content
    dest = tmp_path / "output.bin"

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task-file", "download", "10", "--output", str(dest)],
    )
    assert result.exit_code == 0
    assert dest.read_bytes() == file_content


def test_task_file_download_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file download`` exits non-zero when file not found."""
    mock_client.task_files.get_task_file.side_effect = KanboardNotFoundError(
        "TaskFile 99 not found", resource="TaskFile", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["task-file", "download", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_file_download_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file download --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-file", "download", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-file remove
# ===========================================================================


def test_task_file_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove --yes`` removes without prompting."""
    mock_client.task_files.remove_task_file.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "remove", "10", "--yes"]
    )
    assert result.exit_code == 0
    assert "10" in result.output
    mock_client.task_files.remove_task_file.assert_called_once_with(10)


def test_task_file_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "remove", "10"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.task_files.remove_task_file.assert_not_called()


def test_task_file_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove`` without --yes and answering 'y' proceeds."""
    mock_client.task_files.remove_task_file.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "remove", "10"], input="y\n"
    )
    assert result.exit_code == 0
    mock_client.task_files.remove_task_file.assert_called_once_with(10)


def test_task_file_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-file", "remove", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-file remove-all
# ===========================================================================


def test_task_file_remove_all_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove-all --yes`` removes all without prompting."""
    mock_client.task_files.remove_all_task_files.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task-file", "remove-all", "42", "--yes"])
    assert result.exit_code == 0
    assert "42" in result.output
    mock_client.task_files.remove_all_task_files.assert_called_once_with(42)


def test_task_file_remove_all_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove-all`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "remove-all", "42"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.task_files.remove_all_task_files.assert_not_called()


def test_task_file_remove_all_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove-all`` without --yes and answering 'y' proceeds."""
    mock_client.task_files.remove_all_task_files.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-file", "remove-all", "42"], input="y\n"
    )
    assert result.exit_code == 0
    mock_client.task_files.remove_all_task_files.assert_called_once_with(42)


def test_task_file_remove_all_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-file remove-all --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-file", "remove-all", "--help"])
    assert result.exit_code == 0
