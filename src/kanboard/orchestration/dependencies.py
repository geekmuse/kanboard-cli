"""Dependency analyzer — graph traversal and critical-path computation."""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardNotFoundError
from kanboard.models import DependencyEdge, Task

if TYPE_CHECKING:
    from kanboard.client import KanboardClient

logger = logging.getLogger(__name__)

_LINK_LABEL_BLOCKS = "blocks"
_LINK_LABEL_BLOCKED_BY = "is blocked by"


class DependencyAnalyzer:
    """Builds directed dependency graphs from Kanboard task links.

    Uses topological sort (Kahn's algorithm) for critical-path computation.
    Caches fetched tasks to avoid redundant API calls and deduplicates
    bidirectional edges.  Instantiated separately by callers — not wired into
    :class:`~kanboard.client.KanboardClient` as an attribute.

    The task cache (``self._task_cache``) is populated from input task lists
    and grows with each ``get_task`` enrichment call.  Callers may share a
    single :class:`DependencyAnalyzer` instance across multiple operations to
    benefit from cross-call caching.

    Args:
        client: The :class:`~kanboard.client.KanboardClient` used to fetch
            task links and task data.

    Example:
        >>> analyzer = DependencyAnalyzer(client)
        >>> edges = analyzer.get_dependency_edges(tasks)
        >>> critical = analyzer.get_critical_path(tasks)
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a Kanboard API client.

        Args:
            client: The Kanboard API client used to fetch task links and tasks.
        """
        self._client = client
        self._task_cache: dict[int, Task] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_link_label_map(self) -> dict[int, str]:
        """Fetch all link type definitions and return a ``{link_id: label}`` map.

        Returns an empty dict on failure so callers degrade gracefully (no
        dependency edges will be produced).

        Returns:
            A dict mapping link type IDs to their label strings.
        """
        try:
            links = self._client.links.get_all_links()
        except Exception:
            logger.warning("Failed to fetch link type definitions; dependency analysis disabled")
            return {}
        return {link.id: link.label for link in links}

    def _get_or_fetch_task(self, task_id: int) -> Task | None:
        """Return a :class:`~kanboard.models.Task` from cache or from the API.

        On a cache miss the task is fetched and stored in ``self._task_cache``
        for subsequent calls.  Returns ``None`` when the task cannot be found.

        Args:
            task_id: Unique integer ID of the task to retrieve.

        Returns:
            A :class:`~kanboard.models.Task` instance, or ``None`` if the task
            does not exist in Kanboard.
        """
        if task_id in self._task_cache:
            return self._task_cache[task_id]
        try:
            task = self._client.tasks.get_task(task_id)
            self._task_cache[task_id] = task
            return task
        except KanboardNotFoundError:
            return None

    def _get_project_name(
        self,
        project_id: int,
        project_name_cache: dict[int, str],
    ) -> str:
        """Return a project name, fetching and caching it on first access.

        On failure the name defaults to an empty string so edge creation is
        not blocked by a missing project lookup.

        Args:
            project_id: Unique integer ID of the project.
            project_name_cache: Caller-owned dict used to cache results within
                a single :meth:`get_dependency_edges` call.

        Returns:
            The project name string, or ``""`` on fetch failure.
        """
        if project_id in project_name_cache:
            return project_name_cache[project_id]
        try:
            project = self._client.projects.get_project_by_id(project_id)
            name = project.name
        except Exception:
            logger.warning(
                "Failed to fetch project %d name for edge enrichment; using empty string",
                project_id,
            )
            name = ""
        project_name_cache[project_id] = name
        return name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_dependency_edges(
        self,
        tasks: list[Task],
        cross_project_only: bool = False,
    ) -> list[DependencyEdge]:
        """Fetch dependency edges for the given tasks.

        Fetches ``getAllTaskLinks`` for each task, filters to ``"blocks"`` /
        ``"is blocked by"`` relationships, enriches with task titles and
        project names, and deduplicates bidirectional edges.  When both task A
        and task B are in the input list and A blocks B, exactly one
        :class:`~kanboard.models.DependencyEdge` is produced (in the
        ``"blocks"`` direction).

        All input tasks are seeded into the internal task cache so that
        enrichment calls for tasks in the input list never result in extra
        ``getTask`` API requests.

        Args:
            tasks: The tasks whose dependency links to analyse.
            cross_project_only: When ``True``, return only edges where the two
                tasks belong to different projects.

        Returns:
            A deduplicated list of :class:`~kanboard.models.DependencyEdge`
            instances.  All edges are normalised to the ``"blocks"`` direction
            (``task_id`` blocks ``opposite_task_id``).
        """
        link_label_map = self._get_link_label_map()
        blocks_link_ids: set[int] = {
            lid for lid, label in link_label_map.items() if label == _LINK_LABEL_BLOCKS
        }
        blocked_by_link_ids: set[int] = {
            lid for lid, label in link_label_map.items() if label == _LINK_LABEL_BLOCKED_BY
        }
        relevant_link_ids = blocks_link_ids | blocked_by_link_ids

        # Seed task cache so enrichment never re-fetches input tasks.
        for task in tasks:
            self._task_cache[task.id] = task

        # Canonical (blocker_id, blocked_id) pairs — prevents duplicate edges.
        seen_edges: set[tuple[int, int]] = set()
        edges: list[DependencyEdge] = []
        project_name_cache: dict[int, str] = {}

        for task in tasks:
            try:
                task_links = self._client.task_links.get_all_task_links(task.id)
            except Exception:
                logger.warning("Failed to fetch task links for task %d; skipping", task.id)
                continue

            for tl in task_links:
                if tl.link_id not in relevant_link_ids:
                    continue

                label = link_label_map[tl.link_id]
                # Normalise to canonical "blocks" direction.
                if label == _LINK_LABEL_BLOCKS:
                    blocker_id = tl.task_id
                    blocked_id = tl.opposite_task_id
                else:  # "is blocked by" — flip the pair
                    blocker_id = tl.opposite_task_id
                    blocked_id = tl.task_id

                edge_key = (blocker_id, blocked_id)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                blocker_task = self._get_or_fetch_task(blocker_id)
                blocked_task = self._get_or_fetch_task(blocked_id)

                if blocker_task is None or blocked_task is None:
                    continue

                blocker_project_name = self._get_project_name(
                    blocker_task.project_id, project_name_cache
                )
                blocked_project_name = self._get_project_name(
                    blocked_task.project_id, project_name_cache
                )

                is_cross_project = blocker_task.project_id != blocked_task.project_id
                is_resolved = not blocker_task.is_active

                if cross_project_only and not is_cross_project:
                    continue

                edges.append(
                    DependencyEdge(
                        task_id=blocker_id,
                        task_title=blocker_task.title,
                        task_project_id=blocker_task.project_id,
                        task_project_name=blocker_project_name,
                        opposite_task_id=blocked_id,
                        opposite_task_title=blocked_task.title,
                        opposite_task_project_id=blocked_task.project_id,
                        opposite_task_project_name=blocked_project_name,
                        link_label=_LINK_LABEL_BLOCKS,
                        is_cross_project=is_cross_project,
                        is_resolved=is_resolved,
                    )
                )

        return edges

    def get_blocked_tasks(
        self,
        tasks: list[Task],
    ) -> list[tuple[Task, list[DependencyEdge]]]:
        """Return tasks from the input list that have unresolved (open) blockers.

        A task is *blocked* when at least one of its inbound dependency edges
        is unresolved (the blocking task is still active).

        Args:
            tasks: Tasks to analyse for incoming blocking relationships.

        Returns:
            A list of ``(task, edges)`` tuples for each input task that is
            currently blocked, ordered by their position in ``tasks``.
        """
        edges = self.get_dependency_edges(tasks)
        # Map blocked_task_id → unresolved edges pointing to it.
        unresolved: dict[int, list[DependencyEdge]] = {}
        for edge in edges:
            if not edge.is_resolved:
                unresolved.setdefault(edge.opposite_task_id, []).append(edge)

        return [(task, unresolved[task.id]) for task in tasks if task.id in unresolved]

    def get_blocking_tasks(
        self,
        tasks: list[Task],
    ) -> list[tuple[Task, list[DependencyEdge]]]:
        """Return open tasks from the input list that are actively blocking others.

        A task is *blocking* when it is still active and has at least one
        outbound unresolved dependency edge.

        Args:
            tasks: Tasks to analyse for outgoing blocking relationships.

        Returns:
            A list of ``(task, edges)`` tuples for each open input task that is
            blocking at least one other task, ordered by their position in
            ``tasks``.
        """
        edges = self.get_dependency_edges(tasks)
        # Map blocker_task_id → unresolved edges it owns.
        unresolved: dict[int, list[DependencyEdge]] = {}
        for edge in edges:
            if not edge.is_resolved:
                unresolved.setdefault(edge.task_id, []).append(edge)

        return [
            (task, unresolved[task.id])
            for task in tasks
            if task.id in unresolved and task.is_active
        ]

    def get_critical_path(self, tasks: list[Task]) -> list[Task]:
        """Compute the longest dependency chain via topological sort and DP.

        Only open (active) tasks and unresolved dependency edges between them
        are considered.  Uses Kahn's algorithm to obtain a topological ordering
        and dynamic programming to find the longest path.

        When a cycle is detected in the dependency graph a warning is logged
        and a partial result (using the tasks that could be topologically
        ordered) is returned rather than raising an exception.

        Args:
            tasks: Tasks to include in the critical-path computation.  Closed
                tasks are ignored.

        Returns:
            A list of :class:`~kanboard.models.Task` instances representing the
            critical (longest) dependency chain, ordered from the earliest
            blocker to the final blocked task.  Returns ``[]`` when there are
            no open tasks, no dependency edges, or no edges remain after
            filtering to open tasks.
        """
        open_tasks = [t for t in tasks if t.is_active]
        if not open_tasks:
            return []

        all_edges = self.get_dependency_edges(tasks)
        open_task_ids: set[int] = {t.id for t in open_tasks}

        # Only consider unresolved edges between open tasks.
        active_edges = [
            e
            for e in all_edges
            if not e.is_resolved
            and e.task_id in open_task_ids
            and e.opposite_task_id in open_task_ids
        ]
        if not active_edges:
            return []

        # Build adjacency list and in-degree table.
        successors: dict[int, list[int]] = {t.id: [] for t in open_tasks}
        in_degree: dict[int, int] = {t.id: 0 for t in open_tasks}

        for edge in active_edges:
            successors[edge.task_id].append(edge.opposite_task_id)
            in_degree[edge.opposite_task_id] += 1

        # DP: dist[v] = length of longest chain ending at v.
        dist: dict[int, int] = {t.id: 1 for t in open_tasks}
        pred: dict[int, int | None] = {t.id: None for t in open_tasks}
        remaining_in_degree = dict(in_degree)

        queue: deque[int] = deque(t.id for t in open_tasks if remaining_in_degree[t.id] == 0)
        topo_order: list[int] = []

        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for succ in successors.get(node, []):
                if dist[node] + 1 > dist[succ]:
                    dist[succ] = dist[node] + 1
                    pred[succ] = node
                remaining_in_degree[succ] -= 1
                if remaining_in_degree[succ] == 0:
                    queue.append(succ)

        if len(topo_order) < len(open_tasks):
            logger.warning(
                "Cycle detected in dependency graph (%d of %d open tasks processed); "
                "returning partial critical path",
                len(topo_order),
                len(open_tasks),
            )

        if not topo_order:
            return []

        # The task with the highest dist value is the end of the critical path.
        end_task_id = max(topo_order, key=lambda tid: dist[tid])

        # Trace back predecessor pointers to reconstruct the path.
        path: list[int] = []
        current: int | None = end_task_id
        visited: set[int] = set()
        while current is not None and current not in visited:
            path.append(current)
            visited.add(current)
            current = pred[current]
        path.reverse()

        task_map: dict[int, Task] = {t.id: t for t in open_tasks}
        return [task_map[tid] for tid in path if tid in task_map]

    def get_dependency_graph(
        self,
        tasks: list[Task],
        cross_project_only: bool = False,
    ) -> dict[str, Any]:
        """Return a graph representation of task dependencies.

        Builds a dict with ``"nodes"`` (all input tasks) and ``"edges"`` (the
        filtered dependency edges between them).

        Args:
            tasks: Tasks to include in the graph.
            cross_project_only: When ``True``, include only cross-project edges.

        Returns:
            A dict with two keys:

            - ``"nodes"``: list of dicts with keys ``id``, ``title``,
              ``project_id``, ``is_active``.
            - ``"edges"``: list of dicts with keys ``task_id``,
              ``opposite_task_id``, ``link_label``, ``is_cross_project``,
              ``is_resolved``.
        """
        edges = self.get_dependency_edges(tasks, cross_project_only=cross_project_only)

        nodes = [
            {
                "id": task.id,
                "title": task.title,
                "project_id": task.project_id,
                "is_active": task.is_active,
            }
            for task in tasks
        ]
        edges_data = [
            {
                "task_id": edge.task_id,
                "opposite_task_id": edge.opposite_task_id,
                "link_label": edge.link_label,
                "is_cross_project": edge.is_cross_project,
                "is_resolved": edge.is_resolved,
            }
            for edge in edges
        ]
        return {"nodes": nodes, "edges": edges_data}
