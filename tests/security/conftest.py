"""Security test fixtures — shared between API fuzzing and Python-native tests.

Reuses the integration test Docker lifecycle for API fuzzing; Python-native
tests (bandit, hypothesis) run without Docker.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration (mirrors integration conftest but independent)
# ---------------------------------------------------------------------------

_KANBOARD_HOST: str = os.environ.get("KANBOARD_HOST", "http://localhost:4000")
KANBOARD_URL: str = f"{_KANBOARD_HOST}/jsonrpc.php"
KANBOARD_USERNAME: str = os.environ.get("KANBOARD_USERNAME", "admin")
KANBOARD_PASSWORD: str = os.environ.get("KANBOARD_PASSWORD", "admin")

_COMPOSE_FILE: Path = Path(__file__).parent.parent.parent / "docker-compose.test.yml"
_SCHEMA_FILE: Path = Path(__file__).parent.parent.parent.parent / "api-schema.json"

_HEALTH_TIMEOUT_SECS: int = 90
_HEALTH_POLL_INTERVAL_SECS: float = 2.0
_DOCKER_COMPOSE_UP_TIMEOUT_SECS: int = 180


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_kanboard(url: str, timeout: int = _HEALTH_TIMEOUT_SECS) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.post(
                url,
                json={"jsonrpc": "2.0", "method": "getVersion", "id": 1, "params": {}},
                auth=(KANBOARD_USERNAME, KANBOARD_PASSWORD),
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    return True
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(_HEALTH_POLL_INTERVAL_SECS)
    return False


# ---------------------------------------------------------------------------
# Docker lifecycle (session-scoped, only for fuzz_api tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def docker_kanboard_fuzz():
    """Start Docker Kanboard for API fuzzing; skip if Docker unavailable."""
    if not _is_docker_available():
        pytest.skip("Docker daemon not available — skipping API fuzz tests")
        return

    try:
        subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE_FILE), "up", "-d", "--wait"],
            check=True,
            timeout=_DOCKER_COMPOSE_UP_TIMEOUT_SECS,
        )
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"docker compose up failed (exit {exc.returncode})")
    except subprocess.TimeoutExpired:
        pytest.fail(f"docker compose up timed out after {_DOCKER_COMPOSE_UP_TIMEOUT_SECS}s")

    if not _wait_for_kanboard(KANBOARD_URL):
        pytest.fail(f"Kanboard at {KANBOARD_URL} did not become healthy")

    yield

    if not os.environ.get("KANBOARD_NO_DOCKER_TEARDOWN"):
        subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE_FILE), "down", "-v"],
            check=False,
            timeout=60,
        )


# ---------------------------------------------------------------------------
# HTTP client fixture (raw httpx for low-level fuzzing)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def fuzz_http_client(docker_kanboard_fuzz):
    """Yield an authenticated httpx.Client pointed at the Kanboard JSON-RPC endpoint."""
    with httpx.Client(
        auth=(KANBOARD_USERNAME, KANBOARD_PASSWORD),
        timeout=10.0,
    ) as client:
        yield client


@pytest.fixture(scope="session")
def unauthenticated_http_client(docker_kanboard_fuzz):
    """Yield an httpx.Client with no authentication credentials."""
    with httpx.Client(timeout=10.0) as client:
        yield client


@pytest.fixture(scope="session")
def bad_token_http_client(docker_kanboard_fuzz):
    """Yield an httpx.Client with invalid authentication credentials."""
    with httpx.Client(
        auth=("jsonrpc", "definitely-not-a-valid-token-1234"),
        timeout=10.0,
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# API method registry
# ---------------------------------------------------------------------------

# Core Kanboard methods with param signatures for fuzzing.
# Focused on the most security-relevant categories.
CORE_METHODS: list[dict[str, Any]] = [
    {"name": "getVersion", "params": []},
    {"name": "getTimezone", "params": []},
    {
        "name": "createProject",
        "params": [
            {"name": "name", "type": "string", "required": True},
        ],
    },
    {
        "name": "getProjectById",
        "params": [
            {"name": "project_id", "type": "integer", "required": True},
        ],
    },
    {
        "name": "getProjectByName",
        "params": [
            {"name": "name", "type": "string", "required": True},
        ],
    },
    {"name": "getAllProjects", "params": []},
    {
        "name": "updateProject",
        "params": [
            {"name": "project_id", "type": "integer", "required": True},
            {"name": "name", "type": "string", "required": False},
            {"name": "description", "type": "string", "required": False},
        ],
    },
    {
        "name": "removeProject",
        "params": [
            {"name": "project_id", "type": "integer", "required": True},
        ],
    },
    {
        "name": "createTask",
        "params": [
            {"name": "title", "type": "string", "required": True},
            {"name": "project_id", "type": "integer", "required": True},
        ],
    },
    {
        "name": "getTask",
        "params": [
            {"name": "task_id", "type": "integer", "required": True},
        ],
    },
    {
        "name": "updateTask",
        "params": [
            {"name": "id", "type": "integer", "required": True},
            {"name": "title", "type": "string", "required": False},
            {"name": "description", "type": "string", "required": False},
        ],
    },
    {
        "name": "searchTasks",
        "params": [
            {"name": "project_id", "type": "integer", "required": True},
            {"name": "query", "type": "string", "required": True},
        ],
    },
    {
        "name": "createComment",
        "params": [
            {"name": "task_id", "type": "integer", "required": True},
            {"name": "user_id", "type": "integer", "required": True},
            {"name": "content", "type": "string", "required": True},
        ],
    },
    {
        "name": "createUser",
        "params": [
            {"name": "username", "type": "string", "required": True},
            {"name": "password", "type": "string", "required": True},
        ],
    },
    {
        "name": "getUserByName",
        "params": [
            {"name": "username", "type": "string", "required": True},
        ],
    },
]


@pytest.fixture(scope="session")
def plugin_methods() -> list[dict[str, Any]]:
    """Load plugin API methods from api-schema.json if available."""
    if not _SCHEMA_FILE.exists():
        return []
    with _SCHEMA_FILE.open() as f:
        schema = json.load(f)
    return schema.get("methods", [])


@pytest.fixture(scope="session")
def all_api_methods(plugin_methods) -> list[dict[str, Any]]:
    """Combined list of core + plugin methods for fuzzing."""
    return CORE_METHODS + plugin_methods
