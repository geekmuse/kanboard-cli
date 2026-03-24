"""Integration tests — portfolio plugin backend.

Tests run against the Docker-backed Kanboard instance started by
``docker-compose.test.yml``.  That compose file builds from
``docker/Dockerfile.kanboard-plugin-test``, which installs the
``kanboard-plugin-portfolio-management`` plugin.

Tests in this module are skipped automatically when:

* Docker is unavailable (handled by the session-scoped ``docker_kanboard``
  autouse fixture in ``conftest.py``).
* The portfolio plugin is not installed on the Kanboard instance (detected
  by the module-scoped ``plugin_backend`` fixture on first invocation).

Coverage:
  * Portfolio CRUD lifecycle: create, add project, get, update, remove
  * Milestone CRUD lifecycle: create, add tasks, get progress, remove
  * Dependency query methods: get_portfolio_dependencies, get_blocked_tasks
  * Migration round-trip: local store → remote backend → local store
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardConfigError
from kanboard.orchestration.backend import RemotePortfolioBackend
from kanboard.orchestration.store import LocalPortfolioStore

# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def plugin_backend(kanboard_client: KanboardClient) -> RemotePortfolioBackend:
    """Return a :class:`~kanboard.orchestration.backend.RemotePortfolioBackend`.

    Probes the plugin API via :meth:`~RemotePortfolioBackend.load` on first
    invocation.  If the portfolio plugin is not installed, the entire module
    is skipped with an informative message.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.

    Returns:
        A :class:`~kanboard.orchestration.backend.RemotePortfolioBackend`
        whose ``_plugin_detected`` flag is ``True``.
    """
    backend = RemotePortfolioBackend(kanboard_client)
    try:
        backend.load()
    except KanboardConfigError:
        pytest.skip(
            "Portfolio Management plugin not installed — skipping plugin backend tests. "
            "Build the test image with: docker compose -f docker-compose.test.yml build"
        )
    return backend


# ---------------------------------------------------------------------------
# Function-scoped cleanup fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cleanup_portfolio_names(
    plugin_backend: RemotePortfolioBackend,
) -> Generator[list[str], None, None]:
    """Yield a mutable list; remove every named portfolio after the test.

    Tests should append the portfolio name to this list immediately after
    creating it so teardown removes it even if the test body fails.

    Args:
        plugin_backend: Module-scoped remote backend connected to Docker Kanboard.

    Yields:
        An initially empty list of portfolio name strings.
    """
    names: list[str] = []
    yield names
    for name in names:
        try:
            plugin_backend.remove_portfolio(name)
        except Exception:
            pass


@pytest.fixture()
def plugin_project(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> int:
    """Create and yield a Kanboard project ID for plugin tests.

    Args:
        kanboard_client: Session-scoped client.
        cleanup_project_ids: Fixture that removes the project after the test.

    Returns:
        The integer ID of the newly created project.
    """
    project_id = kanboard_client.projects.create_project("Plugin Integration Test Project")
    cleanup_project_ids.append(project_id)
    return project_id


@pytest.fixture()
def plugin_task(
    kanboard_client: KanboardClient,
    plugin_project: int,
    cleanup_task_ids: list[int],
) -> int:
    """Create and yield a Kanboard task ID for plugin tests.

    Args:
        kanboard_client: Session-scoped client.
        plugin_project: ID of the project to create the task in.
        cleanup_task_ids: Fixture that removes the task after the test.

    Returns:
        The integer ID of the newly created task.
    """
    task_id = kanboard_client.tasks.create_task(
        "Plugin Integration Test Task",
        project_id=plugin_project,
    )
    cleanup_task_ids.append(task_id)
    return task_id


# ---------------------------------------------------------------------------
# Portfolio CRUD lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_portfolio_lifecycle_create_and_get(
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
) -> None:
    """Portfolio lifecycle: create returns a Portfolio; get returns it by name.

    Args:
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
    """
    name = "inttest-create-get"
    cleanup_portfolio_names.append(name)

    portfolio = plugin_backend.create_portfolio(name, description="Integration test portfolio")

    assert portfolio.name == name
    assert portfolio.description == "Integration test portfolio"

    fetched = plugin_backend.get_portfolio(name)
    assert fetched.name == name
    assert fetched.description == "Integration test portfolio"


@pytest.mark.integration
def test_portfolio_lifecycle_add_and_remove_project(
    kanboard_client: KanboardClient,
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
    plugin_project: int,
) -> None:
    """Portfolio lifecycle: add_project and remove_project update project_ids.

    Args:
        kanboard_client: Session-scoped client.
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
        plugin_project: A real Kanboard project ID.
    """
    name = "inttest-add-remove-project"
    cleanup_portfolio_names.append(name)
    plugin_backend.create_portfolio(name)

    # Add project
    updated = plugin_backend.add_project(name, plugin_project)
    assert plugin_project in updated.project_ids

    # Remove project
    updated = plugin_backend.remove_project(name, plugin_project)
    assert plugin_project not in updated.project_ids


@pytest.mark.integration
def test_portfolio_lifecycle_update(
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
) -> None:
    """Portfolio lifecycle: update changes description persistently.

    Args:
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
    """
    name = "inttest-update"
    cleanup_portfolio_names.append(name)
    plugin_backend.create_portfolio(name, description="original")

    updated = plugin_backend.update_portfolio(name, description="updated description")
    assert updated.description == "updated description"

    # Verify persistence
    fetched = plugin_backend.get_portfolio(name)
    assert fetched.description == "updated description"


@pytest.mark.integration
def test_portfolio_lifecycle_remove(
    plugin_backend: RemotePortfolioBackend,
) -> None:
    """Portfolio lifecycle: remove deletes the portfolio from the server.

    Args:
        plugin_backend: Remote backend connected to Docker Kanboard.
    """
    name = "inttest-remove"
    plugin_backend.create_portfolio(name)

    result = plugin_backend.remove_portfolio(name)
    assert result is True

    # Verify it no longer exists
    portfolios = plugin_backend.load()
    assert all(p.name != name for p in portfolios)


# ---------------------------------------------------------------------------
# Milestone CRUD lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_milestone_lifecycle_create_add_tasks_and_progress(
    kanboard_client: KanboardClient,
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
    plugin_task: int,
) -> None:
    """Milestone lifecycle: create, add task, verify progress, then clean up.

    Args:
        kanboard_client: Session-scoped client.
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
        plugin_task: A real Kanboard task ID.
    """
    portfolio_name = "inttest-milestone-crud"
    cleanup_portfolio_names.append(portfolio_name)
    plugin_backend.create_portfolio(portfolio_name)

    # Create milestone
    milestone = plugin_backend.add_milestone(portfolio_name, "M1")
    assert milestone.name == "M1"
    assert milestone.portfolio_name == portfolio_name

    # Add task to milestone
    updated_ms = plugin_backend.add_task_to_milestone(portfolio_name, "M1", plugin_task)
    assert plugin_task in updated_ms.task_ids

    # Fetch progress via the MilestonesResource directly (server-computed)
    milestones = kanboard_client.milestones.get_portfolio_milestones(
        kanboard_client.portfolios.get_portfolio_by_name(portfolio_name).id
    )
    assert any(m.name == "M1" for m in milestones)
    milestone_id = next(m.id for m in milestones if m.name == "M1")
    progress = kanboard_client.milestones.get_milestone_progress(milestone_id)
    assert progress.milestone_id == milestone_id
    assert progress.total >= 1


@pytest.mark.integration
def test_milestone_lifecycle_remove(
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
) -> None:
    """Milestone lifecycle: remove deletes the milestone from the portfolio.

    Args:
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
    """
    portfolio_name = "inttest-milestone-remove"
    cleanup_portfolio_names.append(portfolio_name)
    plugin_backend.create_portfolio(portfolio_name)
    plugin_backend.add_milestone(portfolio_name, "ToRemove")

    result = plugin_backend.remove_milestone(portfolio_name, "ToRemove")
    assert result is True

    # Verify it no longer appears
    portfolio = plugin_backend.get_portfolio(portfolio_name)
    assert all(m.name != "ToRemove" for m in portfolio.milestones)


# ---------------------------------------------------------------------------
# Dependency query methods
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_dependency_query_get_portfolio_dependencies(
    kanboard_client: KanboardClient,
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
) -> None:
    """get_portfolio_dependencies returns a list (empty when no deps exist).

    Args:
        kanboard_client: Session-scoped client.
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
    """
    name = "inttest-deps"
    cleanup_portfolio_names.append(name)
    plugin_backend.create_portfolio(name)
    portfolio_id = kanboard_client.portfolios.get_portfolio_by_name(name).id

    deps = kanboard_client.portfolios.get_portfolio_dependencies(portfolio_id)
    assert isinstance(deps, list)


@pytest.mark.integration
def test_dependency_query_get_blocked_tasks(
    kanboard_client: KanboardClient,
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
) -> None:
    """get_blocked_tasks returns a list (empty when no blocking tasks exist).

    Args:
        kanboard_client: Session-scoped client.
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
    """
    name = "inttest-blocked"
    cleanup_portfolio_names.append(name)
    plugin_backend.create_portfolio(name)
    portfolio_id = kanboard_client.portfolios.get_portfolio_by_name(name).id

    blocked = kanboard_client.portfolios.get_blocked_tasks(portfolio_id)
    assert isinstance(blocked, list)


# ---------------------------------------------------------------------------
# Migration round-trip
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_migration_round_trip_local_to_remote_to_local(
    kanboard_client: KanboardClient,
    plugin_backend: RemotePortfolioBackend,
    cleanup_portfolio_names: list[str],
    cleanup_project_ids: list[int],
    cleanup_task_ids: list[int],
    tmp_path: Path,
) -> None:
    """Round-trip: local portfolio → remote backend → new local store.

    Creates a portfolio in a local :class:`~kanboard.orchestration.store.LocalPortfolioStore`,
    migrates it to the remote backend, then migrates it back to a second local
    store.  Verifies that the restored data matches the original.

    Args:
        kanboard_client: Session-scoped client.
        plugin_backend: Remote backend connected to Docker Kanboard.
        cleanup_portfolio_names: Fixture that removes created portfolios.
        cleanup_project_ids: Fixture that removes created projects.
        cleanup_task_ids: Fixture that removes created tasks.
        tmp_path: Pytest-provided temporary directory.
    """
    # ------------------------------------------------------------------ #
    # 1. Setup: real project + task to reference
    # ------------------------------------------------------------------ #
    project_id = kanboard_client.projects.create_project("Round-trip Test Project")
    cleanup_project_ids.append(project_id)
    task_id = kanboard_client.tasks.create_task(
        "Round-trip Task",
        project_id=project_id,
    )
    cleanup_task_ids.append(task_id)

    portfolio_name = "inttest-round-trip"

    # ------------------------------------------------------------------ #
    # 2. Create a portfolio in local store A
    # ------------------------------------------------------------------ #
    store_a = LocalPortfolioStore(path=tmp_path / "store_a.json")
    store_a.create_portfolio(
        portfolio_name,
        description="Round-trip test portfolio",
        project_ids=[project_id],
    )
    store_a.add_milestone(portfolio_name, "Milestone-1", target_date=None)
    store_a.add_task_to_milestone(portfolio_name, "Milestone-1", task_id)

    original = store_a.get_portfolio(portfolio_name)
    assert original.name == portfolio_name
    assert project_id in original.project_ids
    assert len(original.milestones) == 1
    assert task_id in original.milestones[0].task_ids

    # ------------------------------------------------------------------ #
    # 3. Migrate local → remote (replicate what migrate local-to-remote does)
    # ------------------------------------------------------------------ #
    cleanup_portfolio_names.append(portfolio_name)
    plugin_backend.create_portfolio(
        original.name,
        description=original.description,
        project_ids=original.project_ids,
    )
    for ms in original.milestones:
        plugin_backend.add_milestone(original.name, ms.name, target_date=ms.target_date)
        for tid in ms.task_ids:
            plugin_backend.add_task_to_milestone(original.name, ms.name, tid)

    # Verify remote state
    remote_pf = plugin_backend.get_portfolio(portfolio_name)
    assert remote_pf.name == portfolio_name
    assert project_id in remote_pf.project_ids
    assert any(m.name == "Milestone-1" for m in remote_pf.milestones)

    # ------------------------------------------------------------------ #
    # 4. Migrate remote → local (replicate what migrate remote-to-local does)
    # ------------------------------------------------------------------ #
    store_b = LocalPortfolioStore(path=tmp_path / "store_b.json")
    store_b.create_portfolio(
        remote_pf.name,
        description=remote_pf.description,
        project_ids=remote_pf.project_ids,
    )
    for ms in remote_pf.milestones:
        store_b.add_milestone(remote_pf.name, ms.name, target_date=ms.target_date)
        for tid in ms.task_ids:
            store_b.add_task_to_milestone(remote_pf.name, ms.name, tid)

    # ------------------------------------------------------------------ #
    # 5. Verify restored data matches original
    # ------------------------------------------------------------------ #
    restored = store_b.get_portfolio(portfolio_name)

    assert restored.name == original.name
    assert restored.description == original.description
    assert set(restored.project_ids) == set(original.project_ids)
    assert len(restored.milestones) == len(original.milestones)

    original_ms = original.milestones[0]
    restored_ms = next(m for m in restored.milestones if m.name == original_ms.name)
    assert restored_ms.name == original_ms.name
    assert set(restored_ms.task_ids) == set(original_ms.task_ids)
