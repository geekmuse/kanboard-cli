"""Unit tests for src/kanboard/config.py."""

from pathlib import Path

import pytest

from kanboard.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    WORKFLOW_DIR,
    KanboardConfig,
    _load_toml,
    get_workflow_config,
)
from kanboard.exceptions import KanboardConfigError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_toml(tmp_path: Path, content: str) -> Path:
    """Write a TOML file to tmp_path and return its path."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(content, encoding="utf-8")
    return cfg


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------


def test_config_dir_is_path() -> None:
    assert isinstance(CONFIG_DIR, Path)
    assert CONFIG_DIR.name == "kanboard"


def test_config_file_is_under_config_dir() -> None:
    assert CONFIG_FILE.parent == CONFIG_DIR
    assert CONFIG_FILE.name == "config.toml"


def test_workflow_dir_is_under_config_dir() -> None:
    assert WORKFLOW_DIR.parent == CONFIG_DIR
    assert WORKFLOW_DIR.name == "workflows"


# ---------------------------------------------------------------------------
# _load_toml
# ---------------------------------------------------------------------------


def test_load_toml_reads_file(tmp_path: Path) -> None:
    cfg = _write_toml(tmp_path, '[section]\nkey = "value"\n')
    data = _load_toml(cfg)
    assert data == {"section": {"key": "value"}}


def test_load_toml_missing_file_returns_empty(tmp_path: Path) -> None:
    result = _load_toml(tmp_path / "nonexistent.toml")
    assert result == {}


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — full resolution from config file
# ---------------------------------------------------------------------------


def test_resolve_full_from_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """All values resolved from the config file."""
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[settings]
default_profile = "default"

[profiles.default]
url = "http://kb.example.com/jsonrpc.php"
token = "secret-token"
output_format = "json"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)

    assert config.url == "http://kb.example.com/jsonrpc.php"
    assert config.token == "secret-token"
    assert config.profile == "default"
    assert config.output_format == "json"


def test_resolve_default_output_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """output_format defaults to 'table' when not specified anywhere."""
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb.example.com/jsonrpc.php"
token = "tok"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.output_format == "table"


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — env var layer overrides config file
# ---------------------------------------------------------------------------


def test_env_url_overrides_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KANBOARD_URL", "http://env-override/jsonrpc.php")
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://from-file/jsonrpc.php"
token = "tok"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.url == "http://env-override/jsonrpc.php"


def test_env_token_overrides_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.setenv("KANBOARD_TOKEN", "env-token")
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb.example.com/jsonrpc.php"
token = "file-token"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.token == "env-token"


def test_env_output_format_overrides_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.setenv("KANBOARD_OUTPUT_FORMAT", "csv")

    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb.example.com/jsonrpc.php"
token = "tok"
output_format = "json"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.output_format == "csv"


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — CLI arg layer overrides env vars
# ---------------------------------------------------------------------------


def test_cli_url_overrides_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KANBOARD_URL", "http://env/jsonrpc.php")
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(tmp_path, "")
    config = KanboardConfig.resolve(
        url="http://cli/jsonrpc.php",
        token="tok",
        config_file=cfg_file,
    )
    assert config.url == "http://cli/jsonrpc.php"


def test_cli_token_overrides_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.setenv("KANBOARD_TOKEN", "env-token")
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(tmp_path, "")
    config = KanboardConfig.resolve(
        url="http://kb/jsonrpc.php",
        token="cli-token",
        config_file=cfg_file,
    )
    assert config.token == "cli-token"


def test_cli_output_format_overrides_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.setenv("KANBOARD_OUTPUT_FORMAT", "csv")

    cfg_file = _write_toml(tmp_path, "")
    config = KanboardConfig.resolve(
        url="http://kb/jsonrpc.php",
        token="tok",
        output_format="quiet",
        config_file=cfg_file,
    )
    assert config.output_format == "quiet"


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — missing config file falls back to env vars
# ---------------------------------------------------------------------------


def test_missing_config_file_uses_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KANBOARD_URL", "http://env/jsonrpc.php")
    monkeypatch.setenv("KANBOARD_TOKEN", "env-tok")
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    config = KanboardConfig.resolve(config_file=tmp_path / "nonexistent.toml")
    assert config.url == "http://env/jsonrpc.php"
    assert config.token == "env-tok"
    assert config.profile == "default"
    assert config.output_format == "table"


def test_missing_config_file_uses_cli_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    config = KanboardConfig.resolve(
        url="http://cli/jsonrpc.php",
        token="cli-tok",
        config_file=tmp_path / "nonexistent.toml",
    )
    assert config.url == "http://cli/jsonrpc.php"
    assert config.token == "cli-tok"


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — missing required fields raise KanboardConfigError
# ---------------------------------------------------------------------------


def test_missing_url_raises_config_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(tmp_path, "[profiles.default]\ntoken = 'tok'\n")
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)

    assert exc_info.value.field == "url"
    assert "KANBOARD_URL" in str(exc_info.value)


def test_missing_token_raises_config_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        "[profiles.default]\nurl = 'http://kb/jsonrpc.php'\n",
    )
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)

    assert exc_info.value.field == "token"
    assert "KANBOARD_TOKEN" in str(exc_info.value)


def test_missing_url_and_token_raises_url_error_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(tmp_path, "")
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)

    # url is validated first
    assert exc_info.value.field == "url"


def test_config_error_message_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(tmp_path, "")
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)

    msg = str(exc_info.value)
    assert "--url" in msg or "KANBOARD_URL" in msg


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — profile selection
# ---------------------------------------------------------------------------


def test_profile_from_cli_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.setenv("KANBOARD_PROFILE", "env-profile")
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[settings]
default_profile = "file-profile"

[profiles.cli-profile]
url = "http://cli-profile/jsonrpc.php"
token = "cli-tok"
""",
    )
    config = KanboardConfig.resolve(profile="cli-profile", config_file=cfg_file)
    assert config.profile == "cli-profile"
    assert config.url == "http://cli-profile/jsonrpc.php"


def test_profile_from_env_var_overrides_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.setenv("KANBOARD_PROFILE", "env-profile")
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[settings]
default_profile = "file-profile"

[profiles.env-profile]
url = "http://env-profile/jsonrpc.php"
token = "env-tok"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.profile == "env-profile"
    assert config.url == "http://env-profile/jsonrpc.php"


def test_profile_from_settings_default_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[settings]
default_profile = "work"

[profiles.work]
url = "http://work/jsonrpc.php"
token = "work-tok"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.profile == "work"
    assert config.url == "http://work/jsonrpc.php"


def test_profile_fallback_to_default_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No profile hint anywhere → active profile is the literal 'default'."""
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://default/jsonrpc.php"
token = "default-tok"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.profile == "default"


def test_cli_profile_overrides_env_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.setenv("KANBOARD_PROFILE", "env-profile")
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.cli-profile]
url = "http://cli/jsonrpc.php"
token = "cli-tok"
""",
    )
    config = KanboardConfig.resolve(profile="cli-profile", config_file=cfg_file)
    assert config.profile == "cli-profile"


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — unknown profile falls back to empty profile data
# ---------------------------------------------------------------------------


def test_unknown_profile_falls_back_to_cli_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(tmp_path, "")
    config = KanboardConfig.resolve(
        url="http://direct/jsonrpc.php",
        token="direct-tok",
        profile="nonexistent",
        config_file=cfg_file,
    )
    assert config.profile == "nonexistent"
    assert config.url == "http://direct/jsonrpc.php"


# ---------------------------------------------------------------------------
# KanboardConfig — frozen dataclass properties
# ---------------------------------------------------------------------------


def test_config_is_frozen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KANBOARD_URL", raising=False)
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_PROFILE", raising=False)
    monkeypatch.delenv("KANBOARD_OUTPUT_FORMAT", raising=False)

    cfg_file = _write_toml(
        tmp_path,
        "[profiles.default]\nurl='http://kb/jsonrpc.php'\ntoken='tok'\n",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    with pytest.raises(Exception):  # noqa: B017
        config.url = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_workflow_config
# ---------------------------------------------------------------------------


def test_get_workflow_config_returns_section(tmp_path: Path) -> None:
    cfg_file = _write_toml(
        tmp_path,
        """
[workflows.deploy]
env = "prod"
retries = 3
""",
    )
    result = get_workflow_config("deploy", config_file=cfg_file)
    assert result == {"env": "prod", "retries": 3}


def test_get_workflow_config_missing_name_returns_empty(tmp_path: Path) -> None:
    cfg_file = _write_toml(
        tmp_path,
        """
[workflows.other]
key = "value"
""",
    )
    result = get_workflow_config("nonexistent", config_file=cfg_file)
    assert result == {}


def test_get_workflow_config_missing_file_returns_empty(tmp_path: Path) -> None:
    result = get_workflow_config("any", config_file=tmp_path / "no-such-file.toml")
    assert result == {}


def test_get_workflow_config_no_workflows_section_returns_empty(tmp_path: Path) -> None:
    cfg_file = _write_toml(tmp_path, "[settings]\ndefault_profile = 'default'\n")
    result = get_workflow_config("anything", config_file=cfg_file)
    assert result == {}


def test_get_workflow_config_default_path_used_when_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Passing config_file=None should trigger load from CONFIG_FILE (which may not exist)."""
    # Point CONFIG_FILE to a non-existent path; function must not raise
    import kanboard.config as cfg_mod

    fake_path = tmp_path / "missing.toml"
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", fake_path)
    result = get_workflow_config("something")
    assert result == {}


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — auth_mode / username / password resolution
# ---------------------------------------------------------------------------


def test_auth_mode_defaults_to_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """auth_mode defaults to 'app' when not specified anywhere."""
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(
        tmp_path, "[profiles.default]\nurl='http://kb/jsonrpc.php'\ntoken='tok'\n"
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.auth_mode == "app"


def test_auth_mode_from_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """auth_mode is read from the profile config file."""
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    monkeypatch.delenv("KANBOARD_USERNAME", raising=False)
    monkeypatch.delenv("KANBOARD_PASSWORD", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb/jsonrpc.php"
auth_mode = "user"
username = "admin"
password = "secret"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.auth_mode == "user"
    assert config.username == "admin"
    assert config.password == "secret"


def test_auth_mode_env_var_overrides_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KANBOARD_AUTH_MODE env var overrides profile value."""
    monkeypatch.setenv("KANBOARD_AUTH_MODE", "user")
    monkeypatch.setenv("KANBOARD_USERNAME", "env-user")
    monkeypatch.setenv("KANBOARD_PASSWORD", "env-pass")
    cfg_file = _write_toml(
        tmp_path,
        "[profiles.default]\nurl='http://kb/jsonrpc.php'\nauth_mode='app'\ntoken='tok'\n",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.auth_mode == "user"
    assert config.username == "env-user"
    assert config.password == "env-pass"


def test_auth_mode_cli_arg_overrides_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI auth_mode arg overrides env var."""
    monkeypatch.setenv("KANBOARD_AUTH_MODE", "app")
    monkeypatch.setenv("KANBOARD_USERNAME", "env-user")
    monkeypatch.setenv("KANBOARD_PASSWORD", "env-pass")
    cfg_file = _write_toml(tmp_path, "[profiles.default]\nurl='http://kb/jsonrpc.php'\n")
    config = KanboardConfig.resolve(
        auth_mode="user",
        username="cli-user",
        password="cli-pass",
        config_file=cfg_file,
    )
    assert config.auth_mode == "user"
    assert config.username == "cli-user"
    assert config.password == "cli-pass"


def test_user_auth_mode_does_not_require_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No KanboardConfigError raised when token is absent in user auth mode."""
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    monkeypatch.delenv("KANBOARD_USERNAME", raising=False)
    monkeypatch.delenv("KANBOARD_PASSWORD", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb/jsonrpc.php"
auth_mode = "user"
username = "admin"
password = "secret"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.token == ""


def test_user_auth_mode_missing_username_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KanboardConfigError raised when username is missing in user auth mode."""
    monkeypatch.delenv("KANBOARD_USERNAME", raising=False)
    monkeypatch.delenv("KANBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        "[profiles.default]\nurl='http://kb/jsonrpc.php'\nauth_mode='user'\npassword='pass'\n",
    )
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)
    assert exc_info.value.field == "username"
    assert "KANBOARD_USERNAME" in str(exc_info.value)


def test_user_auth_mode_missing_password_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KanboardConfigError raised when password is missing in user auth mode."""
    monkeypatch.delenv("KANBOARD_USERNAME", raising=False)
    monkeypatch.delenv("KANBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        "[profiles.default]\nurl='http://kb/jsonrpc.php'\nauth_mode='user'\nusername='admin'\n",
    )
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)
    assert exc_info.value.field == "password"
    assert "KANBOARD_PASSWORD" in str(exc_info.value)


def test_app_auth_mode_still_requires_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token is still required when auth_mode is 'app' (existing behaviour)."""
    monkeypatch.delenv("KANBOARD_TOKEN", raising=False)
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(tmp_path, "[profiles.default]\nurl='http://kb/jsonrpc.php'\n")
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)
    assert exc_info.value.field == "token"


def test_username_from_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KANBOARD_USERNAME env var is resolved for user auth mode."""
    monkeypatch.setenv("KANBOARD_USERNAME", "env-admin")
    monkeypatch.setenv("KANBOARD_PASSWORD", "env-pass")
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(
        tmp_path, "[profiles.default]\nurl='http://kb/jsonrpc.php'\nauth_mode='user'\n"
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.username == "env-admin"


def test_password_from_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KANBOARD_PASSWORD env var is resolved for user auth mode."""
    monkeypatch.setenv("KANBOARD_USERNAME", "admin")
    monkeypatch.setenv("KANBOARD_PASSWORD", "env-secret")
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(
        tmp_path, "[profiles.default]\nurl='http://kb/jsonrpc.php'\nauth_mode='user'\n"
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.password == "env-secret"


def test_username_none_in_app_auth_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """username is None when not configured in app auth mode."""
    monkeypatch.delenv("KANBOARD_USERNAME", raising=False)
    monkeypatch.delenv("KANBOARD_AUTH_MODE", raising=False)
    cfg_file = _write_toml(
        tmp_path, "[profiles.default]\nurl='http://kb/jsonrpc.php'\ntoken='tok'\n"
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.username is None
    assert config.password is None


# ---------------------------------------------------------------------------
# KanboardConfig.resolve — portfolio_backend field
# ---------------------------------------------------------------------------


def _base_cfg_file(tmp_path: Path) -> Path:
    """Write a minimal valid config file with url + token."""
    return _write_toml(
        tmp_path,
        "[profiles.default]\nurl='http://kb/jsonrpc.php'\ntoken='tok'\n",
    )


def test_portfolio_backend_defaults_to_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_backend defaults to 'local' when not configured anywhere."""
    monkeypatch.delenv("KANBOARD_PORTFOLIO_BACKEND", raising=False)
    config = KanboardConfig.resolve(config_file=_base_cfg_file(tmp_path))
    assert config.portfolio_backend == "local"


def test_portfolio_backend_from_toml_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_backend is read from the TOML profile."""
    monkeypatch.delenv("KANBOARD_PORTFOLIO_BACKEND", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb/jsonrpc.php"
token = "tok"
portfolio_backend = "remote"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.portfolio_backend == "remote"


def test_portfolio_backend_local_from_toml_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_backend = 'local' is accepted from TOML profile."""
    monkeypatch.delenv("KANBOARD_PORTFOLIO_BACKEND", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb/jsonrpc.php"
token = "tok"
portfolio_backend = "local"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.portfolio_backend == "local"


def test_portfolio_backend_env_var_overrides_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KANBOARD_PORTFOLIO_BACKEND env var overrides the TOML profile value."""
    monkeypatch.setenv("KANBOARD_PORTFOLIO_BACKEND", "remote")
    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb/jsonrpc.php"
token = "tok"
portfolio_backend = "local"
""",
    )
    config = KanboardConfig.resolve(config_file=cfg_file)
    assert config.portfolio_backend == "remote"


def test_portfolio_backend_env_var_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KANBOARD_PORTFOLIO_BACKEND=local is accepted."""
    monkeypatch.setenv("KANBOARD_PORTFOLIO_BACKEND", "local")
    config = KanboardConfig.resolve(config_file=_base_cfg_file(tmp_path))
    assert config.portfolio_backend == "local"


def test_portfolio_backend_cli_overrides_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cli_portfolio_backend parameter overrides KANBOARD_PORTFOLIO_BACKEND env var."""
    monkeypatch.setenv("KANBOARD_PORTFOLIO_BACKEND", "remote")
    config = KanboardConfig.resolve(
        cli_portfolio_backend="local",
        config_file=_base_cfg_file(tmp_path),
    )
    assert config.portfolio_backend == "local"


def test_portfolio_backend_cli_remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cli_portfolio_backend='remote' is accepted."""
    monkeypatch.delenv("KANBOARD_PORTFOLIO_BACKEND", raising=False)
    config = KanboardConfig.resolve(
        cli_portfolio_backend="remote",
        config_file=_base_cfg_file(tmp_path),
    )
    assert config.portfolio_backend == "remote"


def test_portfolio_backend_invalid_value_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KanboardConfigError raised when portfolio_backend is not 'local' or 'remote'."""
    monkeypatch.delenv("KANBOARD_PORTFOLIO_BACKEND", raising=False)
    cfg_file = _write_toml(
        tmp_path,
        """
[profiles.default]
url = "http://kb/jsonrpc.php"
token = "tok"
portfolio_backend = "database"
""",
    )
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=cfg_file)
    assert exc_info.value.field == "portfolio_backend"
    assert "database" in str(exc_info.value)
    assert "local" in str(exc_info.value)
    assert "remote" in str(exc_info.value)


def test_portfolio_backend_invalid_env_var_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KanboardConfigError raised when KANBOARD_PORTFOLIO_BACKEND has an invalid value."""
    monkeypatch.setenv("KANBOARD_PORTFOLIO_BACKEND", "s3")
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=_base_cfg_file(tmp_path))
    assert exc_info.value.field == "portfolio_backend"
    assert "s3" in str(exc_info.value)


def test_portfolio_backend_invalid_cli_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KanboardConfigError raised when cli_portfolio_backend has an invalid value."""
    monkeypatch.delenv("KANBOARD_PORTFOLIO_BACKEND", raising=False)
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(
            cli_portfolio_backend="invalid",
            config_file=_base_cfg_file(tmp_path),
        )
    assert exc_info.value.field == "portfolio_backend"
    assert "invalid" in str(exc_info.value)


def test_portfolio_backend_error_message_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Error message mentions env var and CLI flag for discoverability."""
    monkeypatch.setenv("KANBOARD_PORTFOLIO_BACKEND", "wrong")
    with pytest.raises(KanboardConfigError) as exc_info:
        KanboardConfig.resolve(config_file=_base_cfg_file(tmp_path))
    msg = str(exc_info.value)
    assert "KANBOARD_PORTFOLIO_BACKEND" in msg
    assert "--portfolio-backend" in msg


# ---------------------------------------------------------------------------
# Integration: re-exported from kanboard package
# ---------------------------------------------------------------------------


def test_re_exported_from_kanboard_package() -> None:
    from kanboard import (
        CONFIG_DIR,
        CONFIG_FILE,
        WORKFLOW_DIR,
        KanboardConfig,
        get_workflow_config,
    )

    assert CONFIG_DIR is not None
    assert CONFIG_FILE is not None
    assert WORKFLOW_DIR is not None
    assert KanboardConfig is not None
    assert get_workflow_config is not None
