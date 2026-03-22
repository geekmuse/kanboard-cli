"""Integration tests — extended resource CRUD lifecycles.

Tests run against the Docker-backed Kanboard instance managed by the
session-scoped ``docker_kanboard`` fixture in ``conftest.py``.

Covered resources:
  * Project files     — create → get_all → get → download → remove → remove_all
  * Task files        — create → get_all → get → download → remove → remove_all
  * Project metadata  — save → get_all → get_by_name → remove
  * Task metadata     — save → get_all → get_by_name → remove
  * Project perms     — add_user → get_users → get_user_role → change_role →
                        remove_user  (+ group equivalents)
  * Groups            — create → get → get_all → update → remove
  * Group members     — add → get_members → get_member_groups → is_member → remove
  * External links    — get_types → create → get → get_all → update → remove
  * Actions           — get_available → get_events → get_compatible_events →
                        create → get_actions → remove
  * Subtask timers    — start → has_timer → stop → get_time_spent
  * Application info  — get_version, get_timezone, get_colors, get_roles
"""

from __future__ import annotations

import base64
import uuid
from collections.abc import Generator

import pytest

from kanboard.client import KanboardClient
from kanboard.models import Action, ExternalTaskLink, Group, Project, ProjectFile, TaskFile

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# admin user is always user_id=1 on a fresh Kanboard instance
_ADMIN_USER_ID: int = 1

_TEST_BLOB: str = base64.b64encode(b"integration test file content").decode()
_TEST_FILENAME: str = "test_attachment.txt"


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def integration_project(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> Generator[Project, None, None]:
    """Create a throw-away project for a single test; clean it up afterwards.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.

    Yields:
        The newly created :class:`~kanboard.models.Project` instance.
    """
    project_id = kanboard_client.projects.create_project(
        "Integration Extended Resources Test Project"
    )
    cleanup_project_ids.append(project_id)
    yield kanboard_client.projects.get_project_by_id(project_id)


@pytest.fixture()
def integration_task(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> Generator[int, None, None]:
    """Create a throw-away task in the integration project; yield its integer ID.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.

    Yields:
        The integer ID of the newly created task.
    """
    task_id = kanboard_client.tasks.create_task(
        title="Extended Resources Test Task",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)
    yield task_id


@pytest.fixture()
def integration_subtask(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> Generator[int, None, None]:
    """Create a throw-away subtask inside the integration task; yield its integer ID.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).

    Yields:
        The integer ID of the newly created subtask.
    """
    subtask_id = kanboard_client.subtasks.create_subtask(
        task_id=integration_task,
        title="Extended Resources Test Subtask",
    )
    yield subtask_id


@pytest.fixture()
def integration_user(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> Generator[int, None, None]:
    """Create a throw-away user; yield their integer ID.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.

    Yields:
        The integer ID of the newly created user.
    """
    suffix = uuid.uuid4().hex[:8]
    user_id = kanboard_client.users.create_user(
        username=f"testuser_{suffix}",
        password="Password1!",
        name=f"Test User {suffix}",
    )
    cleanup_user_ids.append(user_id)
    yield user_id


@pytest.fixture()
def integration_group(
    kanboard_client: KanboardClient,
    cleanup_group_ids: list[int],
) -> Generator[int, None, None]:
    """Create a throw-away group; yield its integer ID.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_group_ids: Fixture that removes listed groups after the test.

    Yields:
        The integer ID of the newly created group.
    """
    suffix = uuid.uuid4().hex[:8]
    group_id = kanboard_client.groups.create_group(f"Test Group {suffix}")
    cleanup_group_ids.append(group_id)
    yield group_id


# ---------------------------------------------------------------------------
# Project file lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_project_file_lifecycle_create_and_get_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project file: create returns a positive ID; get_all lists the new file.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    file_id = kanboard_client.project_files.create_project_file(
        project_id=integration_project.id,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )
    assert isinstance(file_id, int)
    assert file_id > 0

    files = kanboard_client.project_files.get_all_project_files(integration_project.id)
    file_ids = [f.id for f in files]
    assert file_id in file_ids


@pytest.mark.integration
def test_project_file_lifecycle_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project file: get_project_file returns the correct ProjectFile model.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    file_id = kanboard_client.project_files.create_project_file(
        project_id=integration_project.id,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )

    pf = kanboard_client.project_files.get_project_file(integration_project.id, file_id)
    assert isinstance(pf, ProjectFile)
    assert pf.id == file_id
    assert pf.name == _TEST_FILENAME


@pytest.mark.integration
def test_project_file_lifecycle_download(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project file: download returns non-empty base64-encoded content.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    file_id = kanboard_client.project_files.create_project_file(
        project_id=integration_project.id,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )

    content = kanboard_client.project_files.download_project_file(integration_project.id, file_id)
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.integration
def test_project_file_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project file: remove_project_file deletes the file; get_all excludes it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    file_id = kanboard_client.project_files.create_project_file(
        project_id=integration_project.id,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )

    result = kanboard_client.project_files.remove_project_file(integration_project.id, file_id)
    assert result is True

    files = kanboard_client.project_files.get_all_project_files(integration_project.id)
    assert not any(f.id == file_id for f in files)


@pytest.mark.integration
def test_project_file_lifecycle_remove_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project file: remove_all_project_files clears all project files at once.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    kanboard_client.project_files.create_project_file(
        project_id=integration_project.id,
        filename="file_a.txt",
        blob=_TEST_BLOB,
    )
    kanboard_client.project_files.create_project_file(
        project_id=integration_project.id,
        filename="file_b.txt",
        blob=_TEST_BLOB,
    )

    result = kanboard_client.project_files.remove_all_project_files(integration_project.id)
    assert result is True

    files = kanboard_client.project_files.get_all_project_files(integration_project.id)
    assert files == []


# ---------------------------------------------------------------------------
# Task file lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_task_file_lifecycle_create_and_get_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_task: int,
) -> None:
    """Task file: create returns a positive ID; get_all lists the new file.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_task: Throw-away task fixture (integer ID).
    """
    file_id = kanboard_client.task_files.create_task_file(
        project_id=integration_project.id,
        task_id=integration_task,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )
    assert isinstance(file_id, int)
    assert file_id > 0

    files = kanboard_client.task_files.get_all_task_files(integration_task)
    file_ids = [f.id for f in files]
    assert file_id in file_ids


@pytest.mark.integration
def test_task_file_lifecycle_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_task: int,
) -> None:
    """Task file: get_task_file returns the correct TaskFile model.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_task: Throw-away task fixture (integer ID).
    """
    file_id = kanboard_client.task_files.create_task_file(
        project_id=integration_project.id,
        task_id=integration_task,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )

    tf = kanboard_client.task_files.get_task_file(file_id)
    assert isinstance(tf, TaskFile)
    assert tf.id == file_id
    assert tf.name == _TEST_FILENAME


@pytest.mark.integration
def test_task_file_lifecycle_download(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_task: int,
) -> None:
    """Task file: download returns non-empty base64-encoded content.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_task: Throw-away task fixture (integer ID).
    """
    file_id = kanboard_client.task_files.create_task_file(
        project_id=integration_project.id,
        task_id=integration_task,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )

    content = kanboard_client.task_files.download_task_file(file_id)
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.integration
def test_task_file_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_task: int,
) -> None:
    """Task file: remove_task_file deletes the file; get_all excludes it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_task: Throw-away task fixture (integer ID).
    """
    file_id = kanboard_client.task_files.create_task_file(
        project_id=integration_project.id,
        task_id=integration_task,
        filename=_TEST_FILENAME,
        blob=_TEST_BLOB,
    )

    result = kanboard_client.task_files.remove_task_file(file_id)
    assert result is True

    files = kanboard_client.task_files.get_all_task_files(integration_task)
    assert not any(f.id == file_id for f in files)


@pytest.mark.integration
def test_task_file_lifecycle_remove_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_task: int,
) -> None:
    """Task file: remove_all_task_files clears all task files at once.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_task: Throw-away task fixture (integer ID).
    """
    kanboard_client.task_files.create_task_file(
        project_id=integration_project.id,
        task_id=integration_task,
        filename="task_file_a.txt",
        blob=_TEST_BLOB,
    )
    kanboard_client.task_files.create_task_file(
        project_id=integration_project.id,
        task_id=integration_task,
        filename="task_file_b.txt",
        blob=_TEST_BLOB,
    )

    result = kanboard_client.task_files.remove_all_task_files(integration_task)
    assert result is True

    files = kanboard_client.task_files.get_all_task_files(integration_task)
    assert files == []


# ---------------------------------------------------------------------------
# Project metadata lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_project_metadata_lifecycle_save_and_get_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project metadata: save multiple values; get_all returns them all.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    kanboard_client.project_metadata.save_project_metadata(
        integration_project.id,
        {"budget": "5000", "priority": "high"},
    )

    meta = kanboard_client.project_metadata.get_project_metadata(integration_project.id)
    assert "budget" in meta
    assert meta["budget"] == "5000"
    assert "priority" in meta
    assert meta["priority"] == "high"


@pytest.mark.integration
def test_project_metadata_lifecycle_get_by_name(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project metadata: get_by_name returns the value for a single key.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    kanboard_client.project_metadata.save_project_metadata(
        integration_project.id,
        {"owner": "alice"},
    )

    value = kanboard_client.project_metadata.get_project_metadata_by_name(
        integration_project.id, "owner"
    )
    assert value == "alice"


@pytest.mark.integration
def test_project_metadata_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Project metadata: remove_project_metadata deletes a key from the store.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    kanboard_client.project_metadata.save_project_metadata(
        integration_project.id,
        {"temp_key": "temp_value"},
    )

    result = kanboard_client.project_metadata.remove_project_metadata(
        integration_project.id, "temp_key"
    )
    assert result is True

    meta = kanboard_client.project_metadata.get_project_metadata(integration_project.id)
    assert "temp_key" not in meta


# ---------------------------------------------------------------------------
# Task metadata lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_task_metadata_lifecycle_save_and_get_all(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Task metadata: save multiple values; get_all returns them all.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    kanboard_client.task_metadata.save_task_metadata(
        integration_task,
        {"sprint": "3", "story_points": "5"},
    )

    meta = kanboard_client.task_metadata.get_task_metadata(integration_task)
    assert "sprint" in meta
    assert meta["sprint"] == "3"
    assert "story_points" in meta
    assert meta["story_points"] == "5"


@pytest.mark.integration
def test_task_metadata_lifecycle_get_by_name(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Task metadata: get_by_name returns the value for a single key.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    kanboard_client.task_metadata.save_task_metadata(
        integration_task,
        {"reviewer": "bob"},
    )

    value = kanboard_client.task_metadata.get_task_metadata_by_name(integration_task, "reviewer")
    assert value == "bob"


@pytest.mark.integration
def test_task_metadata_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Task metadata: remove_task_metadata deletes a key from the store.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    kanboard_client.task_metadata.save_task_metadata(
        integration_task,
        {"disposable": "yes"},
    )

    result = kanboard_client.task_metadata.remove_task_metadata(integration_task, "disposable")
    assert result is True

    meta = kanboard_client.task_metadata.get_task_metadata(integration_task)
    assert "disposable" not in meta


# ---------------------------------------------------------------------------
# Project permissions — user management
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_project_permissions_add_user_and_get_users(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_user: int,
) -> None:
    """Project permissions: add_project_user makes user appear in get_project_users.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_user: Throw-away user fixture (integer ID).
    """
    kanboard_client.project_permissions.add_project_user(integration_project.id, integration_user)

    users = kanboard_client.project_permissions.get_project_users(integration_project.id)
    assert str(integration_user) in users


@pytest.mark.integration
def test_project_permissions_get_user_role(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_user: int,
) -> None:
    """Project permissions: get_project_user_role returns the assigned role.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_user: Throw-away user fixture (integer ID).
    """
    kanboard_client.project_permissions.add_project_user(
        integration_project.id, integration_user, role="project-member"
    )

    role = kanboard_client.project_permissions.get_project_user_role(
        integration_project.id, integration_user
    )
    assert role == "project-member"


@pytest.mark.integration
def test_project_permissions_change_user_role(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_user: int,
) -> None:
    """Project permissions: change_project_user_role updates the user's role.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_user: Throw-away user fixture (integer ID).
    """
    kanboard_client.project_permissions.add_project_user(
        integration_project.id, integration_user, role="project-member"
    )

    result = kanboard_client.project_permissions.change_project_user_role(
        integration_project.id, integration_user, "project-manager"
    )
    assert result is True

    role = kanboard_client.project_permissions.get_project_user_role(
        integration_project.id, integration_user
    )
    assert role == "project-manager"


@pytest.mark.integration
def test_project_permissions_remove_user(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_user: int,
) -> None:
    """Project permissions: remove_project_user removes the user from the project.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_user: Throw-away user fixture (integer ID).
    """
    kanboard_client.project_permissions.add_project_user(integration_project.id, integration_user)

    result = kanboard_client.project_permissions.remove_project_user(
        integration_project.id, integration_user
    )
    assert result is True

    users = kanboard_client.project_permissions.get_project_users(integration_project.id)
    assert str(integration_user) not in users


# ---------------------------------------------------------------------------
# Project permissions — group management
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_project_permissions_add_group_and_change_role(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_group: int,
) -> None:
    """Project permissions: add_project_group and change_project_group_role succeed.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_group: Throw-away group fixture (integer ID).
    """
    kanboard_client.project_permissions.add_project_group(
        integration_project.id, integration_group, role="project-viewer"
    )

    result = kanboard_client.project_permissions.change_project_group_role(
        integration_project.id, integration_group, "project-member"
    )
    assert result is True


@pytest.mark.integration
def test_project_permissions_remove_group(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_group: int,
) -> None:
    """Project permissions: remove_project_group removes the group from the project.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_group: Throw-away group fixture (integer ID).
    """
    kanboard_client.project_permissions.add_project_group(
        integration_project.id, integration_group, role="project-viewer"
    )

    result = kanboard_client.project_permissions.remove_project_group(
        integration_project.id, integration_group
    )
    assert result is True


# ---------------------------------------------------------------------------
# Group lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_group_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    cleanup_group_ids: list[int],
) -> None:
    """Group lifecycle: create returns a positive ID; get returns the correct Group.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_group_ids: Fixture that removes listed groups after the test.
    """
    suffix = uuid.uuid4().hex[:8]
    group_name = f"Create/Get Group {suffix}"
    group_id = kanboard_client.groups.create_group(group_name)
    cleanup_group_ids.append(group_id)

    assert isinstance(group_id, int)
    assert group_id > 0

    group = kanboard_client.groups.get_group(group_id)
    assert isinstance(group, Group)
    assert group.id == group_id
    assert group.name == group_name


@pytest.mark.integration
def test_group_lifecycle_get_all(
    kanboard_client: KanboardClient,
    cleanup_group_ids: list[int],
) -> None:
    """Group lifecycle: get_all returns a list that includes the new group.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_group_ids: Fixture that removes listed groups after the test.
    """
    suffix = uuid.uuid4().hex[:8]
    group_id = kanboard_client.groups.create_group(f"GetAll Group {suffix}")
    cleanup_group_ids.append(group_id)

    groups = kanboard_client.groups.get_all_groups()
    group_ids = [g.id for g in groups]
    assert group_id in group_ids


@pytest.mark.integration
def test_group_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_group: int,
) -> None:
    """Group lifecycle: update_group changes the group name persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_group: Throw-away group fixture (integer ID).
    """
    new_name = f"Updated Group {uuid.uuid4().hex[:8]}"
    kanboard_client.groups.update_group(integration_group, name=new_name)

    group = kanboard_client.groups.get_group(integration_group)
    assert group.name == new_name


@pytest.mark.integration
def test_group_lifecycle_remove(
    kanboard_client: KanboardClient,
) -> None:
    """Group lifecycle: remove_group deletes the group; get_all excludes it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    suffix = uuid.uuid4().hex[:8]
    group_id = kanboard_client.groups.create_group(f"Remove Group {suffix}")
    # Intentionally not added to cleanup_group_ids — removed manually below.

    result = kanboard_client.groups.remove_group(group_id)
    assert result is True

    groups = kanboard_client.groups.get_all_groups()
    assert not any(g.id == group_id for g in groups)


# ---------------------------------------------------------------------------
# Group member lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_group_member_lifecycle_add_and_get_members(
    kanboard_client: KanboardClient,
    integration_group: int,
) -> None:
    """Group member: add_group_member makes the user appear in get_group_members.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_group: Throw-away group fixture (integer ID).
    """
    kanboard_client.group_members.add_group_member(integration_group, _ADMIN_USER_ID)

    members = kanboard_client.group_members.get_group_members(integration_group)
    member_ids = [m.id for m in members]
    assert _ADMIN_USER_ID in member_ids


@pytest.mark.integration
def test_group_member_lifecycle_get_member_groups(
    kanboard_client: KanboardClient,
    integration_group: int,
) -> None:
    """Group member: get_member_groups includes the group the user was added to.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_group: Throw-away group fixture (integer ID).
    """
    kanboard_client.group_members.add_group_member(integration_group, _ADMIN_USER_ID)

    groups = kanboard_client.group_members.get_member_groups(_ADMIN_USER_ID)
    group_ids = [g.id for g in groups]
    assert integration_group in group_ids


@pytest.mark.integration
def test_group_member_lifecycle_is_member(
    kanboard_client: KanboardClient,
    integration_group: int,
) -> None:
    """Group member: is_group_member returns True after add_group_member.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_group: Throw-away group fixture (integer ID).
    """
    kanboard_client.group_members.add_group_member(integration_group, _ADMIN_USER_ID)

    assert kanboard_client.group_members.is_group_member(integration_group, _ADMIN_USER_ID) is True


@pytest.mark.integration
def test_group_member_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_group: int,
) -> None:
    """Group member: remove_group_member removes the user from the group.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_group: Throw-away group fixture (integer ID).
    """
    kanboard_client.group_members.add_group_member(integration_group, _ADMIN_USER_ID)

    result = kanboard_client.group_members.remove_group_member(integration_group, _ADMIN_USER_ID)
    assert result is True

    members = kanboard_client.group_members.get_group_members(integration_group)
    assert not any(m.id == _ADMIN_USER_ID for m in members)


# ---------------------------------------------------------------------------
# External task link lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_external_task_link_get_types(
    kanboard_client: KanboardClient,
) -> None:
    """External task link: get_external_task_link_types returns non-empty dict.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    types = kanboard_client.external_task_links.get_external_task_link_types()
    assert isinstance(types, dict)
    assert len(types) > 0


@pytest.mark.integration
def test_external_task_link_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """External task link: create returns positive ID; get returns the correct link.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    link_id = kanboard_client.external_task_links.create_external_task_link(
        task_id=integration_task,
        url="https://github.com/example/repo/issues/1",
        dependency="related",
        type="weblink",
    )
    assert isinstance(link_id, int)
    assert link_id > 0

    link = kanboard_client.external_task_links.get_external_task_link_by_id(
        integration_task, link_id
    )
    assert isinstance(link, ExternalTaskLink)
    assert link.id == link_id
    assert "github.com" in link.url


@pytest.mark.integration
def test_external_task_link_lifecycle_get_all(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """External task link: get_all returns a list including the created link.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    link_id = kanboard_client.external_task_links.create_external_task_link(
        task_id=integration_task,
        url="https://example.com/doc/1",
        dependency="related",
        type="weblink",
    )

    links = kanboard_client.external_task_links.get_all_external_task_links(integration_task)
    link_ids = [lnk.id for lnk in links]
    assert link_id in link_ids


@pytest.mark.integration
def test_external_task_link_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """External task link: update changes the title and URL persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    link_id = kanboard_client.external_task_links.create_external_task_link(
        task_id=integration_task,
        url="https://example.com/original",
        dependency="related",
        type="weblink",
    )

    result = kanboard_client.external_task_links.update_external_task_link(
        task_id=integration_task,
        link_id=link_id,
        title="Updated External Link",
        url="https://example.com/updated",
    )
    assert result is True


@pytest.mark.integration
def test_external_task_link_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """External task link: remove deletes the link; get_all excludes it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer ID).
    """
    link_id = kanboard_client.external_task_links.create_external_task_link(
        task_id=integration_task,
        url="https://example.com/to-remove",
        dependency="related",
        type="weblink",
    )

    result = kanboard_client.external_task_links.remove_external_task_link(
        integration_task, link_id
    )
    assert result is True

    links = kanboard_client.external_task_links.get_all_external_task_links(integration_task)
    assert not any(lnk.id == link_id for lnk in links)


# ---------------------------------------------------------------------------
# Action lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_action_get_available_actions(
    kanboard_client: KanboardClient,
) -> None:
    """Actions: get_available_actions returns a non-empty dict of action types.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    actions = kanboard_client.actions.get_available_actions()
    assert isinstance(actions, dict)
    assert len(actions) > 0


@pytest.mark.integration
def test_action_get_available_action_events(
    kanboard_client: KanboardClient,
) -> None:
    """Actions: get_available_action_events returns a non-empty dict of event types.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    events = kanboard_client.actions.get_available_action_events()
    assert isinstance(events, dict)
    assert len(events) > 0


@pytest.mark.integration
def test_action_get_compatible_action_events(
    kanboard_client: KanboardClient,
) -> None:
    """Actions: get_compatible_action_events returns a list for a known action name.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    available = kanboard_client.actions.get_available_actions()
    # Pick any available action name to query compatible events
    action_name = next(iter(available))

    events = kanboard_client.actions.get_compatible_action_events(action_name)
    assert isinstance(events, list)
    assert len(events) > 0


@pytest.mark.integration
def test_action_lifecycle_create_and_get_and_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Actions: create → get_actions → remove completes successfully.

    Discovers a column-based action from the available actions, creates it
    for the integration project, verifies it appears in get_actions, then
    removes it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    # Discover a valid action that works with task.move.column and column_id param
    available = kanboard_client.actions.get_available_actions()
    # Find an action name containing "AssignCurrentUser" or "Close" which need only column_id
    action_name = next(
        (k for k in available if "AssignCurrentUser" in k or "CloseColumn" in k),
        next(iter(available)),  # fallback to first available
    )

    # Get the first column of the integration project for the param
    columns = kanboard_client.columns.get_columns(integration_project.id)
    assert columns, "Integration project should have at least one column"
    column_id = str(columns[0].id)

    action_id = kanboard_client.actions.create_action(
        project_id=integration_project.id,
        event_name="task.move.column",
        action_name=action_name,
        params={"column_id": column_id},
    )
    assert isinstance(action_id, int)
    assert action_id > 0

    project_actions = kanboard_client.actions.get_actions(integration_project.id)
    assert isinstance(project_actions, list)
    action_ids = [a.id for a in project_actions]
    assert action_id in action_ids
    # Verify the Action model fields are populated
    created = next(a for a in project_actions if a.id == action_id)
    assert isinstance(created, Action)
    assert created.project_id == integration_project.id
    assert created.event_name == "task.move.column"
    assert created.action_name == action_name

    result = kanboard_client.actions.remove_action(action_id)
    assert result is True

    project_actions_after = kanboard_client.actions.get_actions(integration_project.id)
    assert not any(a.id == action_id for a in project_actions_after)


# ---------------------------------------------------------------------------
# Subtask time tracking
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_subtask_time_tracking_start_and_has_timer(
    kanboard_client: KanboardClient,
    integration_subtask: int,
) -> None:
    """Subtask timer: set_subtask_start_time → has_subtask_timer returns True.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_subtask: Throw-away subtask fixture (integer ID).
    """
    result = kanboard_client.subtask_time_tracking.set_subtask_start_time(
        integration_subtask, user_id=_ADMIN_USER_ID
    )
    assert result is True

    has_timer = kanboard_client.subtask_time_tracking.has_subtask_timer(
        integration_subtask, user_id=_ADMIN_USER_ID
    )
    assert has_timer is True


@pytest.mark.integration
def test_subtask_time_tracking_stop(
    kanboard_client: KanboardClient,
    integration_subtask: int,
) -> None:
    """Subtask timer: set_subtask_end_time stops a running timer successfully.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_subtask: Throw-away subtask fixture (integer ID).
    """
    kanboard_client.subtask_time_tracking.set_subtask_start_time(
        integration_subtask, user_id=_ADMIN_USER_ID
    )

    result = kanboard_client.subtask_time_tracking.set_subtask_end_time(
        integration_subtask, user_id=_ADMIN_USER_ID
    )
    assert result is True


@pytest.mark.integration
def test_subtask_time_tracking_get_time_spent(
    kanboard_client: KanboardClient,
    integration_subtask: int,
) -> None:
    """Subtask timer: get_subtask_time_spent returns a non-negative float.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_subtask: Throw-away subtask fixture (integer ID).
    """
    kanboard_client.subtask_time_tracking.set_subtask_start_time(
        integration_subtask, user_id=_ADMIN_USER_ID
    )
    kanboard_client.subtask_time_tracking.set_subtask_end_time(
        integration_subtask, user_id=_ADMIN_USER_ID
    )

    time_spent = kanboard_client.subtask_time_tracking.get_subtask_time_spent(
        integration_subtask, user_id=_ADMIN_USER_ID
    )
    assert isinstance(time_spent, float)
    assert time_spent >= 0.0


# ---------------------------------------------------------------------------
# Application info
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_application_info_get_version(
    kanboard_client: KanboardClient,
) -> None:
    """Application info: get_version returns a non-empty semver-like string.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    version = kanboard_client.application.get_version()
    assert isinstance(version, str)
    assert len(version) > 0
    # Semver-like: contains at least one dot (e.g. "1.2.30")
    assert "." in version


@pytest.mark.integration
def test_application_info_get_timezone(
    kanboard_client: KanboardClient,
) -> None:
    """Application info: get_timezone returns a non-empty timezone string.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    tz = kanboard_client.application.get_timezone()
    assert isinstance(tz, str)
    assert len(tz) > 0


@pytest.mark.integration
def test_application_info_get_colors(
    kanboard_client: KanboardClient,
) -> None:
    """Application info: get_color_list returns a non-empty colour mapping.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    colors = kanboard_client.application.get_color_list()
    assert isinstance(colors, dict)
    assert len(colors) > 0


@pytest.mark.integration
def test_application_info_get_roles(
    kanboard_client: KanboardClient,
) -> None:
    """Application info: get_application_roles returns a non-empty role mapping.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
    """
    roles = kanboard_client.application.get_application_roles()
    assert isinstance(roles, dict)
    assert len(roles) > 0
