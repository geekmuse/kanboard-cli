"""CLI tests for ``kanboard task-link`` subcommands (US-017, US-012)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Project, Task, TaskLink
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_TL_DATA: dict = {
    "id": "7",
    "task_id": "10",
    "opposite_task_id": "20",
    "link_id": "1",
}

_SAMPLE_TL_DATA_2: dict = {
    "id": "8",
    "task_id": "10",
    "opposite_task_id": "30",
    "link_id": "2",
}


def _make_task_link(data: dict | None = None) -> TaskLink:
    """Build a TaskLink from sample data."""
    return TaskLink.from_api(data or _SAMPLE_TL_DATA)


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
    """Return a MagicMock client with a task_links resource."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
    input: str | None = None,
) -> object:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args, input=input)


# ===========================================================================
# task-link list
# ===========================================================================


def test_task_link_list_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list`` renders task links in table format."""
    mock_client.task_links.get_all_task_links.return_value = [_make_task_link()]
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "10"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.get_all_task_links.assert_called_once_with(10)


def test_task_link_list_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --output json`` renders task links as a JSON array."""
    mock_client.task_links.get_all_task_links.return_value = [
        _make_task_link(),
        _make_task_link(_SAMPLE_TL_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-link", "list", "10"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == 7
    assert data[0]["task_id"] == 10


def test_task_link_list_csv(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --output csv`` renders task links as CSV with a header row."""
    mock_client.task_links.get_all_task_links.return_value = [_make_task_link()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "csv", "task-link", "list", "10"]
    )
    assert result.exit_code == 0
    assert "id" in result.output  # header row
    assert "7" in result.output


def test_task_link_list_quiet(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --output quiet`` prints only task link IDs."""
    mock_client.task_links.get_all_task_links.return_value = [
        _make_task_link(),
        _make_task_link(_SAMPLE_TL_DATA_2),
    ]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "quiet", "task-link", "list", "10"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "7" in lines
    assert "8" in lines


def test_task_link_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list`` with no links exits 0 cleanly."""
    mock_client.task_links.get_all_task_links.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "10"])
    assert result.exit_code == 0


def test_task_link_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on task-link list exits non-zero."""
    mock_client.task_links.get_all_task_links.side_effect = KanboardAPIError(
        "getAllTaskLinks failed", method="getAllTaskLinks", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "10"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_list_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link get
# ===========================================================================


def test_task_link_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get`` shows task link details in table format."""
    mock_client.task_links.get_task_link_by_id.return_value = _make_task_link()
    result = _invoke(runner, mock_config, mock_client, ["task-link", "get", "7"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.get_task_link_by_id.assert_called_once_with(7)


def test_task_link_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get --output json`` renders the task link as a JSON object."""
    mock_client.task_links.get_task_link_by_id.return_value = _make_task_link()
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task-link", "get", "7"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == 7
    assert data["task_id"] == 10
    assert data["opposite_task_id"] == 20
    assert data["link_id"] == 1


def test_task_link_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get`` with unknown ID exits non-zero with an error message."""
    mock_client.task_links.get_task_link_by_id.side_effect = KanboardNotFoundError(
        "TaskLink 99 not found", resource="TaskLink", identifier=99
    )
    result = _invoke(runner, mock_config, mock_client, ["task-link", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_get_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link get --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "get", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link create
# ===========================================================================


def test_task_link_create_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` creates a task link and prints the new ID."""
    mock_client.task_links.create_task_link.return_value = 7
    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.create_task_link.assert_called_once_with(10, 20, 1)


def test_task_link_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.task_links.create_task_link.side_effect = KanboardAPIError(
        "createTaskLink failed", method="createTaskLink", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_create_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link update
# ===========================================================================


def test_task_link_update_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link update`` updates a task link and prints a success message."""
    mock_client.task_links.update_task_link.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task-link", "update", "7", "10", "30", "2"]
    )
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.update_task_link.assert_called_once_with(7, 10, 30, 2)


def test_task_link_update_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link update`` exits non-zero when SDK raises KanboardAPIError."""
    mock_client.task_links.update_task_link.side_effect = KanboardAPIError(
        "updateTaskLink failed", method="updateTaskLink", code=None
    )
    result = _invoke(
        runner, mock_config, mock_client, ["task-link", "update", "7", "10", "30", "2"]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_task_link_update_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link update --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "update", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# task-link remove
# ===========================================================================


def test_task_link_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove --yes`` removes without prompting."""
    mock_client.task_links.remove_task_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "7", "--yes"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.task_links.remove_task_link.assert_called_once_with(7)


def test_task_link_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove`` without --yes and answering 'n' aborts."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "7"], input="n\n")
    assert result.exit_code != 0
    mock_client.task_links.remove_task_link.assert_not_called()


def test_task_link_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove`` without --yes and answering 'y' proceeds."""
    mock_client.task_links.remove_task_link.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "7"], input="y\n")
    assert result.exit_code == 0
    mock_client.task_links.remove_task_link.assert_called_once_with(7)


def test_task_link_remove_help(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link remove --help`` exits cleanly."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "remove", "--help"])
    assert result.exit_code == 0


# ===========================================================================
# Helpers for US-012 tests
# ===========================================================================


def _make_task(task_id: int = 10, project_id: int = 1, title: str = "Task Title") -> Task:
    """Build a Task with the given id and project_id."""
    return Task.from_api(
        {
            "id": str(task_id),
            "title": title,
            "project_id": str(project_id),
            "description": "",
            "date_creation": None,
            "date_modification": None,
            "date_due": None,
            "date_completed": None,
            "date_moved": None,
            "color_id": "blue",
            "column_id": "3",
            "swimlane_id": "0",
            "owner_id": "0",
            "creator_id": "1",
            "category_id": "0",
            "is_active": "1",
            "priority": "0",
            "score": "0",
            "position": "1",
            "reference": "",
            "tags": [],
            "url": "",
        }
    )


def _make_project(project_id: int = 1, name: str = "Alpha Project") -> Project:
    """Build a Project with the given id and name."""
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


# ===========================================================================
# US-012: task-link create — cross-project info message
# ===========================================================================


def test_task_link_create_cross_project_message(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` prints cross-project info when tasks are in different projects."""
    mock_client.task_links.create_task_link.return_value = 7

    task_alpha = _make_task(task_id=10, project_id=1)
    task_beta = _make_task(task_id=20, project_id=2)
    proj_alpha = _make_project(project_id=1, name="Alpha Project")
    proj_beta = _make_project(project_id=2, name="Beta Project")

    def _get_task(task_id: int) -> Task:
        return task_alpha if task_id == 10 else task_beta

    mock_client.tasks.get_task.side_effect = _get_task
    mock_client.projects.get_project_by_id.side_effect = lambda pid: (
        proj_alpha if pid == 1 else proj_beta
    )

    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code == 0
    assert "Task link #7 created" in result.output
    assert "Cross-project dependency" in result.output
    assert "Task #10" in result.output
    assert "Alpha Project" in result.output
    assert "Task #20" in result.output
    assert "Beta Project" in result.output
    assert "blocked by" in result.output


def test_task_link_create_same_project_no_message(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` prints no cross-project message when both tasks share a project."""
    mock_client.task_links.create_task_link.return_value = 7

    task_a = _make_task(task_id=10, project_id=1)
    task_b = _make_task(task_id=20, project_id=1)  # same project

    mock_client.tasks.get_task.side_effect = lambda tid: task_a if tid == 10 else task_b

    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code == 0
    assert "Task link #7 created" in result.output
    assert "Cross-project dependency" not in result.output


def test_task_link_create_enrichment_error_ignored(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link create`` succeeds even when enrichment fetch raises an exception."""
    mock_client.task_links.create_task_link.return_value = 7
    mock_client.tasks.get_task.side_effect = Exception("network error")

    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code == 0
    assert "Task link #7 created" in result.output
    # Enrichment failure must not propagate
    assert "Error" not in result.output


def test_task_link_create_no_enrichment_on_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """On create failure, no task fetches are made (no latency on error path)."""
    mock_client.task_links.create_task_link.side_effect = KanboardAPIError(
        "createTaskLink failed", method="createTaskLink", code=None
    )

    result = _invoke(runner, mock_config, mock_client, ["task-link", "create", "10", "20", "1"])
    assert result.exit_code != 0
    mock_client.tasks.get_task.assert_not_called()


# ===========================================================================
# US-012: task-link list --with-project
# ===========================================================================


def test_task_link_list_with_project_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --with-project`` adds opposite_project column to table output."""
    mock_client.task_links.get_all_task_links.return_value = [_make_task_link()]

    opp_task = _make_task(task_id=20, project_id=2)
    proj_beta = _make_project(project_id=2, name="Beta Project")

    mock_client.tasks.get_task.return_value = opp_task
    mock_client.projects.get_project_by_id.return_value = proj_beta

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task-link", "list", "10", "--with-project"],
    )
    assert result.exit_code == 0
    assert "Beta Project" in result.output
    mock_client.tasks.get_task.assert_called_once_with(20)
    mock_client.projects.get_project_by_id.assert_called_once_with(2)


def test_task_link_list_with_project_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --with-project`` includes opposite_project in JSON output."""
    mock_client.task_links.get_all_task_links.return_value = [_make_task_link()]

    opp_task = _make_task(task_id=20, project_id=2)
    proj_beta = _make_project(project_id=2, name="Beta Project")

    mock_client.tasks.get_task.return_value = opp_task
    mock_client.projects.get_project_by_id.return_value = proj_beta

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "task-link", "list", "10", "--with-project"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["opposite_project"] == "Beta Project"


def test_task_link_list_with_project_caches_project_lookup(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --with-project`` caches project lookups (one call per unique project)."""
    # Two links, both pointing to tasks in the same project (id=2)
    link1 = _make_task_link(_SAMPLE_TL_DATA)
    link2 = _make_task_link(_SAMPLE_TL_DATA_2)
    mock_client.task_links.get_all_task_links.return_value = [link1, link2]

    # opposite tasks: opposite_task_id=20 (proj 2), opposite_task_id=30 (proj 2)
    def _get_task(tid: int) -> Task:
        return _make_task(task_id=tid, project_id=2)

    proj_beta = _make_project(project_id=2, name="Beta Project")
    mock_client.tasks.get_task.side_effect = _get_task
    mock_client.projects.get_project_by_id.return_value = proj_beta

    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task-link", "list", "10", "--with-project"],
    )
    assert result.exit_code == 0
    # get_task called twice (once per link), but get_project_by_id only once (cached)
    assert mock_client.tasks.get_task.call_count == 2
    mock_client.projects.get_project_by_id.assert_called_once_with(2)


def test_task_link_list_with_project_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --with-project`` with no links exits 0 cleanly."""
    mock_client.task_links.get_all_task_links.return_value = []
    result = _invoke(
        runner, mock_config, mock_client, ["task-link", "list", "10", "--with-project"]
    )
    assert result.exit_code == 0
    mock_client.tasks.get_task.assert_not_called()


def test_task_link_list_help_mentions_with_project(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task-link list --help`` documents the --with-project flag."""
    result = _invoke(runner, mock_config, mock_client, ["task-link", "list", "--help"])
    assert result.exit_code == 0
    assert "--with-project" in result.output
