"""Unit tests for SubtaskTimeTrackingResource - all 4 time-tracking API methods."""

from __future__ import annotations

import httpx as httpx_lib
import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardConnectionError
from kanboard.resources.subtask_time_tracking import SubtaskTimeTrackingResource

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rpc_ok(result: object, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


# ===========================================================================
# has_subtask_timer
# ===========================================================================


def test_has_subtask_timer_true(httpx_mock: HTTPXMock) -> None:
    """has_subtask_timer() returns True when a timer is running."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.has_subtask_timer(7)
    assert result is True


def test_has_subtask_timer_false(httpx_mock: HTTPXMock) -> None:
    """has_subtask_timer() returns False when no timer is running."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.has_subtask_timer(7)
    assert result is False


def test_has_subtask_timer_none(httpx_mock: HTTPXMock) -> None:
    """has_subtask_timer() returns False when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.has_subtask_timer(7)
    assert result is False


def test_has_subtask_timer_with_user_id(httpx_mock: HTTPXMock) -> None:
    """has_subtask_timer() forwards user_id kwarg to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.has_subtask_timer(7, user_id=1)
    assert result is True


def test_has_subtask_timer_network_failure(httpx_mock: HTTPXMock) -> None:
    """has_subtask_timer() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.subtask_time_tracking.has_subtask_timer(7)


# ===========================================================================
# set_subtask_start_time
# ===========================================================================


def test_set_subtask_start_time_success(httpx_mock: HTTPXMock) -> None:
    """set_subtask_start_time() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.set_subtask_start_time(7)
    assert result is True


def test_set_subtask_start_time_with_user_id(httpx_mock: HTTPXMock) -> None:
    """set_subtask_start_time() forwards user_id kwarg to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.set_subtask_start_time(7, user_id=1)
    assert result is True


def test_set_subtask_start_time_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """set_subtask_start_time() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to start timer"):
            client.subtask_time_tracking.set_subtask_start_time(7)


def test_set_subtask_start_time_raises_on_none(httpx_mock: HTTPXMock) -> None:
    """set_subtask_start_time() raises KanboardAPIError when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to start timer"):
            client.subtask_time_tracking.set_subtask_start_time(7)


def test_set_subtask_start_time_rpc_error(httpx_mock: HTTPXMock) -> None:
    """set_subtask_start_time() raises KanboardAPIError on RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32602, "Invalid params"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Invalid params"):
            client.subtask_time_tracking.set_subtask_start_time(7)


def test_set_subtask_start_time_network_failure(httpx_mock: HTTPXMock) -> None:
    """set_subtask_start_time() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.subtask_time_tracking.set_subtask_start_time(7)


# ===========================================================================
# set_subtask_end_time
# ===========================================================================


def test_set_subtask_end_time_success(httpx_mock: HTTPXMock) -> None:
    """set_subtask_end_time() returns True on success."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.set_subtask_end_time(7)
    assert result is True


def test_set_subtask_end_time_with_user_id(httpx_mock: HTTPXMock) -> None:
    """set_subtask_end_time() forwards user_id kwarg to the API."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.set_subtask_end_time(7, user_id=1)
    assert result is True


def test_set_subtask_end_time_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """set_subtask_end_time() raises KanboardAPIError when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to stop timer"):
            client.subtask_time_tracking.set_subtask_end_time(7)


def test_set_subtask_end_time_raises_on_none(httpx_mock: HTTPXMock) -> None:
    """set_subtask_end_time() raises KanboardAPIError when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Failed to stop timer"):
            client.subtask_time_tracking.set_subtask_end_time(7)


def test_set_subtask_end_time_rpc_error(httpx_mock: HTTPXMock) -> None:
    """set_subtask_end_time() raises KanboardAPIError on RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32602, "Invalid params"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Invalid params"):
            client.subtask_time_tracking.set_subtask_end_time(7)


def test_set_subtask_end_time_network_failure(httpx_mock: HTTPXMock) -> None:
    """set_subtask_end_time() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.subtask_time_tracking.set_subtask_end_time(7)


# ===========================================================================
# get_subtask_time_spent
# ===========================================================================


def test_get_subtask_time_spent_returns_float(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() returns hours as a float."""
    httpx_mock.add_response(json=_rpc_ok(1.5))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.get_subtask_time_spent(7)
    assert result == 1.5
    assert isinstance(result, float)


def test_get_subtask_time_spent_returns_int_as_float(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() converts integer result to float."""
    httpx_mock.add_response(json=_rpc_ok(3))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.get_subtask_time_spent(7)
    assert result == 3.0
    assert isinstance(result, float)


def test_get_subtask_time_spent_zero_on_false(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() returns 0.0 when API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.get_subtask_time_spent(7)
    assert result == 0.0


def test_get_subtask_time_spent_zero_on_none(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() returns 0.0 when API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.get_subtask_time_spent(7)
    assert result == 0.0


def test_get_subtask_time_spent_zero_on_zero(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() returns 0.0 when API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.get_subtask_time_spent(7)
    assert result == 0.0


def test_get_subtask_time_spent_with_user_id(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() forwards user_id kwarg to the API."""
    httpx_mock.add_response(json=_rpc_ok(2.25))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.subtask_time_tracking.get_subtask_time_spent(7, user_id=1)
    assert result == 2.25


def test_get_subtask_time_spent_network_failure(httpx_mock: HTTPXMock) -> None:
    """get_subtask_time_spent() raises KanboardConnectionError on network failure."""
    httpx_mock.add_exception(httpx_lib.ConnectError("refused"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardConnectionError):
            client.subtask_time_tracking.get_subtask_time_spent(7)


# ===========================================================================
# Client wiring
# ===========================================================================


def test_client_has_subtask_time_tracking_attribute(httpx_mock: HTTPXMock) -> None:
    """KanboardClient exposes a .subtask_time_tracking attribute of the correct type."""
    with KanboardClient(_URL, _TOKEN) as client:
        assert hasattr(client, "subtask_time_tracking")
        assert isinstance(client.subtask_time_tracking, SubtaskTimeTrackingResource)


# ===========================================================================
# Package importability
# ===========================================================================


def test_subtask_time_tracking_resource_importable_from_package() -> None:
    """SubtaskTimeTrackingResource is importable from the top-level kanboard package."""
    from kanboard import SubtaskTimeTrackingResource as Imported

    assert Imported is SubtaskTimeTrackingResource
