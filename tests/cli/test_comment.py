"""CLI tests for ``kanboard comment`` subcommands (US-013)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Comment
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_COMMENT_DATA: dict = {
    "id": "7",
    "task_id": "42",
    "user_id": "1",
    "username": "jdoe",
    "name": "John Doe",
    "comment": "Looks good to me.",
    "date_creation": None,
    "date_modification": None,
}

_SAMPLE_COMMENT_DATA_2: dict = {
    **_SAMPLE_COMMENT_DATA,
    "id": "8",
    "comment": "Needs a second look.",
}


def _make_comment(data: dict | None = None) -> Comment:
    """Build a Comment from sample data."""
    return Comment.from_api(data or _SAMPLE_COMMENT_DATA)


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
    """Return a MagicMock client with a comments resource."""
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
# comment list
# ===========================================================================


def test_comment_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment list`` renders comments in table format."""
    mock_client.comments.get_all_comments.return_value = [_make_comment()]
    result = _invoke(runner, mock_config, mock_client, ["comment", "list", "42"])
    assert result.exit_code == 0
    assert "Looks good to me." in result.output
    mock_client.comments.get_all_comments.assert_called_once_with(42)


def test_comment_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment list --output json`` renders comments as a JSON array."""
    mock_client.comments.get_all_comments.return_value = [_make_comment()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "comment", "list", "42"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 7
    assert data[0]["comment"] == "Looks good to me."


def test_comment_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment list --output csv`` renders comments as CSV with a header row."""
    mock_client.comments.get_all_comments.return_value = [_make_comment()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "comment", "list", "42"]
    )
    assert result.exit_code == 0
    assert "jdoe" in result.output
    assert "id" in result.output  # header row


def test_comment_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment list --output quiet`` prints only comment IDs."""
    mock_client.comments.get_all_comments.return_value = [
        _make_comment(),
        _make_comment(_SAMPLE_COMMENT_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "comment", "list", "42"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "7" in lines
    assert "8" in lines


def test_comment_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment list`` with no comments exits 0 cleanly."""
    mock_client.comments.get_all_comments.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["comment", "list", "42"])
    assert result.exit_code == 0


def test_comment_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on comment list exits non-zero."""
    mock_client.comments.get_all_comments.side_effect = KanboardAPIError(
        "getAllComments failed", method="getAllComments", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["comment", "list", "42"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_comment_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["comment", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# comment get
# ===========================================================================


def test_comment_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment get`` shows comment details in table format."""
    mock_client.comments.get_comment.return_value = _make_comment()
    result = _invoke(runner, mock_config, mock_client, ["comment", "get", "7"])
    assert result.exit_code == 0
    assert "jdoe" in result.output
    mock_client.comments.get_comment.assert_called_once_with(7)


def test_comment_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment get --output json`` renders the comment as a JSON object."""
    mock_client.comments.get_comment.return_value = _make_comment()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "comment", "get", "7"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 7
    assert data["username"] == "jdoe"


def test_comment_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment get`` with unknown ID exits non-zero with an error message."""
    mock_client.comments.get_comment.side_effect = KanboardNotFoundError(
        "Comment 99 not found", resource="Comment", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["comment", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_comment_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["comment", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# comment add
# ===========================================================================


def test_comment_add_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment add`` creates a comment and prints the new ID."""
    mock_client.comments.create_comment.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["comment", "add", "42", "Looks good to me.", "--user-id", "1"],
    )
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.comments.create_comment.assert_called_once_with(42, 1, "Looks good to me.")


def test_comment_add_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment add`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.comments.create_comment.side_effect = KanboardAPIError(
        "createComment failed", method="createComment", code=None
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["comment", "add", "42", "Some text.", "--user-id", "1"],
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_comment_add_missing_user_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment add`` without --user-id exits non-zero (required option)."""
    result = _invoke(
        runner, mock_config, mock_client, ["comment", "add", "42", "Some text."]
    )
    assert result.exit_code != 0


def test_comment_add_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment add --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["comment", "add", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# comment update
# ===========================================================================


def test_comment_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment update`` updates a comment and prints a success message."""
    mock_client.comments.update_comment.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["comment", "update", "7", "Updated text."]
    )
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.comments.update_comment.assert_called_once_with(7, "Updated text.")


def test_comment_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.comments.update_comment.side_effect = KanboardAPIError(
        "updateComment failed", method="updateComment", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["comment", "update", "7", "New text."]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_comment_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["comment", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# comment remove
# ===========================================================================


def test_comment_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment remove --yes`` removes without prompting."""
    mock_client.comments.remove_comment.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["comment", "remove", "7", "--yes"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.comments.remove_comment.assert_called_once_with(7)


def test_comment_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment remove`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner, mock_config, mock_client, ["comment", "remove", "7"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.comments.remove_comment.assert_not_called()


def test_comment_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment remove`` without --yes and answering 'y' proceeds."""
    mock_client.comments.remove_comment.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["comment", "remove", "7"], input="y\n"
    )
    assert result.exit_code == 0
    mock_client.comments.remove_comment.assert_called_once_with(7)


def test_comment_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``comment remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["comment", "remove", "--help"])
    assert result.exit_code == 0
