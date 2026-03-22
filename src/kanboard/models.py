"""SDK response dataclass models for the Kanboard API."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_date(value: Any) -> datetime | None:
    """Parse a Kanboard date value to a datetime or None.

    Handles all date representations that the Kanboard API may return:

    - ``None``, empty string, ``"0"``, or ``0`` → ``None``
    - Unix timestamp as ``int`` or numeric string → ``datetime`` via ``fromtimestamp()``
    - ``"YYYY-MM-DD HH:MM"`` or ``"YYYY-MM-DD HH:MM:SS"`` → parsed ``datetime``
    - ``"YYYY-MM-DD"`` → parsed ``datetime`` (midnight)
    - A ``datetime`` object is returned unchanged.

    Args:
        value: Raw value from an API response dict.

    Returns:
        A ``datetime``, or ``None`` when the value represents "no date".
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if s in ("", "0"):
        return None
    # Try Unix timestamp (integer or numeric string).
    try:
        ts = int(s)
        if ts == 0:
            return None
        return datetime.fromtimestamp(ts)
    except ValueError:
        pass
    # Try known ISO-like string formats.
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _int(value: Any) -> int:
    """Coerce a Kanboard integer field to ``int``, returning ``0`` for ``None`` or invalid.

    Kanboard frequently returns numeric values as strings (e.g. ``"0"``, ``"42"``).
    This helper normalises those to plain Python ``int``.

    Args:
        value: Raw value from an API response dict.

    Returns:
        An integer, or ``0`` when the value is ``None`` or cannot be converted.
    """
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _float(value: Any) -> float:
    """Coerce a Kanboard float field to ``float``, returning ``0.0`` for ``None`` or invalid.

    Used for Subtask ``time_estimated`` and ``time_spent`` fields which Kanboard
    may return as integers, floats, or numeric strings.

    Args:
        value: Raw value from an API response dict.

    Returns:
        A float, or ``0.0`` when the value is ``None`` or cannot be converted.
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Task:
    """Represents a Kanboard task returned by ``getTask`` and related endpoints."""

    id: int
    title: str
    description: str
    date_creation: datetime | None
    date_modification: datetime | None
    date_due: datetime | None
    date_completed: datetime | None
    date_moved: datetime | None
    color_id: str
    project_id: int
    column_id: int
    swimlane_id: int
    owner_id: int
    creator_id: int
    category_id: int
    is_active: bool
    priority: int
    score: int
    position: int
    reference: str
    tags: list[str]
    url: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Task:
        """Construct a :class:`Task` from a raw Kanboard API response dict.

        All integer fields are coerced via :func:`_int`, all date fields via
        :func:`_parse_date`, and missing keys are filled with sensible defaults.

        Args:
            data: Dictionary from a ``getTask`` or ``getAllTasks`` API response.

        Returns:
            A populated :class:`Task` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            date_creation=_parse_date(data.get("date_creation")),
            date_modification=_parse_date(data.get("date_modification")),
            date_due=_parse_date(data.get("date_due")),
            date_completed=_parse_date(data.get("date_completed")),
            date_moved=_parse_date(data.get("date_moved")),
            color_id=str(data.get("color_id", "")),
            project_id=_int(data.get("project_id", 0)),
            column_id=_int(data.get("column_id", 0)),
            swimlane_id=_int(data.get("swimlane_id", 0)),
            owner_id=_int(data.get("owner_id", 0)),
            creator_id=_int(data.get("creator_id", 0)),
            category_id=_int(data.get("category_id", 0)),
            is_active=bool(_int(data.get("is_active", 1))),
            priority=_int(data.get("priority", 0)),
            score=_int(data.get("score", 0)),
            position=_int(data.get("position", 0)),
            reference=str(data.get("reference", "")),
            tags=list(data.get("tags") or []),
            url=str(data.get("url", "")),
        )


@dataclasses.dataclass
class Project:
    """Represents a Kanboard project returned by ``getProjectById`` and related endpoints."""

    id: int
    name: str
    description: str
    is_active: bool
    token: str
    last_modified: datetime | None
    is_public: bool
    is_private: bool
    owner_id: int
    identifier: str
    start_date: datetime | None
    end_date: datetime | None
    url: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Project:
        """Construct a :class:`Project` from a raw Kanboard API response dict.

        The ``url`` field may be a string or a nested dict; the ``board`` URL is
        extracted when a dict is provided.

        Args:
            data: Dictionary from a ``getProjectById`` or ``getAllProjects`` API response.

        Returns:
            A populated :class:`Project` instance.
        """
        raw_url = data.get("url", "")
        if isinstance(raw_url, dict):
            url = str(raw_url.get("board", ""))
        else:
            url = str(raw_url)

        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            is_active=bool(_int(data.get("is_active", 1))),
            token=str(data.get("token", "")),
            last_modified=_parse_date(data.get("last_modified")),
            is_public=bool(_int(data.get("is_public", 0))),
            is_private=bool(data.get("is_private", False)),
            owner_id=_int(data.get("owner_id", 0)),
            identifier=str(data.get("identifier", "")),
            start_date=_parse_date(data.get("start_date")),
            end_date=_parse_date(data.get("end_date")),
            url=url,
        )


@dataclasses.dataclass
class Column:
    """Represents a Kanboard board column returned by ``getColumns``."""

    id: int
    title: str
    project_id: int
    task_limit: int
    position: int
    description: str
    hide_in_dashboard: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Column:
        """Construct a :class:`Column` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getColumns`` API response item.

        Returns:
            A populated :class:`Column` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            title=str(data.get("title", "")),
            project_id=_int(data.get("project_id", 0)),
            task_limit=_int(data.get("task_limit", 0)),
            position=_int(data.get("position", 0)),
            description=str(data.get("description", "")),
            hide_in_dashboard=bool(_int(data.get("hide_in_dashboard", 0))),
        )


@dataclasses.dataclass
class Swimlane:
    """Represents a Kanboard swimlane returned by ``getSwimlane`` and related endpoints."""

    id: int
    name: str
    project_id: int
    position: int
    is_active: bool
    description: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Swimlane:
        """Construct a :class:`Swimlane` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getSwimlane`` or ``getSwimlanes`` API response item.

        Returns:
            A populated :class:`Swimlane` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            project_id=_int(data.get("project_id", 0)),
            position=_int(data.get("position", 0)),
            is_active=bool(_int(data.get("is_active", 1))),
            description=str(data.get("description", "")),
        )


@dataclasses.dataclass
class Comment:
    """Represents a Kanboard task comment returned by ``getComment`` and related endpoints."""

    id: int
    task_id: int
    user_id: int
    username: str
    name: str
    comment: str
    date_creation: datetime | None
    date_modification: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Comment:
        """Construct a :class:`Comment` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getComment`` or ``getAllComments`` API response item.

        Returns:
            A populated :class:`Comment` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            task_id=_int(data.get("task_id", 0)),
            user_id=_int(data.get("user_id", 0)),
            username=str(data.get("username", "")),
            name=str(data.get("name", "")),
            comment=str(data.get("comment", "")),
            date_creation=_parse_date(data.get("date_creation")),
            date_modification=_parse_date(data.get("date_modification")),
        )


@dataclasses.dataclass
class Subtask:
    """Represents a Kanboard subtask returned by ``getSubtask`` and related endpoints.

    Subtask statuses: ``0`` = todo, ``1`` = in progress, ``2`` = done.
    """

    id: int
    title: str
    task_id: int
    user_id: int
    status: int
    time_estimated: float
    time_spent: float
    position: int
    username: str
    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Subtask:
        """Construct a :class:`Subtask` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getSubtask`` or ``getAllSubtasks`` API response item.

        Returns:
            A populated :class:`Subtask` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            title=str(data.get("title", "")),
            task_id=_int(data.get("task_id", 0)),
            user_id=_int(data.get("user_id", 0)),
            status=_int(data.get("status", 0)),
            time_estimated=_float(data.get("time_estimated", 0)),
            time_spent=_float(data.get("time_spent", 0)),
            position=_int(data.get("position", 0)),
            username=str(data.get("username", "")),
            name=str(data.get("name", "")),
        )


@dataclasses.dataclass
class User:
    """Represents a Kanboard user returned by ``getUser`` and related endpoints."""

    id: int
    username: str
    name: str
    email: str
    role: str
    is_active: bool
    is_ldap_user: bool
    notification_method: int
    avatar_path: str | None
    timezone: str | None
    language: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> User:
        """Construct a :class:`User` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getUser`` or ``getAllUsers`` API response item.

        Returns:
            A populated :class:`User` instance.
        """
        avatar = data.get("avatar_path")
        tz = data.get("timezone")
        lang = data.get("language")
        return cls(
            id=_int(data.get("id", 0)),
            username=str(data.get("username", "")),
            name=str(data.get("name", "")),
            email=str(data.get("email", "")),
            role=str(data.get("role", "")),
            is_active=bool(_int(data.get("is_active", 1))),
            is_ldap_user=bool(_int(data.get("is_ldap_user", 0))),
            notification_method=_int(data.get("notification_method", 0)),
            avatar_path=str(avatar) if avatar is not None else None,
            timezone=str(tz) if tz is not None else None,
            language=str(lang) if lang is not None else None,
        )


@dataclasses.dataclass
class Category:
    """Represents a Kanboard task category returned by ``getCategory`` and related endpoints."""

    id: int
    name: str
    project_id: int
    color_id: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Category:
        """Construct a :class:`Category` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getCategory`` or ``getCategories`` API response item.

        Returns:
            A populated :class:`Category` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            project_id=_int(data.get("project_id", 0)),
            color_id=str(data.get("color_id", "")),
        )
