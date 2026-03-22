"""CLI tests for ``kanboard completion`` subcommands (US-002)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(runner: CliRunner, args: list[str]) -> object:
    """Invoke CLI without a valid config (completion commands need none)."""
    from kanboard.exceptions import KanboardConfigError

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("no config", field="url"),
    ):
        return runner.invoke(cli, args)


# ---------------------------------------------------------------------------
# completion bash
# ---------------------------------------------------------------------------


class TestCompletionBash:
    """Tests for ``kanboard completion bash``."""

    def test_bash_outputs_nonempty_script(self, runner: CliRunner) -> None:
        """bash subcommand outputs a non-empty bash completion script."""
        result = _invoke(runner, ["completion", "bash"])
        assert result.exit_code == 0, result.output
        assert len(result.output.strip()) > 0

    def test_bash_output_contains_kanboard(self, runner: CliRunner) -> None:
        """bash completion script references the kanboard program."""
        result = _invoke(runner, ["completion", "bash"])
        assert result.exit_code == 0
        assert "kanboard" in result.output.lower()


# ---------------------------------------------------------------------------
# completion zsh
# ---------------------------------------------------------------------------


class TestCompletionZsh:
    """Tests for ``kanboard completion zsh``."""

    def test_zsh_outputs_nonempty_script(self, runner: CliRunner) -> None:
        """zsh subcommand outputs a non-empty zsh completion script."""
        result = _invoke(runner, ["completion", "zsh"])
        assert result.exit_code == 0, result.output
        assert len(result.output.strip()) > 0

    def test_zsh_output_contains_kanboard(self, runner: CliRunner) -> None:
        """zsh completion script references the kanboard program."""
        result = _invoke(runner, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "kanboard" in result.output.lower()


# ---------------------------------------------------------------------------
# completion fish
# ---------------------------------------------------------------------------


class TestCompletionFish:
    """Tests for ``kanboard completion fish``."""

    def test_fish_outputs_nonempty_script(self, runner: CliRunner) -> None:
        """fish subcommand outputs a non-empty fish completion script."""
        result = _invoke(runner, ["completion", "fish"])
        assert result.exit_code == 0, result.output
        assert len(result.output.strip()) > 0

    def test_fish_output_contains_kanboard(self, runner: CliRunner) -> None:
        """fish completion script references the kanboard program."""
        result = _invoke(runner, ["completion", "fish"])
        assert result.exit_code == 0
        assert "kanboard" in result.output.lower()


# ---------------------------------------------------------------------------
# completion install bash
# ---------------------------------------------------------------------------


class TestCompletionInstallBash:
    """Tests for ``kanboard completion install bash``."""

    def test_install_bash_appends_eval_to_bashrc(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install bash appends eval line to BASH_RC."""
        fake_bashrc = tmp_path / ".bashrc"
        fake_bashrc.write_text("# existing content\n")
        with patch("kanboard_cli.commands.completion.BASH_RC", fake_bashrc):
            result = _invoke(runner, ["completion", "install", "bash"])
        assert result.exit_code == 0, result.output
        content = fake_bashrc.read_text()
        assert 'eval "$(kanboard completion bash)"' in content
        assert "✓" in result.output

    def test_install_bash_creates_bashrc_if_missing(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install bash creates BASH_RC when it does not exist."""
        fake_bashrc = tmp_path / ".bashrc"
        assert not fake_bashrc.exists()
        with patch("kanboard_cli.commands.completion.BASH_RC", fake_bashrc):
            result = _invoke(runner, ["completion", "install", "bash"])
        assert result.exit_code == 0, result.output
        assert fake_bashrc.exists()
        assert 'eval "$(kanboard completion bash)"' in fake_bashrc.read_text()

    def test_install_bash_skips_if_already_present(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install bash does not add a duplicate eval line."""
        fake_bashrc = tmp_path / ".bashrc"
        fake_bashrc.write_text('eval "$(kanboard completion bash)"\n')
        with patch("kanboard_cli.commands.completion.BASH_RC", fake_bashrc):
            result = _invoke(runner, ["completion", "install", "bash"])
        assert result.exit_code == 0, result.output
        assert "skipping" in result.output
        # Content should not be duplicated
        assert result.output.count("kanboard completion") <= 1


# ---------------------------------------------------------------------------
# completion install zsh
# ---------------------------------------------------------------------------


class TestCompletionInstallZsh:
    """Tests for ``kanboard completion install zsh``."""

    def test_install_zsh_appends_eval_to_zshrc(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install zsh appends eval line to ZSH_RC."""
        fake_zshrc = tmp_path / ".zshrc"
        fake_zshrc.write_text("# existing content\n")
        with patch("kanboard_cli.commands.completion.ZSH_RC", fake_zshrc):
            result = _invoke(runner, ["completion", "install", "zsh"])
        assert result.exit_code == 0, result.output
        content = fake_zshrc.read_text()
        assert 'eval "$(kanboard completion zsh)"' in content
        assert "✓" in result.output

    def test_install_zsh_skips_if_already_present(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install zsh does not add a duplicate eval line."""
        fake_zshrc = tmp_path / ".zshrc"
        fake_zshrc.write_text('eval "$(kanboard completion zsh)"\n')
        with patch("kanboard_cli.commands.completion.ZSH_RC", fake_zshrc):
            result = _invoke(runner, ["completion", "install", "zsh"])
        assert result.exit_code == 0, result.output
        assert "skipping" in result.output


# ---------------------------------------------------------------------------
# completion install fish
# ---------------------------------------------------------------------------


class TestCompletionInstallFish:
    """Tests for ``kanboard completion install fish``."""

    def test_install_fish_writes_completion_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install fish writes completion script to FISH_COMPLETIONS_DIR/kanboard.fish."""
        fake_fish_dir = tmp_path / "fish" / "completions"
        with patch(
            "kanboard_cli.commands.completion.FISH_COMPLETIONS_DIR", fake_fish_dir
        ):
            result = _invoke(runner, ["completion", "install", "fish"])
        assert result.exit_code == 0, result.output
        fish_file = fake_fish_dir / "kanboard.fish"
        assert fish_file.exists()
        assert len(fish_file.read_text().strip()) > 0
        assert "✓" in result.output

    def test_install_fish_creates_parent_dirs(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """install fish creates the completions directory if it does not exist."""
        fake_fish_dir = tmp_path / "nested" / "completions"
        assert not fake_fish_dir.exists()
        with patch(
            "kanboard_cli.commands.completion.FISH_COMPLETIONS_DIR", fake_fish_dir
        ):
            result = _invoke(runner, ["completion", "install", "fish"])
        assert result.exit_code == 0, result.output
        assert fake_fish_dir.exists()
        assert (fake_fish_dir / "kanboard.fish").exists()


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------


class TestCompletionEdgeCases:
    """Edge-case and error tests for completion commands."""

    def test_invalid_shell_is_rejected(self, runner: CliRunner) -> None:
        """install rejects an unknown shell name with a usage error."""
        result = _invoke(runner, ["completion", "install", "powershell"])
        assert result.exit_code != 0

    def test_completion_group_help(self, runner: CliRunner) -> None:
        """completion --help exits cleanly with usage information."""
        result = _invoke(runner, ["completion", "--help"])
        assert result.exit_code == 0
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output
