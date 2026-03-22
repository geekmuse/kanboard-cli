"""Shell completion commands for kanboard-cli.

Subcommands: bash, zsh, fish, install.

Uses Click's built-in :mod:`click.shell_completion` module to generate
completion scripts for bash, zsh, and fish.  The ``install`` subcommand
writes the appropriate snippet to the user's shell initialisation file.
"""

from __future__ import annotations

from pathlib import Path

import click
from click.shell_completion import BashComplete, FishComplete, ZshComplete

# ---------------------------------------------------------------------------
# Module-level install-path constants — override in tests by patching
# ---------------------------------------------------------------------------

BASH_RC: Path = Path.home() / ".bashrc"
ZSH_RC: Path = Path.home() / ".zshrc"
FISH_COMPLETIONS_DIR: Path = Path.home() / ".config" / "fish" / "completions"

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_SHELL_CLASS: dict[str, type[BashComplete | ZshComplete | FishComplete]] = {
    "bash": BashComplete,
    "zsh": ZshComplete,
    "fish": FishComplete,
}

_SHELL_INIT_FILE: dict[str, str] = {
    "bash": "BASH_RC",
    "zsh": "ZSH_RC",
}


def _get_completion_source(shell: str) -> str:
    """Return the Click-generated completion script for *shell*.

    Uses a lazy import of :data:`~kanboard_cli.main.cli` to avoid a circular
    import at module load time.

    Args:
        shell: One of ``"bash"``, ``"zsh"``, or ``"fish"``.

    Returns:
        The shell completion script as a plain string.
    """
    from kanboard_cli.main import cli  # lazy — main imports completion, not the reverse

    cls = _SHELL_CLASS[shell]
    complete = cls(cli, {}, "kanboard", "_KANBOARD_COMPLETE")
    return complete.source()


# ---------------------------------------------------------------------------
# Completion command group
# ---------------------------------------------------------------------------


@click.group(name="completion")
def completion_cmd() -> None:
    """Generate and install shell completion scripts."""


# ---------------------------------------------------------------------------
# completion bash
# ---------------------------------------------------------------------------


@completion_cmd.command(name="bash")
def completion_bash() -> None:
    r"""Output the bash completion script to stdout.

    Evaluate once in the current shell:

    \b
        eval "$(kanboard completion bash)"

    Or persist by adding to ~/.bashrc:

    \b
        kanboard completion install bash
    """
    click.echo(_get_completion_source("bash"))


# ---------------------------------------------------------------------------
# completion zsh
# ---------------------------------------------------------------------------


@completion_cmd.command(name="zsh")
def completion_zsh() -> None:
    r"""Output the zsh completion script to stdout.

    Evaluate once in the current shell:

    \b
        eval "$(kanboard completion zsh)"

    Or persist by adding to ~/.zshrc:

    \b
        kanboard completion install zsh
    """
    click.echo(_get_completion_source("zsh"))


# ---------------------------------------------------------------------------
# completion fish
# ---------------------------------------------------------------------------


@completion_cmd.command(name="fish")
def completion_fish() -> None:
    r"""Output the fish completion script to stdout.

    Persist by piping to the fish completions directory:

    \b
        kanboard completion fish > ~/.config/fish/completions/kanboard.fish

    Or use the install command:

    \b
        kanboard completion install fish
    """
    click.echo(_get_completion_source("fish"))


# ---------------------------------------------------------------------------
# completion install
# ---------------------------------------------------------------------------


@completion_cmd.command(name="install")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"], case_sensitive=False))
def completion_install(shell: str) -> None:
    """Install the completion script to the appropriate shell config file.

    For **bash** and **zsh**, appends an ``eval`` line to the shell RC file
    (``~/.bashrc`` or ``~/.zshrc``).  For **fish**, writes the completion
    script directly to ``~/.config/fish/completions/kanboard.fish``.

    Args:
        shell: Target shell — one of ``bash``, ``zsh``, or ``fish``.
    """
    import kanboard_cli.commands.completion as _this_module

    shell = shell.lower()
    source = _get_completion_source(shell)

    if shell == "fish":
        fish_dir: Path = _this_module.FISH_COMPLETIONS_DIR
        fish_dir.mkdir(parents=True, exist_ok=True)
        target = fish_dir / "kanboard.fish"
        target.write_text(source)
        click.echo(f"✓ Fish completion installed to {target}")
        click.echo("Open a new shell session to activate completions.")
    else:
        init_attr = _SHELL_INIT_FILE[shell]
        init_file: Path = getattr(_this_module, init_attr)
        eval_line = f'\n# kanboard completion\neval "$(kanboard completion {shell})"\n'
        existing = init_file.read_text(encoding="utf-8") if init_file.exists() else ""
        if "kanboard completion" in existing:
            click.echo(f"Completion already present in {init_file} — skipping.")
        else:
            with init_file.open("a", encoding="utf-8") as fh:
                fh.write(eval_line)
            click.echo(f"✓ {shell.capitalize()} completion installed to {init_file}")
            click.echo(f"Restart your shell or run:  source {init_file}")
