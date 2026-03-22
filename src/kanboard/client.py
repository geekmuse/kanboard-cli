"""JSON-RPC 2.0 transport client for the Kanboard API."""

from __future__ import annotations

import json
import logging
import types
from typing import Any, Self

import httpx

from kanboard.exceptions import (
    KanboardAPIError,
    KanboardAuthError,
    KanboardConnectionError,
    KanboardResponseError,
)
from kanboard.resources.tasks import TasksResource

logger = logging.getLogger(__name__)

_JSONRPC_VERSION = "2.0"
_JSONRPC_USERNAME = "jsonrpc"


class KanboardClient:
    """JSON-RPC 2.0 HTTP transport client for the Kanboard API.

    Handles authentication, request serialisation, response parsing, and
    exception mapping for all Kanboard JSON-RPC calls.

    Resource accessors are available as typed attributes:

    - :attr:`tasks` — :class:`~kanboard.resources.tasks.TasksResource`

    Example:
        >>> with KanboardClient("https://kb.example.com/jsonrpc.php", "secret") as c:
        ...     task = c.tasks.get_task(42)
    """

    def __init__(self, url: str, token: str, timeout: float = 30.0) -> None:
        """Initialise the client with connection parameters.

        Args:
            url: The Kanboard JSON-RPC endpoint URL
                (e.g. ``"https://kb.example.com/jsonrpc.php"``).
            token: The Kanboard API token used as the HTTP Basic Auth password.
            timeout: Request timeout in seconds.  Defaults to ``30.0``.
        """
        self._url = url
        self._token = token
        self._timeout = timeout
        self._request_id: int = 0
        self._http = httpx.Client(
            auth=(_JSONRPC_USERNAME, token),
            timeout=timeout,
        )
        self.tasks: TasksResource = TasksResource(self)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def call(self, method: str, **params: Any) -> Any:
        """Send a single JSON-RPC 2.0 request and return the ``result``.

        Args:
            method: The Kanboard JSON-RPC method name (e.g. ``"getVersion"``).
            **params: Keyword arguments forwarded verbatim as the JSON-RPC
                ``params`` object.

        Returns:
            The parsed ``result`` value from the JSON-RPC response.

        Raises:
            KanboardAPIError: Server returned a JSON-RPC ``error`` response.
            KanboardAuthError: Server responded with HTTP 401 or 403.
            KanboardConnectionError: A network or connection failure occurred.
            KanboardResponseError: Response body could not be parsed as JSON.
        """
        payload = self._build_request(method, params)
        logger.debug("JSON-RPC request: method=%s", method)
        raw = self._send(json.dumps(payload))
        data = self._parse_json(raw, method)
        result = self._extract_result(data, method)
        logger.debug("JSON-RPC response: method=%s result=%r", method, result)
        return result

    def batch(self, calls: list[tuple[str, dict[str, Any]]]) -> list[Any]:
        """Send a batch of JSON-RPC 2.0 requests and return ordered results.

        Responses may be returned in any order by the server; this method
        re-orders them to match the original *calls* sequence.

        Args:
            calls: A list of ``(method, params)`` tuples to send in a single
                HTTP request.

        Returns:
            A list of result values in the same order as the input *calls*.

        Raises:
            KanboardAPIError: Any request in the batch returned a JSON-RPC error.
            KanboardAuthError: Server responded with HTTP 401 or 403.
            KanboardConnectionError: A network or connection failure occurred.
            KanboardResponseError: Response body is not a JSON array or is malformed.
        """
        requests: list[dict[str, Any]] = []
        id_to_method: dict[int, str] = {}
        for method, params in calls:
            req = self._build_request(method, params)
            id_to_method[req["id"]] = method
            requests.append(req)

        logger.debug("JSON-RPC batch: %d calls", len(calls))
        raw = self._send(json.dumps(requests))
        response_list = self._parse_json(raw, "<batch>")

        if not isinstance(response_list, list):
            raise KanboardResponseError(
                "Batch response must be a JSON array",
                raw_body=raw,
            )

        id_to_item: dict[int, dict[str, Any]] = {item.get("id"): item for item in response_list}

        results: list[Any] = []
        for req in requests:
            item = id_to_item.get(req["id"])
            if item is None:
                raise KanboardResponseError(
                    f"Missing batch response for request id={req['id']}",
                    raw_body=raw,
                )
            results.append(self._extract_result(item, id_to_method[req["id"]]))
        return results

    def close(self) -> None:
        """Close the underlying HTTP client and release all resources."""
        self._http.close()

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            This client instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the context manager and close the HTTP client.

        Args:
            exc_type: Exception type, if an exception occurred.
            exc_val: Exception instance, if an exception occurred.
            exc_tb: Traceback object, if an exception occurred.
        """
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        """Return the next auto-incremented request ID.

        Returns:
            The next integer request ID (starts at 1).
        """
        self._request_id += 1
        return self._request_id

    def _build_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request object.

        Args:
            method: The JSON-RPC method name.
            params: The request parameters dict.

        Returns:
            A dict representing the JSON-RPC 2.0 request envelope.
        """
        return {
            "jsonrpc": _JSONRPC_VERSION,
            "method": method,
            "id": self._next_id(),
            "params": params,
        }

    def _send(self, body: str) -> str:
        """POST *body* to the Kanboard endpoint and return the response text.

        Args:
            body: The serialised JSON request body.

        Returns:
            The response body as a decoded string.

        Raises:
            KanboardAuthError: Server responded with HTTP 401 or 403.
            KanboardConnectionError: Any network-level failure occurred.
        """
        try:
            response = self._http.post(
                self._url,
                content=body.encode(),
                headers={"Content-Type": "application/json"},
            )
        except httpx.ConnectError as exc:
            raise KanboardConnectionError(
                str(exc),
                url=self._url,
                cause=exc,
            ) from exc
        except httpx.TimeoutException as exc:
            raise KanboardConnectionError(
                f"Request timed out after {self._timeout}s",
                url=self._url,
                cause=exc,
            ) from exc
        except httpx.HTTPError as exc:
            raise KanboardConnectionError(
                str(exc),
                url=self._url,
                cause=exc,
            ) from exc

        if response.status_code in (401, 403):
            raise KanboardAuthError(
                f"HTTP {response.status_code} — check your API token",
                http_status=response.status_code,
            )

        return response.text

    def _parse_json(self, raw: str, method: str) -> Any:
        """Parse a JSON string, raising :class:`KanboardResponseError` on failure.

        Args:
            raw: The raw JSON string to parse.
            method: Method name used in the error context message.

        Returns:
            The parsed Python object (dict, list, str, int, bool, or None).

        Raises:
            KanboardResponseError: *raw* is not valid JSON.
        """
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            raise KanboardResponseError(
                f"Invalid JSON response for method '{method}'",
                raw_body=raw,
            ) from exc

    def _extract_result(self, data: dict[str, Any], method: str) -> Any:
        """Extract ``result`` from a JSON-RPC response or raise on error.

        Args:
            data: A parsed JSON-RPC response object.
            method: Method name used in error context.

        Returns:
            The value of the ``result`` field (may be ``None`` for not-found resources).

        Raises:
            KanboardAPIError: The response contains an ``error`` field.
        """
        if "error" in data:
            error = data["error"]
            code: int | None = error.get("code")
            message: str = error.get("message", "Unknown API error")
            raise KanboardAPIError(message, method=method, code=code)
        return data.get("result")
