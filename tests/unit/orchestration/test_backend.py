"""Unit tests for orchestration/backend.py.

Covers:
- PortfolioBackend protocol conformance for LocalPortfolioStore and RemotePortfolioBackend
- create_backend() factory — all input combinations
- RemotePortfolioBackend method delegation (each of the 12 protocol methods)
- Name-to-ID translation in RemotePortfolioBackend
- Error paths: missing client, invalid backend_type, milestone not found
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kanboard.exceptions import KanboardConfigError, KanboardNotFoundError
from kanboard.models import Milestone, PluginMilestone, PluginPortfolio, Portfolio
from kanboard.orchestration.backend import (
    PortfolioBackend,
    RemotePortfolioBackend,
    create_backend,
)
from kanboard.orchestration.store import LocalPortfolioStore

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _plugin_portfolio(
    id: int = 1,
    name: str = "Alpha",
    description: str = "Test",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> PluginPortfolio:
    """Return a minimal PluginPortfolio for use in tests."""
    now = datetime(2026, 3, 24, 10, 0, 0)
    return PluginPortfolio(
        id=id,
        name=name,
        description=description,
        owner_id=1,
        is_active=True,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def _plugin_milestone(
    id: int = 10,
    portfolio_id: int = 1,
    name: str = "v1.0",
    target_date: datetime | None = None,
) -> PluginMilestone:
    """Return a minimal PluginMilestone for use in tests."""
    now = datetime(2026, 3, 24, 10, 0, 0)
    return PluginMilestone(
        id=id,
        portfolio_id=portfolio_id,
        name=name,
        description="",
        target_date=target_date,
        status=0,
        color_id="",
        owner_id=0,
        created_at=now,
        updated_at=now,
    )


def _make_remote_backend() -> tuple[RemotePortfolioBackend, MagicMock, MagicMock]:
    """Return (backend, mock_portfolios_resource, mock_milestones_resource)."""
    client = MagicMock()
    mock_portfolios = MagicMock()
    mock_milestones = MagicMock()
    client.portfolios = mock_portfolios
    client.milestones = mock_milestones
    backend = RemotePortfolioBackend(client)
    return backend, mock_portfolios, mock_milestones


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """Verify both backends satisfy the PortfolioBackend protocol at runtime."""

    def test_local_store_satisfies_protocol(self, tmp_path: Path) -> None:
        store = LocalPortfolioStore(path=tmp_path / "p.json")
        assert isinstance(store, PortfolioBackend)

    def test_remote_backend_satisfies_protocol(self) -> None:
        backend, _, _ = _make_remote_backend()
        assert isinstance(backend, PortfolioBackend)

    def test_protocol_is_runtime_checkable(self) -> None:
        # Arbitrary object does NOT satisfy protocol (missing methods)
        assert not isinstance(object(), PortfolioBackend)

    def test_local_store_has_all_protocol_methods(self, tmp_path: Path) -> None:
        store = LocalPortfolioStore(path=tmp_path / "p.json")
        for method in (
            "load",
            "create_portfolio",
            "get_portfolio",
            "update_portfolio",
            "remove_portfolio",
            "add_project",
            "remove_project",
            "add_milestone",
            "update_milestone",
            "remove_milestone",
            "add_task_to_milestone",
            "remove_task_from_milestone",
        ):
            assert callable(getattr(store, method, None)), f"Missing method: {method}"

    def test_remote_backend_has_all_protocol_methods(self) -> None:
        backend, _, _ = _make_remote_backend()
        for method in (
            "load",
            "create_portfolio",
            "get_portfolio",
            "update_portfolio",
            "remove_portfolio",
            "add_project",
            "remove_project",
            "add_milestone",
            "update_milestone",
            "remove_milestone",
            "add_task_to_milestone",
            "remove_task_from_milestone",
        ):
            assert callable(getattr(backend, method, None)), f"Missing method: {method}"


# ---------------------------------------------------------------------------
# Factory — create_backend()
# ---------------------------------------------------------------------------


class TestCreateBackend:
    """Factory returns the correct backend instance for all input combinations."""

    def test_local_returns_local_store(self, tmp_path: Path) -> None:
        backend = create_backend("local", path=tmp_path / "p.json")
        assert isinstance(backend, LocalPortfolioStore)

    def test_local_without_path_returns_local_store(self) -> None:
        backend = create_backend("local")
        assert isinstance(backend, LocalPortfolioStore)

    def test_remote_with_client_returns_remote_backend(self) -> None:
        client = MagicMock()
        client.portfolios = MagicMock()
        client.milestones = MagicMock()
        backend = create_backend("remote", client=client)
        assert isinstance(backend, RemotePortfolioBackend)

    def test_remote_without_client_raises_config_error(self) -> None:
        with pytest.raises(KanboardConfigError) as exc_info:
            create_backend("remote")
        assert "client=" in str(exc_info.value)
        assert exc_info.value.field == "portfolio_backend"

    def test_invalid_backend_type_raises_config_error(self) -> None:
        with pytest.raises(KanboardConfigError) as exc_info:
            create_backend("foobar")
        assert "foobar" in str(exc_info.value)
        assert exc_info.value.field == "portfolio_backend"

    def test_returned_backends_satisfy_protocol(self, tmp_path: Path) -> None:
        local = create_backend("local", path=tmp_path / "p.json")
        assert isinstance(local, PortfolioBackend)

        client = MagicMock()
        client.portfolios = MagicMock()
        client.milestones = MagicMock()
        remote = create_backend("remote", client=client)
        assert isinstance(remote, PortfolioBackend)


# ---------------------------------------------------------------------------
# RemotePortfolioBackend — internal helpers
# ---------------------------------------------------------------------------


class TestRemoteHelpers:
    """Internal helper methods for name-to-ID translation."""

    def test_resolve_portfolio_id_success(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        pp = _plugin_portfolio(id=42, name="Alpha")
        mock_p.get_portfolio_by_name.return_value = pp

        pid = backend._resolve_portfolio_id("Alpha")

        mock_p.get_portfolio_by_name.assert_called_once_with("Alpha")
        assert pid == 42

    def test_resolve_portfolio_id_not_found_propagates(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        mock_p.get_portfolio_by_name.side_effect = KanboardNotFoundError("not found")

        with pytest.raises(KanboardNotFoundError):
            backend._resolve_portfolio_id("Missing")

    def test_resolve_milestone_id_success(self) -> None:
        backend, _, mock_m = _make_remote_backend()
        ms = [_plugin_milestone(id=99, name="v1.0"), _plugin_milestone(id=100, name="v2.0")]
        mock_m.get_portfolio_milestones.return_value = ms

        mid = backend._resolve_milestone_id(1, "v1.0")

        assert mid == 99

    def test_resolve_milestone_id_second_match(self) -> None:
        backend, _, mock_m = _make_remote_backend()
        ms = [_plugin_milestone(id=99, name="v1.0"), _plugin_milestone(id=100, name="v2.0")]
        mock_m.get_portfolio_milestones.return_value = ms

        mid = backend._resolve_milestone_id(1, "v2.0")

        assert mid == 100

    def test_resolve_milestone_id_not_found_raises(self) -> None:
        backend, _, mock_m = _make_remote_backend()
        mock_m.get_portfolio_milestones.return_value = []

        with pytest.raises(KanboardConfigError, match=r"v3\.0"):
            backend._resolve_milestone_id(1, "v3.0")

    def test_to_milestone_populates_task_ids(self) -> None:
        backend, _, mock_m = _make_remote_backend()
        pm = _plugin_milestone(id=10, name="v1.0")
        mock_m.get_milestone_tasks.return_value = [{"id": 5}, {"id": 6}]

        m = backend._to_milestone(pm, "Alpha")

        assert m.name == "v1.0"
        assert m.portfolio_name == "Alpha"
        assert m.task_ids == [5, 6]
        mock_m.get_milestone_tasks.assert_called_once_with(10)

    def test_to_milestone_empty_tasks(self) -> None:
        backend, _, mock_m = _make_remote_backend()
        pm = _plugin_milestone(id=10, name="v1.0")
        mock_m.get_milestone_tasks.return_value = []

        m = backend._to_milestone(pm, "Alpha")

        assert m.task_ids == []

    def test_build_portfolio_populates_projects_and_milestones(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        pp = _plugin_portfolio(id=1, name="Alpha")
        mock_p.get_portfolio_projects.return_value = [{"id": 10}, {"id": 11}]
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=99, name="v1.0")]
        mock_m.get_milestone_tasks.return_value = [{"id": 5}]

        portfolio = backend._build_portfolio(pp)

        assert portfolio.name == "Alpha"
        assert portfolio.project_ids == [10, 11]
        assert len(portfolio.milestones) == 1
        assert portfolio.milestones[0].name == "v1.0"
        assert portfolio.milestones[0].task_ids == [5]

    def test_build_portfolio_empty_projects_and_milestones(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        pp = _plugin_portfolio(id=1, name="Alpha")
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        portfolio = backend._build_portfolio(pp)

        assert portfolio.project_ids == []
        assert portfolio.milestones == []


# ---------------------------------------------------------------------------
# RemotePortfolioBackend — portfolio CRUD
# ---------------------------------------------------------------------------


class TestRemoteLoad:
    def test_load_returns_all_portfolios(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        pp1 = _plugin_portfolio(id=1, name="Alpha")
        pp2 = _plugin_portfolio(id=2, name="Beta")
        mock_p.get_all_portfolios.return_value = [pp1, pp2]
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.load()

        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"
        mock_p.get_all_portfolios.assert_called_once()

    def test_load_empty_returns_empty_list(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        mock_p.get_all_portfolios.return_value = []

        result = backend.load()

        assert result == []


class TestRemoteCreatePortfolio:
    def test_create_portfolio_no_projects(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.create_portfolio.return_value = 7
        mock_p.get_portfolio.return_value = _plugin_portfolio(id=7, name="Gamma")
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.create_portfolio("Gamma", description="Desc")

        mock_p.create_portfolio.assert_called_once_with("Gamma", description="Desc")
        assert result.name == "Gamma"

    def test_create_portfolio_with_initial_project_ids(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.create_portfolio.return_value = 7
        mock_p.add_project_to_portfolio.return_value = True
        mock_p.get_portfolio.return_value = _plugin_portfolio(id=7, name="Gamma")
        mock_p.get_portfolio_projects.return_value = [{"id": 3}, {"id": 4}]
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.create_portfolio("Gamma", project_ids=[3, 4])

        assert mock_p.add_project_to_portfolio.call_count == 2
        mock_p.add_project_to_portfolio.assert_any_call(7, 3)
        mock_p.add_project_to_portfolio.assert_any_call(7, 4)
        assert result.project_ids == [3, 4]


class TestRemoteGetPortfolio:
    def test_get_portfolio_success(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        pp = _plugin_portfolio(id=1, name="Alpha")
        mock_p.get_portfolio_by_name.return_value = pp
        mock_p.get_portfolio_projects.return_value = [{"id": 10}]
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.get_portfolio("Alpha")

        mock_p.get_portfolio_by_name.assert_called_once_with("Alpha")
        assert isinstance(result, Portfolio)
        assert result.name == "Alpha"
        assert result.project_ids == [10]

    def test_get_portfolio_not_found_propagates(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        mock_p.get_portfolio_by_name.side_effect = KanboardNotFoundError("not found")

        with pytest.raises(KanboardNotFoundError):
            backend.get_portfolio("Missing")


class TestRemoteUpdatePortfolio:
    def test_update_portfolio_delegates_correctly(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        pp = _plugin_portfolio(id=5, name="Alpha")
        mock_p.get_portfolio_by_name.return_value = pp
        mock_p.update_portfolio.return_value = True
        updated_pp = _plugin_portfolio(id=5, name="Alpha", description="New desc")
        mock_p.get_portfolio.return_value = updated_pp
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.update_portfolio("Alpha", description="New desc")

        mock_p.update_portfolio.assert_called_once_with(5, description="New desc")
        mock_p.get_portfolio.assert_called_once_with(5)
        assert isinstance(result, Portfolio)

    def test_update_portfolio_not_found_propagates(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        mock_p.get_portfolio_by_name.side_effect = KanboardNotFoundError("not found")

        with pytest.raises(KanboardNotFoundError):
            backend.update_portfolio("Missing")


class TestRemoteRemovePortfolio:
    def test_remove_portfolio_success(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=3, name="Alpha")
        mock_p.remove_portfolio.return_value = True

        result = backend.remove_portfolio("Alpha")

        mock_p.remove_portfolio.assert_called_once_with(3)
        assert result is True

    def test_remove_portfolio_not_found_returns_false(self) -> None:
        backend, mock_p, _ = _make_remote_backend()
        mock_p.get_portfolio_by_name.side_effect = KanboardNotFoundError("not found")

        result = backend.remove_portfolio("Missing")

        assert result is False
        mock_p.remove_portfolio.assert_not_called()


# ---------------------------------------------------------------------------
# RemotePortfolioBackend — project membership
# ---------------------------------------------------------------------------


class TestRemoteAddProject:
    def test_add_project_delegates_and_returns_updated_portfolio(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_p.add_project_to_portfolio.return_value = True
        updated_pp = _plugin_portfolio(id=1, name="Alpha")
        mock_p.get_portfolio.return_value = updated_pp
        mock_p.get_portfolio_projects.return_value = [{"id": 5}]
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.add_project("Alpha", 5)

        mock_p.add_project_to_portfolio.assert_called_once_with(1, 5)
        assert isinstance(result, Portfolio)
        assert result.project_ids == [5]


class TestRemoteRemoveProject:
    def test_remove_project_delegates_and_returns_updated_portfolio(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_p.remove_project_from_portfolio.return_value = True
        updated_pp = _plugin_portfolio(id=1, name="Alpha")
        mock_p.get_portfolio.return_value = updated_pp
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.remove_project("Alpha", 5)

        mock_p.remove_project_from_portfolio.assert_called_once_with(1, 5)
        assert isinstance(result, Portfolio)


# ---------------------------------------------------------------------------
# RemotePortfolioBackend — milestone CRUD
# ---------------------------------------------------------------------------


class TestRemoteAddMilestone:
    def test_add_milestone_no_target_date(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.create_milestone.return_value = 20
        pm = _plugin_milestone(id=20, name="v1.0")
        mock_m.get_milestone.return_value = pm
        mock_m.get_milestone_tasks.return_value = []

        result = backend.add_milestone("Alpha", "v1.0")

        mock_m.create_milestone.assert_called_once_with(1, "v1.0")
        assert isinstance(result, Milestone)
        assert result.name == "v1.0"
        assert result.portfolio_name == "Alpha"

    def test_add_milestone_with_target_date(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.create_milestone.return_value = 20
        td = datetime(2026, 6, 30)
        pm = _plugin_milestone(id=20, name="v1.0", target_date=td)
        mock_m.get_milestone.return_value = pm
        mock_m.get_milestone_tasks.return_value = []

        result = backend.add_milestone("Alpha", "v1.0", target_date=td)

        mock_m.create_milestone.assert_called_once_with(1, "v1.0", target_date=td)
        assert result.target_date == td


class TestRemoteUpdateMilestone:
    def test_update_milestone_delegates_correctly(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=10, name="v1.0")]
        mock_m.update_milestone.return_value = True
        pm = _plugin_milestone(id=10, name="v1.0")
        mock_m.get_milestone.return_value = pm
        mock_m.get_milestone_tasks.return_value = []

        result = backend.update_milestone("Alpha", "v1.0", status=1)

        mock_m.update_milestone.assert_called_once_with(10, status=1)
        mock_m.get_milestone.assert_called_once_with(10)
        assert isinstance(result, Milestone)

    def test_update_milestone_not_found_raises(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = []

        with pytest.raises(KanboardConfigError, match=r"v9\.9"):
            backend.update_milestone("Alpha", "v9.9")


class TestRemoteRemoveMilestone:
    def test_remove_milestone_success(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=10, name="v1.0")]
        mock_m.remove_milestone.return_value = True

        result = backend.remove_milestone("Alpha", "v1.0")

        mock_m.remove_milestone.assert_called_once_with(10)
        assert result is True

    def test_remove_milestone_not_found_returns_false(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = []

        result = backend.remove_milestone("Alpha", "ghost")

        assert result is False
        mock_m.remove_milestone.assert_not_called()


# ---------------------------------------------------------------------------
# RemotePortfolioBackend — milestone task membership
# ---------------------------------------------------------------------------


class TestRemoteAddTaskToMilestone:
    def test_add_task_delegates_and_returns_milestone(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=10, name="v1.0")]
        mock_m.add_task_to_milestone.return_value = True
        pm = _plugin_milestone(id=10, name="v1.0")
        mock_m.get_milestone.return_value = pm
        mock_m.get_milestone_tasks.return_value = [{"id": 42}]

        result = backend.add_task_to_milestone("Alpha", "v1.0", 42)

        mock_m.add_task_to_milestone.assert_called_once_with(10, 42)
        assert isinstance(result, Milestone)
        assert result.task_ids == [42]

    def test_add_task_critical_flag_accepted(self) -> None:
        """critical=True is accepted for protocol compatibility without error."""
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=10, name="v1.0")]
        mock_m.add_task_to_milestone.return_value = True
        mock_m.get_milestone.return_value = _plugin_milestone(id=10, name="v1.0")
        mock_m.get_milestone_tasks.return_value = []

        # Should not raise even with critical=True
        backend.add_task_to_milestone("Alpha", "v1.0", 42, critical=True)


class TestRemoteRemoveTaskFromMilestone:
    def test_remove_task_delegates_and_returns_milestone(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=10, name="v1.0")]
        mock_m.remove_task_from_milestone.return_value = True
        pm = _plugin_milestone(id=10, name="v1.0")
        mock_m.get_milestone.return_value = pm
        mock_m.get_milestone_tasks.return_value = []

        result = backend.remove_task_from_milestone("Alpha", "v1.0", 42)

        mock_m.remove_task_from_milestone.assert_called_once_with(10, 42)
        assert isinstance(result, Milestone)

    def test_remove_task_milestone_not_found_raises(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=1, name="Alpha")
        mock_m.get_portfolio_milestones.return_value = []

        with pytest.raises(KanboardConfigError):
            backend.remove_task_from_milestone("Alpha", "ghost", 42)


# ---------------------------------------------------------------------------
# Name-to-ID translation coverage
# ---------------------------------------------------------------------------


class TestNameToIdTranslation:
    """Verify every method that needs name-to-ID translation calls the resolver."""

    def test_update_portfolio_uses_name_lookup(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=99, name="X")
        mock_p.update_portfolio.return_value = True
        mock_p.get_portfolio.return_value = _plugin_portfolio(id=99, name="X")
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        backend.update_portfolio("X")

        # Lookup happened with the name, update happened with the numeric ID
        mock_p.get_portfolio_by_name.assert_called_once_with("X")
        mock_p.update_portfolio.assert_called_once_with(99)

    def test_add_project_uses_name_lookup(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=7, name="X")
        mock_p.add_project_to_portfolio.return_value = True
        mock_p.get_portfolio.return_value = _plugin_portfolio(id=7, name="X")
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        backend.add_project("X", 55)

        mock_p.add_project_to_portfolio.assert_called_once_with(7, 55)

    def test_remove_project_uses_name_lookup(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=7, name="X")
        mock_p.remove_project_from_portfolio.return_value = True
        mock_p.get_portfolio.return_value = _plugin_portfolio(id=7, name="X")
        mock_p.get_portfolio_projects.return_value = []
        mock_m.get_portfolio_milestones.return_value = []

        backend.remove_project("X", 55)

        mock_p.remove_project_from_portfolio.assert_called_once_with(7, 55)

    def test_add_milestone_uses_portfolio_name_lookup(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=3, name="X")
        mock_m.create_milestone.return_value = 50
        mock_m.get_milestone.return_value = _plugin_milestone(id=50, name="M")
        mock_m.get_milestone_tasks.return_value = []

        backend.add_milestone("X", "M")

        mock_m.create_milestone.assert_called_once_with(3, "M")

    def test_update_milestone_uses_both_name_lookups(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=3, name="X")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=77, name="M")]
        mock_m.update_milestone.return_value = True
        mock_m.get_milestone.return_value = _plugin_milestone(id=77, name="M")
        mock_m.get_milestone_tasks.return_value = []

        backend.update_milestone("X", "M", status=2)

        mock_m.update_milestone.assert_called_once_with(77, status=2)

    def test_remove_milestone_uses_both_name_lookups(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=3, name="X")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=77, name="M")]
        mock_m.remove_milestone.return_value = True

        backend.remove_milestone("X", "M")

        mock_m.remove_milestone.assert_called_once_with(77)

    def test_add_task_uses_both_name_lookups(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=3, name="X")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=77, name="M")]
        mock_m.add_task_to_milestone.return_value = True
        mock_m.get_milestone.return_value = _plugin_milestone(id=77, name="M")
        mock_m.get_milestone_tasks.return_value = []

        backend.add_task_to_milestone("X", "M", 100)

        mock_m.add_task_to_milestone.assert_called_once_with(77, 100)

    def test_remove_task_uses_both_name_lookups(self) -> None:
        backend, mock_p, mock_m = _make_remote_backend()
        mock_p.get_portfolio_by_name.return_value = _plugin_portfolio(id=3, name="X")
        mock_m.get_portfolio_milestones.return_value = [_plugin_milestone(id=77, name="M")]
        mock_m.remove_task_from_milestone.return_value = True
        mock_m.get_milestone.return_value = _plugin_milestone(id=77, name="M")
        mock_m.get_milestone_tasks.return_value = []

        backend.remove_task_from_milestone("X", "M", 100)

        mock_m.remove_task_from_milestone.assert_called_once_with(77, 100)
