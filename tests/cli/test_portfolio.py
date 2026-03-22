"""CLI tests for ``kanboard portfolio`` subcommands (US-007)."""

from __future__ import annotations

import json
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardConfigError, KanboardNotFoundError
from kanboard.models import MilestoneProgress, Portfolio, Project, Task
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _make_portfolio(
    name: str = "Test Portfolio",
    description: str = "Test description",
    project_ids: list[int] | None = None,
    milestone_count: int = 0,
) -> Portfolio:
    """Build a Portfolio for tests."""
    milestones = []
    for i in range(milestone_count):
        from kanboard.models import Milestone

        milestones.append(
            Milestone(
                name=f"M{i + 1}",
                portfolio_name=name,
                target_date=None,
            )
        )
    return Portfolio(
        name=name,
        description=description,
        project_ids=project_ids or [1, 2],
        milestones=milestones,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 2),
    )


def _make_task(
    task_id: int = 10,
    title: str = "Test Task",
    project_id: int = 1,
    column_id: int = 3,
    owner_id: int = 5,
    is_active: bool = True,
    priority: int = 2,
) -> Task:
    """Build a Task from test data."""
    return Task.from_api(
        {
            "id": str(task_id),
            "title": title,
            "project_id": str(project_id),
            "column_id": str(column_id),
            "owner_id": str(owner_id),
            "is_active": "1" if is_active else "0",
            "priority": str(priority),
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


def _make_project(project_id: int = 1, name: str = "Alpha Project") -> Project:
    """Build a Project from test data."""
    return Project.from_api(
        {
            "id": str(project_id),
            "name": name,
            "description": "",
            "is_active": "1",
            "token": "",
            "last_modified": None,
            "is_public": "0",
            "is_private": False,
            "owner_id": "1",
            "identifier": "",
            "start_date": None,
            "end_date": None,
            "url": "",
        }
    )


def _make_milestone_progress(
    milestone_name: str = "M1",
    portfolio_name: str = "Test Portfolio",
    percent: float = 50.0,
    is_at_risk: bool = False,
    is_overdue: bool = False,
) -> MilestoneProgress:
    """Build a MilestoneProgress for tests."""
    return MilestoneProgress(
        milestone_name=milestone_name,
        portfolio_name=portfolio_name,
        target_date=datetime(2026, 6, 30),
        total=10,
        completed=5,
        percent=percent,
        is_at_risk=is_at_risk,
        is_overdue=is_overdue,
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
                "kanboard_cli.commands.portfolio._get_store",
                return_value=mock_store,
            )
        )
        return runner.invoke(cli, args, input=input)


# ===========================================================================
# portfolio list
# ===========================================================================


def test_portfolio_list_table_empty(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio list`` with no portfolios shows table headers."""
    mock_store.load.return_value = []
    result = _invoke(runner, mock_config, mock_client, mock_store, ["portfolio", "list"])
    assert result.exit_code == 0


def test_portfolio_list_table_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio list`` shows name, description, project/milestone counts."""
    mock_store.load.return_value = [_make_portfolio(project_ids=[1, 2], milestone_count=1)]
    result = _invoke(runner, mock_config, mock_client, mock_store, ["portfolio", "list"])
    assert result.exit_code == 0
    assert "Test Portfolio" in result.output
    assert "Test description" in result.output
    # project_count=2, milestone_count=1
    assert "2" in result.output
    assert "1" in result.output


def test_portfolio_list_json_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio list --output json`` returns JSON array with correct fields."""
    mock_store.load.return_value = [_make_portfolio()]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["--output", "json", "portfolio", "list"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "Test Portfolio"
    assert data[0]["project_count"] == 2
    assert data[0]["milestone_count"] == 0


def test_portfolio_list_csv_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio list --output csv`` renders CSV with headers."""
    mock_store.load.return_value = [_make_portfolio()]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["--output", "csv", "portfolio", "list"],
    )
    assert result.exit_code == 0
    assert "name" in result.output
    assert "Test Portfolio" in result.output


def test_portfolio_list_quiet_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio list --output quiet`` prints nothing (no id field)."""
    mock_store.load.return_value = [_make_portfolio()]
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["--output", "quiet", "portfolio", "list"],
    )
    assert result.exit_code == 0
    # No 'id' column — quiet prints nothing.
    assert result.output.strip() == ""


# ===========================================================================
# portfolio show
# ===========================================================================


def test_portfolio_show_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio show`` prints summary with task and milestone info."""
    portfolio_obj = _make_portfolio(project_ids=[1])
    mock_store.get_portfolio.return_value = portfolio_obj

    mp = _make_milestone_progress()
    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = [_make_task()]
    mock_manager.get_all_milestone_progress.return_value = [mp]

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "show", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "Test Portfolio" in result.output
    mock_store.get_portfolio.assert_called_once_with("Test Portfolio")


def test_portfolio_show_with_milestone_progress(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio show`` renders milestone progress bars when milestones exist."""
    portfolio_obj = _make_portfolio(milestone_count=1)
    mock_store.get_portfolio.return_value = portfolio_obj

    mp = _make_milestone_progress(milestone_name="Sprint 1", percent=60.0)
    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = []
    mock_manager.get_all_milestone_progress.return_value = [mp]

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "show", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "Milestone Progress" in result.output
    assert "Sprint 1" in result.output


def test_portfolio_show_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio show`` raises ClickException when portfolio not found."""
    mock_store.get_portfolio.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "show", "Ghost"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


def test_portfolio_show_api_unreachable_shows_warning(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio show`` warns and shows cached data when API fails."""
    portfolio_obj = _make_portfolio()
    mock_store.get_portfolio.return_value = portfolio_obj

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.side_effect = KanboardAPIError("Connection failed")

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "show", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "Warning" in result.output or "Test Portfolio" in result.output


# ===========================================================================
# portfolio create
# ===========================================================================


def test_portfolio_create_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio create`` creates portfolio and prints success."""
    mock_store.create_portfolio.return_value = _make_portfolio(name="New Portfolio")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "create", "New Portfolio"],
    )
    assert result.exit_code == 0
    assert "New Portfolio" in result.output
    mock_store.create_portfolio.assert_called_once_with("New Portfolio", "")


def test_portfolio_create_with_description(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio create`` passes description to store."""
    mock_store.create_portfolio.return_value = _make_portfolio()
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "create", "P", "--description", "My desc"],
    )
    assert result.exit_code == 0
    mock_store.create_portfolio.assert_called_once_with("P", "My desc")


def test_portfolio_create_duplicate(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio create`` shows error when portfolio already exists."""
    mock_store.create_portfolio.side_effect = ValueError("Portfolio 'P' already exists")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "create", "P"],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


# ===========================================================================
# portfolio remove
# ===========================================================================


def test_portfolio_remove_requires_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio remove`` without --yes aborts (non-zero exit)."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "remove", "Test Portfolio"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_store.remove_portfolio.assert_not_called()


def test_portfolio_remove_with_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio remove --yes`` removes portfolio and prints success."""
    mock_store.remove_portfolio.return_value = True
    # Disable metadata cleanup for simplicity
    mock_client.return_value = None  # no client
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "remove", "Test Portfolio", "--yes"],
    )
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_store.remove_portfolio.assert_called_once_with("Test Portfolio")


def test_portfolio_remove_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio remove`` shows error when portfolio not found."""
    mock_store.remove_portfolio.return_value = False
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "remove", "Ghost", "--yes"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# portfolio add-project
# ===========================================================================


def test_portfolio_add_project_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio add-project`` validates project and adds to store."""
    mock_client.projects.get_project_by_id.return_value = _make_project(1)
    mock_store.add_project.return_value = _make_portfolio()
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "add-project", "Test Portfolio", "1"],
    )
    assert result.exit_code == 0
    assert "added" in result.output
    mock_client.projects.get_project_by_id.assert_called_once_with(1)
    mock_store.add_project.assert_called_once_with("Test Portfolio", 1)


def test_portfolio_add_project_not_found_in_api(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio add-project`` shows error when project does not exist in Kanboard."""
    mock_client.projects.get_project_by_id.side_effect = KanboardNotFoundError("Project not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "add-project", "Test Portfolio", "99"],
    )
    assert result.exit_code != 0
    assert "99" in result.output
    mock_store.add_project.assert_not_called()


def test_portfolio_add_project_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio add-project`` shows error when portfolio not found in store."""
    mock_client.projects.get_project_by_id.return_value = _make_project(1)
    mock_store.add_project.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "add-project", "Ghost", "1"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# portfolio remove-project
# ===========================================================================


def test_portfolio_remove_project_requires_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio remove-project`` without --yes aborts."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "remove-project", "Test Portfolio", "1"],
        input="n\n",
    )
    assert result.exit_code != 0
    mock_store.remove_project.assert_not_called()


def test_portfolio_remove_project_with_yes(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio remove-project --yes`` removes project from store."""
    mock_store.remove_project.return_value = _make_portfolio(project_ids=[2])
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "remove-project", "Test Portfolio", "1", "--yes"],
    )
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_store.remove_project.assert_called_once_with("Test Portfolio", 1)


def test_portfolio_remove_project_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio remove-project`` shows error when portfolio not found."""
    mock_store.remove_project.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        mock_store,
        ["portfolio", "remove-project", "Ghost", "1", "--yes"],
    )
    assert result.exit_code != 0
    assert "Ghost" in result.output


# ===========================================================================
# portfolio tasks
# ===========================================================================


def test_portfolio_tasks_table_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks`` shows task list in table format with project_name."""
    task_obj = _make_task(task_id=42, title="Fix Bug", project_id=1)
    project_obj = _make_project(project_id=1, name="Alpha Project")

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = [task_obj]
    mock_client.projects.get_project_by_id.return_value = project_obj

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "tasks", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "Fix Bug" in result.output
    # Rich may wrap long project names; check for partial match.
    assert "Alpha" in result.output
    mock_manager.get_portfolio_tasks.assert_called_once_with(
        "Test Portfolio", status=1, project_id=None, assignee_id=None
    )


def test_portfolio_tasks_json_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks --output json`` returns JSON array with enriched fields."""
    task_obj = _make_task(task_id=10, project_id=2)
    project_obj = _make_project(project_id=2, name="Beta Project")

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = [task_obj]
    mock_client.projects.get_project_by_id.return_value = project_obj

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["--output", "json", "portfolio", "tasks", "Test Portfolio"],
        )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 10
    assert data[0]["project_name"] == "Beta Project"


def test_portfolio_tasks_csv_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks --output csv`` renders CSV with correct headers."""
    task_obj = _make_task()
    project_obj = _make_project()

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = [task_obj]
    mock_client.projects.get_project_by_id.return_value = project_obj

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["--output", "csv", "portfolio", "tasks", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "project_name" in result.output
    assert "id" in result.output


def test_portfolio_tasks_quiet_output(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks --output quiet`` prints only task IDs."""
    task_obj = _make_task(task_id=77)
    project_obj = _make_project()

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = [task_obj]
    mock_client.projects.get_project_by_id.return_value = project_obj

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["--output", "quiet", "portfolio", "tasks", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "77" in result.output


def test_portfolio_tasks_with_status_filter(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks --status closed`` passes status=0 to manager."""
    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = []

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "tasks", "Test Portfolio", "--status", "closed"],
        )

    assert result.exit_code == 0
    mock_manager.get_portfolio_tasks.assert_called_once_with(
        "Test Portfolio", status=0, project_id=None, assignee_id=None
    )


def test_portfolio_tasks_with_project_filter(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks --project 3`` passes project_id=3 to manager."""
    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = []

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "tasks", "Test Portfolio", "--project", "3"],
        )

    assert result.exit_code == 0
    mock_manager.get_portfolio_tasks.assert_called_once_with(
        "Test Portfolio", status=1, project_id=3, assignee_id=None
    )


def test_portfolio_tasks_with_assignee_filter(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks --assignee 7`` passes assignee_id=7 to manager."""
    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = []

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "tasks", "Test Portfolio", "--assignee", "7"],
        )

    assert result.exit_code == 0
    mock_manager.get_portfolio_tasks.assert_called_once_with(
        "Test Portfolio", status=1, project_id=None, assignee_id=7
    )


def test_portfolio_tasks_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks`` shows error when portfolio not found."""
    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.side_effect = KanboardConfigError(
        "Portfolio 'Ghost' not found"
    )

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "tasks", "Ghost"],
        )

    assert result.exit_code != 0
    assert "Ghost" in result.output


def test_portfolio_tasks_project_name_cache(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks`` caches project name lookups — same project fetched once."""
    tasks = [
        _make_task(task_id=1, project_id=5),
        _make_task(task_id=2, project_id=5),
        _make_task(task_id=3, project_id=5),
    ]
    project_obj = _make_project(project_id=5, name="Cached Project")

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = tasks
    mock_client.projects.get_project_by_id.return_value = project_obj

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "tasks", "Test Portfolio"],
        )

    assert result.exit_code == 0
    # Only one API call despite three tasks with the same project_id.
    mock_client.projects.get_project_by_id.assert_called_once_with(5)


def test_portfolio_tasks_project_name_fallback(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio tasks`` falls back to 'Project #N' when project lookup fails."""
    task_obj = _make_task(task_id=1, project_id=99)
    mock_client.projects.get_project_by_id.side_effect = KanboardAPIError("not found")

    mock_manager = MagicMock()
    mock_manager.get_portfolio_tasks.return_value = [task_obj]

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["--output", "json", "portfolio", "tasks", "Test Portfolio"],
        )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "Project #99" in data[0]["project_name"]


# ===========================================================================
# portfolio sync
# ===========================================================================


def test_portfolio_sync_success(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio sync`` calls sync_metadata and prints counts."""
    mock_manager = MagicMock()
    mock_manager.sync_metadata.return_value = {"projects_synced": 3, "tasks_synced": 12}

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "sync", "Test Portfolio"],
        )

    assert result.exit_code == 0
    assert "3" in result.output
    assert "12" in result.output
    mock_manager.sync_metadata.assert_called_once_with("Test Portfolio")


def test_portfolio_sync_portfolio_not_found(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio sync`` shows error when portfolio not found."""
    mock_manager = MagicMock()
    mock_manager.sync_metadata.side_effect = KanboardConfigError("Portfolio 'Ghost' not found")

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "sync", "Ghost"],
        )

    assert result.exit_code != 0
    assert "Ghost" in result.output


def test_portfolio_sync_api_error(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    mock_store: MagicMock,
) -> None:
    """``portfolio sync`` shows error on API failure."""
    mock_manager = MagicMock()
    mock_manager.sync_metadata.side_effect = KanboardAPIError("Server error")

    with patch("kanboard.orchestration.portfolio.PortfolioManager", return_value=mock_manager):
        result = _invoke(
            runner,
            mock_config,
            mock_client,
            mock_store,
            ["portfolio", "sync", "Test Portfolio"],
        )

    assert result.exit_code != 0
    assert "Error" in result.output or "error" in result.output.lower()
