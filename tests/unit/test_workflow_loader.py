"""Unit tests for ``kanboard_cli.workflow_loader`` (US-014)."""

from __future__ import annotations

from pathlib import Path

from kanboard_cli.workflow_loader import discover_workflows

# ---------------------------------------------------------------------------
# Helpers: tiny workflow plugins written as strings
# ---------------------------------------------------------------------------

_VALID_WORKFLOW = """\
import click
from kanboard_cli.workflows.base import BaseWorkflow


class GreetWorkflow(BaseWorkflow):
    @property
    def name(self) -> str:
        return "greet"

    @property
    def description(self) -> str:
        return "Say hello from a workflow"

    def register_commands(self, cli: click.Group) -> None:
        @cli.command(name="greet-hello")
        def hello() -> None:
            click.echo("Hello from GreetWorkflow!")
"""

_SECOND_WORKFLOW = """\
import click
from kanboard_cli.workflows.base import BaseWorkflow


class DeployWorkflow(BaseWorkflow):
    @property
    def name(self) -> str:
        return "deploy"

    @property
    def description(self) -> str:
        return "Deployment automation"

    def register_commands(self, cli: click.Group) -> None:
        pass
"""

_INVALID_SYNTAX = """\
def this is not valid python(
"""

_NO_WORKFLOW_CLASS = """\
# This module is valid Python but has no BaseWorkflow subclass.
x = 42
"""

_ABSTRACT_ONLY = """\
from kanboard_cli.workflows.base import BaseWorkflow


class StillAbstract(BaseWorkflow):
    # Missing all abstract implementations - should be skipped.
    pass
"""

_BROKEN_INIT = """\
import click
from kanboard_cli.workflows.base import BaseWorkflow


class BadInitWorkflow(BaseWorkflow):
    def __init__(self) -> None:
        raise RuntimeError("boom")

    @property
    def name(self) -> str:
        return "bad-init"

    @property
    def description(self) -> str:
        return "Broken init"

    def register_commands(self, cli: click.Group) -> None:
        pass
"""

_PACKAGE_WORKFLOW = """\
import click
from kanboard_cli.workflows.base import BaseWorkflow


class PkgWorkflow(BaseWorkflow):
    @property
    def name(self) -> str:
        return "pkg"

    @property
    def description(self) -> str:
        return "Package workflow"

    def register_commands(self, cli: click.Group) -> None:
        pass
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiscoverWorkflows:
    """Tests for ``discover_workflows``."""

    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent directory returns empty list without error."""
        result = discover_workflows(workflow_dir=tmp_path / "nope")
        assert result == []

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_discovers_valid_py_file(self, tmp_path: Path) -> None:
        """Valid .py file with BaseWorkflow subclass is discovered."""
        (tmp_path / "greet.py").write_text(_VALID_WORKFLOW)
        result = discover_workflows(workflow_dir=tmp_path)
        assert len(result) == 1
        assert result[0].name == "greet"
        assert result[0].description == "Say hello from a workflow"

    def test_discovers_multiple_workflows(self, tmp_path: Path) -> None:
        """Multiple valid .py files are all discovered and sorted by name."""
        (tmp_path / "greet.py").write_text(_VALID_WORKFLOW)
        (tmp_path / "deploy.py").write_text(_SECOND_WORKFLOW)
        result = discover_workflows(workflow_dir=tmp_path)
        assert len(result) == 2
        assert result[0].name == "deploy"
        assert result[1].name == "greet"

    def test_discovers_package_workflow(self, tmp_path: Path) -> None:
        """Directory with __init__.py is discovered as a package."""
        pkg_dir = tmp_path / "mypkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(_PACKAGE_WORKFLOW)
        result = discover_workflows(workflow_dir=tmp_path)
        assert len(result) == 1
        assert result[0].name == "pkg"

    def test_skips_invalid_syntax(self, tmp_path: Path) -> None:
        """File with syntax errors is skipped gracefully."""
        (tmp_path / "bad.py").write_text(_INVALID_SYNTAX)
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_skips_no_workflow_class(self, tmp_path: Path) -> None:
        """File without BaseWorkflow subclass yields nothing."""
        (tmp_path / "util.py").write_text(_NO_WORKFLOW_CLASS)
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_skips_abstract_subclass(self, tmp_path: Path) -> None:
        """Abstract subclass of BaseWorkflow is not instantiated."""
        (tmp_path / "abstract.py").write_text(_ABSTRACT_ONLY)
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_skips_broken_init(self, tmp_path: Path) -> None:
        """Workflow whose __init__ raises is skipped gracefully."""
        (tmp_path / "broken.py").write_text(_BROKEN_INIT)
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_skips_underscore_files(self, tmp_path: Path) -> None:
        """Files starting with _ are ignored."""
        (tmp_path / "_helper.py").write_text(_VALID_WORKFLOW)
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_skips_non_py_files(self, tmp_path: Path) -> None:
        """Non-.py files in the directory are ignored."""
        (tmp_path / "readme.txt").write_text("not a workflow")
        (tmp_path / "data.json").write_text("{}")
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_skips_dir_without_init(self, tmp_path: Path) -> None:
        """Directory without __init__.py is not treated as a package."""
        pkg_dir = tmp_path / "notpkg"
        pkg_dir.mkdir()
        (pkg_dir / "stuff.py").write_text(_VALID_WORKFLOW)
        result = discover_workflows(workflow_dir=tmp_path)
        assert result == []

    def test_mixed_valid_and_invalid(self, tmp_path: Path) -> None:
        """Valid workflows are returned even when invalid ones are present."""
        (tmp_path / "good.py").write_text(_VALID_WORKFLOW)
        (tmp_path / "bad.py").write_text(_INVALID_SYNTAX)
        (tmp_path / "noclass.py").write_text(_NO_WORKFLOW_CLASS)
        result = discover_workflows(workflow_dir=tmp_path)
        assert len(result) == 1
        assert result[0].name == "greet"

    def test_default_dir_used_when_none(self) -> None:
        """When workflow_dir is None, uses WORKFLOW_DIR default (no crash)."""
        # This should not raise even if ~/.config/kanboard/workflows/ is absent.
        result = discover_workflows(workflow_dir=None)
        assert isinstance(result, list)
