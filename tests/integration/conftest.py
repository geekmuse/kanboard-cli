"""Integration test fixtures — Docker-backed Kanboard instance.

All fixtures in this module are scoped to the integration test session.
Tests skip automatically when the Docker daemon is not available.

Environment variables for override:
  KANBOARD_HOST     Base URL of the Kanboard instance (default: http://localhost:4000)
  KANBOARD_USERNAME Admin username (default: admin)
  KANBOARD_PASSWORD Admin password (default: admin)
  KANBOARD_NO_DOCKER_TEARDOWN  Set to any non-empty value to skip teardown of Docker Compose.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

from kanboard.client import KanboardClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_KANBOARD_HOST: str = os.environ.get("KANBOARD_HOST", "http://localhost:4000")
KANBOARD_URL: str = f"{_KANBOARD_HOST}/jsonrpc.php"
KANBOARD_USERNAME: str = os.environ.get("KANBOARD_USERNAME", "admin")
KANBOARD_PASSWORD: str = os.environ.get("KANBOARD_PASSWORD", "admin")

_COMPOSE_FILE: Path = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

_HEALTH_TIMEOUT_SECS: int = 90
_HEALTH_POLL_INTERVAL_SECS: float = 2.0
_DOCKER_COMPOSE_UP_TIMEOUT_SECS: int = 180


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_docker_available() -> bool:
    """Return ``True`` if the Docker daemon is accessible, ``False`` otherwise."""
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_kanboard(url: str, timeout: int = _HEALTH_TIMEOUT_SECS) -> bool:
    """Poll *url* until Kanboard responds with a valid JSON-RPC reply.

    Sends a ``getVersion`` JSON-RPC request to *url* every
    :data:`_HEALTH_POLL_INTERVAL_SECS` seconds until the server returns HTTP
    200 or *timeout* seconds elapse.

    Args:
        url: The Kanboard JSON-RPC endpoint URL to poll.
        timeout: Maximum number of seconds to wait before giving up.

    Returns:
        ``True`` when Kanboard is healthy; ``False`` on timeout.
    """
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
# Session-scoped Docker lifecycle fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def docker_kanboard() -> Generator[None, None, None]:
    """Start the Docker Compose Kanboard service and wait for it to be healthy.

    This session-scoped, autouse fixture gates the entire integration test
    suite.  When the Docker daemon is unreachable the fixture calls
    :func:`pytest.skip` which causes every test in the ``tests/integration/``
    directory to be reported as *skipped* rather than *failed*.

    Yields:
        Nothing — tests run while the Docker service is up.

    Raises:
        pytest.fail: If Docker is available but the Kanboard service fails to
            start or does not become healthy within the timeout.
    """
    if not _is_docker_available():
        pytest.skip("Docker daemon not available — skipping integration tests")
        return  # unreachable; satisfies type checkers

    try:
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(_COMPOSE_FILE),
                "up",
                "-d",
                "--wait",
            ],
            check=True,
            timeout=_DOCKER_COMPOSE_UP_TIMEOUT_SECS,
        )
    except subprocess.CalledProcessError as exc:
        pytest.fail(
            f"docker compose up failed (exit {exc.returncode}) — "
            "check that Docker Desktop is running and port 4000 is free."
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"docker compose up timed out after {_DOCKER_COMPOSE_UP_TIMEOUT_SECS}s")

    # Extra readiness poll — ensures the JSON-RPC API is responding.
    if not _wait_for_kanboard(KANBOARD_URL):
        pytest.fail(
            f"Kanboard at {KANBOARD_URL} did not become healthy within {_HEALTH_TIMEOUT_SECS}s"
        )

    yield

    # Teardown: stop and remove containers + volumes for a clean slate.
    if not os.environ.get("KANBOARD_NO_DOCKER_TEARDOWN"):
        subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE_FILE), "down", "-v"],
            check=False,
            timeout=60,
        )


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def kanboard_url() -> str:
    """Return the Kanboard JSON-RPC endpoint URL for the test instance.

    Returns:
        The full JSON-RPC URL (e.g. ``"http://localhost:4000/jsonrpc.php"``).
    """
    return KANBOARD_URL


@pytest.fixture(scope="session")
def kanboard_client(docker_kanboard: None) -> Generator[KanboardClient, None, None]:
    """Yield a session-scoped :class:`~kanboard.client.KanboardClient`.

    The client is authenticated via **User API** mode using the admin
    credentials so that all JSON-RPC methods are accessible.

    Args:
        docker_kanboard: Session fixture that ensures Docker Compose is running.

    Yields:
        A connected :class:`~kanboard.client.KanboardClient` instance.
    """
    with KanboardClient(
        KANBOARD_URL,
        auth_mode="user",
        username=KANBOARD_USERNAME,
        password=KANBOARD_PASSWORD,
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Resource cleanup helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def cleanup_project_ids(
    kanboard_client: KanboardClient,
) -> Generator[list[int], None, None]:
    """Yield a mutable list; remove every project ID added to it after the test.

    Tests that create projects should append the resulting project ID to this
    list.  Teardown calls :meth:`~kanboard.resources.projects.ProjectsResource.remove_project`
    for each ID, ignoring errors so other cleanup can continue.

    Args:
        kanboard_client: The shared :class:`~kanboard.client.KanboardClient`.

    Yields:
        An initially empty list of integer project IDs.
    """
    ids: list[int] = []
    yield ids
    for project_id in ids:
        try:
            kanboard_client.projects.remove_project(project_id)
        except Exception:
            pass


@pytest.fixture()
def cleanup_task_ids(
    kanboard_client: KanboardClient,
) -> Generator[list[int], None, None]:
    """Yield a mutable list; remove every task ID added to it after the test.

    Tests that create tasks should append the resulting task ID to this list.
    Teardown calls :meth:`~kanboard.resources.tasks.TasksResource.remove_task`
    for each ID, ignoring errors so other cleanup can continue.

    Args:
        kanboard_client: The shared :class:`~kanboard.client.KanboardClient`.

    Yields:
        An initially empty list of integer task IDs.
    """
    ids: list[int] = []
    yield ids
    for task_id in ids:
        try:
            kanboard_client.tasks.remove_task(task_id)
        except Exception:
            pass


@pytest.fixture()
def cleanup_user_ids(
    kanboard_client: KanboardClient,
) -> Generator[list[int], None, None]:
    """Yield a mutable list; remove every user ID added to it after the test.

    Tests that create users should append the resulting user ID to this list.
    Teardown calls :meth:`~kanboard.resources.users.UsersResource.remove_user`
    for each ID, ignoring errors so other cleanup can continue.

    Args:
        kanboard_client: The shared :class:`~kanboard.client.KanboardClient`.

    Yields:
        An initially empty list of integer user IDs.
    """
    ids: list[int] = []
    yield ids
    for user_id in ids:
        try:
            kanboard_client.users.remove_user(user_id)
        except Exception:
            pass


@pytest.fixture()
def cleanup_group_ids(
    kanboard_client: KanboardClient,
) -> Generator[list[int], None, None]:
    """Yield a mutable list; remove every group ID added to it after the test.

    Tests that create groups should append the resulting group ID to this list.
    Teardown calls :meth:`~kanboard.resources.groups.GroupsResource.remove_group`
    for each ID, ignoring errors so other cleanup can continue.

    Args:
        kanboard_client: The shared :class:`~kanboard.client.KanboardClient`.

    Yields:
        An initially empty list of integer group IDs.
    """
    ids: list[int] = []
    yield ids
    for group_id in ids:
        try:
            kanboard_client.groups.remove_group(group_id)
        except Exception:
            pass


@pytest.fixture()
def cleanup_link_ids(
    kanboard_client: KanboardClient,
) -> Generator[list[int], None, None]:
    """Yield a mutable list; remove every link type ID added to it after the test.

    Tests that create link types (via
    :meth:`~kanboard.resources.links.LinksResource.create_link`) should append
    the resulting link ID(s) to this list.  When a link has a distinct opposite,
    both IDs should be appended.  Teardown calls
    :meth:`~kanboard.resources.links.LinksResource.remove_link` for each ID,
    ignoring errors so other cleanup can continue.

    Args:
        kanboard_client: The shared :class:`~kanboard.client.KanboardClient`.

    Yields:
        An initially empty list of integer link type IDs.
    """
    ids: list[int] = []
    yield ids
    seen: set[int] = set()
    for link_id in ids:
        if link_id in seen:
            continue
        seen.add(link_id)
        try:
            kanboard_client.links.remove_link(link_id)
        except Exception:
            pass
