"""CLI tests for ``kanboard task`` subcommands (US-011)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kanboard.config import KanboardConfig
from kanboard.exceptions import KanboardAPIError, KanboardNotFoundError
from kanboard.models import Task
from kanboard_cli.main import cli

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_SAMPLE_TASK_DATA: dict = {
    "id": "1",
    "title": "Fix login bug",
    "description": "Login broken on mobile",
    "date_creation": "1711000000",
    "date_modification": "1711100000",
    "date_due": "1711200000",
    "date_completed": None,
    "date_moved": None,
    "color_id": "red",
    "project_id": "1",
    "column_id": "2",
    "swimlane_id": "0",
    "owner_id": "3",
    "creator_id": "1",
    "category_id": "0",
    "is_active": "1",
    "priority": "0",
    "score": "5",
    "position": "1",
    "reference": "REF-001",
    "tags": ["backend"],
    "url": "http://kanboard.test/task/1",
}

_SAMPLE_TASK_DATA_2: dict = {
    **_SAMPLE_TASK_DATA,
    "id": "2",
    "title": "Add dark mode",
    "reference": "",
    "tags": [],
}


def _make_task(data: dict | None = None) -> Task:
    """Build a Task from sample data."""
    return Task.from_api(data or _SAMPLE_TASK_DATA)


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
    """Return a MagicMock client with a tasks resource."""
    client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _invoke(
    runner: CliRunner,
    mock_config: KanboardConfig,
    mock_client: MagicMock,
    args: list[str],
) -> object:
    """Invoke the CLI with patched config + client."""
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        return runner.invoke(cli, args)


# ===========================================================================
# task list
# ===========================================================================


def test_task_list_table_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task list`` renders tasks in table format by default."""
    mock_client.tasks.get_all_tasks.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["task", "list", "1"])
    assert result.exit_code == 0
    # Column headers are always visible in the table output regardless of terminal width.
    assert "id" in result.output
    assert "title" in result.output
    mock_client.tasks.get_all_tasks.assert_called_once_with(1, status_id=1)


def test_task_list_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task list`` renders tasks as a JSON array with data values."""
    mock_client.tasks.get_all_tasks.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "list", "1"])
    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Fix login bug"


def test_task_list_csv_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task list`` renders tasks as CSV with data values."""
    mock_client.tasks.get_all_tasks.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "csv", "task", "list", "1"])
    assert result.exit_code == 0
    assert "Fix login bug" in result.output
    assert "id" in result.output  # header row
    assert "title" in result.output  # header row


def test_task_list_quiet_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task list --output quiet`` prints only IDs."""
    mock_client.tasks.get_all_tasks.return_value = [_make_task(), _make_task(_SAMPLE_TASK_DATA_2)]
    result = _invoke(runner, mock_config, mock_client, ["--output", "quiet", "task", "list", "1"])
    assert result.exit_code == 0
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert "1" in lines
    assert "2" in lines


def test_task_list_inactive_status(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``--status inactive`` passes status_id=0 to the SDK."""
    mock_client.tasks.get_all_tasks.return_value = []
    result = _invoke(
        runner, mock_config, mock_client, ["task", "list", "1", "--status", "inactive"]
    )
    assert result.exit_code == 0
    mock_client.tasks.get_all_tasks.assert_called_once_with(1, status_id=0)


def test_task_list_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task list`` with no results exits 0 cleanly."""
    mock_client.tasks.get_all_tasks.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["task", "list", "1"])
    assert result.exit_code == 0


def test_task_list_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error exits non-zero with a message."""
    mock_client.tasks.get_all_tasks.side_effect = KanboardAPIError(
        "Server error", method="getAllTasks", code=-1
    )
    result = _invoke(runner, mock_config, mock_client, ["task", "list", "1"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# task get
# ===========================================================================


def test_task_get_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task get`` exits 0 in table format and calls get_task."""
    mock_client.tasks.get_task.return_value = _make_task()
    result = _invoke(runner, mock_config, mock_client, ["task", "get", "1"])
    assert result.exit_code == 0
    mock_client.tasks.get_task.assert_called_once_with(1)


def test_task_get_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task get`` with --output json renders a single JSON object with all fields."""
    mock_client.tasks.get_task.return_value = _make_task()
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "get", "1"])
    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["title"] == "Fix login bug"
    assert data["id"] == 1


def test_task_get_not_found(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task get`` with unknown ID exits non-zero with an error."""
    mock_client.tasks.get_task.side_effect = KanboardNotFoundError(
        "Task not found",
        method="getTask",
        code=None,
        resource="Task",
        identifier="99",
    )
    result = _invoke(runner, mock_config, mock_client, ["task", "get", "99"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# task create
# ===========================================================================


def test_task_create_minimal(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task create`` with only required args creates a task and prints its ID."""
    mock_client.tasks.create_task.return_value = 7
    result = _invoke(runner, mock_config, mock_client, ["task", "create", "1", "Fix login bug"])
    assert result.exit_code == 0
    assert "7" in result.output
    mock_client.tasks.create_task.assert_called_once_with("Fix login bug", 1)


def test_task_create_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task create`` passes all supplied options to the SDK."""
    mock_client.tasks.create_task.return_value = 8
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "task",
            "create",
            "1",
            "Deploy feature",
            "--owner-id",
            "2",
            "--column-id",
            "3",
            "--swimlane-id",
            "1",
            "--due",
            "2025-12-31",
            "--description",
            "Deploy it",
            "--color",
            "blue",
            "--category-id",
            "4",
            "--score",
            "5",
            "--priority",
            "2",
            "--reference",
            "JIRA-42",
            "--tag",
            "backend",
            "--tag",
            "api",
        ],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.tasks.create_task.call_args
    assert kwargs["owner_id"] == 2
    assert kwargs["column_id"] == 3
    assert kwargs["swimlane_id"] == 1
    assert kwargs["date_due"] == "2025-12-31"
    assert kwargs["description"] == "Deploy it"
    assert kwargs["color_id"] == "blue"
    assert kwargs["category_id"] == 4
    assert kwargs["score"] == 5
    assert kwargs["priority"] == 2
    assert kwargs["reference"] == "JIRA-42"
    assert kwargs["tags"] == ["backend", "api"]


def test_task_create_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task create --output json`` emits JSON success object."""
    mock_client.tasks.create_task.return_value = 9
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task", "create", "1", "My task"]
    )
    assert result.exit_code == 0
    assert '"status"' in result.output
    assert '"ok"' in result.output


def test_task_create_api_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """SDK error on create exits non-zero."""
    mock_client.tasks.create_task.side_effect = KanboardAPIError(
        "createTask failed", method="createTask", code=None
    )
    result = _invoke(runner, mock_config, mock_client, ["task", "create", "1", "Bad task"])
    assert result.exit_code != 0
    assert "Error" in result.output


# ===========================================================================
# task update
# ===========================================================================


def test_task_update_with_title(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task update --title`` updates the title."""
    mock_client.tasks.update_task.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["task", "update", "1", "--title", "New title"]
    )
    assert result.exit_code == 0
    assert "updated" in result.output
    mock_client.tasks.update_task.assert_called_once_with(1, title="New title")


def test_task_update_multiple_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task update`` passes only supplied options to the SDK."""
    mock_client.tasks.update_task.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task", "update", "1", "--priority", "3", "--due", "2025-06-01", "--tag", "urgent"],
    )
    assert result.exit_code == 0
    _, kwargs = mock_client.tasks.update_task.call_args
    assert kwargs["priority"] == 3
    assert kwargs["date_due"] == "2025-06-01"
    assert kwargs["tags"] == ["urgent"]
    # options NOT provided must NOT be passed
    assert "title" not in kwargs
    assert "description" not in kwargs


def test_task_update_no_options_is_error(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task update`` with no options exits non-zero with a usage error."""
    result = _invoke(runner, mock_config, mock_client, ["task", "update", "1"])
    assert result.exit_code != 0
    # SDK must NOT be called
    mock_client.tasks.update_task.assert_not_called()


def test_task_update_json_success(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task update`` with --output json emits JSON success."""
    mock_client.tasks.update_task.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["--output", "json", "task", "update", "1", "--score", "8"],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# task close / open
# ===========================================================================


def test_task_close(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``task close`` calls close_task and prints confirmation."""
    mock_client.tasks.close_task.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task", "close", "5"])
    assert result.exit_code == 0
    assert "closed" in result.output
    mock_client.tasks.close_task.assert_called_once_with(5)


def test_task_open(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``task open`` calls open_task and prints confirmation."""
    mock_client.tasks.open_task.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task", "open", "5"])
    assert result.exit_code == 0
    assert "reopened" in result.output
    mock_client.tasks.open_task.assert_called_once_with(5)


def test_task_close_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task close`` with --output json emits JSON success."""
    mock_client.tasks.close_task.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "close", "5"])
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# task remove
# ===========================================================================


def test_task_remove_with_yes(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task remove --yes`` deletes without prompting."""
    mock_client.tasks.remove_task.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task", "remove", "3", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.tasks.remove_task.assert_called_once_with(3)


def test_task_remove_without_yes_aborts(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task remove`` without --yes and answering 'n' aborts and does not call SDK."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task", "remove", "3"],
    )
    # Click's confirm defaults to 'n' in non-interactive CliRunner — exits non-zero
    assert result.exit_code != 0
    mock_client.tasks.remove_task.assert_not_called()


def test_task_remove_interactive_confirm(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task remove`` with interactive 'y' answer removes the task."""
    mock_client.tasks.remove_task.return_value = True
    with (
        patch("kanboard_cli.main.KanboardConfig.resolve", return_value=mock_config),
        patch("kanboard_cli.main.KanboardClient", return_value=mock_client),
    ):
        result = runner.invoke(cli, ["task", "remove", "3"], input="y\n")
    assert result.exit_code == 0
    assert "removed" in result.output
    mock_client.tasks.remove_task.assert_called_once_with(3)


def test_task_remove_json_output(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task remove --yes --output json`` emits JSON success."""
    mock_client.tasks.remove_task.return_value = True
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task", "remove", "3", "--yes"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# task search
# ===========================================================================


def test_task_search_table(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task search`` exits 0 in table format and calls search_tasks."""
    mock_client.tasks.search_tasks.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["task", "search", "1", "login"])
    assert result.exit_code == 0
    assert "title" in result.output
    mock_client.tasks.search_tasks.assert_called_once_with(1, "login")


def test_task_search_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task search --output json`` renders a JSON array with data values."""
    mock_client.tasks.search_tasks.return_value = [_make_task()]
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task", "search", "1", "login"]
    )
    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Fix login bug"


def test_task_search_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task search`` with no matches exits 0."""
    mock_client.tasks.search_tasks.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["task", "search", "1", "noresults"])
    assert result.exit_code == 0


# ===========================================================================
# task move
# ===========================================================================


def test_task_move(runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock) -> None:
    """``task move`` calls move_task_position with all required options."""
    mock_client.tasks.move_task_position.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "task",
            "move",
            "10",
            "--project-id",
            "1",
            "--column-id",
            "3",
            "--position",
            "2",
            "--swimlane-id",
            "0",
        ],
    )
    assert result.exit_code == 0
    assert "moved" in result.output
    mock_client.tasks.move_task_position.assert_called_once_with(1, 10, 3, 2, 0)


def test_task_move_missing_required_option(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task move`` without required options exits non-zero."""
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        ["task", "move", "10", "--column-id", "3"],  # missing --project-id etc.
    )
    assert result.exit_code != 0


def test_task_move_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task move --output json`` emits JSON success."""
    mock_client.tasks.move_task_position.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "--output",
            "json",
            "task",
            "move",
            "10",
            "--project-id",
            "1",
            "--column-id",
            "3",
            "--position",
            "1",
            "--swimlane-id",
            "0",
        ],
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# task move-to-project
# ===========================================================================


def test_task_move_to_project_minimal(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task move-to-project`` with only required args calls SDK correctly."""
    mock_client.tasks.move_task_to_project.return_value = True
    result = _invoke(runner, mock_config, mock_client, ["task", "move-to-project", "5", "2"])
    assert result.exit_code == 0
    assert "moved" in result.output
    mock_client.tasks.move_task_to_project.assert_called_once_with(5, 2)


def test_task_move_to_project_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task move-to-project`` passes optional placement args to SDK."""
    mock_client.tasks.move_task_to_project.return_value = True
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "task",
            "move-to-project",
            "5",
            "2",
            "--swimlane-id",
            "1",
            "--column-id",
            "4",
            "--category-id",
            "2",
            "--owner-id",
            "3",
        ],
    )
    assert result.exit_code == 0
    mock_client.tasks.move_task_to_project.assert_called_once_with(
        5, 2, swimlane_id=1, column_id=4, category_id=2, owner_id=3
    )


# ===========================================================================
# task duplicate
# ===========================================================================


def test_task_duplicate_minimal(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task duplicate`` with required args calls SDK and shows new ID."""
    mock_client.tasks.duplicate_task_to_project.return_value = 11
    result = _invoke(runner, mock_config, mock_client, ["task", "duplicate", "5", "3"])
    assert result.exit_code == 0
    assert "11" in result.output
    mock_client.tasks.duplicate_task_to_project.assert_called_once_with(5, 3)


def test_task_duplicate_with_options(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task duplicate`` passes optional placement to SDK."""
    mock_client.tasks.duplicate_task_to_project.return_value = 12
    result = _invoke(
        runner,
        mock_config,
        mock_client,
        [
            "task",
            "duplicate",
            "5",
            "3",
            "--swimlane-id",
            "2",
            "--column-id",
            "5",
        ],
    )
    assert result.exit_code == 0
    mock_client.tasks.duplicate_task_to_project.assert_called_once_with(
        5, 3, swimlane_id=2, column_id=5
    )


def test_task_duplicate_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task duplicate --output json`` emits JSON success."""
    mock_client.tasks.duplicate_task_to_project.return_value = 13
    result = _invoke(
        runner, mock_config, mock_client, ["--output", "json", "task", "duplicate", "5", "3"]
    )
    assert result.exit_code == 0
    assert '"ok"' in result.output


# ===========================================================================
# task overdue
# ===========================================================================


def test_task_overdue_all_projects(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task overdue`` without --project-id fetches across all projects."""
    mock_client.tasks.get_overdue_tasks.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["task", "overdue"])
    assert result.exit_code == 0
    assert "title" in result.output  # column header visible
    mock_client.tasks.get_overdue_tasks.assert_called_once_with()
    mock_client.tasks.get_overdue_tasks_by_project.assert_not_called()


def test_task_overdue_by_project(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task overdue --project-id 1`` fetches overdue tasks for project 1."""
    mock_client.tasks.get_overdue_tasks_by_project.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["task", "overdue", "--project-id", "1"])
    assert result.exit_code == 0
    assert "title" in result.output  # column header visible
    mock_client.tasks.get_overdue_tasks_by_project.assert_called_once_with(1)
    mock_client.tasks.get_overdue_tasks.assert_not_called()


def test_task_overdue_json(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task overdue --output json`` renders a JSON array with data values."""
    mock_client.tasks.get_overdue_tasks.return_value = [_make_task()]
    result = _invoke(runner, mock_config, mock_client, ["--output", "json", "task", "overdue"])
    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Fix login bug"


def test_task_overdue_empty(
    runner: CliRunner, mock_config: KanboardConfig, mock_client: MagicMock
) -> None:
    """``task overdue`` with no results exits 0."""
    mock_client.tasks.get_overdue_tasks.return_value = []
    result = _invoke(runner, mock_config, mock_client, ["task", "overdue"])
    assert result.exit_code == 0


# ===========================================================================
# --help smoke tests
# ===========================================================================


@pytest.mark.parametrize(
    "subcommand",
    [
        "list",
        "get",
        "create",
        "update",
        "close",
        "open",
        "remove",
        "search",
        "move",
        "move-to-project",
        "duplicate",
        "overdue",
    ],
)
def test_task_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Every task subcommand must respond to --help with exit 0."""
    from kanboard.exceptions import KanboardConfigError

    with patch(
        "kanboard_cli.main.KanboardConfig.resolve",
        side_effect=KanboardConfigError("x", field="url"),
    ):
        result = runner.invoke(cli, ["task", subcommand, "--help"])
    assert result.exit_code == 0, (
        f"'task {subcommand} --help' exited {result.exit_code}: {result.output}"
    )
