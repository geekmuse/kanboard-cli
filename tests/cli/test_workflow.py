"""CLI tests for ``kanboard workflow`` subcommands (US-014)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard_cli.main import cli
from kanboard_cli.workflows.base import BaseWorkflow

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
    """Return a MagicMock client."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeWorkflow(BaseWorkflow):
    """Fake workflow for testing."""

    def __init__(self, name: str = "demo", description: str = "Demo workflow") -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        """Return workflow name."""
        return self._name

    @property
    def description(self) -> str:
        """Return workflow description."""
        return self._description

    def register_commands(self, cli: click.Group) -> None:
        """No-op registration."""


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
    workflows: list[BaseWorkflow] | None = None,
) -> object:
    """Invoke the CLI with patched config + client + workflow loader."""
    wfs = workflows if workflows is not None else []
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
        patch(
            "kanboard_cli.main.discover_workflows",
            return_value=wfs,
        ),
    ):
        return runner.invoke(cli, args)


# ---------------------------------------------------------------------------
# Tests: kanboard workflow list
# ---------------------------------------------------------------------------


class TestWorkflowList:
    """Tests for ``kanboard workflow list``."""

    def test_list_no_workflows_table(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """Empty workflow list renders cleanly in table format."""
        result = _invoke(runner, mock_config, mock_client, ["workflow", "list"])
        assert result.exit_code == 0

    def test_list_with_workflows_table(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """Discovered workflows appear in table output."""
        wfs = [
            _FakeWorkflow("alpha", "Alpha workflow"),
            _FakeWorkflow("beta", "Beta workflow"),
        ]
        result = _invoke(runner, mock_config, mock_client, ["workflow", "list"], workflows=wfs)
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "Alpha workflow" in result.output
        assert "beta" in result.output
        assert "Beta workflow" in result.output

    def test_list_json_format(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """JSON output contains workflow name and description."""
        wfs = [_FakeWorkflow("deploy", "Deployment automation")]
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            ["--output", "json", "workflow", "list"],
            workflows=wfs,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "deploy"
        assert data[0]["description"] == "Deployment automation"

    def test_list_csv_format(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """CSV output contains workflow name and description."""
        wfs = [_FakeWorkflow("deploy", "Deployment automation")]
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            ["--output", "csv", "workflow", "list"],
            workflows=wfs,
        )
        assert result.exit_code == 0
        assert "deploy" in result.output
        assert "Deployment automation" in result.output

    def test_list_quiet_format(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """Quiet output renders without errors."""
        wfs = [_FakeWorkflow("deploy", "Deployment automation")]
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            ["--output", "quiet", "workflow", "list"],
            workflows=wfs,
        )
        assert result.exit_code == 0

    def test_workflow_help(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """``kanboard workflow --help`` shows the group help."""
        result = _invoke(runner, mock_config, mock_client, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "workflow plugins" in result.output.lower()

    def test_workflow_list_help(
        self,
        runner: CliRunner,
        mock_config: KanboardConfig,
        mock_client: MagicMock,
    ) -> None:
        """``kanboard workflow list --help`` shows the list help."""
        result = _invoke(runner, mock_config, mock_client, ["workflow", "list", "--help"])
        assert result.exit_code == 0
        assert "discovered" in result.output.lower() or "workflow" in result.output.lower()
