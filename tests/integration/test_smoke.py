"""Smoke integration tests — basic connectivity and health checks.

These tests verify that the SDK can connect to the Docker-backed Kanboard
instance and receive valid responses from the JSON-RPC API.  They serve as
a fast sanity check before running the full integration suite.
"""

from __future__ import annotations

import pytest

from kanboard.client import KanboardClient


@pytest.mark.integration
def test_get_version_returns_non_empty_string(kanboard_client: KanboardClient) -> None:
    """``getVersion`` returns a non-empty version string.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    version = kanboard_client.application.get_version()
    assert isinstance(version, str), "getVersion should return a string"
    assert version, "getVersion should return a non-empty string"


@pytest.mark.integration
def test_get_version_looks_like_semver(kanboard_client: KanboardClient) -> None:
    """``getVersion`` returns a string containing at least one dot (semver-like).

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    version = kanboard_client.application.get_version()
    assert "." in version, f"Expected semver-like version, got: {version!r}"


@pytest.mark.integration
def test_get_timezone_returns_string(kanboard_client: KanboardClient) -> None:
    """``getTimezone`` returns a non-empty timezone string.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    tz = kanboard_client.application.get_timezone()
    assert isinstance(tz, str), "getTimezone should return a string"
    assert tz, "getTimezone should return a non-empty string"


@pytest.mark.integration
def test_get_color_list_returns_dict(kanboard_client: KanboardClient) -> None:
    """``getColorList`` returns a non-empty dict of colour identifiers.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    colors = kanboard_client.application.get_color_list()
    assert isinstance(colors, dict), "getColorList should return a dict"
    assert colors, "getColorList should return a non-empty dict"


@pytest.mark.integration
def test_get_application_roles_returns_dict(kanboard_client: KanboardClient) -> None:
    """``getApplicationRoles`` returns a non-empty dict of role definitions.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    roles = kanboard_client.application.get_application_roles()
    assert isinstance(roles, dict), "getApplicationRoles should return a dict"
    assert roles, "getApplicationRoles should return a non-empty dict"


@pytest.mark.integration
def test_kanboard_url_fixture(kanboard_url: str) -> None:
    """The ``kanboard_url`` fixture returns a non-empty URL string.

    Args:
        kanboard_url: The Kanboard JSON-RPC endpoint URL fixture.
    """
    assert kanboard_url
    assert kanboard_url.startswith("http"), f"Expected http(s) URL, got: {kanboard_url!r}"
    assert "jsonrpc.php" in kanboard_url
