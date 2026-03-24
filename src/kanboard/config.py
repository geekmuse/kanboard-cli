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
    auth_mode = "app"

    [profiles.work]
    url = "https://kanboard.example.com/jsonrpc.php"
    token = "another-token"

    [profiles.me]
    url = "https://kanboard.example.com/jsonrpc.php"
    auth_mode = "user"
    username = "admin"
    password = "my-password"

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
_ENV_AUTH_MODE = "KANBOARD_AUTH_MODE"
_ENV_USERNAME = "KANBOARD_USERNAME"
_ENV_PASSWORD = "KANBOARD_PASSWORD"
_ENV_PORTFOLIO_BACKEND = "KANBOARD_PORTFOLIO_BACKEND"

_VALID_PORTFOLIO_BACKENDS = frozenset({"local", "remote"})


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
    4. Built-in default (``output_format`` and ``auth_mode`` only;
       ``url`` is always required; ``token`` is required for app auth
       and ``username`` + ``password`` are required for user auth)

    Attributes:
        url: The Kanboard JSON-RPC endpoint URL.
        token: The Kanboard API token used for Application API authentication.
            Required when ``auth_mode`` is ``'app'``; may be empty for user
            auth mode.
        profile: The active configuration profile name.
        output_format: The default output format (``table``, ``json``,
            ``csv``, or ``quiet``).
        auth_mode: Authentication mode — ``'app'`` (default, JSON-RPC token) or
            ``'user'`` (HTTP Basic Auth with username + password).
        username: Username for User API authentication.  Required when
            ``auth_mode`` is ``'user'``.
        password: Password or personal access token for User API
            authentication.  Required when ``auth_mode`` is ``'user'``.
        portfolio_backend: The portfolio orchestration backend to use.  Either
            ``'local'`` (default, uses the local JSON file store) or
            ``'remote'`` (uses the Kanboard Portfolio Plugin API).
    """

    url: str
    token: str
    profile: str
    output_format: str
    auth_mode: str = "app"
    username: str | None = None
    password: str | None = None
    portfolio_backend: str = "local"

    @classmethod
    def resolve(
        cls,
        url: str | None = None,
        token: str | None = None,
        profile: str | None = None,
        output_format: str | None = None,
        auth_mode: str | None = None,
        username: str | None = None,
        password: str | None = None,
        config_file: Path | None = None,
        cli_portfolio_backend: str | None = None,
    ) -> KanboardConfig:
        """Resolve configuration from all available layers.

        Profile selection order:

        1. ``profile`` CLI argument
        2. ``KANBOARD_PROFILE`` environment variable
        3. ``settings.default_profile`` key in the config file
        4. Literal ``"default"``

        Field resolution order for ``url``, ``token``, ``output_format``,
        ``auth_mode``, ``username``, ``password``, and ``portfolio_backend``:

        1. CLI argument (parameter passed to this method)
        2. Environment variable (``KANBOARD_URL`` / ``KANBOARD_TOKEN`` /
           ``KANBOARD_OUTPUT_FORMAT`` / ``KANBOARD_AUTH_MODE`` /
           ``KANBOARD_USERNAME`` / ``KANBOARD_PASSWORD`` /
           ``KANBOARD_PORTFOLIO_BACKEND``)
        3. Config file value for the active profile
        4. Built-in default (``"table"`` for ``output_format``;
           ``"app"`` for ``auth_mode``; ``"local"`` for ``portfolio_backend``)

        Required fields depend on ``auth_mode``:

        - ``'app'`` (default): ``url`` and ``token`` are required.
        - ``'user'``: ``url``, ``username``, and ``password`` are required.
          ``token`` is optional and may be left unset.

        Args:
            url: Kanboard JSON-RPC endpoint URL from a CLI flag, or ``None``.
            token: Kanboard API token from a CLI flag, or ``None``.
            profile: Profile name from a CLI flag, or ``None``.
            output_format: Output format from a CLI flag, or ``None``.
            auth_mode: Authentication mode (``'app'`` or ``'user'``) from a
                CLI flag, or ``None`` to fall back to env var / config file.
            username: Username for User API auth from a CLI flag, or ``None``.
            password: Password for User API auth from a CLI flag, or ``None``.
            config_file: Path to the TOML config file.  Defaults to
                :data:`CONFIG_FILE` when ``None``.
            cli_portfolio_backend: Portfolio backend selection from a CLI flag
                (``'local'`` or ``'remote'``), or ``None`` to fall back to env
                var / config file / default.

        Returns:
            A fully resolved, frozen :class:`KanboardConfig` instance.

        Raises:
            KanboardConfigError: If required fields cannot be resolved from any
                layer, or if ``portfolio_backend`` is not ``'local'`` or
                ``'remote'``.  The error message includes actionable advice on
                how to supply the missing value.
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

        resolved_auth_mode: str = (
            auth_mode or os.environ.get(_ENV_AUTH_MODE) or profile_data.get("auth_mode") or "app"
        )

        resolved_username: str | None = (
            username or os.environ.get(_ENV_USERNAME) or profile_data.get("username")
        )

        resolved_password: str | None = (
            password or os.environ.get(_ENV_PASSWORD) or profile_data.get("password")
        )

        resolved_portfolio_backend: str = (
            cli_portfolio_backend
            or os.environ.get(_ENV_PORTFOLIO_BACKEND)
            or profile_data.get("portfolio_backend")
            or "local"
        )

        # ── Required field validation ─────────────────────────────────────
        if not resolved_url:
            raise KanboardConfigError(
                "Kanboard URL is required. "
                "Set it via --url, the KANBOARD_URL environment variable, "
                "or 'url' in your config file profile.",
                field="url",
            )

        if resolved_auth_mode == "user":
            if not resolved_username:
                raise KanboardConfigError(
                    "Username is required for user auth mode. "
                    "Set it via --username, the KANBOARD_USERNAME environment variable, "
                    "or 'username' in your config file profile.",
                    field="username",
                )
            if not resolved_password:
                raise KanboardConfigError(
                    "Password is required for user auth mode. "
                    "Set it via --password, the KANBOARD_PASSWORD environment variable, "
                    "or 'password' in your config file profile.",
                    field="password",
                )
        else:
            if not resolved_token:
                raise KanboardConfigError(
                    "Kanboard API token is required. "
                    "Set it via --token, the KANBOARD_TOKEN environment variable, "
                    "or 'token' in your config file profile.",
                    field="token",
                )

        if resolved_portfolio_backend not in _VALID_PORTFOLIO_BACKENDS:
            raise KanboardConfigError(
                f"Invalid portfolio_backend value '{resolved_portfolio_backend}'. "
                "Must be 'local' or 'remote'. "
                "Set it via --portfolio-backend, the KANBOARD_PORTFOLIO_BACKEND "
                "environment variable, or 'portfolio_backend' in your config file profile.",
                field="portfolio_backend",
            )

        return cls(
            url=resolved_url,
            token=resolved_token or "",
            profile=active_profile,
            output_format=resolved_output_format,
            auth_mode=resolved_auth_mode,
            username=resolved_username,
            password=resolved_password,
            portfolio_backend=resolved_portfolio_backend,
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
