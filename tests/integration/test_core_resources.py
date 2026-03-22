"""Integration tests — core resource CRUD lifecycles.

Tests run against the Docker-backed Kanboard instance managed by the
session-scoped ``docker_kanboard`` fixture in ``conftest.py``.

Covered resources:
  * Projects — create → get → update → enable/disable → activity → remove
  * Tasks    — create → get → update → search → open/close → move → duplicate → remove
  * Board    — get_board returns expected column/swimlane structure for a project with tasks
  * Columns  — add → get → update → change position → remove
  * Swimlanes — add → get → get_by_name → update → enable/disable → change position → remove
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from kanboard.client import KanboardClient
from kanboard.models import Project, Swimlane

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def integration_project(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> Generator[Project, None, None]:
    """Create a throw-away project for a single test, clean it up afterwards.

    Yields:
        The newly created :class:`~kanboard.models.Project` instance.
    """
    project_id = kanboard_client.projects.create_project("Integration Core Resources Test Project")
    cleanup_project_ids.append(project_id)
    yield kanboard_client.projects.get_project_by_id(project_id)


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_project_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> None:
    """Project lifecycle: create returns a positive ID; get returns the correct project.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.
    """
    project_id = kanboard_client.projects.create_project("Lifecycle Test Project — Create/Get")
    cleanup_project_ids.append(project_id)

    assert isinstance(project_id, int)
    assert project_id > 0

    project = kanboard_client.projects.get_project_by_id(project_id)
    assert project.id == project_id
    assert project.name == "Lifecycle Test Project — Create/Get"
    assert project.is_active is True


@pytest.mark.integration
def test_project_lifecycle_update(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> None:
    """Project lifecycle: update changes the project name persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.
    """
    project_id = kanboard_client.projects.create_project("Lifecycle Test Project — Before Update")
    cleanup_project_ids.append(project_id)

    result = kanboard_client.projects.update_project(
        project_id, name="Lifecycle Test Project — After Update"
    )
    assert result is True

    project = kanboard_client.projects.get_project_by_id(project_id)
    assert project.name == "Lifecycle Test Project — After Update"


@pytest.mark.integration
def test_project_lifecycle_enable_disable(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> None:
    """Project lifecycle: disable deactivates the project; enable reactivates it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.
    """
    project_id = kanboard_client.projects.create_project("Lifecycle Test Project — Enable/Disable")
    cleanup_project_ids.append(project_id)

    # Disable
    assert kanboard_client.projects.disable_project(project_id) is True
    disabled = kanboard_client.projects.get_project_by_id(project_id)
    assert disabled.is_active is False

    # Re-enable
    assert kanboard_client.projects.enable_project(project_id) is True
    enabled = kanboard_client.projects.get_project_by_id(project_id)
    assert enabled.is_active is True


@pytest.mark.integration
def test_project_lifecycle_activity(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> None:
    """Project lifecycle: get_project_activity returns a list (may be empty for new projects).

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.
    """
    project_id = kanboard_client.projects.create_project("Lifecycle Test Project — Activity")
    cleanup_project_ids.append(project_id)

    activity = kanboard_client.projects.get_project_activity(project_id)
    assert isinstance(activity, list)


@pytest.mark.integration
def test_project_lifecycle_remove(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> None:
    """Project lifecycle: remove_project permanently deletes the project.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.
    """
    project_id = kanboard_client.projects.create_project("Lifecycle Test Project — Remove")
    cleanup_project_ids.append(project_id)

    result = kanboard_client.projects.remove_project(project_id)
    assert result is True

    # Verify it's gone — Kanboard returns 403 for deleted project IDs,
    # so check via get_all_projects() instead.
    all_projects = kanboard_client.projects.get_all_projects()
    assert not any(p.id == project_id for p in all_projects), (
        f"Project {project_id} still visible in get_all_projects after removal"
    )


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_task_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: create returns a positive ID; get returns the correct task.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task_id = kanboard_client.tasks.create_task(
        title="Lifecycle Test Task — Create/Get",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    assert isinstance(task_id, int)
    assert task_id > 0

    task = kanboard_client.tasks.get_task(task_id)
    assert task.id == task_id
    assert task.title == "Lifecycle Test Task — Create/Get"
    assert task.project_id == integration_project.id
    assert task.is_active is True


@pytest.mark.integration
def test_task_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: update_task changes the title and description persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task_id = kanboard_client.tasks.create_task(
        title="Lifecycle Test Task — Before Update",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    result = kanboard_client.tasks.update_task(
        task_id,
        title="Lifecycle Test Task — After Update",
        description="Updated description",
    )
    assert result is True

    task = kanboard_client.tasks.get_task(task_id)
    assert task.title == "Lifecycle Test Task — After Update"
    assert task.description == "Updated description"


@pytest.mark.integration
def test_task_lifecycle_search(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: search_tasks finds the task by a keyword in its title.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task_id = kanboard_client.tasks.create_task(
        title="UniqueSearchableTaskXYZ",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    results = kanboard_client.tasks.search_tasks(
        project_id=integration_project.id,
        query="UniqueSearchableTaskXYZ",
    )
    assert isinstance(results, list)
    assert any(t.id == task_id for t in results), (
        f"Expected task {task_id} in search results but got: {[t.id for t in results]}"
    )


@pytest.mark.integration
def test_task_lifecycle_open_close(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: close_task deactivates the task; open_task reactivates it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task_id = kanboard_client.tasks.create_task(
        title="Lifecycle Test Task — Open/Close",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    # Close the task
    assert kanboard_client.tasks.close_task(task_id) is True
    closed = kanboard_client.tasks.get_task(task_id)
    assert closed.is_active is False

    # Reopen the task
    assert kanboard_client.tasks.open_task(task_id) is True
    reopened = kanboard_client.tasks.get_task(task_id)
    assert reopened.is_active is True


@pytest.mark.integration
def test_task_lifecycle_move_position(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: move_task_position moves the task to a different column.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    # Discover the project's columns and default swimlane
    columns = kanboard_client.columns.get_columns(integration_project.id)
    assert len(columns) >= 2, "Expected at least 2 default columns in a new project"

    # Create a task in the first column
    first_col = columns[0]
    task_id = kanboard_client.tasks.create_task(
        title="Lifecycle Test Task — Move",
        project_id=integration_project.id,
        column_id=first_col.id,
    )
    cleanup_task_ids.append(task_id)

    # Move to the second column, default swimlane (0)
    second_col = columns[1]
    result = kanboard_client.tasks.move_task_position(
        project_id=integration_project.id,
        task_id=task_id,
        column_id=second_col.id,
        position=1,
        swimlane_id=0,
    )
    assert result is True

    moved_task = kanboard_client.tasks.get_task(task_id)
    assert moved_task.column_id == second_col.id


@pytest.mark.integration
def test_task_lifecycle_duplicate_to_project(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_project_ids: list[int],
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: duplicate_task_to_project creates a copy in another project.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (source project).
        cleanup_project_ids: Fixture that removes listed projects after the test.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    # Create a destination project
    dest_project_id = kanboard_client.projects.create_project(
        "Lifecycle Test Project — Duplicate Destination"
    )
    cleanup_project_ids.append(dest_project_id)

    # Create the original task
    task_id = kanboard_client.tasks.create_task(
        title="Lifecycle Test Task — Duplicate Source",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    # Duplicate to the destination project
    duplicate_id = kanboard_client.tasks.duplicate_task_to_project(
        task_id=task_id,
        project_id=dest_project_id,
    )
    cleanup_task_ids.append(duplicate_id)

    assert isinstance(duplicate_id, int)
    assert duplicate_id > 0
    assert duplicate_id != task_id

    duplicate = kanboard_client.tasks.get_task(duplicate_id)
    assert duplicate.project_id == dest_project_id
    assert duplicate.title == "Lifecycle Test Task — Duplicate Source"


@pytest.mark.integration
def test_task_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task lifecycle: remove_task permanently deletes the task.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task_id = kanboard_client.tasks.create_task(
        title="Lifecycle Test Task — Remove",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    result = kanboard_client.tasks.remove_task(task_id)
    assert result is True

    # Kanboard returns 403 for deleted task IDs, so verify via task list instead.
    active_tasks = kanboard_client.tasks.get_all_tasks(integration_project.id, status_id=1)
    closed_tasks = kanboard_client.tasks.get_all_tasks(integration_project.id, status_id=0)
    all_task_ids = {t.id for t in active_tasks} | {t.id for t in closed_tasks}
    assert task_id not in all_task_ids, (
        f"Task {task_id} still visible in task list after removal"
    )


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_board_structure_with_tasks(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Board: get_board returns expected column/swimlane structure for a project with tasks.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    # Add a task so the board is not completely empty
    task_id = kanboard_client.tasks.create_task(
        title="Board Structure Test Task",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)

    board = kanboard_client.board.get_board(integration_project.id)

    # Board must be a non-empty list of dicts
    assert isinstance(board, list), "get_board should return a list"
    assert len(board) > 0, "Board should have at least one row/swimlane entry"
    assert all(isinstance(entry, dict) for entry in board), "Every board entry should be a dict"

    # Each entry should have an id-like field (swimlane id) and a columns sub-list
    first_entry = board[0]
    assert "columns" in first_entry or "id" in first_entry, (
        f"Board entries should have 'columns' or 'id' key; got keys: {list(first_entry.keys())}"
    )

    # If the response has a "columns" key, verify the columns contain tasks dicts
    if "columns" in first_entry:
        columns_in_board = first_entry["columns"]
        assert isinstance(columns_in_board, list)
        assert len(columns_in_board) > 0, "Board swimlane should have at least one column"


# ---------------------------------------------------------------------------
# Column lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_column_lifecycle_add_and_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Column lifecycle: add_column creates a column; get_column retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades columns).
    """
    col_id = kanboard_client.columns.add_column(
        project_id=integration_project.id,
        title="Lifecycle Test Column",
        description="Added by integration test",
    )
    assert isinstance(col_id, int)
    assert col_id > 0

    col = kanboard_client.columns.get_column(col_id)
    assert col.id == col_id
    assert col.title == "Lifecycle Test Column"
    assert col.project_id == integration_project.id


@pytest.mark.integration
def test_column_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Column lifecycle: update_column changes the column title and task limit.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades columns).
    """
    col_id = kanboard_client.columns.add_column(
        project_id=integration_project.id,
        title="Column Before Update",
    )

    result = kanboard_client.columns.update_column(
        column_id=col_id,
        title="Column After Update",
        task_limit=5,
    )
    assert result is True

    updated = kanboard_client.columns.get_column(col_id)
    assert updated.title == "Column After Update"
    assert updated.task_limit == 5


@pytest.mark.integration
def test_column_lifecycle_change_position(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Column lifecycle: change_column_position repositions the column within the board.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades columns).
    """
    col_id = kanboard_client.columns.add_column(
        project_id=integration_project.id,
        title="Lifecycle Test Column — Position",
    )

    # New columns are appended at the end; move it to position 1
    result = kanboard_client.columns.change_column_position(
        project_id=integration_project.id,
        column_id=col_id,
        position=1,
    )
    assert result is True

    # Verify position was updated
    repositioned = kanboard_client.columns.get_column(col_id)
    assert repositioned.position == 1


@pytest.mark.integration
def test_column_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Column lifecycle: remove_column permanently deletes the column.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades columns).
    """
    col_id = kanboard_client.columns.add_column(
        project_id=integration_project.id,
        title="Lifecycle Test Column — Remove",
    )

    result = kanboard_client.columns.remove_column(col_id)
    assert result is True

    # Kanboard returns 403 for deleted column IDs, so verify via column list instead.
    remaining = kanboard_client.columns.get_columns(integration_project.id)
    assert not any(c.id == col_id for c in remaining), (
        f"Column {col_id} still visible in get_columns after removal"
    )


# ---------------------------------------------------------------------------
# Swimlane lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_swimlane_lifecycle_add_and_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Swimlane lifecycle: add_swimlane creates a swimlane; get_swimlane retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades swimlanes).
    """
    swimlane_id = kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="Lifecycle Test Swimlane",
        description="Added by integration test",
    )
    assert isinstance(swimlane_id, int)
    assert swimlane_id > 0

    swimlane = kanboard_client.swimlanes.get_swimlane(swimlane_id)
    assert swimlane.id == swimlane_id
    assert swimlane.name == "Lifecycle Test Swimlane"
    assert swimlane.project_id == integration_project.id
    assert swimlane.is_active is True


@pytest.mark.integration
def test_swimlane_lifecycle_get_by_name(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Swimlane lifecycle: get_swimlane_by_name retrieves the swimlane by name.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades swimlanes).
    """
    kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="ByNameSearchSwimlane",
    )

    swimlane = kanboard_client.swimlanes.get_swimlane_by_name(
        project_id=integration_project.id,
        name="ByNameSearchSwimlane",
    )
    assert isinstance(swimlane, Swimlane)
    assert swimlane.name == "ByNameSearchSwimlane"
    assert swimlane.project_id == integration_project.id


@pytest.mark.integration
def test_swimlane_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Swimlane lifecycle: update_swimlane renames the swimlane persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades swimlanes).
    """
    swimlane_id = kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="Swimlane Before Update",
    )

    result = kanboard_client.swimlanes.update_swimlane(
        project_id=integration_project.id,
        swimlane_id=swimlane_id,
        name="Swimlane After Update",
        description="Updated by integration test",
    )
    assert result is True

    updated = kanboard_client.swimlanes.get_swimlane(swimlane_id)
    assert updated.name == "Swimlane After Update"


@pytest.mark.integration
def test_swimlane_lifecycle_enable_disable(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Swimlane lifecycle: disable_swimlane deactivates; enable_swimlane reactivates.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades swimlanes).
    """
    swimlane_id = kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="Lifecycle Test Swimlane — Enable/Disable",
    )

    # Disable
    assert kanboard_client.swimlanes.disable_swimlane(integration_project.id, swimlane_id) is True
    # Disabled swimlane won't appear in get_active_swimlanes; check via get_all_swimlanes
    all_swimlanes = kanboard_client.swimlanes.get_all_swimlanes(integration_project.id)
    disabled = next((s for s in all_swimlanes if s.id == swimlane_id), None)
    assert disabled is not None, f"Swimlane {swimlane_id} not found in get_all_swimlanes"
    assert disabled.is_active is False

    # Re-enable
    assert kanboard_client.swimlanes.enable_swimlane(integration_project.id, swimlane_id) is True
    active_swimlanes = kanboard_client.swimlanes.get_active_swimlanes(integration_project.id)
    enabled = next((s for s in active_swimlanes if s.id == swimlane_id), None)
    assert enabled is not None, (
        f"Swimlane {swimlane_id} not found in get_active_swimlanes after re-enable"
    )
    assert enabled.is_active is True


@pytest.mark.integration
def test_swimlane_lifecycle_change_position(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Swimlane lifecycle: change_swimlane_position repositions a swimlane in the board.

    Two user-created swimlanes are added so that position changes are meaningful.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades swimlanes).
    """
    swimlane_a_id = kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="Position Test Swimlane A",
    )
    swimlane_b_id = kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="Position Test Swimlane B",
    )

    # A is at position 1, B is at position 2; move A to position 2
    result = kanboard_client.swimlanes.change_swimlane_position(
        project_id=integration_project.id,
        swimlane_id=swimlane_a_id,
        position=2,
    )
    assert result is True

    # Verify positions flipped
    all_swimlanes = kanboard_client.swimlanes.get_all_swimlanes(integration_project.id)
    by_id = {s.id: s for s in all_swimlanes}
    assert swimlane_a_id in by_id, "Swimlane A missing from get_all_swimlanes"
    assert swimlane_b_id in by_id, "Swimlane B missing from get_all_swimlanes"
    assert by_id[swimlane_a_id].position == 2


@pytest.mark.integration
def test_swimlane_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Swimlane lifecycle: remove_swimlane permanently deletes the swimlane.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture (project removal cascades swimlanes).
    """
    swimlane_id = kanboard_client.swimlanes.add_swimlane(
        project_id=integration_project.id,
        name="Lifecycle Test Swimlane — Remove",
    )

    result = kanboard_client.swimlanes.remove_swimlane(integration_project.id, swimlane_id)
    assert result is True

    # Removed swimlane should no longer appear in get_all_swimlanes
    all_swimlanes = kanboard_client.swimlanes.get_all_swimlanes(integration_project.id)
    assert not any(s.id == swimlane_id for s in all_swimlanes), (
        f"Swimlane {swimlane_id} still present after remove_swimlane"
    )
