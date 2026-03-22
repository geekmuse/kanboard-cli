"""Unit tests for src/kanboard/models.py — helpers and dataclass models."""

from datetime import datetime

import pytest

from kanboard.models import (
    Action,
    Category,
    Column,
    Comment,
    DependencyEdge,
    ExternalTaskLink,
    Group,
    Link,
    Milestone,
    MilestoneProgress,
    Portfolio,
    Project,
    ProjectFile,
    Subtask,
    Swimlane,
    Tag,
    Task,
    TaskFile,
    TaskLink,
    User,
    _float,
    _int,
    _parse_date,
)

# ---------------------------------------------------------------------------
# _parse_date tests
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_whitespace_only_returns_none(self):
        assert _parse_date("   ") is None

    def test_string_zero_returns_none(self):
        assert _parse_date("0") is None

    def test_int_zero_returns_none(self):
        assert _parse_date(0) is None

    def test_datetime_passthrough(self):
        dt = datetime(2024, 6, 15, 10, 30)
        assert _parse_date(dt) is dt

    def test_unix_timestamp_int(self):
        ts = 1410865507
        result = _parse_date(ts)
        assert isinstance(result, datetime)
        assert result == datetime.fromtimestamp(ts)

    def test_unix_timestamp_string(self):
        result = _parse_date("1410865507")
        assert isinstance(result, datetime)
        assert result == datetime.fromtimestamp(1410865507)

    def test_iso_datetime_hhmm(self):
        result = _parse_date("2024-01-15 14:30")
        assert result == datetime(2024, 1, 15, 14, 30)

    def test_iso_datetime_hhmmss(self):
        result = _parse_date("2024-01-15 14:30:59")
        assert result == datetime(2024, 1, 15, 14, 30, 59)

    def test_iso_date_only(self):
        result = _parse_date("2024-01-15")
        assert result == datetime(2024, 1, 15, 0, 0, 0)

    def test_invalid_string_returns_none(self):
        assert _parse_date("not-a-date") is None

    def test_negative_timestamp_still_parsed(self):
        # Negative timestamps are valid (pre-1970) — just ensure no crash.
        result = _parse_date("-1")
        # fromtimestamp(-1) may or may not succeed depending on platform; we just
        # verify it returns a datetime or None without raising.
        assert result is None or isinstance(result, datetime)

    def test_large_timestamp_string(self):
        result = _parse_date("9999999999")
        assert isinstance(result, datetime)

    def test_numeric_string_zero_variant_returns_none(self):
        # "00" and "000" parse to int 0 → None
        assert _parse_date("00") is None
        assert _parse_date("000") is None


# ---------------------------------------------------------------------------
# _int tests
# ---------------------------------------------------------------------------


class TestInt:
    def test_none_returns_zero(self):
        assert _int(None) == 0

    def test_string_zero(self):
        assert _int("0") == 0

    def test_string_integer(self):
        assert _int("42") == 42

    def test_plain_int(self):
        assert _int(99) == 99

    def test_float_truncates(self):
        assert _int(3.9) == 3

    def test_invalid_string_returns_zero(self):
        assert _int("bad") == 0

    def test_empty_string_returns_zero(self):
        assert _int("") == 0

    def test_negative(self):
        assert _int("-5") == -5


# ---------------------------------------------------------------------------
# _float tests
# ---------------------------------------------------------------------------


class TestFloat:
    def test_none_returns_zero(self):
        assert _float(None) == 0.0

    def test_int_value(self):
        assert _float(5) == 5.0

    def test_float_string(self):
        assert _float("1.5") == 1.5

    def test_plain_float(self):
        assert _float(2.25) == 2.25

    def test_invalid_string_returns_zero(self):
        assert _float("nope") == 0.0


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

_TASK_PAYLOAD = {
    "id": "1",
    "title": "Fix the bug",
    "description": "Detailed description",
    "date_creation": "1410865507",
    "date_modification": "1410865507",
    "date_due": "0",
    "date_completed": None,
    "date_moved": "1410865507",
    "color_id": "green",
    "project_id": "2",
    "column_id": "3",
    "swimlane_id": "0",
    "owner_id": "5",
    "creator_id": "1",
    "category_id": "0",
    "is_active": "1",
    "priority": "2",
    "score": "10",
    "position": "1",
    "reference": "BUG-42",
    "tags": ["backend", "urgent"],
    "url": "http://kanboard.example.com/task/1",
}


class TestTask:
    def test_from_api_basic(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert task.id == 1
        assert task.title == "Fix the bug"
        assert task.description == "Detailed description"

    def test_from_api_int_coercion(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert task.project_id == 2
        assert task.column_id == 3
        assert task.owner_id == 5
        assert task.priority == 2
        assert task.score == 10

    def test_from_api_dates(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert isinstance(task.date_creation, datetime)
        assert task.date_due is None  # "0" → None
        assert task.date_completed is None  # None → None
        assert isinstance(task.date_moved, datetime)

    def test_from_api_is_active_true(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert task.is_active is True

    def test_from_api_is_active_false(self):
        task = Task.from_api({**_TASK_PAYLOAD, "is_active": "0"})
        assert task.is_active is False

    def test_from_api_tags(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert task.tags == ["backend", "urgent"]

    def test_from_api_tags_none_becomes_empty_list(self):
        task = Task.from_api({**_TASK_PAYLOAD, "tags": None})
        assert task.tags == []

    def test_from_api_tags_missing_becomes_empty_list(self):
        data = {k: v for k, v in _TASK_PAYLOAD.items() if k != "tags"}
        task = Task.from_api(data)
        assert task.tags == []

    def test_from_api_url(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert task.url == "http://kanboard.example.com/task/1"

    def test_from_api_empty_dict_uses_defaults(self):
        task = Task.from_api({})
        assert task.id == 0
        assert task.title == ""
        assert task.is_active is True  # default is_active=1
        assert task.tags == []
        assert task.date_creation is None

    def test_swimlane_id_zero(self):
        task = Task.from_api(_TASK_PAYLOAD)
        assert task.swimlane_id == 0


# ---------------------------------------------------------------------------
# Project tests
# ---------------------------------------------------------------------------

_PROJECT_PAYLOAD = {
    "id": "1",
    "name": "My Project",
    "description": "A test project",
    "is_active": "1",
    "token": "abc123",
    "last_modified": "1410263727",
    "is_public": "0",
    "is_private": False,
    "owner_id": "3",
    "identifier": "MYPROJ",
    "start_date": None,
    "end_date": None,
    "url": "http://kanboard.example.com/board/1",
}


class TestProject:
    def test_from_api_basic(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert proj.id == 1
        assert proj.name == "My Project"
        assert proj.token == "abc123"

    def test_from_api_is_active(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert proj.is_active is True

    def test_from_api_is_public_false(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert proj.is_public is False

    def test_from_api_is_private(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert proj.is_private is False

    def test_from_api_last_modified_date(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert isinstance(proj.last_modified, datetime)

    def test_from_api_start_end_date_none(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert proj.start_date is None
        assert proj.end_date is None

    def test_from_api_url_string(self):
        proj = Project.from_api(_PROJECT_PAYLOAD)
        assert proj.url == "http://kanboard.example.com/board/1"

    def test_from_api_url_dict_extracts_board(self):
        data = {
            **_PROJECT_PAYLOAD,
            "url": {
                "board": "http://kanboard.example.com/board/1",
                "calendar": "http://kanboard.example.com/calendar/1",
                "list": "http://kanboard.example.com/list/1",
            },
        }
        proj = Project.from_api(data)
        assert proj.url == "http://kanboard.example.com/board/1"

    def test_from_api_empty_dict_uses_defaults(self):
        proj = Project.from_api({})
        assert proj.id == 0
        assert proj.name == ""
        assert proj.is_active is True
        assert proj.last_modified is None


# ---------------------------------------------------------------------------
# Column tests
# ---------------------------------------------------------------------------

_COLUMN_PAYLOAD = {
    "id": "1",
    "title": "Backlog",
    "project_id": "1",
    "task_limit": "5",
    "position": "1",
    "description": "Incoming work",
    "hide_in_dashboard": 0,
}


class TestColumn:
    def test_from_api_basic(self):
        col = Column.from_api(_COLUMN_PAYLOAD)
        assert col.id == 1
        assert col.title == "Backlog"
        assert col.project_id == 1
        assert col.task_limit == 5
        assert col.position == 1

    def test_hide_in_dashboard_false(self):
        col = Column.from_api(_COLUMN_PAYLOAD)
        assert col.hide_in_dashboard is False

    def test_hide_in_dashboard_true(self):
        col = Column.from_api({**_COLUMN_PAYLOAD, "hide_in_dashboard": 1})
        assert col.hide_in_dashboard is True

    def test_from_api_empty_dict_uses_defaults(self):
        col = Column.from_api({})
        assert col.id == 0
        assert col.title == ""
        assert col.task_limit == 0


# ---------------------------------------------------------------------------
# Swimlane tests
# ---------------------------------------------------------------------------

_SWIMLANE_PAYLOAD = {
    "id": "2",
    "name": "Sprint 1",
    "project_id": "1",
    "position": 2,
    "is_active": 1,
    "description": "First sprint",
}


class TestSwimlane:
    def test_from_api_basic(self):
        lane = Swimlane.from_api(_SWIMLANE_PAYLOAD)
        assert lane.id == 2
        assert lane.name == "Sprint 1"
        assert lane.project_id == 1
        assert lane.position == 2

    def test_is_active_true(self):
        lane = Swimlane.from_api(_SWIMLANE_PAYLOAD)
        assert lane.is_active is True

    def test_is_active_false(self):
        lane = Swimlane.from_api({**_SWIMLANE_PAYLOAD, "is_active": 0})
        assert lane.is_active is False

    def test_description(self):
        lane = Swimlane.from_api(_SWIMLANE_PAYLOAD)
        assert lane.description == "First sprint"

    def test_from_api_empty_dict_uses_defaults(self):
        lane = Swimlane.from_api({})
        assert lane.id == 0
        assert lane.name == ""
        assert lane.is_active is True  # default 1


# ---------------------------------------------------------------------------
# Comment tests
# ---------------------------------------------------------------------------

_COMMENT_PAYLOAD = {
    "id": "10",
    "task_id": "1",
    "user_id": "3",
    "username": "alice",
    "name": "Alice Smith",
    "comment": "Looks good to me!",
    "date_creation": "1410456198",
    "date_modification": "1410456198",
}


class TestComment:
    def test_from_api_basic(self):
        c = Comment.from_api(_COMMENT_PAYLOAD)
        assert c.id == 10
        assert c.task_id == 1
        assert c.user_id == 3
        assert c.username == "alice"
        assert c.comment == "Looks good to me!"

    def test_dates_parsed(self):
        c = Comment.from_api(_COMMENT_PAYLOAD)
        assert isinstance(c.date_creation, datetime)
        assert isinstance(c.date_modification, datetime)

    def test_from_api_empty_dict_uses_defaults(self):
        c = Comment.from_api({})
        assert c.id == 0
        assert c.comment == ""
        assert c.date_creation is None


# ---------------------------------------------------------------------------
# Subtask tests
# ---------------------------------------------------------------------------

_SUBTASK_PAYLOAD = {
    "id": "5",
    "title": "Write tests",
    "task_id": "1",
    "user_id": "2",
    "status": 1,
    "time_estimated": "2.5",
    "time_spent": "1.0",
    "position": 1,
    "username": "bob",
    "name": "Bob Jones",
}


class TestSubtask:
    def test_from_api_basic(self):
        s = Subtask.from_api(_SUBTASK_PAYLOAD)
        assert s.id == 5
        assert s.title == "Write tests"
        assert s.task_id == 1
        assert s.user_id == 2

    def test_status_int(self):
        s = Subtask.from_api(_SUBTASK_PAYLOAD)
        assert s.status == 1

    def test_time_fields_as_float(self):
        s = Subtask.from_api(_SUBTASK_PAYLOAD)
        assert s.time_estimated == pytest.approx(2.5)
        assert s.time_spent == pytest.approx(1.0)

    def test_time_fields_zero_when_missing(self):
        s = Subtask.from_api({**_SUBTASK_PAYLOAD, "time_estimated": None, "time_spent": None})
        assert s.time_estimated == 0.0
        assert s.time_spent == 0.0

    def test_from_api_empty_dict_uses_defaults(self):
        s = Subtask.from_api({})
        assert s.id == 0
        assert s.status == 0
        assert s.time_estimated == 0.0


# ---------------------------------------------------------------------------
# User tests
# ---------------------------------------------------------------------------

_USER_PAYLOAD = {
    "id": "1",
    "username": "admin",
    "name": "Administrator",
    "email": "admin@example.com",
    "role": "app-admin",
    "is_active": "1",
    "is_ldap_user": 0,
    "notification_method": 0,
    "avatar_path": "/avatars/admin.png",
    "timezone": "America/New_York",
    "language": "en_US",
}


class TestUser:
    def test_from_api_basic(self):
        u = User.from_api(_USER_PAYLOAD)
        assert u.id == 1
        assert u.username == "admin"
        assert u.email == "admin@example.com"
        assert u.role == "app-admin"

    def test_is_active_true(self):
        u = User.from_api(_USER_PAYLOAD)
        assert u.is_active is True

    def test_is_ldap_user_false(self):
        u = User.from_api(_USER_PAYLOAD)
        assert u.is_ldap_user is False

    def test_optional_string_fields_populated(self):
        u = User.from_api(_USER_PAYLOAD)
        assert u.avatar_path == "/avatars/admin.png"
        assert u.timezone == "America/New_York"
        assert u.language == "en_US"

    def test_optional_fields_none_when_null(self):
        data = {**_USER_PAYLOAD, "avatar_path": None, "timezone": None, "language": None}
        u = User.from_api(data)
        assert u.avatar_path is None
        assert u.timezone is None
        assert u.language is None

    def test_from_api_empty_dict_uses_defaults(self):
        u = User.from_api({})
        assert u.id == 0
        assert u.username == ""
        assert u.is_active is True  # default 1
        assert u.avatar_path is None


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------

_CATEGORY_PAYLOAD = {
    "id": "3",
    "name": "Backend",
    "project_id": "1",
    "color_id": "yellow",
}


class TestCategory:
    def test_from_api_basic(self):
        cat = Category.from_api(_CATEGORY_PAYLOAD)
        assert cat.id == 3
        assert cat.name == "Backend"
        assert cat.project_id == 1
        assert cat.color_id == "yellow"

    def test_from_api_empty_dict_uses_defaults(self):
        cat = Category.from_api({})
        assert cat.id == 0
        assert cat.name == ""
        assert cat.color_id == ""

    def test_from_api_string_id_coerced(self):
        data = {"id": "99", "name": "Frontend", "project_id": "2", "color_id": "blue"}
        cat = Category.from_api(data)
        assert cat.id == 99
        assert cat.project_id == 2


# ---------------------------------------------------------------------------
# Tag tests
# ---------------------------------------------------------------------------

_TAG_PAYLOAD = {
    "id": "1",
    "name": "security",
    "project_id": "2",
    "color_id": "blue",
}


class TestTag:
    def test_from_api_basic(self):
        tag = Tag.from_api(_TAG_PAYLOAD)
        assert tag.id == 1
        assert tag.name == "security"
        assert tag.project_id == 2
        assert tag.color_id == "blue"

    def test_from_api_string_id_coerced(self):
        tag = Tag.from_api({**_TAG_PAYLOAD, "id": "99"})
        assert tag.id == 99

    def test_from_api_missing_color_uses_default(self):
        data = {"id": "1", "name": "bug", "project_id": "1"}
        tag = Tag.from_api(data)
        assert tag.color_id == ""

    def test_from_api_empty_dict_uses_defaults(self):
        tag = Tag.from_api({})
        assert tag.id == 0
        assert tag.name == ""
        assert tag.project_id == 0
        assert tag.color_id == ""


# ---------------------------------------------------------------------------
# Link tests
# ---------------------------------------------------------------------------

_LINK_PAYLOAD = {
    "id": "1",
    "label": "blocks",
    "opposite_id": "2",
}


class TestLink:
    def test_from_api_basic(self):
        link = Link.from_api(_LINK_PAYLOAD)
        assert link.id == 1
        assert link.label == "blocks"
        assert link.opposite_id == 2

    def test_from_api_string_ids_coerced(self):
        link = Link.from_api({"id": "5", "label": "relates to", "opposite_id": "5"})
        assert link.id == 5
        assert link.opposite_id == 5

    def test_from_api_empty_dict_uses_defaults(self):
        link = Link.from_api({})
        assert link.id == 0
        assert link.label == ""
        assert link.opposite_id == 0


# ---------------------------------------------------------------------------
# TaskLink tests
# ---------------------------------------------------------------------------

_TASK_LINK_PAYLOAD = {
    "id": "10",
    "task_id": "3",
    "opposite_task_id": "7",
    "link_id": "1",
}


class TestTaskLink:
    def test_from_api_basic(self):
        tl = TaskLink.from_api(_TASK_LINK_PAYLOAD)
        assert tl.id == 10
        assert tl.task_id == 3
        assert tl.opposite_task_id == 7
        assert tl.link_id == 1

    def test_from_api_string_ids_coerced(self):
        tl = TaskLink.from_api({**_TASK_LINK_PAYLOAD, "id": "99", "link_id": "3"})
        assert tl.id == 99
        assert tl.link_id == 3

    def test_from_api_empty_dict_uses_defaults(self):
        tl = TaskLink.from_api({})
        assert tl.id == 0
        assert tl.task_id == 0
        assert tl.opposite_task_id == 0
        assert tl.link_id == 0


# ---------------------------------------------------------------------------
# ExternalTaskLink tests
# ---------------------------------------------------------------------------

_EXT_LINK_PAYLOAD = {
    "id": "5",
    "task_id": "3",
    "url": "https://github.com/example/repo/issues/42",
    "title": "GitHub Issue #42",
    "link_type": "weblink",
    "dependency": "related",
}


class TestExternalTaskLink:
    def test_from_api_basic(self):
        el = ExternalTaskLink.from_api(_EXT_LINK_PAYLOAD)
        assert el.id == 5
        assert el.task_id == 3
        assert el.url == "https://github.com/example/repo/issues/42"
        assert el.title == "GitHub Issue #42"
        assert el.link_type == "weblink"
        assert el.dependency == "related"

    def test_from_api_string_id_coerced(self):
        el = ExternalTaskLink.from_api({**_EXT_LINK_PAYLOAD, "id": "77"})
        assert el.id == 77

    def test_from_api_empty_dict_uses_defaults(self):
        el = ExternalTaskLink.from_api({})
        assert el.id == 0
        assert el.url == ""
        assert el.title == ""
        assert el.link_type == ""
        assert el.dependency == ""


# ---------------------------------------------------------------------------
# Group tests
# ---------------------------------------------------------------------------

_GROUP_PAYLOAD = {
    "id": "1",
    "name": "Admins",
    "external_id": "ldap-admins",
}


class TestGroup:
    def test_from_api_basic(self):
        g = Group.from_api(_GROUP_PAYLOAD)
        assert g.id == 1
        assert g.name == "Admins"
        assert g.external_id == "ldap-admins"

    def test_from_api_missing_external_id_defaults_empty(self):
        g = Group.from_api({"id": "2", "name": "Developers"})
        assert g.external_id == ""

    def test_from_api_empty_external_id(self):
        g = Group.from_api({**_GROUP_PAYLOAD, "external_id": ""})
        assert g.external_id == ""

    def test_from_api_empty_dict_uses_defaults(self):
        g = Group.from_api({})
        assert g.id == 0
        assert g.name == ""
        assert g.external_id == ""


# ---------------------------------------------------------------------------
# ProjectFile tests
# ---------------------------------------------------------------------------

_PROJECT_FILE_PAYLOAD = {
    "id": "1",
    "name": "spec.pdf",
    "path": "1/abcdef.pdf",
    "is_image": "0",
    "project_id": "1",
    "owner_id": "2",
    "date": "1519578598",
    "size": "52483",
    "username": "alice",
    "task_id": "0",
    "mime_type": "application/pdf",
}


class TestProjectFile:
    def test_from_api_basic(self):
        pf = ProjectFile.from_api(_PROJECT_FILE_PAYLOAD)
        assert pf.id == 1
        assert pf.name == "spec.pdf"
        assert pf.path == "1/abcdef.pdf"
        assert pf.project_id == 1
        assert pf.owner_id == 2
        assert pf.size == 52483
        assert pf.username == "alice"
        assert pf.task_id == 0
        assert pf.mime_type == "application/pdf"

    def test_is_image_false(self):
        pf = ProjectFile.from_api(_PROJECT_FILE_PAYLOAD)
        assert pf.is_image is False

    def test_is_image_true(self):
        pf = ProjectFile.from_api({**_PROJECT_FILE_PAYLOAD, "is_image": "1"})
        assert pf.is_image is True

    def test_date_parsed(self):
        pf = ProjectFile.from_api(_PROJECT_FILE_PAYLOAD)
        assert isinstance(pf.date, datetime)
        assert pf.date == datetime.fromtimestamp(1519578598)

    def test_date_none_when_missing(self):
        pf = ProjectFile.from_api({**_PROJECT_FILE_PAYLOAD, "date": None})
        assert pf.date is None

    def test_from_api_empty_dict_uses_defaults(self):
        pf = ProjectFile.from_api({})
        assert pf.id == 0
        assert pf.name == ""
        assert pf.is_image is False
        assert pf.date is None
        assert pf.size == 0


# ---------------------------------------------------------------------------
# TaskFile tests
# ---------------------------------------------------------------------------

_TASK_FILE_PAYLOAD = {
    "id": "3",
    "name": "screenshot.png",
    "path": "1/task/5/screenshot.png",
    "is_image": "1",
    "task_id": "5",
    "date": "1519578598",
    "size": "12800",
    "username": "bob",
    "user_id": "4",
    "project_id": "1",
    "mime_type": "image/png",
}


class TestTaskFile:
    def test_from_api_basic(self):
        tf = TaskFile.from_api(_TASK_FILE_PAYLOAD)
        assert tf.id == 3
        assert tf.name == "screenshot.png"
        assert tf.path == "1/task/5/screenshot.png"
        assert tf.task_id == 5
        assert tf.size == 12800
        assert tf.username == "bob"
        assert tf.user_id == 4
        assert tf.project_id == 1
        assert tf.mime_type == "image/png"

    def test_is_image_true(self):
        tf = TaskFile.from_api(_TASK_FILE_PAYLOAD)
        assert tf.is_image is True

    def test_is_image_false(self):
        tf = TaskFile.from_api({**_TASK_FILE_PAYLOAD, "is_image": "0"})
        assert tf.is_image is False

    def test_date_parsed(self):
        tf = TaskFile.from_api(_TASK_FILE_PAYLOAD)
        assert isinstance(tf.date, datetime)
        assert tf.date == datetime.fromtimestamp(1519578598)

    def test_date_none_when_missing(self):
        tf = TaskFile.from_api({**_TASK_FILE_PAYLOAD, "date": "0"})
        assert tf.date is None

    def test_from_api_empty_dict_uses_defaults(self):
        tf = TaskFile.from_api({})
        assert tf.id == 0
        assert tf.name == ""
        assert tf.is_image is False
        assert tf.date is None
        assert tf.size == 0
        assert tf.project_id == 0


# ---------------------------------------------------------------------------
# Action tests
# ---------------------------------------------------------------------------

_ACTION_PAYLOAD = {
    "id": "1",
    "project_id": "2",
    "event_name": "task.move.column",
    "action_name": "TaskAssignSpecificUser",
    "params": {"column_id": "3", "user_id": "5"},
}


class TestAction:
    def test_from_api_basic(self):
        a = Action.from_api(_ACTION_PAYLOAD)
        assert a.id == 1
        assert a.project_id == 2
        assert a.event_name == "task.move.column"
        assert a.action_name == "TaskAssignSpecificUser"

    def test_params_dict(self):
        a = Action.from_api(_ACTION_PAYLOAD)
        assert a.params == {"column_id": "3", "user_id": "5"}

    def test_params_none_becomes_empty_dict(self):
        a = Action.from_api({**_ACTION_PAYLOAD, "params": None})
        assert a.params == {}

    def test_params_missing_becomes_empty_dict(self):
        data = {k: v for k, v in _ACTION_PAYLOAD.items() if k != "params"}
        a = Action.from_api(data)
        assert a.params == {}

    def test_from_api_empty_dict_uses_defaults(self):
        a = Action.from_api({})
        assert a.id == 0
        assert a.project_id == 0
        assert a.event_name == ""
        assert a.action_name == ""
        assert a.params == {}


# ---------------------------------------------------------------------------
# Orchestration model tests (US-002)
# ---------------------------------------------------------------------------


class TestMilestone:
    def test_minimal_construction(self):
        m = Milestone(name="v1.0", portfolio_name="alpha", target_date=None)
        assert m.name == "v1.0"
        assert m.portfolio_name == "alpha"
        assert m.target_date is None
        assert m.task_ids == []
        assert m.critical_task_ids == []

    def test_with_all_fields(self):
        dt = datetime(2025, 12, 31)
        m = Milestone(
            name="Q4 Release",
            portfolio_name="my-portfolio",
            target_date=dt,
            task_ids=[1, 2, 3],
            critical_task_ids=[2],
        )
        assert m.target_date == dt
        assert m.task_ids == [1, 2, 3]
        assert m.critical_task_ids == [2]

    def test_task_ids_are_independent_per_instance(self):
        m1 = Milestone(name="A", portfolio_name="p", target_date=None)
        m2 = Milestone(name="B", portfolio_name="p", target_date=None)
        m1.task_ids.append(99)
        assert m2.task_ids == [], "default list must not be shared between instances"

    def test_is_mutable(self):
        m = Milestone(name="M", portfolio_name="p", target_date=None)
        m.name = "Updated"
        assert m.name == "Updated"

    def test_no_from_api_classmethod(self):
        assert not hasattr(Milestone, "from_api")


class TestPortfolio:
    def test_minimal_construction(self):
        p = Portfolio(name="my-portfolio", description="A test portfolio")
        assert p.name == "my-portfolio"
        assert p.description == "A test portfolio"
        assert p.project_ids == []
        assert p.milestones == []
        assert p.created_at is None
        assert p.updated_at is None

    def test_with_all_fields(self):
        dt = datetime(2025, 1, 1)
        m = Milestone(name="M1", portfolio_name="my-portfolio", target_date=None)
        p = Portfolio(
            name="my-portfolio",
            description="Full portfolio",
            project_ids=[10, 20],
            milestones=[m],
            created_at=dt,
            updated_at=dt,
        )
        assert p.project_ids == [10, 20]
        assert len(p.milestones) == 1
        assert p.milestones[0].name == "M1"
        assert p.created_at == dt

    def test_lists_are_independent_per_instance(self):
        p1 = Portfolio(name="A", description="")
        p2 = Portfolio(name="B", description="")
        p1.project_ids.append(1)
        assert p2.project_ids == [], "default list must not be shared between instances"

    def test_is_mutable(self):
        p = Portfolio(name="P", description="old")
        p.description = "new"
        assert p.description == "new"

    def test_no_from_api_classmethod(self):
        assert not hasattr(Portfolio, "from_api")


class TestMilestoneProgress:
    def test_construction(self):
        mp = MilestoneProgress(
            milestone_name="v1.0",
            portfolio_name="alpha",
            target_date=None,
            total=10,
            completed=5,
            percent=50.0,
            is_at_risk=False,
            is_overdue=False,
        )
        assert mp.milestone_name == "v1.0"
        assert mp.portfolio_name == "alpha"
        assert mp.total == 10
        assert mp.completed == 5
        assert mp.percent == pytest.approx(50.0)
        assert mp.is_at_risk is False
        assert mp.is_overdue is False
        assert mp.blocked_task_ids == []

    def test_at_risk_and_overdue_flags(self):
        mp = MilestoneProgress(
            milestone_name="M",
            portfolio_name="P",
            target_date=datetime(2024, 1, 1),
            total=10,
            completed=5,
            percent=50.0,
            is_at_risk=True,
            is_overdue=True,
            blocked_task_ids=[3, 7],
        )
        assert mp.is_at_risk is True
        assert mp.is_overdue is True
        assert mp.blocked_task_ids == [3, 7]

    def test_blocked_task_ids_independent_per_instance(self):
        mp1 = MilestoneProgress(
            milestone_name="M1",
            portfolio_name="P",
            target_date=None,
            total=0,
            completed=0,
            percent=0.0,
            is_at_risk=False,
            is_overdue=False,
        )
        mp2 = MilestoneProgress(
            milestone_name="M2",
            portfolio_name="P",
            target_date=None,
            total=0,
            completed=0,
            percent=0.0,
            is_at_risk=False,
            is_overdue=False,
        )
        mp1.blocked_task_ids.append(42)
        assert mp2.blocked_task_ids == []

    def test_no_from_api_classmethod(self):
        assert not hasattr(MilestoneProgress, "from_api")


class TestDependencyEdge:
    def test_construction(self):
        edge = DependencyEdge(
            task_id=1,
            task_title="Fix auth",
            task_project_id=10,
            task_project_name="Backend",
            opposite_task_id=2,
            opposite_task_title="Deploy service",
            opposite_task_project_id=20,
            opposite_task_project_name="Infra",
            link_label="blocks",
            is_cross_project=True,
            is_resolved=False,
        )
        assert edge.task_id == 1
        assert edge.task_title == "Fix auth"
        assert edge.task_project_id == 10
        assert edge.task_project_name == "Backend"
        assert edge.opposite_task_id == 2
        assert edge.opposite_task_title == "Deploy service"
        assert edge.opposite_task_project_id == 20
        assert edge.opposite_task_project_name == "Infra"
        assert edge.link_label == "blocks"
        assert edge.is_cross_project is True
        assert edge.is_resolved is False

    def test_same_project_edge(self):
        edge = DependencyEdge(
            task_id=5,
            task_title="Write tests",
            task_project_id=1,
            task_project_name="Main",
            opposite_task_id=6,
            opposite_task_title="Implement feature",
            opposite_task_project_id=1,
            opposite_task_project_name="Main",
            link_label="is blocked by",
            is_cross_project=False,
            is_resolved=True,
        )
        assert edge.is_cross_project is False
        assert edge.is_resolved is True
        assert edge.link_label == "is blocked by"

    def test_is_mutable(self):
        edge = DependencyEdge(
            task_id=1,
            task_title="T",
            task_project_id=1,
            task_project_name="P",
            opposite_task_id=2,
            opposite_task_title="T2",
            opposite_task_project_id=1,
            opposite_task_project_name="P",
            link_label="blocks",
            is_cross_project=False,
            is_resolved=False,
        )
        edge.is_resolved = True
        assert edge.is_resolved is True

    def test_no_from_api_classmethod(self):
        assert not hasattr(DependencyEdge, "from_api")


# ---------------------------------------------------------------------------
# Re-export from kanboard package
# ---------------------------------------------------------------------------


class TestReExports:
    def test_all_models_importable_from_kanboard(self):
        import kanboard

        names = (
            "Task",
            "Project",
            "Column",
            "Swimlane",
            "Comment",
            "Subtask",
            "User",
            "Category",
            "Tag",
            "Link",
            "TaskLink",
            "ExternalTaskLink",
            "Group",
            "ProjectFile",
            "TaskFile",
            "Action",
            # Orchestration models (US-002)
            "DependencyEdge",
            "Milestone",
            "MilestoneProgress",
            "Portfolio",
        )
        for name in names:
            assert hasattr(kanboard, name), f"{name} not exported from kanboard"

    def test_orchestration_models_in_all(self):
        import kanboard

        for name in ("DependencyEdge", "Milestone", "MilestoneProgress", "Portfolio"):
            assert name in kanboard.__all__, f"{name} missing from kanboard.__all__"
