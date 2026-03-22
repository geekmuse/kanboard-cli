"""Unit tests for LocalPortfolioStore — JSON persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from kanboard.exceptions import KanboardConfigError
from kanboard.models import Milestone, Portfolio
from kanboard.orchestration.store import (
    _SCHEMA_VERSION,
    LocalPortfolioStore,
    _dt_to_str,
    _milestone_from_dict,
    _milestone_to_dict,
    _portfolio_from_dict,
    _portfolio_to_dict,
    _str_to_dt,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_store(tmp_path: Path) -> LocalPortfolioStore:
    """Return a store backed by a temp file (never touches real ~/.config)."""
    return LocalPortfolioStore(path=tmp_path / "portfolios.json")


def make_portfolio(
    name: str = "Alpha",
    description: str = "Test portfolio",
    project_ids: list[int] | None = None,
) -> Portfolio:
    """Return a minimal Portfolio for use in tests."""
    now = datetime(2026, 3, 22, 12, 0, 0)
    return Portfolio(
        name=name,
        description=description,
        project_ids=project_ids or [1, 2, 3],
        milestones=[],
        created_at=now,
        updated_at=now,
    )


def make_milestone(
    name: str = "Sprint 1",
    portfolio_name: str = "Alpha",
    target_date: datetime | None = None,
    task_ids: list[int] | None = None,
    critical_task_ids: list[int] | None = None,
) -> Milestone:
    """Return a minimal Milestone for use in tests."""
    return Milestone(
        name=name,
        portfolio_name=portfolio_name,
        target_date=target_date,
        task_ids=task_ids or [],
        critical_task_ids=critical_task_ids or [],
    )


# ---------------------------------------------------------------------------
# Serialisation helper tests
# ---------------------------------------------------------------------------


class TestSerialiseHelpers:
    def test_dt_to_str_none(self) -> None:
        assert _dt_to_str(None) is None

    def test_dt_to_str_roundtrip(self) -> None:
        dt = datetime(2026, 4, 1, 9, 30, 0)
        assert _dt_to_str(dt) == "2026-04-01T09:30:00"

    def test_str_to_dt_none(self) -> None:
        assert _str_to_dt(None) is None

    def test_str_to_dt_roundtrip(self) -> None:
        s = "2026-04-01T09:30:00"
        dt = _str_to_dt(s)
        assert dt == datetime(2026, 4, 1, 9, 30, 0)

    def test_milestone_to_dict(self) -> None:
        m = make_milestone(
            task_ids=[10, 20],
            critical_task_ids=[10],
            target_date=datetime(2026, 5, 1),
        )
        d = _milestone_to_dict(m)
        assert d["name"] == "Sprint 1"
        assert d["portfolio_name"] == "Alpha"
        assert d["target_date"] == "2026-05-01T00:00:00"
        assert d["task_ids"] == [10, 20]
        assert d["critical_task_ids"] == [10]

    def test_milestone_from_dict(self) -> None:
        raw = {
            "name": "Sprint 1",
            "portfolio_name": "Alpha",
            "target_date": "2026-05-01T00:00:00",
            "task_ids": [10, 20],
            "critical_task_ids": [10],
        }
        m = _milestone_from_dict(raw)
        assert m.name == "Sprint 1"
        assert m.target_date == datetime(2026, 5, 1)
        assert m.task_ids == [10, 20]
        assert m.critical_task_ids == [10]

    def test_milestone_from_dict_no_target(self) -> None:
        raw = {
            "name": "M",
            "portfolio_name": "P",
        }
        m = _milestone_from_dict(raw)
        assert m.target_date is None
        assert m.task_ids == []
        assert m.critical_task_ids == []

    def test_portfolio_to_dict(self) -> None:
        p = make_portfolio()
        d = _portfolio_to_dict(p)
        assert d["name"] == "Alpha"
        assert d["project_ids"] == [1, 2, 3]
        assert d["milestones"] == []
        assert d["created_at"] == "2026-03-22T12:00:00"

    def test_portfolio_from_dict(self) -> None:
        raw = {
            "name": "Alpha",
            "description": "Desc",
            "project_ids": [1, 2],
            "milestones": [],
            "created_at": "2026-03-22T12:00:00",
            "updated_at": "2026-03-22T12:00:00",
        }
        p = _portfolio_from_dict(raw)
        assert p.name == "Alpha"
        assert p.project_ids == [1, 2]
        assert p.created_at == datetime(2026, 3, 22, 12, 0, 0)

    def test_portfolio_from_dict_with_milestones(self) -> None:
        raw = {
            "name": "Alpha",
            "description": "",
            "project_ids": [],
            "milestones": [
                {
                    "name": "M1",
                    "portfolio_name": "Alpha",
                    "target_date": None,
                    "task_ids": [5],
                    "critical_task_ids": [],
                }
            ],
            "created_at": None,
            "updated_at": None,
        }
        p = _portfolio_from_dict(raw)
        assert len(p.milestones) == 1
        assert p.milestones[0].name == "M1"


# ---------------------------------------------------------------------------
# Store.load() tests
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        assert store.load() == []

    def test_load_valid_file(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        p = make_portfolio()
        store.save([p])
        loaded = store.load()
        assert len(loaded) == 1
        assert loaded[0].name == "Alpha"
        assert loaded[0].project_ids == [1, 2, 3]

    def test_load_malformed_json_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store._path.write_text("{ not valid json", encoding="utf-8")
        with pytest.raises(KanboardConfigError, match="Malformed JSON"):
            store.load()

    def test_load_wrong_schema_version_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        data = {"version": 99, "portfolios": []}
        store._path.parent.mkdir(parents=True, exist_ok=True)
        store._path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(KanboardConfigError, match="schema version mismatch"):
            store.load()

    def test_load_version_none_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        data = {"portfolios": []}
        store._path.parent.mkdir(parents=True, exist_ok=True)
        store._path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(KanboardConfigError, match="schema version mismatch"):
            store.load()

    def test_load_preserves_datetime(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        dt = datetime(2026, 6, 15, 10, 30, 0)
        p = make_portfolio()
        p.milestones.append(make_milestone(target_date=dt))
        store.save([p])
        loaded = store.load()
        assert loaded[0].milestones[0].target_date == dt


# ---------------------------------------------------------------------------
# Store.save() tests
# ---------------------------------------------------------------------------


class TestSave:
    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "portfolios.json"
        store = LocalPortfolioStore(path=deep_path)
        store.save([])
        assert deep_path.exists()

    def test_save_writes_correct_schema_version(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.save([])
        data = json.loads(store._path.read_text(encoding="utf-8"))
        assert data["version"] == _SCHEMA_VERSION

    def test_save_round_trip(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        p = make_portfolio(project_ids=[10, 20])
        store.save([p])
        loaded = store.load()
        assert loaded[0].project_ids == [10, 20]

    def test_save_overwrites_previous(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.save([make_portfolio("A")])
        store.save([make_portfolio("B"), make_portfolio("C")])
        loaded = store.load()
        assert [p.name for p in loaded] == ["B", "C"]

    def test_save_atomic_no_tmp_leftover(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.save([make_portfolio()])
        tmp_files = list((tmp_path).glob("*.tmp"))
        assert tmp_files == [], f"Unexpected .tmp files: {tmp_files}"


# ---------------------------------------------------------------------------
# Portfolio CRUD tests
# ---------------------------------------------------------------------------


class TestCreatePortfolio:
    def test_create_returns_portfolio(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        p = store.create_portfolio("Alpha", description="Desc", project_ids=[1, 2])
        assert p.name == "Alpha"
        assert p.description == "Desc"
        assert p.project_ids == [1, 2]

    def test_create_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        loaded = store.load()
        assert len(loaded) == 1
        assert loaded[0].name == "Alpha"

    def test_create_sets_timestamps(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        p = store.create_portfolio("Alpha")
        assert p.created_at is not None
        assert p.updated_at is not None

    def test_create_duplicate_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        with pytest.raises(ValueError, match="already exists"):
            store.create_portfolio("Alpha")

    def test_create_case_sensitive(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        p2 = store.create_portfolio("alpha")  # Different name — should not raise
        assert p2.name == "alpha"

    def test_create_empty_project_ids_default(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        p = store.create_portfolio("Alpha")
        assert p.project_ids == []


class TestGetPortfolio:
    def test_get_existing(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        p = store.get_portfolio("Alpha")
        assert p.name == "Alpha"

    def test_get_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.get_portfolio("NoSuch")

    def test_get_error_includes_name(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="MyPortfolio"):
            store.get_portfolio("MyPortfolio")


class TestUpdatePortfolio:
    def test_update_description(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha", description="Old")
        updated = store.update_portfolio("Alpha", description="New")
        assert updated.description == "New"

    def test_update_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha", description="Old")
        store.update_portfolio("Alpha", description="New")
        reloaded = store.get_portfolio("Alpha")
        assert reloaded.description == "New"

    def test_update_refreshes_updated_at(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        p = store.create_portfolio("Alpha")
        original_ts = p.updated_at
        updated = store.update_portfolio("Alpha", description="X")
        assert updated.updated_at is not None
        # updated_at should be >= the created timestamp
        assert updated.updated_at >= original_ts  # type: ignore[operator]

    def test_update_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.update_portfolio("NoSuch", description="X")

    def test_update_unknown_field_ignored(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        # Should not raise
        store.update_portfolio("Alpha", nonexistent_field="value")


class TestRemovePortfolio:
    def test_remove_existing(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        result = store.remove_portfolio("Alpha")
        assert result is True
        assert store.load() == []

    def test_remove_not_found_returns_false(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        result = store.remove_portfolio("NoSuch")
        assert result is False

    def test_remove_only_removes_target(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.create_portfolio("Beta")
        store.remove_portfolio("Alpha")
        remaining = store.load()
        assert len(remaining) == 1
        assert remaining[0].name == "Beta"


# ---------------------------------------------------------------------------
# Project membership tests
# ---------------------------------------------------------------------------


class TestProjectMembership:
    def test_add_project(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        updated = store.add_project("Alpha", 42)
        assert 42 in updated.project_ids

    def test_add_project_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_project("Alpha", 42)
        p = store.get_portfolio("Alpha")
        assert 42 in p.project_ids

    def test_add_project_idempotent(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_project("Alpha", 42)
        store.add_project("Alpha", 42)  # second call must not duplicate
        p = store.get_portfolio("Alpha")
        assert p.project_ids.count(42) == 1

    def test_add_project_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.add_project("NoSuch", 1)

    def test_remove_project(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha", project_ids=[1, 2, 3])
        updated = store.remove_project("Alpha", 2)
        assert 2 not in updated.project_ids
        assert updated.project_ids == [1, 3]

    def test_remove_project_missing_id_noop(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha", project_ids=[1, 2])
        updated = store.remove_project("Alpha", 99)
        assert updated.project_ids == [1, 2]

    def test_remove_project_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.remove_project("NoSuch", 1)


# ---------------------------------------------------------------------------
# Milestone CRUD tests
# ---------------------------------------------------------------------------


class TestAddMilestone:
    def test_add_milestone_returns_milestone(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        m = store.add_milestone("Alpha", "Sprint 1")
        assert m.name == "Sprint 1"
        assert m.portfolio_name == "Alpha"

    def test_add_milestone_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        p = store.get_portfolio("Alpha")
        assert any(m.name == "Sprint 1" for m in p.milestones)

    def test_add_milestone_with_target_date(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        dt = datetime(2026, 6, 30, 0, 0, 0)
        m = store.add_milestone("Alpha", "Sprint 1", target_date=dt)
        assert m.target_date == dt

    def test_add_milestone_duplicate_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        with pytest.raises(ValueError, match="already exists"):
            store.add_milestone("Alpha", "Sprint 1")

    def test_add_milestone_portfolio_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.add_milestone("NoSuch", "Sprint 1")


class TestUpdateMilestone:
    def test_update_target_date(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        dt = datetime(2026, 8, 1)
        m = store.update_milestone("Alpha", "Sprint 1", target_date=dt)
        assert m.target_date == dt

    def test_update_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        dt = datetime(2026, 8, 1)
        store.update_milestone("Alpha", "Sprint 1", target_date=dt)
        p = store.get_portfolio("Alpha")
        assert p.milestones[0].target_date == dt

    def test_update_milestone_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        with pytest.raises(KanboardConfigError, match="not found"):
            store.update_milestone("Alpha", "NoSuch", target_date=None)

    def test_update_portfolio_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.update_milestone("NoSuch", "Sprint 1", target_date=None)


class TestRemoveMilestone:
    def test_remove_milestone(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        result = store.remove_milestone("Alpha", "Sprint 1")
        assert result is True
        p = store.get_portfolio("Alpha")
        assert p.milestones == []

    def test_remove_milestone_not_found_returns_false(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        result = store.remove_milestone("Alpha", "NoSuch")
        assert result is False

    def test_remove_milestone_portfolio_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.remove_milestone("NoSuch", "Sprint 1")

    def test_remove_only_removes_target_milestone(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_milestone("Alpha", "Sprint 2")
        store.remove_milestone("Alpha", "Sprint 1")
        p = store.get_portfolio("Alpha")
        assert len(p.milestones) == 1
        assert p.milestones[0].name == "Sprint 2"


# ---------------------------------------------------------------------------
# Milestone task membership tests
# ---------------------------------------------------------------------------


class TestAddTaskToMilestone:
    def test_add_task(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        m = store.add_task_to_milestone("Alpha", "Sprint 1", 101)
        assert 101 in m.task_ids
        assert 101 not in m.critical_task_ids

    def test_add_task_critical(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        m = store.add_task_to_milestone("Alpha", "Sprint 1", 101, critical=True)
        assert 101 in m.task_ids
        assert 101 in m.critical_task_ids

    def test_add_task_idempotent(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_task_to_milestone("Alpha", "Sprint 1", 101)
        m = store.add_task_to_milestone("Alpha", "Sprint 1", 101)
        assert m.task_ids.count(101) == 1

    def test_add_task_critical_idempotent(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_task_to_milestone("Alpha", "Sprint 1", 101, critical=True)
        m = store.add_task_to_milestone("Alpha", "Sprint 1", 101, critical=True)
        assert m.critical_task_ids.count(101) == 1

    def test_add_task_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_task_to_milestone("Alpha", "Sprint 1", 101, critical=True)
        p = store.get_portfolio("Alpha")
        m = p.milestones[0]
        assert 101 in m.task_ids
        assert 101 in m.critical_task_ids

    def test_add_task_portfolio_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.add_task_to_milestone("NoSuch", "Sprint 1", 101)

    def test_add_task_milestone_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        with pytest.raises(KanboardConfigError, match="not found"):
            store.add_task_to_milestone("Alpha", "NoSuch", 101)


class TestRemoveTaskFromMilestone:
    def test_remove_task(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_task_to_milestone("Alpha", "Sprint 1", 101, critical=True)
        store.add_task_to_milestone("Alpha", "Sprint 1", 202)
        m = store.remove_task_from_milestone("Alpha", "Sprint 1", 101)
        assert 101 not in m.task_ids
        assert 101 not in m.critical_task_ids
        assert 202 in m.task_ids

    def test_remove_task_persists(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_task_to_milestone("Alpha", "Sprint 1", 101)
        store.remove_task_from_milestone("Alpha", "Sprint 1", 101)
        p = store.get_portfolio("Alpha")
        assert 101 not in p.milestones[0].task_ids

    def test_remove_non_critical_task_noop_on_critical_ids(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        store.add_task_to_milestone("Alpha", "Sprint 1", 101)  # not critical
        m = store.remove_task_from_milestone("Alpha", "Sprint 1", 101)
        assert m.critical_task_ids == []

    def test_remove_task_not_in_list_noop(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.add_milestone("Alpha", "Sprint 1")
        # Removing a task that was never added — should not raise
        m = store.remove_task_from_milestone("Alpha", "Sprint 1", 999)
        assert m.task_ids == []

    def test_remove_task_portfolio_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        with pytest.raises(KanboardConfigError, match="not found"):
            store.remove_task_from_milestone("NoSuch", "Sprint 1", 101)

    def test_remove_task_milestone_not_found_raises(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        with pytest.raises(KanboardConfigError, match="not found"):
            store.remove_task_from_milestone("Alpha", "NoSuch", 101)


# ---------------------------------------------------------------------------
# Multi-portfolio isolation
# ---------------------------------------------------------------------------


class TestMultiPortfolioIsolation:
    def test_multiple_portfolios_persisted(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.create_portfolio("Beta")
        store.create_portfolio("Gamma")
        loaded = store.load()
        assert len(loaded) == 3
        assert {p.name for p in loaded} == {"Alpha", "Beta", "Gamma"}

    def test_update_does_not_affect_other_portfolios(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha", description="A")
        store.create_portfolio("Beta", description="B")
        store.update_portfolio("Alpha", description="Updated")
        beta = store.get_portfolio("Beta")
        assert beta.description == "B"

    def test_milestone_scoped_to_portfolio(self, tmp_path: Path) -> None:
        store = make_store(tmp_path)
        store.create_portfolio("Alpha")
        store.create_portfolio("Beta")
        store.add_milestone("Alpha", "Sprint 1")
        beta = store.get_portfolio("Beta")
        assert beta.milestones == []


# ---------------------------------------------------------------------------
# Default path test (does NOT touch real filesystem)
# ---------------------------------------------------------------------------


class TestDefaultPath:
    def test_default_path_uses_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from kanboard import config as cfg_module

        fake_config_dir = Path("/tmp/fake-kanboard-config")
        monkeypatch.setattr(cfg_module, "CONFIG_DIR", fake_config_dir)
        store = LocalPortfolioStore()
        assert store._path == fake_config_dir / "portfolios.json"
