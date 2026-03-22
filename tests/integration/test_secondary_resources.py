"""Integration tests — secondary resource CRUD lifecycles.

Tests run against the Docker-backed Kanboard instance managed by the
session-scoped ``docker_kanboard`` fixture in ``conftest.py``.

Covered resources:
  * Comments   — create → get → get_all → update → remove
  * Categories — create → get → get_all → update → remove
  * Tags       — create → get_all → get_tags_by_project → set_task_tags →
                 get_task_tags → update → remove
  * Subtasks   — create → get → get_all → update → remove
  * Users      — create → get → get_by_name → update → enable/disable →
                 is_active → remove
  * Link types — create → get_by_id → get_by_label → get_all →
                 get_opposite_link_id → update → remove
  * Task links — create → get → get_all → update → remove
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest

from kanboard.client import KanboardClient
from kanboard.models import Category, Comment, Link, Project, Subtask, Tag, TaskLink, User

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

# admin user is always user_id=1 on a fresh Kanboard instance
_ADMIN_USER_ID: int = 1


@pytest.fixture()
def integration_project(
    kanboard_client: KanboardClient,
    cleanup_project_ids: list[int],
) -> Generator[Project, None, None]:
    """Create a throw-away project for a single test, clean it up afterwards.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_project_ids: Fixture that removes listed projects after the test.

    Yields:
        The newly created :class:`~kanboard.models.Project` instance.
    """
    project_id = kanboard_client.projects.create_project(
        "Integration Secondary Resources Test Project"
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
        title="Secondary Resources Test Task",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task_id)
    yield task_id


# ---------------------------------------------------------------------------
# Comment lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_comment_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Comment lifecycle: create_comment returns a positive ID; get_comment retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    comment_id = kanboard_client.comments.create_comment(
        task_id=integration_task,
        user_id=_ADMIN_USER_ID,
        content="Integration test comment — create/get",
    )
    assert isinstance(comment_id, int)
    assert comment_id > 0

    comment = kanboard_client.comments.get_comment(comment_id)
    assert isinstance(comment, Comment)
    assert comment.id == comment_id
    assert comment.task_id == integration_task
    assert comment.comment == "Integration test comment — create/get"


@pytest.mark.integration
def test_comment_lifecycle_get_all(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Comment lifecycle: get_all_comments returns a list including the created comment.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    comment_id = kanboard_client.comments.create_comment(
        task_id=integration_task,
        user_id=_ADMIN_USER_ID,
        content="Integration test comment — get all",
    )

    comments = kanboard_client.comments.get_all_comments(integration_task)
    assert isinstance(comments, list)
    assert len(comments) >= 1
    assert any(c.id == comment_id for c in comments), (
        f"Comment {comment_id} not found in get_all_comments result"
    )


@pytest.mark.integration
def test_comment_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Comment lifecycle: update_comment changes the content persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    comment_id = kanboard_client.comments.create_comment(
        task_id=integration_task,
        user_id=_ADMIN_USER_ID,
        content="Comment before update",
    )

    result = kanboard_client.comments.update_comment(
        id=comment_id,
        content="Comment after update",
    )
    assert result is True

    updated = kanboard_client.comments.get_comment(comment_id)
    assert updated.comment == "Comment after update"


@pytest.mark.integration
def test_comment_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Comment lifecycle: remove_comment permanently deletes the comment.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    comment_id = kanboard_client.comments.create_comment(
        task_id=integration_task,
        user_id=_ADMIN_USER_ID,
        content="Comment to remove",
    )

    result = kanboard_client.comments.remove_comment(comment_id)
    assert result is True

    remaining = kanboard_client.comments.get_all_comments(integration_task)
    assert not any(c.id == comment_id for c in remaining), (
        f"Comment {comment_id} still present after remove_comment"
    )


# ---------------------------------------------------------------------------
# Category lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_category_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Category lifecycle: create_category returns positive ID; get_category retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    cat_id = kanboard_client.categories.create_category(
        project_id=integration_project.id,
        name="Integration Test Category",
    )
    assert isinstance(cat_id, int)
    assert cat_id > 0

    cat = kanboard_client.categories.get_category(cat_id)
    assert isinstance(cat, Category)
    assert cat.id == cat_id
    assert cat.name == "Integration Test Category"
    assert cat.project_id == integration_project.id


@pytest.mark.integration
def test_category_lifecycle_get_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Category lifecycle: get_all_categories returns a list including the created category.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    cat_id = kanboard_client.categories.create_category(
        project_id=integration_project.id,
        name="Integration Test Category — Get All",
    )

    cats = kanboard_client.categories.get_all_categories(integration_project.id)
    assert isinstance(cats, list)
    assert any(c.id == cat_id for c in cats), (
        f"Category {cat_id} not found in get_all_categories result"
    )


@pytest.mark.integration
def test_category_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Category lifecycle: update_category changes the name persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    cat_id = kanboard_client.categories.create_category(
        project_id=integration_project.id,
        name="Category Before Update",
    )

    result = kanboard_client.categories.update_category(
        id=cat_id,
        name="Category After Update",
    )
    assert result is True

    updated = kanboard_client.categories.get_category(cat_id)
    assert updated.name == "Category After Update"


@pytest.mark.integration
def test_category_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Category lifecycle: remove_category permanently deletes the category.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    cat_id = kanboard_client.categories.create_category(
        project_id=integration_project.id,
        name="Category to Remove",
    )

    result = kanboard_client.categories.remove_category(cat_id)
    assert result is True

    remaining = kanboard_client.categories.get_all_categories(integration_project.id)
    assert not any(c.id == cat_id for c in remaining), (
        f"Category {cat_id} still visible after remove_category"
    )


# ---------------------------------------------------------------------------
# Tag lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_tag_lifecycle_create_and_get_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Tag lifecycle: create_tag returns a positive ID; get_all_tags includes the new tag.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    tag_id = kanboard_client.tags.create_tag(
        project_id=integration_project.id,
        tag="integration-test-tag",
    )
    assert isinstance(tag_id, int)
    assert tag_id > 0

    all_tags = kanboard_client.tags.get_all_tags()
    assert isinstance(all_tags, list)
    assert any(t.id == tag_id for t in all_tags), f"Tag {tag_id} not found in get_all_tags result"


@pytest.mark.integration
def test_tag_lifecycle_get_tags_by_project(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Tag lifecycle: get_tags_by_project returns only tags scoped to the project.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    tag_id = kanboard_client.tags.create_tag(
        project_id=integration_project.id,
        tag="project-scoped-tag",
    )

    tags = kanboard_client.tags.get_tags_by_project(integration_project.id)
    assert isinstance(tags, list)
    assert any(t.id == tag_id for t in tags), (
        f"Tag {tag_id} not found in get_tags_by_project result"
    )
    assert all(isinstance(t, Tag) for t in tags)
    assert all(t.project_id == integration_project.id for t in tags), (
        "get_tags_by_project returned tags from a different project"
    )


@pytest.mark.integration
def test_tag_lifecycle_set_and_get_task_tags(
    kanboard_client: KanboardClient,
    integration_project: Project,
    integration_task: int,
) -> None:
    """Tag lifecycle: set_task_tags assigns tags; get_task_tags returns the assignment.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        integration_task: Throw-away task fixture (integer task ID).
    """
    tag_name = "task-assignment-tag"
    kanboard_client.tags.create_tag(
        project_id=integration_project.id,
        tag=tag_name,
    )

    result = kanboard_client.tags.set_task_tags(
        project_id=integration_project.id,
        task_id=integration_task,
        tags=[tag_name],
    )
    assert result is True

    task_tags = kanboard_client.tags.get_task_tags(integration_task)
    assert isinstance(task_tags, dict)
    assert tag_name in task_tags.values(), (
        f"Tag '{tag_name}' not found in get_task_tags result: {task_tags}"
    )


@pytest.mark.integration
def test_tag_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Tag lifecycle: update_tag renames the tag persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    tag_id = kanboard_client.tags.create_tag(
        project_id=integration_project.id,
        tag="tag-before-update",
    )

    result = kanboard_client.tags.update_tag(tag_id=tag_id, tag="tag-after-update")
    assert result is True

    tags = kanboard_client.tags.get_tags_by_project(integration_project.id)
    updated = next((t for t in tags if t.id == tag_id), None)
    assert updated is not None, f"Tag {tag_id} not found after update"
    assert updated.name == "tag-after-update"


@pytest.mark.integration
def test_tag_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
) -> None:
    """Tag lifecycle: remove_tag permanently deletes the tag.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
    """
    tag_id = kanboard_client.tags.create_tag(
        project_id=integration_project.id,
        tag="tag-to-remove",
    )

    result = kanboard_client.tags.remove_tag(tag_id=tag_id)
    assert result is True

    remaining = kanboard_client.tags.get_tags_by_project(integration_project.id)
    assert not any(t.id == tag_id for t in remaining), (
        f"Tag {tag_id} still visible after remove_tag"
    )


# ---------------------------------------------------------------------------
# Subtask lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_subtask_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Subtask lifecycle: create_subtask returns positive ID; get_subtask retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    subtask_id = kanboard_client.subtasks.create_subtask(
        task_id=integration_task,
        title="Integration Test Subtask",
    )
    assert isinstance(subtask_id, int)
    assert subtask_id > 0

    subtask = kanboard_client.subtasks.get_subtask(subtask_id)
    assert isinstance(subtask, Subtask)
    assert subtask.id == subtask_id
    assert subtask.task_id == integration_task
    assert subtask.title == "Integration Test Subtask"
    assert subtask.status == 0  # 0 = todo (default)


@pytest.mark.integration
def test_subtask_lifecycle_get_all(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Subtask lifecycle: get_all_subtasks returns a list including the created subtask.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    subtask_id = kanboard_client.subtasks.create_subtask(
        task_id=integration_task,
        title="Integration Test Subtask — Get All",
    )

    subtasks = kanboard_client.subtasks.get_all_subtasks(integration_task)
    assert isinstance(subtasks, list)
    assert any(s.id == subtask_id for s in subtasks), (
        f"Subtask {subtask_id} not found in get_all_subtasks result"
    )


@pytest.mark.integration
def test_subtask_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Subtask lifecycle: update_subtask changes title and status persistently.

    Subtask statuses: 0 = todo, 1 = in progress, 2 = done.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    subtask_id = kanboard_client.subtasks.create_subtask(
        task_id=integration_task,
        title="Subtask Before Update",
    )

    result = kanboard_client.subtasks.update_subtask(
        id=subtask_id,
        task_id=integration_task,
        title="Subtask After Update",
        status=1,  # in progress
    )
    assert result is True

    updated = kanboard_client.subtasks.get_subtask(subtask_id)
    assert updated.title == "Subtask After Update"
    assert updated.status == 1


@pytest.mark.integration
def test_subtask_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_task: int,
) -> None:
    """Subtask lifecycle: remove_subtask permanently deletes the subtask.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_task: Throw-away task fixture (integer task ID).
    """
    subtask_id = kanboard_client.subtasks.create_subtask(
        task_id=integration_task,
        title="Subtask to Remove",
    )

    result = kanboard_client.subtasks.remove_subtask(subtask_id)
    assert result is True

    remaining = kanboard_client.subtasks.get_all_subtasks(integration_task)
    assert not any(s.id == subtask_id for s in remaining), (
        f"Subtask {subtask_id} still present after remove_subtask"
    )


# ---------------------------------------------------------------------------
# User lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_user_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> None:
    """User lifecycle: create_user returns a positive ID; get_user retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.
    """
    username = f"test-user-{uuid.uuid4().hex[:8]}"
    user_id = kanboard_client.users.create_user(
        username=username,
        password="Test-Password-123!",
        name="Integration Test User",
    )
    cleanup_user_ids.append(user_id)

    assert isinstance(user_id, int)
    assert user_id > 0

    user = kanboard_client.users.get_user(user_id)
    assert isinstance(user, User)
    assert user.id == user_id
    assert user.username == username
    assert user.name == "Integration Test User"
    assert user.is_active is True


@pytest.mark.integration
def test_user_lifecycle_get_by_name(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> None:
    """User lifecycle: get_user_by_name retrieves the user by username.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.
    """
    username = f"test-user-{uuid.uuid4().hex[:8]}"
    user_id = kanboard_client.users.create_user(
        username=username,
        password="Test-Password-123!",
    )
    cleanup_user_ids.append(user_id)

    user = kanboard_client.users.get_user_by_name(username)
    assert user.id == user_id
    assert user.username == username


@pytest.mark.integration
def test_user_lifecycle_update(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> None:
    """User lifecycle: update_user changes the display name persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.
    """
    username = f"test-user-{uuid.uuid4().hex[:8]}"
    user_id = kanboard_client.users.create_user(
        username=username,
        password="Test-Password-123!",
        name="Before Update",
    )
    cleanup_user_ids.append(user_id)

    result = kanboard_client.users.update_user(id=user_id, name="After Update")
    assert result is True

    updated = kanboard_client.users.get_user(user_id)
    assert updated.name == "After Update"


@pytest.mark.integration
def test_user_lifecycle_enable_disable(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> None:
    """User lifecycle: disable_user deactivates the account; enable_user reactivates it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.
    """
    username = f"test-user-{uuid.uuid4().hex[:8]}"
    user_id = kanboard_client.users.create_user(
        username=username,
        password="Test-Password-123!",
    )
    cleanup_user_ids.append(user_id)

    # Disable
    assert kanboard_client.users.disable_user(user_id) is True
    disabled = kanboard_client.users.get_user(user_id)
    assert disabled.is_active is False

    # Re-enable
    assert kanboard_client.users.enable_user(user_id) is True
    enabled = kanboard_client.users.get_user(user_id)
    assert enabled.is_active is True


@pytest.mark.integration
def test_user_lifecycle_is_active(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> None:
    """User lifecycle: is_active_user returns True for active and False for disabled users.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.
    """
    username = f"test-user-{uuid.uuid4().hex[:8]}"
    user_id = kanboard_client.users.create_user(
        username=username,
        password="Test-Password-123!",
    )
    cleanup_user_ids.append(user_id)

    assert kanboard_client.users.is_active_user(user_id) is True

    kanboard_client.users.disable_user(user_id)
    assert kanboard_client.users.is_active_user(user_id) is False

    # Re-enable so cleanup (remove_user) can proceed without issues
    kanboard_client.users.enable_user(user_id)


@pytest.mark.integration
def test_user_lifecycle_remove(
    kanboard_client: KanboardClient,
    cleanup_user_ids: list[int],
) -> None:
    """User lifecycle: remove_user permanently deletes the user.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_user_ids: Fixture that removes listed users after the test.
    """
    username = f"test-user-{uuid.uuid4().hex[:8]}"
    user_id = kanboard_client.users.create_user(
        username=username,
        password="Test-Password-123!",
    )
    cleanup_user_ids.append(user_id)

    result = kanboard_client.users.remove_user(user_id)
    assert result is True

    all_users = kanboard_client.users.get_all_users()
    assert not any(u.id == user_id for u in all_users), (
        f"User {user_id} still visible after remove_user"
    )


# ---------------------------------------------------------------------------
# Link type lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_link_lifecycle_create_and_get_by_id(
    kanboard_client: KanboardClient,
    cleanup_link_ids: list[int],
) -> None:
    """Link type lifecycle: create_link returns positive ID; get_link_by_id retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_link_ids: Fixture that removes listed link types after the test.
    """
    label = f"int-test-link-{uuid.uuid4().hex[:6]}"
    link_id = kanboard_client.links.create_link(label=label)
    cleanup_link_ids.append(link_id)

    link = kanboard_client.links.get_link_by_id(link_id)
    assert isinstance(link, Link)
    assert link.id == link_id
    assert link.label == label


@pytest.mark.integration
def test_link_lifecycle_get_by_label(
    kanboard_client: KanboardClient,
    cleanup_link_ids: list[int],
) -> None:
    """Link type lifecycle: get_link_by_label retrieves the link type by its label string.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_link_ids: Fixture that removes listed link types after the test.
    """
    label = f"int-test-link-{uuid.uuid4().hex[:6]}"
    link_id = kanboard_client.links.create_link(label=label)
    cleanup_link_ids.append(link_id)

    link = kanboard_client.links.get_link_by_label(label)
    assert link.id == link_id
    assert link.label == label


@pytest.mark.integration
def test_link_lifecycle_get_all(
    kanboard_client: KanboardClient,
    cleanup_link_ids: list[int],
) -> None:
    """Link type lifecycle: get_all_links returns a list including the newly created link type.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_link_ids: Fixture that removes listed link types after the test.
    """
    label = f"int-test-link-{uuid.uuid4().hex[:6]}"
    link_id = kanboard_client.links.create_link(label=label)
    cleanup_link_ids.append(link_id)

    all_links = kanboard_client.links.get_all_links()
    assert isinstance(all_links, list)
    assert len(all_links) >= 1
    assert any(lk.id == link_id for lk in all_links), (
        f"Link {link_id} not found in get_all_links result"
    )


@pytest.mark.integration
def test_link_lifecycle_get_opposite_link_id(
    kanboard_client: KanboardClient,
    cleanup_link_ids: list[int],
) -> None:
    """Link type lifecycle: get_opposite_link_id returns the opposite relationship link ID.

    Creates a link with a distinct opposite label to exercise the bidirectional
    relationship.  Both the forward and reverse link IDs are registered for cleanup.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_link_ids: Fixture that removes listed link types after the test.
    """
    uid = uuid.uuid4().hex[:6]
    forward_label = f"int-test-fwd-{uid}"
    opposite_label = f"int-test-rev-{uid}"

    link_id = kanboard_client.links.create_link(
        label=forward_label,
        opposite_label=opposite_label,
    )
    cleanup_link_ids.append(link_id)

    opposite_id = kanboard_client.links.get_opposite_link_id(link_id)
    assert isinstance(opposite_id, int)
    assert opposite_id > 0

    # Register the opposite ID for cleanup (may equal link_id for self-referencing links)
    if opposite_id != link_id:
        cleanup_link_ids.append(opposite_id)

    # The opposite link's label should match the opposite_label we provided
    opposite_link = kanboard_client.links.get_link_by_id(opposite_id)
    assert opposite_link.label == opposite_label


@pytest.mark.integration
def test_link_lifecycle_update(
    kanboard_client: KanboardClient,
    cleanup_link_ids: list[int],
) -> None:
    """Link type lifecycle: update_link changes the label persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_link_ids: Fixture that removes listed link types after the test.
    """
    label = f"int-test-link-{uuid.uuid4().hex[:6]}"
    link_id = kanboard_client.links.create_link(label=label)
    cleanup_link_ids.append(link_id)

    # Retrieve the opposite ID (self-referencing for a no-opposite-label link)
    opposite_id = kanboard_client.links.get_opposite_link_id(link_id)
    if opposite_id != link_id:
        cleanup_link_ids.append(opposite_id)

    new_label = f"int-test-link-updated-{uuid.uuid4().hex[:6]}"
    result = kanboard_client.links.update_link(
        link_id=link_id,
        opposite_link_id=opposite_id,
        label=new_label,
    )
    assert result is True

    updated = kanboard_client.links.get_link_by_id(link_id)
    assert updated.label == new_label


@pytest.mark.integration
def test_link_lifecycle_remove(
    kanboard_client: KanboardClient,
    cleanup_link_ids: list[int],
) -> None:
    """Link type lifecycle: remove_link permanently deletes the link type.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        cleanup_link_ids: Fixture that removes listed link types after the test.
    """
    label = f"int-test-link-{uuid.uuid4().hex[:6]}"
    link_id = kanboard_client.links.create_link(label=label)
    cleanup_link_ids.append(link_id)

    result = kanboard_client.links.remove_link(link_id)
    assert result is True

    all_links = kanboard_client.links.get_all_links()
    assert not any(lk.id == link_id for lk in all_links), (
        f"Link {link_id} still visible after remove_link"
    )


# ---------------------------------------------------------------------------
# Task link lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_task_link_lifecycle_create_and_get(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task link lifecycle: create_task_link returns positive ID; get_task_link_by_id retrieves it.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task1_id = kanboard_client.tasks.create_task(
        title="Task Link Source Task",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task1_id)

    task2_id = kanboard_client.tasks.create_task(
        title="Task Link Target Task",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task2_id)

    # Use the first available (built-in) link type
    available_links = kanboard_client.links.get_all_links()
    assert len(available_links) >= 1, "Expected at least one built-in link type"
    link_type = available_links[0]

    task_link_id = kanboard_client.task_links.create_task_link(
        task_id=task1_id,
        opposite_task_id=task2_id,
        link_id=link_type.id,
    )
    assert isinstance(task_link_id, int)
    assert task_link_id > 0

    task_link = kanboard_client.task_links.get_task_link_by_id(task_link_id)
    assert isinstance(task_link, TaskLink)
    assert task_link.id == task_link_id
    assert task_link.task_id == task1_id
    assert task_link.opposite_task_id == task2_id
    assert task_link.link_id == link_type.id


@pytest.mark.integration
def test_task_link_lifecycle_get_all(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task link lifecycle: get_all_task_links returns a list including the created task link.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task1_id = kanboard_client.tasks.create_task(
        title="Task Link Get All — Source",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task1_id)

    task2_id = kanboard_client.tasks.create_task(
        title="Task Link Get All — Target",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task2_id)

    available_links = kanboard_client.links.get_all_links()
    link_type = available_links[0]

    task_link_id = kanboard_client.task_links.create_task_link(
        task_id=task1_id,
        opposite_task_id=task2_id,
        link_id=link_type.id,
    )

    all_task_links = kanboard_client.task_links.get_all_task_links(task1_id)
    assert isinstance(all_task_links, list)
    assert any(tl.id == task_link_id for tl in all_task_links), (
        f"Task link {task_link_id} not found in get_all_task_links result"
    )


@pytest.mark.integration
def test_task_link_lifecycle_update(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task link lifecycle: update_task_link changes the relationship type persistently.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task1_id = kanboard_client.tasks.create_task(
        title="Task Link Update — Source",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task1_id)

    task2_id = kanboard_client.tasks.create_task(
        title="Task Link Update — Target",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task2_id)

    available_links = kanboard_client.links.get_all_links()
    assert len(available_links) >= 2, "Expected at least two built-in link types for update test"
    link_type_1 = available_links[0]
    link_type_2 = available_links[1]

    task_link_id = kanboard_client.task_links.create_task_link(
        task_id=task1_id,
        opposite_task_id=task2_id,
        link_id=link_type_1.id,
    )

    result = kanboard_client.task_links.update_task_link(
        task_link_id=task_link_id,
        task_id=task1_id,
        opposite_task_id=task2_id,
        link_id=link_type_2.id,
    )
    assert result is True

    updated = kanboard_client.task_links.get_task_link_by_id(task_link_id)
    assert updated.link_id == link_type_2.id


@pytest.mark.integration
def test_task_link_lifecycle_remove(
    kanboard_client: KanboardClient,
    integration_project: Project,
    cleanup_task_ids: list[int],
) -> None:
    """Task link lifecycle: remove_task_link permanently deletes the task link.

    Args:
        kanboard_client: Session-scoped client connected to the Docker Kanboard.
        integration_project: Throw-away project fixture.
        cleanup_task_ids: Fixture that removes listed tasks after the test.
    """
    task1_id = kanboard_client.tasks.create_task(
        title="Task Link Remove — Source",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task1_id)

    task2_id = kanboard_client.tasks.create_task(
        title="Task Link Remove — Target",
        project_id=integration_project.id,
    )
    cleanup_task_ids.append(task2_id)

    available_links = kanboard_client.links.get_all_links()
    link_type = available_links[0]

    task_link_id = kanboard_client.task_links.create_task_link(
        task_id=task1_id,
        opposite_task_id=task2_id,
        link_id=link_type.id,
    )

    result = kanboard_client.task_links.remove_task_link(task_link_id)
    assert result is True

    remaining = kanboard_client.task_links.get_all_task_links(task1_id)
    assert not any(tl.id == task_link_id for tl in remaining), (
        f"Task link {task_link_id} still visible after remove_task_link"
    )
