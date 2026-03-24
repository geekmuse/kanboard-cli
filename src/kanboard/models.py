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


# ---------------------------------------------------------------------------
# Extended models (US-006)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Tag:
    """Represents a Kanboard tag returned by ``getTagsByProject`` and related endpoints."""

    id: int
    name: str
    project_id: int
    color_id: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Tag:
        """Construct a :class:`Tag` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getTagsByProject`` API response item.

        Returns:
            A populated :class:`Tag` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            project_id=_int(data.get("project_id", 0)),
            color_id=str(data.get("color_id", "")),
        )


@dataclasses.dataclass
class Link:
    """Represents a Kanboard internal link type returned by ``getLinkById`` and related endpoints.

    Links describe the *relationship label* between two tasks (e.g. "blocks", "is blocked by").
    Each link has an opposite label that mirrors the relationship from the other direction.
    """

    id: int
    label: str
    opposite_id: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Link:
        """Construct a :class:`Link` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getLinkById`` or ``getAllLinks`` API response item.

        Returns:
            A populated :class:`Link` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            label=str(data.get("label", "")),
            opposite_id=_int(data.get("opposite_id", 0)),
        )


@dataclasses.dataclass
class TaskLink:
    """Represents a task-to-task link returned by ``getTaskLinkById`` and related endpoints.

    A task link associates two tasks via a :class:`Link` relationship type.
    """

    id: int
    task_id: int
    opposite_task_id: int
    link_id: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TaskLink:
        """Construct a :class:`TaskLink` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getTaskLinkById`` or ``getAllTaskLinks`` API response item.

        Returns:
            A populated :class:`TaskLink` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            task_id=_int(data.get("task_id", 0)),
            opposite_task_id=_int(data.get("opposite_task_id", 0)),
            link_id=_int(data.get("link_id", 0)),
        )


@dataclasses.dataclass
class ExternalTaskLink:
    """Represents an external task link returned by ``getExternalTaskLinkById``.

    External task links associate a task with an external URL (e.g. a GitHub issue or document).
    """

    id: int
    task_id: int
    url: str
    title: str
    link_type: str
    dependency: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ExternalTaskLink:
        """Construct a :class:`ExternalTaskLink` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getExternalTaskLinkById`` or ``getAllExternalTaskLinks``
                API response item.

        Returns:
            A populated :class:`ExternalTaskLink` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            task_id=_int(data.get("task_id", 0)),
            url=str(data.get("url", "")),
            title=str(data.get("title", "")),
            link_type=str(data.get("link_type", "")),
            dependency=str(data.get("dependency", "")),
        )


@dataclasses.dataclass
class Group:
    """Represents a Kanboard user group returned by ``getGroup`` and related endpoints."""

    id: int
    name: str
    external_id: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Group:
        """Construct a :class:`Group` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getGroup`` or ``getAllGroups`` API response item.

        Returns:
            A populated :class:`Group` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            external_id=str(data.get("external_id", "")),
        )


@dataclasses.dataclass
class ProjectFile:
    """Represents a Kanboard project-level file.

    Returned by ``getProjectFile`` and related endpoints.
    """

    id: int
    name: str
    path: str
    is_image: bool
    project_id: int
    owner_id: int
    date: datetime | None
    size: int
    username: str
    task_id: int
    mime_type: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProjectFile:
        """Construct a :class:`ProjectFile` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getProjectFile`` or ``getAllProjectFiles`` API response item.

        Returns:
            A populated :class:`ProjectFile` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            path=str(data.get("path", "")),
            is_image=bool(_int(data.get("is_image", 0))),
            project_id=_int(data.get("project_id", 0)),
            owner_id=_int(data.get("owner_id", 0)),
            date=_parse_date(data.get("date")),
            size=_int(data.get("size", 0)),
            username=str(data.get("username", "")),
            task_id=_int(data.get("task_id", 0)),
            mime_type=str(data.get("mime_type", "")),
        )


@dataclasses.dataclass
class TaskFile:
    """Represents a Kanboard task-level file returned by ``getTaskFile`` and related endpoints."""

    id: int
    name: str
    path: str
    is_image: bool
    task_id: int
    date: datetime | None
    size: int
    username: str
    user_id: int
    project_id: int
    mime_type: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TaskFile:
        """Construct a :class:`TaskFile` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getTaskFile`` or ``getAllTaskFiles`` API response item.

        Returns:
            A populated :class:`TaskFile` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            path=str(data.get("path", "")),
            is_image=bool(_int(data.get("is_image", 0))),
            task_id=_int(data.get("task_id", 0)),
            date=_parse_date(data.get("date")),
            size=_int(data.get("size", 0)),
            username=str(data.get("username", "")),
            user_id=_int(data.get("user_id", 0)),
            project_id=_int(data.get("project_id", 0)),
            mime_type=str(data.get("mime_type", "")),
        )


# ---------------------------------------------------------------------------
# Orchestration models (Phase 0 — cross-project portfolio management)
#
# These models are composed client-side from multiple API responses.
# They do NOT have from_api() classmethods — they are never deserialized
# from a single Kanboard JSON-RPC response.
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Milestone:
    """A cross-project milestone grouping tasks within a portfolio.

    Persisted locally via
    :class:`~kanboard.orchestration.store.LocalPortfolioStore`.  Composed
    client-side — no ``from_api()`` classmethod.

    Attributes:
        name: Human-readable milestone name (unique within its portfolio).
        portfolio_name: Name of the parent :class:`Portfolio`.
        target_date: Optional due date for the milestone.
        task_ids: All task IDs tracked against this milestone.
        critical_task_ids: Subset of ``task_ids`` on the critical path.
    """

    name: str
    portfolio_name: str
    target_date: datetime | None
    task_ids: list[int] = dataclasses.field(default_factory=list)
    critical_task_ids: list[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Portfolio:
    """A named portfolio grouping multiple Kanboard projects.

    Persisted locally via
    :class:`~kanboard.orchestration.store.LocalPortfolioStore`.  Composed
    client-side — no ``from_api()`` classmethod.

    Attributes:
        name: Unique portfolio name (case-sensitive).
        description: Human-readable description.
        project_ids: Kanboard project IDs belonging to this portfolio.
        milestones: Cross-project milestones within this portfolio.
        created_at: Timestamp when the portfolio was first created.
        updated_at: Timestamp of the last modification.
    """

    name: str
    description: str
    project_ids: list[int] = dataclasses.field(default_factory=list)
    milestones: list[Milestone] = dataclasses.field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclasses.dataclass
class MilestoneProgress:
    """Progress snapshot for a single milestone, computed by the portfolio manager.

    Produced by
    :meth:`~kanboard.orchestration.portfolio.PortfolioManager.get_milestone_progress`.
    Composed client-side — no ``from_api()`` classmethod.

    Attributes:
        milestone_name: Name of the milestone.
        portfolio_name: Name of the parent portfolio.
        target_date: Optional due date for the milestone.
        total: Total number of tasks tracked by the milestone.
        completed: Number of closed/completed tasks.
        percent: Completion percentage (0.0-100.0).
        is_at_risk: ``True`` when ``target_date`` is within 7 days and
            ``percent < 80``.
        is_overdue: ``True`` when ``target_date`` is in the past and
            ``percent < 100``.
        blocked_task_ids: Task IDs with at least one unresolved blocker.
    """

    milestone_name: str
    portfolio_name: str
    target_date: datetime | None
    total: int
    completed: int
    percent: float
    is_at_risk: bool
    is_overdue: bool
    blocked_task_ids: list[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class DependencyEdge:
    """A directed dependency relationship between two tasks (blocks / is-blocked-by).

    Built by
    :class:`~kanboard.orchestration.dependencies.DependencyAnalyzer` from
    Kanboard task-link data.  Cross-project awareness is derived by comparing
    ``task_project_id`` with ``opposite_task_project_id``.  No
    ``from_api()`` classmethod — composed from multiple API responses.

    Attributes:
        task_id: ID of the source task.
        task_title: Title of the source task.
        task_project_id: Project ID of the source task.
        task_project_name: Project name of the source task.
        opposite_task_id: ID of the related task on the other end.
        opposite_task_title: Title of the related task.
        opposite_task_project_id: Project ID of the related task.
        opposite_task_project_name: Project name of the related task.
        link_label: Relationship label (e.g. ``"blocks"``).
        is_cross_project: ``True`` when the two tasks belong to different
            projects.
        is_resolved: ``True`` when the blocking task is closed/completed.
    """

    task_id: int
    task_title: str
    task_project_id: int
    task_project_name: str
    opposite_task_id: int
    opposite_task_title: str
    opposite_task_project_id: int
    opposite_task_project_name: str
    link_label: str
    is_cross_project: bool
    is_resolved: bool


# ---------------------------------------------------------------------------
# Plugin models (Phase 1 — server-side portfolio plugin entities)
#
# These models map directly to Kanboard plugin JSON-RPC API responses.
# They have from_api() classmethods because they ARE deserialized from
# single plugin API responses.  Distinct from the Phase 0 orchestration
# models above (Portfolio, Milestone, MilestoneProgress) which are
# client-side composites without from_api().
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class PluginPortfolio:
    """Server-side portfolio entity returned by the Kanboard Portfolio plugin.

    Returned by ``createPortfolio``, ``getPortfolio``, ``getAllPortfolios``,
    and related plugin endpoints.  Distinct from the client-side
    :class:`Portfolio` orchestration model which has no ``from_api()``.

    Attributes:
        id: Server-assigned portfolio ID.
        name: Unique portfolio name.
        description: Human-readable description.
        owner_id: ID of the portfolio owner user.
        is_active: Whether the portfolio is active.
        created_at: Timestamp when the portfolio was created.
        updated_at: Timestamp of the last modification.
    """

    id: int
    name: str
    description: str
    owner_id: int
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PluginPortfolio:
        """Construct a :class:`PluginPortfolio` from a raw plugin API response dict.

        All integer fields are coerced via :func:`_int`, date fields via
        :func:`_parse_date`, and missing keys are filled with sensible defaults.

        Args:
            data: Dictionary from a ``getPortfolio`` or ``getAllPortfolios`` response.

        Returns:
            A populated :class:`PluginPortfolio` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            owner_id=_int(data.get("owner_id", 0)),
            is_active=bool(_int(data.get("is_active", 1))),
            created_at=_parse_date(data.get("created_at")),
            updated_at=_parse_date(data.get("updated_at")),
        )


@dataclasses.dataclass
class PluginMilestone:
    """Server-side milestone entity returned by the Kanboard Portfolio plugin.

    Returned by ``createMilestone``, ``getMilestone``, ``getPortfolioMilestones``,
    and related plugin endpoints.  Distinct from the client-side
    :class:`Milestone` orchestration model which has no ``from_api()``.

    Attributes:
        id: Server-assigned milestone ID.
        portfolio_id: ID of the parent portfolio.
        name: Human-readable milestone name.
        description: Optional description.
        target_date: Optional due date for the milestone.
        status: Milestone status as an integer (plugin-defined values).
        color_id: Optional color identifier string.
        owner_id: ID of the milestone owner user.
        created_at: Timestamp when the milestone was created.
        updated_at: Timestamp of the last modification.
    """

    id: int
    portfolio_id: int
    name: str
    description: str
    target_date: datetime | None
    status: int
    color_id: str
    owner_id: int
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PluginMilestone:
        """Construct a :class:`PluginMilestone` from a raw plugin API response dict.

        All integer fields are coerced via :func:`_int`, date fields via
        :func:`_parse_date`, ``color_id`` defaults to empty string, and
        missing keys are filled with sensible defaults.

        Args:
            data: Dictionary from a ``getMilestone`` or ``getPortfolioMilestones`` response.

        Returns:
            A populated :class:`PluginMilestone` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            portfolio_id=_int(data.get("portfolio_id", 0)),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            target_date=_parse_date(data.get("target_date")),
            status=_int(data.get("status", 0)),
            color_id=str(data.get("color_id", "")),
            owner_id=_int(data.get("owner_id", 0)),
            created_at=_parse_date(data.get("created_at")),
            updated_at=_parse_date(data.get("updated_at")),
        )


@dataclasses.dataclass
class PluginMilestoneProgress:
    """Server-computed milestone progress returned by the Kanboard Portfolio plugin.

    Returned by ``getMilestoneProgress``.  Represents server-side SQL-computed
    progress rather than the client-side computation done by
    :class:`~kanboard.orchestration.portfolio.PortfolioManager`.

    Attributes:
        milestone_id: ID of the milestone this progress belongs to.
        total: Total number of tasks tracked by the milestone.
        completed: Number of closed/completed tasks.
        percent: Completion percentage (0.0-100.0).
        is_at_risk: ``True`` when the milestone is behind schedule.
        is_overdue: ``True`` when the milestone target date has passed.
    """

    milestone_id: int
    total: int
    completed: int
    percent: float
    is_at_risk: bool
    is_overdue: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PluginMilestoneProgress:
        """Construct a :class:`PluginMilestoneProgress` from a raw plugin API response dict.

        Integer fields coerced via :func:`_int`, ``percent`` via ``float()``,
        boolean flags via ``bool()``.

        Args:
            data: Dictionary from a ``getMilestoneProgress`` API response.

        Returns:
            A populated :class:`PluginMilestoneProgress` instance.
        """
        raw_percent = data.get("percent", 0.0)
        try:
            percent = float(raw_percent) if raw_percent is not None else 0.0
        except (ValueError, TypeError):
            percent = 0.0

        return cls(
            milestone_id=_int(data.get("milestone_id", 0)),
            total=_int(data.get("total", 0)),
            completed=_int(data.get("completed", 0)),
            percent=percent,
            is_at_risk=bool(data.get("is_at_risk", False)),
            is_overdue=bool(data.get("is_overdue", False)),
        )


@dataclasses.dataclass
class Action:
    """Represents a Kanboard automatic action returned by ``getActions`` and related endpoints.

    Actions automate task changes when a specific event fires (e.g. assign a user when
    a task is moved to a column).
    """

    id: int
    project_id: int
    event_name: str
    action_name: str
    params: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Action:
        """Construct a :class:`Action` from a raw Kanboard API response dict.

        Args:
            data: Dictionary from a ``getActions`` API response item.

        Returns:
            A populated :class:`Action` instance.
        """
        return cls(
            id=_int(data.get("id", 0)),
            project_id=_int(data.get("project_id", 0)),
            event_name=str(data.get("event_name", "")),
            action_name=str(data.get("action_name", "")),
            params=dict(data.get("params") or {}),
        )
