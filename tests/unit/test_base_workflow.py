"""Unit tests for ``kanboard_cli.workflows.base.BaseWorkflow`` (US-014)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import click
import pytest

from kanboard_cli.workflows.base import BaseWorkflow

# ---------------------------------------------------------------------------
# Concrete test subclass
# ---------------------------------------------------------------------------


class DummyWorkflow(BaseWorkflow):
    """Concrete workflow for testing."""

    @property
    def name(self) -> str:
        """Return the workflow name."""
        return "dummy"

    @property
    def description(self) -> str:
        """Return the workflow description."""
        return "A dummy workflow for testing"

    def register_commands(self, cli: click.Group) -> None:
        """Register a trivial command."""

        @cli.command(name="dummy-cmd")
        def _dummy() -> None:
            click.echo("dummy")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBaseWorkflow:
    """Tests for BaseWorkflow ABC."""

    def test_cannot_instantiate_abc(self) -> None:
        """BaseWorkflow itself cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseWorkflow()  # type: ignore[abstract]

    def test_concrete_subclass_properties(self) -> None:
        """Concrete subclass exposes name and description."""
        wf = DummyWorkflow()
        assert wf.name == "dummy"
        assert wf.description == "A dummy workflow for testing"

    def test_register_commands_adds_command(self) -> None:
        """register_commands adds a Click command to the group."""
        wf = DummyWorkflow()
        grp = click.Group(name="test")
        wf.register_commands(grp)
        assert "dummy-cmd" in grp.commands

    def test_get_config_delegates_to_get_workflow_config(self) -> None:
        """get_config calls get_workflow_config with the workflow name."""
        wf = DummyWorkflow()
        fake_config: dict[str, Any] = {"key": "value"}
        with patch(
            "kanboard_cli.workflows.base.get_workflow_config",
            return_value=fake_config,
        ) as mock_fn:
            result = wf.get_config()
        mock_fn.assert_called_once_with("dummy")
        assert result == fake_config

    def test_get_config_returns_empty_dict_when_absent(self) -> None:
        """get_config returns {} when no config section exists."""
        wf = DummyWorkflow()
        with patch(
            "kanboard_cli.workflows.base.get_workflow_config",
            return_value={},
        ):
            result = wf.get_config()
        assert result == {}
