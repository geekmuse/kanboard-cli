"""Configuration system for the Kanboard SDK.

Implements a layered configuration resolution strategy::

    TOML config file  →  environment variables  →  CLI flags

Supported config file format (``~/.config/kanboard/config.toml``)::

    [settings]
    default_profile = "work"

    [profiles.default]
    url = "http://localhost/jsonrpc.php"
    token = "my-api-token"
    output_format = "table"

    [profiles.work]
    url = "https://kanboard.example.com/jsonrpc.php"
    token = "another-token"

    [workflows.my_workflow]
    some_setting = "value"
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kanboard.exceptions import KanboardConfigError

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

CONFIG_DIR: Path = Path.home() / ".config" / "kanboard"
"""Directory that holds the Kanboard CLI / SDK configuration."""

CONFIG_FILE: Path = CONFIG_DIR / "config.toml"
"""Path to the primary TOML configuration file."""

WORKFLOW_DIR: Path = CONFIG_DIR / "workflows"
"""Directory where workflow plugin scripts/configs reside."""

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_ENV_URL = "KANBOARD_URL"
_ENV_TOKEN = "KANBOARD_TOKEN"
_ENV_PROFILE = "KANBOARD_PROFILE"
_ENV_OUTPUT_FORMAT = "KANBOARD_OUTPUT_FORMAT"


def _load_toml(path: Path) -> dict[str, Any]:
    """Load and parse a TOML file, returning an empty dict if the file is missing.

    Args:
        path: Path to the TOML file to load.

    Returns:
        The parsed TOML data as a dictionary, or an empty dict if the file
        does not exist.
    """
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KanboardConfig:
    """Resolved, immutable configuration for the Kanboard SDK.

    All fields are resolved through a layered strategy so the most specific
    source wins:

    1. CLI argument (parameter passed to :meth:`resolve`)
    2. Environment variable
    3. Config file value for the active profile
    4. Built-in default (``output_format`` only; ``url`` and ``token`` are
       required)

    Attributes:
        url: The Kanboard JSON-RPC endpoint URL.
        token: The Kanboard API token used for authentication.
        profile: The active configuration profile name.
        output_format: The default output format (``table``, ``json``,
            ``csv``, or ``quiet``).
    """

    url: str
    token: str
    profile: str
    output_format: str

    @classmethod
    def resolve(
        cls,
        url: str | None = None,
        token: str | None = None,
        profile: str | None = None,
        output_format: str | None = None,
        config_file: Path | None = None,
    ) -> KanboardConfig:
        """Resolve configuration from all available layers.

        Profile selection order:

        1. ``profile`` CLI argument
        2. ``KANBOARD_PROFILE`` environment variable
        3. ``settings.default_profile`` key in the config file
        4. Literal ``"default"``

        Field resolution order for ``url``, ``token``, and ``output_format``:

        1. CLI argument (parameter passed to this method)
        2. Environment variable (``KANBOARD_URL`` / ``KANBOARD_TOKEN`` /
           ``KANBOARD_OUTPUT_FORMAT``)
        3. Config file value for the active profile
        4. Built-in default (``"table"`` for ``output_format`` only)

        Args:
            url: Kanboard JSON-RPC endpoint URL from a CLI flag, or ``None``.
            token: Kanboard API token from a CLI flag, or ``None``.
            profile: Profile name from a CLI flag, or ``None``.
            output_format: Output format from a CLI flag, or ``None``.
            config_file: Path to the TOML config file.  Defaults to
                :data:`CONFIG_FILE` when ``None``.

        Returns:
            A fully resolved, frozen :class:`KanboardConfig` instance.

        Raises:
            KanboardConfigError: If ``url`` or ``token`` cannot be resolved
                from any layer.  The error message includes actionable advice
                on how to supply the missing value.
        """
        cfg_path = config_file if config_file is not None else CONFIG_FILE
        raw_cfg = _load_toml(cfg_path)

        # ── Profile resolution ────────────────────────────────────────────
        active_profile: str = (
            profile
            or os.environ.get(_ENV_PROFILE)
            or raw_cfg.get("settings", {}).get("default_profile")
            or "default"
        )

        profile_data: dict[str, Any] = raw_cfg.get("profiles", {}).get(active_profile, {})

        # ── Field resolution ──────────────────────────────────────────────
        resolved_url: str | None = url or os.environ.get(_ENV_URL) or profile_data.get("url")

        resolved_token: str | None = (
            token or os.environ.get(_ENV_TOKEN) or profile_data.get("token")
        )

        resolved_output_format: str = (
            output_format
            or os.environ.get(_ENV_OUTPUT_FORMAT)
            or profile_data.get("output_format")
            or "table"
        )

        # ── Required field validation ─────────────────────────────────────
        if not resolved_url:
            raise KanboardConfigError(
                "Kanboard URL is required. "
                "Set it via --url, the KANBOARD_URL environment variable, "
                "or 'url' in your config file profile.",
                field="url",
            )

        if not resolved_token:
            raise KanboardConfigError(
                "Kanboard API token is required. "
                "Set it via --token, the KANBOARD_TOKEN environment variable, "
                "or 'token' in your config file profile.",
                field="token",
            )

        return cls(
            url=resolved_url,
            token=resolved_token,
            profile=active_profile,
            output_format=resolved_output_format,
        )


def get_workflow_config(
    name: str,
    config_file: Path | None = None,
) -> dict[str, Any]:
    """Load configuration for a named workflow plugin.

    Reads the ``[workflows.<name>]`` section from the TOML config file.

    Args:
        name: The workflow plugin name (the key under ``[workflows]``).
        config_file: Path to the TOML config file.  Defaults to
            :data:`CONFIG_FILE` when ``None``.

    Returns:
        A dictionary of workflow configuration values, or an empty dict
        if the ``[workflows.<name>]`` section is absent from the config file
        (including when the file does not exist).
    """
    cfg_path = config_file if config_file is not None else CONFIG_FILE
    raw_cfg = _load_toml(cfg_path)
    return raw_cfg.get("workflows", {}).get(name, {})
