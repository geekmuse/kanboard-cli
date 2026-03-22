"""Base class for kanboard-cli workflow plugins.

All workflow plugins must subclass :class:`BaseWorkflow` and implement
the required abstract properties and methods.  The workflow loader
discovers subclasses automatically when scanning the user's workflow
directory (``~/.config/kanboard/workflows/``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import click

from kanboard.config import get_workflow_config


class BaseWorkflow(ABC):
    """Abstract base class that every workflow plugin must subclass.

    Subclasses **must** implement:

    * :attr:`name` - a short, unique identifier for the workflow.
    * :attr:`description` - a one-line human-readable summary.
    * :meth:`register_commands` - adds Click commands/groups to the CLI.

    A concrete :meth:`get_config` helper is provided so plugins can read
    their ``[workflows.<name>]`` section from the Kanboard config file.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short, unique identifier for this workflow (e.g. ``'deploy'``)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line human-readable summary of the workflow."""

    @abstractmethod
    def register_commands(self, cli: click.Group) -> None:
        """Register this workflow's Click commands/groups on *cli*.

        Args:
            cli: The root Click group to attach commands to.
        """

    def get_config(self) -> dict[str, Any]:
        """Load this workflow's configuration from the TOML config file.

        Reads the ``[workflows.<name>]`` section and returns its contents
        as a plain dictionary.  Returns an empty dict when the section is
        absent.

        Returns:
            Workflow-specific configuration dictionary.
        """
        return get_workflow_config(self.name)
