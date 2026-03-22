"""CLI tests for ``kanboard category`` subcommands (US-014)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Category
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_CATEGORY_DATA: dict = {
    "id": "3",
    "name": "Frontend",
    "project_id": "1",
    "color_id": "blue",
}

_SAMPLE_CATEGORY_DATA_2: dict = {
    **_SAMPLE_CATEGORY_DATA,
    "id": "4",
    "name": "Backend",
}


def _make_category(data: dict | None = None) -> Category:
    """Build a Category from sample data."""
    return Category.from_api(data or _SAMPLE_CATEGORY_DATA)


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
    """Return a MagicMock client with a categories resource."""
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
# category list
# ===========================================================================


def test_category_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category list`` renders categories in table format."""
    mock_client.categories.get_all_categories.return_value = [_make_category()]
    result = _invoke(runner, mock_config, mock_client, ["category", "list", "1"])
    assert result.exit_code == 0
    assert "Frontend" in result.output
    mock_client.categories.get_all_categories.assert_called_once_with(1)


def test_category_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category list --output json`` renders categories as a JSON array."""
    mock_client.categories.get_all_categories.return_value = [_make_category()]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "category", "list", "1"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 3
    assert data[0]["name"] == "Frontend"


def test_category_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category list --output csv`` renders categories as CSV with a header row."""
    mock_client.categories.get_all_categories.return_value = [_make_category()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "category", "list", "1"])
    assert result.exit_code == 0
    assert "Frontend" in result.output
    assert "id" in result.output  # header row


def test_category_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category list --output quiet`` prints only category IDs."""
    mock_client.categories.get_all_categories.return_value = [
        _make_category(),
        _make_category(_SAMPLE_CATEGORY_DATA_2),
    ]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "quiet", "category", "list", "1"],
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "3" in lines
    assert "4" in lines


def test_category_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category list`` with no categories exits 0 cleanly."""
    mock_client.categories.get_all_categories.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["category", "list", "1"])
    assert result.exit_code == 0


def test_category_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on category list exits non-zero."""
    mock_client.categories.get_all_categories.side_effect = KanboardAPIError(
        "getAllCategories failed", method="getAllCategories", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["category", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_category_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["category", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# category get
# ===========================================================================


def test_category_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category get`` shows category details in table format."""
    mock_client.categories.get_category.return_value = _make_category()
    result = _invoke(runner, mock_config, mock_client, ["category", "get", "3"])
    assert result.exit_code == 0
    assert "Frontend" in result.output
    mock_client.categories.get_category.assert_called_once_with(3)


def test_category_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category get --output json`` renders the category as a JSON object."""
    mock_client.categories.get_category.return_value = _make_category()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "category", "get", "3"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 3
    assert data["name"] == "Frontend"


def test_category_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category get`` with unknown ID exits non-zero with an error message."""
    mock_client.categories.get_category.side_effect = KanboardNotFoundError(
        "Category 99 not found", resource="Category", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["category", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_category_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["category", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# category create
# ===========================================================================


def test_category_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category create`` creates a category and prints the new ID."""
    mock_client.categories.create_category.return_value = 3
    result = _invoke(runner, mock_config, mock_client, ["category", "create", "1", "Frontend"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.categories.create_category.assert_called_once_with(1, "Frontend")


def test_category_create_with_color_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category create`` with --color-id passes it to the SDK."""
    mock_client.categories.create_category.return_value = 5
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["category", "create", "1", "Backend", "--color-id", "blue"],
    )
    assert result.exit_code == 0
    mock_client.categories.create_category.assert_called_once_with(1, "Backend", color_id="blue")


def test_category_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.categories.create_category.side_effect = KanboardAPIError(
        "createCategory failed", method="createCategory", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["category", "create", "1", "Frontend"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_category_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["category", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# category update
# ===========================================================================


def test_category_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category update`` updates a category and prints a success message."""
    mock_client.categories.update_category.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["category", "update", "3", "Renamed"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.categories.update_category.assert_called_once_with(3, "Renamed")


def test_category_update_with_color_id(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category update`` with --color-id passes it to the SDK."""
    mock_client.categories.update_category.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["category", "update", "3", "Frontend", "--color-id", "green"],
    )
    assert result.exit_code == 0
    mock_client.categories.update_category.assert_called_once_with(3, "Frontend", color_id="green")


def test_category_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.categories.update_category.side_effect = KanboardAPIError(
        "updateCategory failed", method="updateCategory", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["category", "update", "3", "New Name"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_category_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["category", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# category remove
# ===========================================================================


def test_category_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category remove --yes`` removes without prompting."""
    mock_client.categories.remove_category.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["category", "remove", "3", "--yes"])
    assert result.exit_code == 0
    assert "3" in result.output
    mock_client.categories.remove_category.assert_called_once_with(3)


def test_category_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["category", "remove", "3"], input="n\n")
    assert result.exit_code != 0
    mock_client.categories.remove_category.assert_not_called()


def test_category_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category remove`` without --yes and answering 'y' proceeds."""
    mock_client.categories.remove_category.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["category", "remove", "3"], input="y\n")
    assert result.exit_code == 0
    mock_client.categories.remove_category.assert_called_once_with(3)


def test_category_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``category remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["category", "remove", "--help"])
    assert result.exit_code == 0
