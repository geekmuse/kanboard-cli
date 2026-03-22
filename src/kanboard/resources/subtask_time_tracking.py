"""Subtask time tracking resource module - timer management for subtasks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kanboard.exceptions import KanboardAPIError

if TYPE_CHECKING:
    from kanboard.client import KanboardClient


class SubtaskTimeTrackingResource:
    """Kanboard Subtask Time Tracking API resource.

    Exposes all four subtask time-tracking JSON-RPC methods as typed Python
    methods.  Subtask timers allow users to track how long they spend working
    on individual subtasks.

    Accessed via ``KanboardClient.subtask_time_tracking``.

    Example:
        >>> client.subtask_time_tracking.set_subtask_start_time(subtask_id=7)
        True
        >>> client.subtask_time_tracking.has_subtask_timer(subtask_id=7)
        True
        >>> client.subtask_time_tracking.set_subtask_end_time(subtask_id=7)
        True
        >>> client.subtask_time_tracking.get_subtask_time_spent(subtask_id=7)
        1.5
    """

    def __init__(self, client: KanboardClient) -> None:
        """Initialise with a parent :class:`~kanboard.client.KanboardClient`.

        Args:
            client: The parent ``KanboardClient`` instance used to make API calls.
        """
        self._client = client

    def has_subtask_timer(self, subtask_id: int, **kwargs: Any) -> bool:
        """Check whether a subtask timer is currently running.

        Maps to the Kanboard ``hasSubtaskTimer`` JSON-RPC method.

        Args:
            subtask_id: ID of the subtask to check.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``user_id``).

        Returns:
            ``True`` when a timer is running, ``False`` otherwise.
        """
        result = self._client.call(
            "hasSubtaskTimer",
            subtask_id=subtask_id,
            **kwargs,
        )
        return bool(result)

    def set_subtask_start_time(self, subtask_id: int, **kwargs: Any) -> bool:
        """Start the timer for a subtask.

        Maps to the Kanboard ``setSubtaskStartTime`` JSON-RPC method.

        Args:
            subtask_id: ID of the subtask to start timing.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``user_id``).

        Returns:
            ``True`` when the timer was started successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                timer could not be started.
        """
        result = self._client.call(
            "setSubtaskStartTime",
            subtask_id=subtask_id,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to start timer for subtask {subtask_id}",
                method="setSubtaskStartTime",
            )
        return True

    def set_subtask_end_time(self, subtask_id: int, **kwargs: Any) -> bool:
        """Stop the timer for a subtask.

        Maps to the Kanboard ``setSubtaskEndTime`` JSON-RPC method.

        Args:
            subtask_id: ID of the subtask to stop timing.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``user_id``).

        Returns:
            ``True`` when the timer was stopped successfully.

        Raises:
            KanboardAPIError: The API returned ``False`` indicating the
                timer could not be stopped.
        """
        result = self._client.call(
            "setSubtaskEndTime",
            subtask_id=subtask_id,
            **kwargs,
        )
        if not result:
            raise KanboardAPIError(
                f"Failed to stop timer for subtask {subtask_id}",
                method="setSubtaskEndTime",
            )
        return True

    def get_subtask_time_spent(self, subtask_id: int, **kwargs: Any) -> float:
        """Get the total time spent on a subtask in hours.

        Maps to the Kanboard ``getSubtaskTimeSpent`` JSON-RPC method.

        Args:
            subtask_id: ID of the subtask to query.
            **kwargs: Optional keyword arguments forwarded to the API
                (e.g. ``user_id``).

        Returns:
            The total hours spent as a float. Returns ``0.0`` when the API
            responds with a falsy value.
        """
        result = self._client.call(
            "getSubtaskTimeSpent",
            subtask_id=subtask_id,
            **kwargs,
        )
        if not result:
            return 0.0
        return float(result)
