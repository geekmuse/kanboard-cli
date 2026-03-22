"""CLI tests for ``kanboard external-link`` subcommands (US-009)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import ExternalTaskLink
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_EL_DATA: dict = {
    "id": "5",
    "task_id": "42",
    "url": "https://github.com/org/repo/issues/1",
    "title": "GitHub Issue #1",
    "link_type": "weblink",
    "dependency": "related",
}

_SAMPLE_EL_DATA_2: dict = {
    "id": "6",
    "task_id": "42",
    "url": "https://docs.example.com/spec",
    "title": "Specification",
    "link_type": "weblink",
    "dependency": "blocked",
}


def _make_ext_link(data: dict | None = None) -> ExternalTaskLink:
    """Build an ExternalTaskLink from sample data."""
    return ExternalTaskLink.from_api(data or _SAMPLE_EL_DATA)


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
    """Return a MagicMock client with an external_task_links resource."""
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
# external-link types
# ===========================================================================


def test_external_link_types_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link types`` renders provider types in table format."""
    mock_client.external_task_links.get_external_task_link_types.return_value = {
        "weblink": "Web Link",
        "attachment": "Attachment",
    }
    result = _invoke(runner, mock_config, mock_client, ["external-link", "types"])
    assert result.exit_code == 0
    assert "weblink" in result.output
    assert "Web Link" in result.output


def test_external_link_types_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link types --output json`` renders as JSON."""
    mock_client.external_task_links.get_external_task_link_types.return_value = {
        "weblink": "Web Link",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "external-link", "types"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["provider"] == "weblink"
    assert data[0]["label"] == "Web Link"


def test_external_link_types_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link types --output csv`` renders as CSV."""
    mock_client.external_task_links.get_external_task_link_types.return_value = {
        "weblink": "Web Link",
    }
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "external-link", "types"]
    )
    assert result.exit_code == 0
    assert "provider" in result.output
    assert "weblink" in result.output


def test_external_link_types_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link types`` with no types exits 0 cleanly."""
    mock_client.external_task_links.get_external_task_link_types.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["external-link", "types"])
    assert result.exit_code == 0


def test_external_link_types_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on external-link types exits non-zero."""
    mock_client.external_task_links.get_external_task_link_types.side_effect = KanboardAPIError(
        "API error", method="getExternalTaskLinkTypes", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["external-link", "types"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_external_link_types_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link types --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "types", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# external-link dependencies
# ===========================================================================


def test_external_link_dependencies_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link dependencies`` renders dependency types in table format."""
    mock_client.external_task_links.get_external_task_link_provider_dependencies.return_value = {
        "related": "Related",
        "blocked": "Blocked",
    }
    result = _invoke(runner, mock_config, mock_client, ["external-link", "dependencies", "weblink"])
    assert result.exit_code == 0
    assert "related" in result.output
    assert "Related" in result.output


def test_external_link_dependencies_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link dependencies --output json`` renders as JSON."""
    mock_client.external_task_links.get_external_task_link_provider_dependencies.return_value = {
        "related": "Related",
    }
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "external-link", "dependencies", "weblink"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["dependency"] == "related"


def test_external_link_dependencies_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link dependencies`` with empty result exits 0."""
    mock_client.external_task_links.get_external_task_link_provider_dependencies.return_value = {}
    result = _invoke(runner, mock_config, mock_client, ["external-link", "dependencies", "unknown"])
    assert result.exit_code == 0


def test_external_link_dependencies_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link dependencies --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "dependencies", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# external-link list
# ===========================================================================


def test_external_link_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list`` renders links in table format."""
    mock_client.external_task_links.get_all_external_task_links.return_value = [_make_ext_link()]
    result = _invoke(runner, mock_config, mock_client, ["external-link", "list", "42"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.external_task_links.get_all_external_task_links.assert_called_once_with(42)


def test_external_link_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list --output json`` renders as JSON array."""
    mock_client.external_task_links.get_all_external_task_links.return_value = [
        _make_ext_link(),
        _make_ext_link(_SAMPLE_EL_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "external-link", "list", "42"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 5
    assert data[0]["url"] == "https://github.com/org/repo/issues/1"


def test_external_link_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list --output csv`` renders as CSV."""
    mock_client.external_task_links.get_all_external_task_links.return_value = [_make_ext_link()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "external-link", "list", "42"]
    )
    assert result.exit_code == 0
    assert "id" in result.output
    assert "5" in result.output


def test_external_link_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list --output quiet`` prints only link IDs."""
    mock_client.external_task_links.get_all_external_task_links.return_value = [
        _make_ext_link(),
        _make_ext_link(_SAMPLE_EL_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "external-link", "list", "42"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "5" in lines
    assert "6" in lines


def test_external_link_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list`` with no links exits 0 cleanly."""
    mock_client.external_task_links.get_all_external_task_links.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["external-link", "list", "42"])
    assert result.exit_code == 0


def test_external_link_list_empty_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list`` with no links renders clean JSON (empty array)."""
    mock_client.external_task_links.get_all_external_task_links.return_value = []
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "external-link", "list", "42"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == []


def test_external_link_list_empty_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list`` with no links renders cleanly in quiet mode."""
    mock_client.external_task_links.get_all_external_task_links.return_value = []
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "quiet", "external-link", "list", "42"],
    )
    assert result.exit_code == 0


def test_external_link_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on external-link list exits non-zero."""
    mock_client.external_task_links.get_all_external_task_links.side_effect = KanboardAPIError(
        "API error", method="getAllExternalTaskLinks", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["external-link", "list", "42"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_external_link_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# external-link get
# ===========================================================================


def test_external_link_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link get`` shows link details in table format."""
    mock_client.external_task_links.get_external_task_link_by_id.return_value = _make_ext_link()
    result = _invoke(runner, mock_config, mock_client, ["external-link", "get", "42", "5"])
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.external_task_links.get_external_task_link_by_id.assert_called_once_with(42, 5)


def test_external_link_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link get --output json`` renders the link as a JSON object."""
    mock_client.external_task_links.get_external_task_link_by_id.return_value = _make_ext_link()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "external-link", "get", "42", "5"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 5
    assert data["task_id"] == 42
    assert data["url"] == "https://github.com/org/repo/issues/1"
    assert data["dependency"] == "related"


def test_external_link_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link get`` with unknown ID exits non-zero."""
    mock_client.external_task_links.get_external_task_link_by_id.side_effect = (
        KanboardNotFoundError(
            "ExternalTaskLink 99 not found", resource="ExternalTaskLink", identifier=99
        )
    )
    result = _invoke(runner, mock_config, mock_client, ["external-link", "get", "42", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_external_link_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# external-link create
# ===========================================================================


def test_external_link_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link create`` creates a link and prints the new ID."""
    mock_client.external_task_links.create_external_task_link.return_value = 5
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["external-link", "create", "42", "https://example.com", "related"],
    )
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.external_task_links.create_external_task_link.assert_called_once_with(
        42, "https://example.com", "related"
    )


def test_external_link_create_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link create`` with --type and --title passes kwargs."""
    mock_client.external_task_links.create_external_task_link.return_value = 7
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "external-link",
            "create",
            "42",
            "https://example.com",
            "related",
            "--type",
            "weblink",
            "--title",
            "My Link",
        ],
    )
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.external_task_links.create_external_task_link.assert_called_once_with(
        42, "https://example.com", "related", type="weblink", title="My Link"
    )


def test_external_link_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link create`` exits non-zero on SDK error."""
    mock_client.external_task_links.create_external_task_link.side_effect = KanboardAPIError(
        "Creation failed", method="createExternalTaskLink", code=None
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["external-link", "create", "42", "https://example.com", "related"],
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_external_link_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# external-link update
# ===========================================================================


def test_external_link_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link update`` updates a link and prints success."""
    mock_client.external_task_links.update_external_task_link.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["external-link", "update", "42", "5", "New Title", "https://new.example.com"],
    )
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.external_task_links.update_external_task_link.assert_called_once_with(
        42, 5, "New Title", "https://new.example.com"
    )


def test_external_link_update_with_dependency(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link update`` with --dependency passes kwargs."""
    mock_client.external_task_links.update_external_task_link.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "external-link",
            "update",
            "42",
            "5",
            "Title",
            "https://example.com",
            "--dependency",
            "blocked",
        ],
    )
    assert result.exit_code == 0
    mock_client.external_task_links.update_external_task_link.assert_called_once_with(
        42, 5, "Title", "https://example.com", dependency="blocked"
    )


def test_external_link_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link update`` exits non-zero on SDK error."""
    mock_client.external_task_links.update_external_task_link.side_effect = KanboardAPIError(
        "Update failed", method="updateExternalTaskLink", code=None
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["external-link", "update", "42", "5", "Title", "https://example.com"],
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_external_link_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# external-link remove
# ===========================================================================


def test_external_link_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link remove --yes`` removes without prompting."""
    mock_client.external_task_links.remove_external_task_link.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["external-link", "remove", "42", "5", "--yes"]
    )
    assert result.exit_code == 0
    assert "5" in result.output
    mock_client.external_task_links.remove_external_task_link.assert_called_once_with(42, 5)


def test_external_link_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link remove`` without --yes and answering 'n' aborts."""
    result = _invoke(
        runner, mock_config, mock_client, ["external-link", "remove", "42", "5"], input="n\n"
    )
    assert result.exit_code != 0
    mock_client.external_task_links.remove_external_task_link.assert_not_called()


def test_external_link_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link remove`` without --yes and answering 'y' proceeds."""
    mock_client.external_task_links.remove_external_task_link.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["external-link", "remove", "42", "5"], input="y\n"
    )
    assert result.exit_code == 0
    mock_client.external_task_links.remove_external_task_link.assert_called_once_with(42, 5)


def test_external_link_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``external-link remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["external-link", "remove", "--help"])
    assert result.exit_code == 0
