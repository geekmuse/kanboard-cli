"""Workflow plugin discovery and loading.

Scans ``~/.config/kanboard/workflows/`` for Python files (``.py``) and
packages (directories with ``__init__.py``).  Each discovered module is
loaded via :mod:`importlib.util` and inspected for concrete
:class:`~kanboard_cli.workflows.base.BaseWorkflow` subclasses.

Usage::

    from kanboard_cli.workflow_loader import discover_workflows

    workflows = discover_workflows()
    for wf in workflows:
        wf.register_commands(cli)
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import sys
from pathlib import Path

from kanboard.config import WORKFLOW_DIR
from kanboard_cli.workflows.base import BaseWorkflow

logger = logging.getLogger(__name__)


def _load_module_from_path(name: str, path: Path) -> list[BaseWorkflow]:
    """Load a Python module from *path* and return workflow instances.

    Args:
        name: Fully-qualified module name to assign.
        path: Filesystem path to the ``.py`` file to load.

    Returns:
        A list of instantiated :class:`BaseWorkflow` subclasses found in
        the module.  Returns an empty list when the module contains no
        valid workflow classes or fails to load.
    """
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            logger.warning("Could not create module spec for %s", path)
            return []

        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    except Exception:
        logger.warning("Failed to load workflow from %s", path, exc_info=True)
        return []

    workflows: list[BaseWorkflow] = []
    for _attr_name, obj in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(obj, BaseWorkflow)
            and obj is not BaseWorkflow
            and not inspect.isabstract(obj)
        ):
            try:
                workflows.append(obj())
            except Exception:
                logger.warning(
                    "Failed to instantiate workflow class %s from %s",
                    obj.__name__,
                    path,
                    exc_info=True,
                )
    return workflows


def discover_workflows(
    workflow_dir: Path | None = None,
) -> list[BaseWorkflow]:
    """Discover and instantiate all workflow plugins.

    Scans *workflow_dir* (defaulting to ``~/.config/kanboard/workflows/``)
    for ``.py`` files and packages (directories containing
    ``__init__.py``).  Each candidate is loaded and inspected for concrete
    :class:`BaseWorkflow` subclasses.

    Args:
        workflow_dir: Directory to scan.  Defaults to
            :data:`~kanboard.config.WORKFLOW_DIR` when ``None``.

    Returns:
        A list of instantiated workflow objects, sorted by name.  Returns
        an empty list when the directory does not exist or contains no
        valid workflows.
    """
    scan_dir = workflow_dir if workflow_dir is not None else WORKFLOW_DIR

    if not scan_dir.is_dir():
        logger.debug("Workflow directory %s does not exist - skipping", scan_dir)
        return []

    workflows: list[BaseWorkflow] = []

    for entry in sorted(scan_dir.iterdir()):
        module_name = f"kanboard_workflows.{entry.stem}"

        if entry.is_file() and entry.suffix == ".py" and not entry.name.startswith("_"):
            workflows.extend(_load_module_from_path(module_name, entry))
        elif entry.is_dir() and (entry / "__init__.py").exists():
            workflows.extend(_load_module_from_path(module_name, entry / "__init__.py"))

    # Sort by workflow name for deterministic ordering.
    workflows.sort(key=lambda w: w.name)

    return workflows
