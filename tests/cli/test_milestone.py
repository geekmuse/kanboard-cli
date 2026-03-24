"""CLI tests for ``kanboard milestone`` subcommands (US-008, US-009)."""

from __future__ import annotations

import json
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardConfigError
from kanboard.models import Milestone, MilestoneProgress, Portfolio, Task
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _make_milestone(
    name: str = "Sprint 1",
    portfolio_name: str = "Test Portfolio",
    target_date: datetime | None = datetime(2026, 6, 30),
    task_ids: list[int] | None = None,
    critical_task_ids: list[int] | None = None,
) -> Milestone:
    """Build a Milestone for tests."""
    return Milestone(
        name=name,
        portfolio_name=portfolio_name,
        target_date=target_date,
        task_ids=task_ids if task_ids is not None else [10, 11],
        critical_task_ids=critical_task_ids if critical_task_ids is not None else [10],
    )


def _make_portfolio(
    name: str = "Test Portfolio",
    project_ids: list[int] | None = None,
    milestones: list[Milestone] | None = None,
) -> Portfolio:
    """Build a Portfolio for tests."""
    return Portfolio(
        name=name,
        description="Test description",
        project_ids=project_ids if project_ids is not None else [1, 2],
        milestones=milestones if milestones is not None else [_make_milestone()],
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 2),
    )


def _make_task(
    task_id: int = 10,
    title: str = "Test Task",
    project_id: int = 1,
    is_active: bool = True,
) -> Task:
    """Build a Task from test data."""
    return Task.from_api(
        {
            "id": str(task_id),
            "title": title,
            "project_id": str(project_id),
            "column_id": "3",
            "owner_id": "5",
            "is_active": "1" if is_active else "0",
            "priority": "2",
            "description": "",
            "date_due": None,
            "date_creation": None,
            "date_modification": None,
            "date_completed": None,
            "date_moved": None,
            "color_id": "blue",
            "swimlane_id": "0",
            "creator_id": "1",
            "category_id": "0",
            "score": "0",
            "position": "1",
            "reference": "",
            "tags": [],
            "url": "",
        }
    )


def _make_milestone_progress(
    milestone_name: str = "Sprint 1",
    portfolio_name: str = "Test Portfolio",
    percent: float = 50.0,
    total: int = 10,
    completed: int = 5,
    is_at_risk: bool = False,
    is_overdue: bool = False,
    blocked_task_ids: list[int] | None = None,
) -> MilestoneProgress:
    """Build a MilestoneProgress for tests."""
    return MilestoneProgress(
        milestone_name=milestone_name,
        portfolio_name=portfolio_name,
        target_date=datetime(2026, 6, 30),
        total=total,
        completed=completed,
        percent=percent,
        is_at_risk=is_at_risk,
        is_overdue=is_overdue,
        blocked_task_ids=blocked_task_ids if blocked_task_ids is not None else [],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def mock_config() -> KanboardConfig:
    """Return a minimal resolved config."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a MagicMock Kanboard client."""
    return MagicMock()


@pytest.fixture()
def mock_store() -> MagicMock:
    """Return a MagicMock LocalPortfolioStore."""
    store = MagicMock()
    store.load.return_value = []
    return store


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
    args: list[str],
    input: str | None = None,
) -> object:
    """Invoke the CLI with patched config, client, and store."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config)
        )
        stack.enter_context(patch("kanboard_cli.main.KanboardClient", return_value=mock_client))
        stack.enter_context(
            patch(
                "kanboard_cli.commands.milestone._get_store",
                return_value=mock_store,
            )
        )
        return runner.invoke(cli, args, input=input)


# ===========================================================================
# milestone list
# ===========================================================================


def test_milestone_list_table_empty(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone list`` with no milestones shows table headers."""
    mock_store.get_portfolio.return_value = _make_portfolio(milestones=[])
    result = _invoke(
        runner, mock_config, mock_client, mock_store, ["milestone", "list", "Test Portfolio"]
    )
    assert result.exit_code == 0


def test_milestone_list_table_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone list`` shows name, target_date, task_count, critical_count."""
    ms = _make_milestone(task_ids=[1, 2, 3], critical_task_ids=[1])
    mock_store.get_portfolio.return_value = _make_portfolio(milestones=[ms])
    result = _invoke(
        runner, mock_config, mock_client, mock_store, ["milestone", "list", "Test Portfolio"]
    )
    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    assert "2026-06-30" in result.output
    assert "3" in result.output  # task_count
    assert "1" in result.output  # critical_count


def test_milestone_list_json_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone list --output json`` returns JSON array with correct fields."""
    ms = _make_milestone(task_ids=[1, 2], critical_task_ids=[1])
    mock_store.get_portfolio.return_value = _make_portfolio(milestones=[ms])
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["--output", "json", "milestone", "list", "Test Portfolio"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Sprint 1"
    assert data[0]["task_count"] == 2
    assert data[0]["critical_count"] == 1
    assert data[0]["target_date"] == "2026-06-30"


def test_milestone_list_csv_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone list --output csv`` renders CSV with headers."""
    ms = _make_milestone()
    mock_store.get_portfolio.return_value = _make_portfolio(milestones=[ms])
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["--output", "csv", "milestone", "list", "Test Portfolio"],
    )
    assert result.exit_code == 0
    assert "name" in result.output
    assert "Sprint 1" in result.output


def test_milestone_list_quiet_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone list --output quiet`` prints nothing (no id field)."""
    ms = _make_milestone()
    mock_store.get_portfolio.return_value = _make_portfolio(milestones=[ms])
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["--output", "quiet", "milestone", "list", "Test Portfolio"],
    )
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_milestone_list_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone list`` shows error when portfolio not found."""
    mock_store.get_portfolio.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(runner, mock_config, mock_client, mock_store, ["milestone", "list", "Ghost"])
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# milestone show
# ===========================================================================


def test_milestone_show_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone show`` displays progress bar and task info."""
    portfolio_obj = _make_portfolio(milestones=[_make_milestone()])
    mock_store.get_portfolio.return_value = portfolio_obj

    mp = _make_milestone_progress(total=10, completed=5)
    mock_manager = MagicMock()
    mock_manager.get_milestone_progress.return_value = mp

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "show", "Test Portfolio", "Sprint 1"],
        )

    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    mock_manager.get_milestone_progress.assert_called_once_with("Test Portfolio", "Sprint 1")


def test_milestone_show_with_blocked_tasks(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone show`` displays blocked task IDs when present."""
    portfolio_obj = _make_portfolio(milestones=[_make_milestone()])
    mock_store.get_portfolio.return_value = portfolio_obj

    mp = _make_milestone_progress(blocked_task_ids=[42, 43])
    mock_manager = MagicMock()
    mock_manager.get_milestone_progress.return_value = mp

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "show", "Test Portfolio", "Sprint 1"],
        )

    assert result.exit_code == 0
    assert "42" in result.output
    assert "43" in result.output


def test_milestone_show_not_found_in_store(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone show`` shows error when milestone not in portfolio."""
    portfolio_obj = _make_portfolio(milestones=[])
    mock_store.get_portfolio.return_value = portfolio_obj
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "show", "Test Portfolio", "Ghost Milestone"],
    )
    assert result.exit_code != 0
    assert "Ghost Milestone" in result.output


def test_milestone_show_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone show`` shows error when portfolio not found."""
    mock_store.get_portfolio.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "show", "Ghost", "Sprint 1"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


def test_milestone_show_api_unreachable_fallback(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone show`` falls back to store data when API fails."""
    ms = _make_milestone()
    portfolio_obj = _make_portfolio(milestones=[ms])
    mock_store.get_portfolio.return_value = portfolio_obj

    mock_manager = MagicMock()
    mock_manager.get_milestone_progress.side_effect = KanboardAPIError("unreachable")

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "show", "Test Portfolio", "Sprint 1"],
        )

    assert result.exit_code == 0
    assert "Sprint 1" in result.output


# ===========================================================================
# milestone create
# ===========================================================================


def test_milestone_create_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone create`` creates milestone and prints success."""
    mock_store.add_milestone.return_value = _make_milestone(name="Q3 Release")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "create", "Test Portfolio", "Q3 Release"],
    )
    assert result.exit_code == 0
    assert "Q3 Release" in result.output
    mock_store.add_milestone.assert_called_once_with(
        "Test Portfolio", "Q3 Release", target_date=None
    )


def test_milestone_create_with_target_date(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone create --target-date`` parses date and passes to store."""
    mock_store.add_milestone.return_value = _make_milestone()
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "create", "Test Portfolio", "Sprint 1", "--target-date", "2026-09-15"],
    )
    assert result.exit_code == 0
    call_args = mock_store.add_milestone.call_args
    assert call_args[0][0] == "Test Portfolio"
    assert call_args[0][1] == "Sprint 1"
    assert call_args[1]["target_date"] == datetime(2026, 9, 15)


def test_milestone_create_invalid_date(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone create`` shows error for invalid date format."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "create", "Test Portfolio", "Sprint 1", "--target-date", "15/09/2026"],
    )
    assert result.exit_code != 0
    assert "Invalid date" in result.output or "YYYY-MM-DD" in result.output


def test_milestone_create_duplicate(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone create`` shows error when milestone already exists."""
    mock_store.add_milestone.side_effect = ValueError(
        "Milestone 'Sprint 1' already exists in portfolio 'Test Portfolio'"
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "create", "Test Portfolio", "Sprint 1"],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_milestone_create_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone create`` shows error when portfolio not found."""
    mock_store.add_milestone.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "create", "Ghost", "Sprint 1"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


def test_milestone_create_with_description(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone create --description`` is accepted without error (not persisted)."""
    mock_store.add_milestone.return_value = _make_milestone()
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "create", "Test Portfolio", "Sprint 1", "--description", "First sprint"],
    )
    assert result.exit_code == 0


# ===========================================================================
# milestone remove
# ===========================================================================


def test_milestone_remove_requires_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove`` without --yes aborts (non-zero exit)."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove", "Test Portfolio", "Sprint 1"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_store.remove_milestone.assert_not_called()


def test_milestone_remove_with_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove --yes`` removes milestone and prints success."""
    mock_store.remove_milestone.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove", "Test Portfolio", "Sprint 1", "--yes"],
    )
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_store.remove_milestone.assert_called_once_with("Test Portfolio", "Sprint 1")


def test_milestone_remove_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove`` shows error when milestone not found."""
    mock_store.remove_milestone.return_value = False
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove", "Test Portfolio", "Ghost Milestone", "--yes"],
    )
    assert result.exit_code != 0
    assert "Ghost Milestone" in result.output


def test_milestone_remove_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove`` shows error when portfolio not found."""
    mock_store.remove_milestone.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove", "Ghost", "Sprint 1", "--yes"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# milestone add-task
# ===========================================================================


def test_milestone_add_task_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone add-task`` validates task and adds to milestone."""
    portfolio_obj = _make_portfolio(project_ids=[1, 2])
    mock_store.get_portfolio.return_value = portfolio_obj
    mock_client.tasks.get_task.return_value = _make_task(task_id=42, project_id=1)
    mock_store.add_task_to_milestone.return_value = _make_milestone()

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "add-task", "Test Portfolio", "Sprint 1", "42"],
    )
    assert result.exit_code == 0
    assert "42" in result.output
    mock_client.tasks.get_task.assert_called_once_with(42)
    mock_store.add_task_to_milestone.assert_called_once_with(
        "Test Portfolio", "Sprint 1", 42, critical=False
    )


def test_milestone_add_task_critical(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone add-task --critical`` marks task as critical."""
    portfolio_obj = _make_portfolio(project_ids=[1])
    mock_store.get_portfolio.return_value = portfolio_obj
    mock_client.tasks.get_task.return_value = _make_task(task_id=10, project_id=1)
    mock_store.add_task_to_milestone.return_value = _make_milestone()

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "add-task", "Test Portfolio", "Sprint 1", "10", "--critical"],
    )
    assert result.exit_code == 0
    assert "critical" in result.output
    mock_store.add_task_to_milestone.assert_called_once_with(
        "Test Portfolio", "Sprint 1", 10, critical=True
    )


def test_milestone_add_task_not_in_portfolio_project(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone add-task`` shows error when task project not in portfolio."""
    portfolio_obj = _make_portfolio(project_ids=[1, 2])
    mock_store.get_portfolio.return_value = portfolio_obj
    # Task belongs to project 5, not in portfolio [1, 2]
    mock_client.tasks.get_task.return_value = _make_task(task_id=99, project_id=5)

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "add-task", "Test Portfolio", "Sprint 1", "99"],
    )
    assert result.exit_code != 0
    assert "99" in result.output
    assert "5" in result.output
    mock_store.add_task_to_milestone.assert_not_called()


def test_milestone_add_task_not_found_in_api(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone add-task`` shows error when task does not exist in Kanboard."""
    portfolio_obj = _make_portfolio(project_ids=[1])
    mock_store.get_portfolio.return_value = portfolio_obj
    mock_client.tasks.get_task.side_effect = Exception("Task not found")

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "add-task", "Test Portfolio", "Sprint 1", "999"],
    )
    assert result.exit_code != 0
    assert "999" in result.output
    mock_store.add_task_to_milestone.assert_not_called()


def test_milestone_add_task_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone add-task`` shows error when portfolio not found."""
    mock_store.get_portfolio.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "add-task", "Ghost", "Sprint 1", "42"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output
    mock_store.add_task_to_milestone.assert_not_called()


def test_milestone_add_task_milestone_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone add-task`` shows error when milestone not found in store."""
    portfolio_obj = _make_portfolio(project_ids=[1])
    mock_store.get_portfolio.return_value = portfolio_obj
    mock_client.tasks.get_task.return_value = _make_task(task_id=42, project_id=1)
    mock_store.add_task_to_milestone.side_effect = KanboardConfigError(
        "Milestone 'Ghost' not found in portfolio 'Test Portfolio'"
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "add-task", "Test Portfolio", "Ghost", "42"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# milestone remove-task
# ===========================================================================


def test_milestone_remove_task_requires_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove-task`` without --yes aborts."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove-task", "Test Portfolio", "Sprint 1", "42"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_store.remove_task_from_milestone.assert_not_called()


def test_milestone_remove_task_with_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove-task --yes`` removes task and prints success."""
    mock_store.remove_task_from_milestone.return_value = _make_milestone(task_ids=[11])
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove-task", "Test Portfolio", "Sprint 1", "42", "--yes"],
    )
    assert result.exit_code == 0
    assert "42" in result.output
    mock_store.remove_task_from_milestone.assert_called_once_with("Test Portfolio", "Sprint 1", 42)


def test_milestone_remove_task_milestone_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone remove-task`` shows error when milestone not found."""
    mock_store.remove_task_from_milestone.side_effect = KanboardConfigError(
        "Milestone 'Ghost' not found in portfolio 'Test Portfolio'"
    )
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["milestone", "remove-task", "Test Portfolio", "Ghost", "42", "--yes"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# milestone progress
# ===========================================================================


def test_milestone_progress_single(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone progress <portfolio> <milestone>`` shows single milestone progress."""
    mp = _make_milestone_progress(milestone_name="Sprint 1", percent=75.0)
    mock_manager = MagicMock()
    mock_manager.get_milestone_progress.return_value = mp

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "progress", "Test Portfolio", "Sprint 1"],
        )

    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    mock_manager.get_milestone_progress.assert_called_once_with("Test Portfolio", "Sprint 1")


def test_milestone_progress_all(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone progress <portfolio>`` shows all milestone progress bars."""
    mp1 = _make_milestone_progress(milestone_name="Sprint 1", percent=50.0)
    mp2 = _make_milestone_progress(milestone_name="Sprint 2", percent=20.0)
    mock_manager = MagicMock()
    mock_manager.get_all_milestone_progress.return_value = [mp1, mp2]

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "progress", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    assert "Sprint 2" in result.output
    mock_manager.get_all_milestone_progress.assert_called_once_with("Test Portfolio")


def test_milestone_progress_empty(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone progress`` with no milestones prints 'No milestones found.'"""
    mock_manager = MagicMock()
    mock_manager.get_all_milestone_progress.return_value = []

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "progress", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "No milestones" in result.output


def test_milestone_progress_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone progress`` shows error when portfolio not found."""
    mock_manager = MagicMock()
    mock_manager.get_all_milestone_progress.side_effect = KanboardConfigError(
        "Portfolio 'Ghost' not found"
    )

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "progress", "Ghost"],
        )

    assert result.exit_code != 0
    assert "Ghost" in result.output


def test_milestone_progress_api_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``milestone progress`` shows error on API failure."""
    mock_manager = MagicMock()
    mock_manager.get_all_milestone_progress.side_effect = KanboardAPIError("Server error")

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["milestone", "progress", "Test Portfolio"],
        )

    assert result.exit_code != 0
    assert "Error" in result.output or "error" in result.output.lower()


# ===========================================================================
# Remote backend tests (US-009)
# ===========================================================================


@pytest.fixture()
def mock_remote_config() -> KanboardConfig:
    """Return a minimal resolved config with portfolio_backend='remote'."""
    return KanboardConfig(
        url="http://kanboard.test/jsonrpc.php",
        token="test-token",
        profile="default",
        output_format="table",
        portfolio_backend="remote",
    )


@pytest.fixture()
def mock_remote_backend() -> MagicMock:
    """Return a MagicMock remote portfolio backend."""
    return MagicMock()


def _invoke_remote(
    runner: CliRunner,
    remote_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
    mock_backend: MagicMock | None = None,
    input: str | None = None,
) -> object:
    """Invoke CLI with remote backend config.

    Patches KanboardConfig.resolve to return *remote_config* (portfolio_backend='remote').
    Optionally patches _get_backend to return *mock_backend* for commands that call it.
    The ``milestone progress`` remote path calls ``client.milestones`` directly and
    does not need mock_backend.
    """
    with ExitStack() as stack:
        stack.enter_context(
            patch("kanboard_cli.main.KanboardConfig.resolve", return_value=remote_config)
        )
        stack.enter_context(patch("kanboard_cli.main.KanboardClient", return_value=mock_client))
        if mock_backend is not None:
            stack.enter_context(
                patch(
                    "kanboard_cli.commands.milestone._get_backend",
                    return_value=mock_backend,
                )
            )
        return runner.invoke(cli, args, input=input)


# ---------------------------------------------------------------------------
# milestone list — remote
# ---------------------------------------------------------------------------


def test_milestone_list_remote_backend(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
    mock_remote_backend: MagicMock,
) -> None:
    """``milestone list`` with remote backend calls backend.get_portfolio()."""
    ms = _make_milestone(task_ids=[1, 2], critical_task_ids=[1])
    mock_remote_backend.get_portfolio.return_value = _make_portfolio(milestones=[ms])
    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "list", "Test Portfolio"],
        mock_backend=mock_remote_backend,
    )
    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    mock_remote_backend.get_portfolio.assert_called_once_with("Test Portfolio")


def test_milestone_list_remote_json(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
    mock_remote_backend: MagicMock,
) -> None:
    """``milestone list --output json`` with remote backend returns JSON array."""
    ms = _make_milestone(task_ids=[1, 2], critical_task_ids=[1])
    mock_remote_backend.get_portfolio.return_value = _make_portfolio(milestones=[ms])
    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["--output", "json", "milestone", "list", "Test Portfolio"],
        mock_backend=mock_remote_backend,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Sprint 1"
    assert data[0]["task_count"] == 2


# ---------------------------------------------------------------------------
# milestone create — remote
# ---------------------------------------------------------------------------


def test_milestone_create_remote_backend(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
    mock_remote_backend: MagicMock,
) -> None:
    """``milestone create`` with remote backend calls backend.add_milestone()."""
    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "create", "Test Portfolio", "Q3 Release"],
        mock_backend=mock_remote_backend,
    )
    assert result.exit_code == 0
    assert "Q3 Release" in result.output
    mock_remote_backend.add_milestone.assert_called_once_with(
        "Test Portfolio", "Q3 Release", target_date=None
    )


def test_milestone_create_remote_with_date(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
    mock_remote_backend: MagicMock,
) -> None:
    """``milestone create --target-date`` with remote backend passes date to backend."""
    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        [
            "milestone",
            "create",
            "Test Portfolio",
            "Sprint 1",
            "--target-date",
            "2026-09-15",
        ],
        mock_backend=mock_remote_backend,
    )
    assert result.exit_code == 0
    call_args = mock_remote_backend.add_milestone.call_args
    assert call_args[1]["target_date"] == datetime(2026, 9, 15)


# ---------------------------------------------------------------------------
# milestone remove — remote
# ---------------------------------------------------------------------------


def test_milestone_remove_remote_backend(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
    mock_remote_backend: MagicMock,
) -> None:
    """``milestone remove --yes`` with remote backend calls backend.remove_milestone()."""
    mock_remote_backend.remove_milestone.return_value = True
    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "remove", "Test Portfolio", "Sprint 1", "--yes"],
        mock_backend=mock_remote_backend,
    )
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_remote_backend.remove_milestone.assert_called_once_with("Test Portfolio", "Sprint 1")


def test_milestone_remove_remote_skips_metadata_sync(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
    mock_remote_backend: MagicMock,
) -> None:
    """``milestone remove`` with remote backend does NOT call PortfolioManager.sync_metadata."""
    mock_remote_backend.remove_milestone.return_value = True
    with patch("kanboard.orchestration.portfolio.PortfolioManager") as mock_pm_class:
        result = _invoke_remote(
            runner,
            mock_remote_config,
            mock_client,
            ["milestone", "remove", "Test Portfolio", "Sprint 1", "--yes"],
            mock_backend=mock_remote_backend,
        )
    assert result.exit_code == 0
    mock_pm_class.assert_not_called()


# ---------------------------------------------------------------------------
# milestone progress — remote
# ---------------------------------------------------------------------------


def test_milestone_progress_remote_single(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``milestone progress <portfolio> <milestone>`` with remote backend calls plugin API."""
    # Set up plugin portfolio stub
    plugin_pf = MagicMock()
    plugin_pf.id = 1
    mock_client.portfolios.get_portfolio_by_name.return_value = plugin_pf

    # Set up plugin milestone stub
    plugin_ms = MagicMock()
    plugin_ms.id = 10
    plugin_ms.name = "Sprint 1"
    plugin_ms.target_date = datetime(2026, 6, 30)
    mock_client.milestones.get_portfolio_milestones.return_value = [plugin_ms]

    # Set up plugin progress stub
    plugin_prog = MagicMock()
    plugin_prog.total = 10
    plugin_prog.completed = 5
    plugin_prog.percent = 50.0
    plugin_prog.is_at_risk = False
    plugin_prog.is_overdue = False
    mock_client.milestones.get_milestone_progress.return_value = plugin_prog

    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "progress", "Test Portfolio", "Sprint 1"],
    )
    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    mock_client.portfolios.get_portfolio_by_name.assert_called_once_with("Test Portfolio")
    mock_client.milestones.get_portfolio_milestones.assert_called_once_with(1)
    mock_client.milestones.get_milestone_progress.assert_called_once_with(10)


def test_milestone_progress_remote_all(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``milestone progress <portfolio>`` with remote backend returns all milestone bars."""
    plugin_pf = MagicMock()
    plugin_pf.id = 2
    mock_client.portfolios.get_portfolio_by_name.return_value = plugin_pf

    ms1 = MagicMock()
    ms1.id = 11
    ms1.name = "Sprint 1"
    ms1.target_date = datetime(2026, 6, 30)
    ms2 = MagicMock()
    ms2.id = 12
    ms2.name = "Sprint 2"
    ms2.target_date = None
    mock_client.milestones.get_portfolio_milestones.return_value = [ms1, ms2]

    prog1 = MagicMock()
    prog1.total = 8
    prog1.completed = 4
    prog1.percent = 50.0
    prog1.is_at_risk = False
    prog1.is_overdue = False

    prog2 = MagicMock()
    prog2.total = 6
    prog2.completed = 6
    prog2.percent = 100.0
    prog2.is_at_risk = False
    prog2.is_overdue = False

    mock_client.milestones.get_milestone_progress.side_effect = [prog1, prog2]

    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "progress", "Test Portfolio"],
    )
    assert result.exit_code == 0
    assert "Sprint 1" in result.output
    assert "Sprint 2" in result.output
    assert mock_client.milestones.get_milestone_progress.call_count == 2


def test_milestone_progress_remote_no_milestones(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``milestone progress`` with remote backend and empty portfolio prints no-milestones."""
    plugin_pf = MagicMock()
    plugin_pf.id = 3
    mock_client.portfolios.get_portfolio_by_name.return_value = plugin_pf
    mock_client.milestones.get_portfolio_milestones.return_value = []

    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "progress", "Test Portfolio"],
    )
    assert result.exit_code == 0
    assert "No milestones" in result.output


def test_milestone_progress_remote_milestone_not_found(
    runner: CliRunner,
    mock_remote_config: KanboardConfig,
    mock_client: MagicMock,
) -> None:
    """``milestone progress`` with remote backend shows error when named milestone absent."""
    plugin_pf = MagicMock()
    plugin_pf.id = 4
    mock_client.portfolios.get_portfolio_by_name.return_value = plugin_pf
    mock_client.milestones.get_portfolio_milestones.return_value = []

    result = _invoke_remote(
        runner,
        mock_remote_config,
        mock_client,
        ["milestone", "progress", "Test Portfolio", "Ghost Milestone"],
    )
    assert result.exit_code != 0
    assert "Ghost Milestone" in result.output
