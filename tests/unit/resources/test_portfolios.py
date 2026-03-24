"""Unit tests for PortfoliosResource — all 13 portfolio plugin API methods."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kanboard.client import KanboardClient
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import PluginPortfolio

_URL = "http://kanboard.test/jsonrpc.php"
_TOKEN = "test-api-token"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PORTFOLIO_DATA: dict = {
    "id": "1",
    "name": "Q1 Projects",
    "description": "First quarter portfolio",
    "owner_id": "2",
    "is_active": "1",
    "created_at": "1711077600",
    "updated_at": "1711077700",
}

_PORTFOLIO_DATA_2: dict = {
    "id": "2",
    "name": "Q2 Projects",
    "description": "",
    "owner_id": "1",
    "is_active": "0",
    "created_at": "1711100000",
    "updated_at": "1711100100",
}

_PROJECT_DATA: dict = {
    "id": "3",
    "name": "Alpha",
    "portfolio_id": "1",
}

_TASK_DATA: dict = {
    "id": "10",
    "title": "Fix bug",
    "project_id": "3",
    "portfolio_id": "1",
}


def _rpc_ok(result, request_id: int = 1) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_err(code: int, message: str, request_id: int = 1) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# create_portfolio
# ---------------------------------------------------------------------------


def test_create_portfolio_returns_new_id(httpx_mock: HTTPXMock) -> None:
    """create_portfolio() returns the new portfolio ID as an integer on success."""
    httpx_mock.add_response(json=_rpc_ok(1))
    with KanboardClient(_URL, _TOKEN) as client:
        portfolio_id = client.portfolios.create_portfolio("Q1 Projects")
    assert portfolio_id == 1


def test_create_portfolio_with_optional_kwargs(httpx_mock: HTTPXMock) -> None:
    """create_portfolio() passes optional kwargs to the API call."""
    httpx_mock.add_response(json=_rpc_ok(5))
    with KanboardClient(_URL, _TOKEN) as client:
        portfolio_id = client.portfolios.create_portfolio(
            "Q1 Projects", description="Quarter 1", owner_id=2
        )
    assert portfolio_id == 5


def test_create_portfolio_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """create_portfolio() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createPortfolio"):
            client.portfolios.create_portfolio("Duplicate Name")


def test_create_portfolio_raises_on_zero(httpx_mock: HTTPXMock) -> None:
    """create_portfolio() raises KanboardAPIError when the API returns 0."""
    httpx_mock.add_response(json=_rpc_ok(0))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="createPortfolio"):
            client.portfolios.create_portfolio("Bad Portfolio")


def test_create_portfolio_raises_on_json_rpc_error(httpx_mock: HTTPXMock) -> None:
    """create_portfolio() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.portfolios.create_portfolio("Blocked")


# ---------------------------------------------------------------------------
# get_portfolio
# ---------------------------------------------------------------------------


def test_get_portfolio_returns_plugin_portfolio_instance(httpx_mock: HTTPXMock) -> None:
    """get_portfolio() returns a populated PluginPortfolio dataclass for a valid ID."""
    httpx_mock.add_response(json=_rpc_ok(_PORTFOLIO_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        portfolio = client.portfolios.get_portfolio(1)
    assert isinstance(portfolio, PluginPortfolio)
    assert portfolio.id == 1
    assert portfolio.name == "Q1 Projects"
    assert portfolio.owner_id == 2
    assert portfolio.is_active is True


def test_get_portfolio_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_portfolio() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.portfolios.get_portfolio(999)
    assert "999" in str(exc_info.value)


def test_get_portfolio_not_found_identifies_resource(httpx_mock: HTTPXMock) -> None:
    """get_portfolio() KanboardNotFoundError carries resource='PluginPortfolio'."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.portfolios.get_portfolio(42)
    assert exc_info.value.resource == "PluginPortfolio"


def test_get_portfolio_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_portfolio() propagates KanboardAPIError from a JSON-RPC error response."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.portfolios.get_portfolio(1)


# ---------------------------------------------------------------------------
# get_portfolio_by_name
# ---------------------------------------------------------------------------


def test_get_portfolio_by_name_returns_plugin_portfolio_instance(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_by_name() returns a PluginPortfolio for a matching name."""
    httpx_mock.add_response(json=_rpc_ok(_PORTFOLIO_DATA))
    with KanboardClient(_URL, _TOKEN) as client:
        portfolio = client.portfolios.get_portfolio_by_name("Q1 Projects")
    assert isinstance(portfolio, PluginPortfolio)
    assert portfolio.name == "Q1 Projects"


def test_get_portfolio_by_name_raises_not_found_on_none(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_by_name() raises KanboardNotFoundError when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.portfolios.get_portfolio_by_name("Unknown")
    assert "Unknown" in str(exc_info.value)


def test_get_portfolio_by_name_raises_not_found_on_false(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_by_name() raises KanboardNotFoundError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.portfolios.get_portfolio_by_name("Missing")
    assert "Missing" in str(exc_info.value)


def test_get_portfolio_by_name_not_found_identifies_resource(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_by_name() KanboardNotFoundError carries resource='PluginPortfolio'."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardNotFoundError) as exc_info:
            client.portfolios.get_portfolio_by_name("Ghost")
    assert exc_info.value.resource == "PluginPortfolio"


def test_get_portfolio_by_name_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_by_name() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.portfolios.get_portfolio_by_name("Blocked")


# ---------------------------------------------------------------------------
# get_all_portfolios
# ---------------------------------------------------------------------------


def test_get_all_portfolios_returns_list_of_plugin_portfolios(
    httpx_mock: HTTPXMock,
) -> None:
    """get_all_portfolios() returns a list of PluginPortfolio instances."""
    httpx_mock.add_response(json=_rpc_ok([_PORTFOLIO_DATA, _PORTFOLIO_DATA_2]))
    with KanboardClient(_URL, _TOKEN) as client:
        portfolios = client.portfolios.get_all_portfolios()
    assert len(portfolios) == 2
    assert all(isinstance(p, PluginPortfolio) for p in portfolios)
    assert portfolios[0].name == "Q1 Projects"
    assert portfolios[1].name == "Q2 Projects"


def test_get_all_portfolios_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_all_portfolios() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_all_portfolios()
    assert result == []


def test_get_all_portfolios_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_all_portfolios() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_all_portfolios()
    assert result == []


def test_get_all_portfolios_returns_empty_list_on_empty_array(
    httpx_mock: HTTPXMock,
) -> None:
    """get_all_portfolios() returns [] when the API returns an empty list."""
    httpx_mock.add_response(json=_rpc_ok([]))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_all_portfolios()
    assert result == []


# ---------------------------------------------------------------------------
# update_portfolio
# ---------------------------------------------------------------------------


def test_update_portfolio_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """update_portfolio() returns True when the update succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.update_portfolio(1, name="Renamed")
    assert result is True


def test_update_portfolio_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """update_portfolio() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="updatePortfolio"):
            client.portfolios.update_portfolio(999, name="Ghost")


def test_update_portfolio_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """update_portfolio() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.portfolios.update_portfolio(1, name="Blocked")


# ---------------------------------------------------------------------------
# remove_portfolio
# ---------------------------------------------------------------------------


def test_remove_portfolio_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """remove_portfolio() returns True when deletion succeeds."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.remove_portfolio(1)
    assert result is True


def test_remove_portfolio_returns_false_on_failure(httpx_mock: HTTPXMock) -> None:
    """remove_portfolio() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.remove_portfolio(999)
    assert result is False


def test_remove_portfolio_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """remove_portfolio() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Server error"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Server error"):
            client.portfolios.remove_portfolio(1)


# ---------------------------------------------------------------------------
# add_project_to_portfolio
# ---------------------------------------------------------------------------


def test_add_project_to_portfolio_returns_true_on_success(httpx_mock: HTTPXMock) -> None:
    """add_project_to_portfolio() returns True when the project is added."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.add_project_to_portfolio(1, 3)
    assert result is True


def test_add_project_to_portfolio_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """add_project_to_portfolio() passes optional kwargs to the API call."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.add_project_to_portfolio(1, 3, sort_order=1)
    assert result is True


def test_add_project_to_portfolio_raises_on_false(httpx_mock: HTTPXMock) -> None:
    """add_project_to_portfolio() raises KanboardAPIError when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="addProjectToPortfolio"):
            client.portfolios.add_project_to_portfolio(1, 999)


def test_add_project_to_portfolio_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """add_project_to_portfolio() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Permission denied"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Permission denied"):
            client.portfolios.add_project_to_portfolio(1, 3)


# ---------------------------------------------------------------------------
# remove_project_from_portfolio
# ---------------------------------------------------------------------------


def test_remove_project_from_portfolio_returns_true_on_success(
    httpx_mock: HTTPXMock,
) -> None:
    """remove_project_from_portfolio() returns True on successful removal."""
    httpx_mock.add_response(json=_rpc_ok(True))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.remove_project_from_portfolio(1, 3)
    assert result is True


def test_remove_project_from_portfolio_returns_false_on_failure(
    httpx_mock: HTTPXMock,
) -> None:
    """remove_project_from_portfolio() returns False when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.remove_project_from_portfolio(1, 999)
    assert result is False


# ---------------------------------------------------------------------------
# get_portfolio_projects
# ---------------------------------------------------------------------------


def test_get_portfolio_projects_returns_list_of_dicts(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_projects() returns a list of project dicts."""
    httpx_mock.add_response(json=_rpc_ok([_PROJECT_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        projects = client.portfolios.get_portfolio_projects(1)
    assert len(projects) == 1
    assert projects[0]["name"] == "Alpha"


def test_get_portfolio_projects_returns_empty_list_on_false(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_projects() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_projects(1)
    assert result == []


def test_get_portfolio_projects_returns_empty_list_on_none(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_projects() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_projects(1)
    assert result == []


# ---------------------------------------------------------------------------
# get_project_portfolios
# ---------------------------------------------------------------------------


def test_get_project_portfolios_returns_list_of_plugin_portfolios(
    httpx_mock: HTTPXMock,
) -> None:
    """get_project_portfolios() returns a list of PluginPortfolio instances."""
    httpx_mock.add_response(json=_rpc_ok([_PORTFOLIO_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        portfolios = client.portfolios.get_project_portfolios(3)
    assert len(portfolios) == 1
    assert isinstance(portfolios[0], PluginPortfolio)
    assert portfolios[0].id == 1


def test_get_project_portfolios_returns_empty_list_on_false(
    httpx_mock: HTTPXMock,
) -> None:
    """get_project_portfolios() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_project_portfolios(99)
    assert result == []


def test_get_project_portfolios_returns_empty_list_on_none(
    httpx_mock: HTTPXMock,
) -> None:
    """get_project_portfolios() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_project_portfolios(99)
    assert result == []


# ---------------------------------------------------------------------------
# get_portfolio_tasks
# ---------------------------------------------------------------------------


def test_get_portfolio_tasks_returns_list_of_dicts(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_tasks() returns a list of task dicts."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.portfolios.get_portfolio_tasks(1)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Fix bug"


def test_get_portfolio_tasks_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_tasks() passes optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok([_TASK_DATA]))
    with KanboardClient(_URL, _TOKEN) as client:
        tasks = client.portfolios.get_portfolio_tasks(1, status_id=1)
    assert len(tasks) == 1


def test_get_portfolio_tasks_returns_empty_list_on_false(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_tasks() returns [] when the API returns False."""
    httpx_mock.add_response(json=_rpc_ok(False))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_tasks(1)
    assert result == []


def test_get_portfolio_tasks_returns_empty_list_on_none(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_tasks() returns [] when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_tasks(1)
    assert result == []


# ---------------------------------------------------------------------------
# get_portfolio_task_count
# ---------------------------------------------------------------------------


def test_get_portfolio_task_count_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_task_count() returns the task count dict from the API."""
    count_data = {"total": 5, "open": 3, "closed": 2}
    httpx_mock.add_response(json=_rpc_ok(count_data))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_task_count(1)
    assert result == count_data


def test_get_portfolio_task_count_with_kwargs(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_task_count() passes optional kwargs to the API."""
    httpx_mock.add_response(json=_rpc_ok({"total": 2}))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_task_count(1, status_id=1)
    assert result == {"total": 2}


def test_get_portfolio_task_count_returns_empty_dict_on_none(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_task_count() returns {} when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_task_count(1)
    assert result == {}


# ---------------------------------------------------------------------------
# get_portfolio_overview
# ---------------------------------------------------------------------------


def test_get_portfolio_overview_returns_dict(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_overview() returns the overview dict from the API."""
    overview_data = {
        "portfolio": _PORTFOLIO_DATA,
        "projects": [_PROJECT_DATA],
        "milestones": [],
        "task_count": {"total": 1, "open": 1, "closed": 0},
    }
    httpx_mock.add_response(json=_rpc_ok(overview_data))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_overview(1)
    assert result["task_count"]["total"] == 1
    assert len(result["projects"]) == 1


def test_get_portfolio_overview_returns_empty_dict_on_none(
    httpx_mock: HTTPXMock,
) -> None:
    """get_portfolio_overview() returns {} when the API returns None."""
    httpx_mock.add_response(json=_rpc_ok(None))
    with KanboardClient(_URL, _TOKEN) as client:
        result = client.portfolios.get_portfolio_overview(1)
    assert result == {}


def test_get_portfolio_overview_raises_on_api_error(httpx_mock: HTTPXMock) -> None:
    """get_portfolio_overview() propagates KanboardAPIError from JSON-RPC error."""
    httpx_mock.add_response(json=_rpc_err(-32001, "Plugin not installed"))
    with KanboardClient(_URL, _TOKEN) as client:
        with pytest.raises(KanboardAPIError, match="Plugin not installed"):
            client.portfolios.get_portfolio_overview(1)


# ---------------------------------------------------------------------------
# PortfoliosResource is importable from kanboard package
# ---------------------------------------------------------------------------


def test_portfolios_resource_importable_from_kanboard_package() -> None:
    """PortfoliosResource is accessible in the kanboard package __all__."""
    import kanboard

    assert hasattr(kanboard, "PortfoliosResource")
    assert "PortfoliosResource" in kanboard.__all__


def test_portfolios_resource_accessible_on_client(httpx_mock: HTTPXMock) -> None:
    """client.portfolios is an instance of PortfoliosResource."""
    from kanboard.resources.portfolios import PortfoliosResource

    with KanboardClient(_URL, _TOKEN) as client:
        assert isinstance(client.portfolios, PortfoliosResource)
