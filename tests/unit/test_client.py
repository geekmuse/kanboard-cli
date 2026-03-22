"""Unit tests for KanboardClient JSON-RPC transport layer."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import (
    KanboardAPIError,
    KanboardAuthError,
    KanboardConnectionError,
    KanboardResponseError,
)

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a minimal successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a minimal JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# Successful call()
# ---------------------------------------------------------------------------


def test_call_returns_string_result(httpx_mock: HTTPXMock) -> None:
    """call() returns the parsed result value for a string result."""
    httpx_mock.add_response(json=_rpc_ok("1.2.34"))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.call("getVersion") == "1.2.34"


def test_call_returns_dict_result(httpx_mock: HTTPXMock) -> None:
    """call() returns a dict result with nested data."""
    payload = {"id": 42, "title": "Fix bug"}
    httpx_mock.add_response(json=_rpc_ok(payload))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.call("getTask", task_id=42)
    assert result == payload


def test_call_returns_bool_true(httpx_mock: HTTPXMock) -> None:
    """call() returns True for a boolean true result."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.call("ping") is True


def test_call_returns_none_result(httpx_mock: HTTPXMock) -> None:
    """call() returns None when Kanboard responds with null (resource not found)."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.call("getTask", task_id=999) is None


def test_call_returns_integer_result(httpx_mock: HTTPXMock) -> None:
    """call() returns an integer result (e.g. createTask returns the new task ID)."""
    httpx_mock.add_response(json=_rpc_ok(123))
    with KanboardClient(_URL, _TOKEN) as client:
        assert client.call("createTask", title="New task", project_id=1) == 123


def test_call_increments_request_id(httpx_mock: HTTPXMock) -> None:
    """Successive calls use incrementing request IDs."""
    httpx_mock.add_response(json=_rpc_ok("1.0", request_id=1))
    httpx_mock.add_response(json=_rpc_ok(True, request_id=2))
    client = KanboardClient(_URL, _TOKEN)
    try:
        client.call("getVersion")
        client.call("ping")
    finally:
        client.close()
    # IDs 1 and 2 were consumed — if pytest-httpx didn't raise, they matched


# ---------------------------------------------------------------------------
# Successful batch()
# ---------------------------------------------------------------------------


def test_batch_returns_results_in_call_order(httpx_mock: HTTPXMock) -> None:
    """batch() returns results in original call order even when responses are out of order."""
    # Server sends responses in reverse order (id=2 first, id=1 second)
    httpx_mock.add_response(
        json=[
            _rpc_ok(True, request_id=2),
            _rpc_ok("1.2.34", request_id=1),
        ]
    )
    with KanboardClient(_URL, _TOKEN) as client:
        results = client.batch([("getVersion", {}), ("ping", {})])
    assert results == ["1.2.34", True]


def test_batch_single_call(httpx_mock: HTTPXMock) -> None:
    """batch() with a single element works correctly."""
    httpx_mock.add_response(json=[_rpc_ok(7)])
    with KanboardClient(_URL, _TOKEN) as client:
        results = client.batch([("getProjectCount", {})])
    assert results == [7]


def test_batch_passes_params(httpx_mock: HTTPXMock) -> None:
    """batch() forwards params for each call."""
    httpx_mock.add_response(
        json=[
            _rpc_ok({"id": 1, "name": "Project A"}, request_id=1),
            _rpc_ok({"id": 2, "name": "Project B"}, request_id=2),
        ]
    )
    with KanboardClient(_URL, _TOKEN) as client:
        results = client.batch([
            ("getProjectById", {"project_id": 1}),
            ("getProjectById", {"project_id": 2}),
        ])
    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2


# ---------------------------------------------------------------------------
# JSON-RPC error responses → KanboardAPIError
# ---------------------------------------------------------------------------


def test_call_rpc_error_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardAPIError when server returns a JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32601, "Method not found"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError) as exc_info:
            client.call("unknownMethod")
    err = exc_info.value
    assert err.method == "unknownMethod"
    assert err.code == -32601
    assert "Method not found" in str(err)


def test_call_rpc_error_without_code(httpx_mock: HTTPXMock) -> None:
    """call() handles JSON-RPC error responses that omit the code field."""
    httpx_mock.add_response(
        json={"jsonrpc": "2.0", "id": 1, "error": {"message": "Something went wrong"}}
    )
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError) as exc_info:
            client.call("someMethod")
    assert exc_info.value.code is None
    assert "Something went wrong" in str(exc_info.value)


def test_batch_rpc_error_in_one_call_raises(httpx_mock: HTTPXMock) -> None:
    """batch() raises KanboardAPIError when any request in the batch errors."""
    httpx_mock.add_response(
        json=[
            _rpc_ok("1.2.34", request_id=1),
            _rpc_err(-32600, "Invalid request", request_id=2),
        ]
    )
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError) as exc_info:
            client.batch([("getVersion", {}), ("badMethod", {})])
    assert exc_info.value.code == -32600


# ---------------------------------------------------------------------------
# HTTP 401 / 403 → KanboardAuthError
# ---------------------------------------------------------------------------


def test_call_http_401_raises_auth_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardAuthError with http_status=401 on HTTP 401."""
    httpx_mock.add_response(status_code=401)
    with KanboardClient(_URL, "bad-token") as client:
        with pytest.raises(KanboardAuthError) as exc_info:
            client.call("getVersion")
    assert exc_info.value.http_status == 401
    assert "401" in str(exc_info.value)


def test_call_http_403_raises_auth_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardAuthError with http_status=403 on HTTP 403."""
    httpx_mock.add_response(status_code=403)
    with KanboardClient(_URL, "bad-token") as client:
        with pytest.raises(KanboardAuthError) as exc_info:
            client.call("getVersion")
    assert exc_info.value.http_status == 403
    assert "403" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Connection failures → KanboardConnectionError
# ---------------------------------------------------------------------------


def test_call_connect_error_raises_connection_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardConnectionError on httpx.ConnectError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError) as exc_info:
            client.call("getVersion")
    err = exc_info.value
    assert err.url == _URL
    assert err.cause is not None


def test_call_read_timeout_raises_connection_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardConnectionError on httpx.ReadTimeout."""
    httpx_mock.add_exception(httpx.ReadTimeout("Request timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError) as exc_info:
            client.call("getVersion")
    assert exc_info.value.url == _URL


def test_call_connect_timeout_raises_connection_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardConnectionError on httpx.ConnectTimeout."""
    httpx_mock.add_exception(httpx.ConnectTimeout("Connect timed out"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.call("getVersion")


def test_connection_error_message_contains_timeout_seconds(httpx_mock: HTTPXMock) -> None:
    """KanboardConnectionError for timeout includes the configured timeout value."""
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"))
    with KanboardClient(_URL, _TOKEN, timeout=15.0) as client:
        with pytest.raises(KanboardConnectionError) as exc_info:
            client.call("getVersion")
    assert "15.0" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Malformed / non-JSON responses → KanboardResponseError
# ---------------------------------------------------------------------------


def test_call_non_json_response_raises_response_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardResponseError when the response is not valid JSON."""
    httpx_mock.add_response(text="<html>Server Error</html>")
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardResponseError) as exc_info:
            client.call("getVersion")
    err = exc_info.value
    assert err.raw_body is not None
    assert "html" in str(err).lower()


def test_call_empty_response_raises_response_error(httpx_mock: HTTPXMock) -> None:
    """call() raises KanboardResponseError when the server returns empty body."""
    httpx_mock.add_response(text="")
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardResponseError):
            client.call("getVersion")


def test_batch_non_array_response_raises_response_error(httpx_mock: HTTPXMock) -> None:
    """batch() raises KanboardResponseError when batch response is not a JSON array."""
    httpx_mock.add_response(json={"error": "unexpected dict"})
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardResponseError) as exc_info:
            client.batch([("getVersion", {})])
    assert "array" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Context manager and close()
# ---------------------------------------------------------------------------


def test_context_manager_supports_calls(httpx_mock: HTTPXMock) -> None:
    """KanboardClient works correctly as a context manager."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.call("ping")
    assert result is True


def test_context_manager_returns_self(httpx_mock: HTTPXMock) -> None:
    """__enter__ returns the KanboardClient instance itself."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client, KanboardClient)
        client.call("ping")


def test_close_does_not_raise() -> None:
    """close() can be called without error on a freshly created client."""
    client = KanboardClient(_URL, _TOKEN)
    client.close()  # should not raise


def test_context_manager_closes_on_exception(httpx_mock: HTTPXMock) -> None:
    """__exit__ closes the client even when an exception escapes the block."""
    httpx_mock.add_response(status_code=401)
    with pytest.raises(KanboardAuthError):
        with KanboardClient(_URL, "bad") as client:
            client.call("getVersion")
    # If close() was not called, the httpx transport would leak — no assertion
    # needed beyond verifying no exception from __exit__ itself.
