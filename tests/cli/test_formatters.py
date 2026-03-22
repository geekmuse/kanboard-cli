"""Unit tests for kanboard_cli.formatters."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime

import pytest

from kanboard_cli.formatters import format_output, format_success

# ---------------------------------------------------------------------------
# Minimal test dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _FakeRow:
    """Minimal dataclass used as test fixture data."""

    id: int
    name: str
    active: bool = True
    created: datetime | None = None


# ---------------------------------------------------------------------------
# Normalization (exercised via format_output "json")
# ---------------------------------------------------------------------------


class TestNormalize:
    """Tests for _normalize helper (verified through format_output)."""

    def test_none_input_gives_empty_object(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None input → empty JSON object (no rows, non-list)."""
        format_output(None, "json")
        assert json.loads(capsys.readouterr().out) == {}

    def test_empty_list_gives_empty_array(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Empty list input → empty JSON array."""
        format_output([], "json")
        assert json.loads(capsys.readouterr().out) == []

    def test_single_dataclass_normalised(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Single dataclass converted to dict via dataclasses.asdict."""
        row = _FakeRow(id=1, name="Alpha")
        format_output(row, "json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, dict)
        assert data["id"] == 1
        assert data["name"] == "Alpha"
        assert data["active"] is True

    def test_list_of_dataclasses_normalised(self, capsys: pytest.CaptureFixture[str]) -> None:
        """List of dataclasses → JSON array of dicts."""
        rows = [_FakeRow(id=1, name="A"), _FakeRow(id=2, name="B")]
        format_output(rows, "json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    def test_single_dict_passthrough(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Single plain dict is passed through unchanged."""
        format_output({"id": 5, "name": "task"}, "json")
        data = json.loads(capsys.readouterr().out)
        assert data["id"] == 5
        assert data["name"] == "task"

    def test_list_of_dicts_passthrough(self, capsys: pytest.CaptureFixture[str]) -> None:
        """List of plain dicts is passed through unchanged."""
        format_output([{"id": 1}, {"id": 2}], "json")
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 2

    def test_unknown_type_wrapped(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Non-dict, non-dataclass scalar is wrapped as {'value': str(x)}."""
        format_output(42, "json")
        data = json.loads(capsys.readouterr().out)
        assert data == {"value": "42"}


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------


class TestJsonFormat:
    """Tests for the JSON output renderer."""

    def test_single_non_list_is_object(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A single (non-list) item renders as a JSON object, not array."""
        format_output({"id": 1, "name": "task"}, "json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, dict)

    def test_single_element_list_is_array(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A single-element list still renders as a JSON array."""
        format_output([{"id": 1}], "json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_multi_element_list_is_array(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Multiple items always render as a JSON array."""
        format_output([{"id": 1}, {"id": 2}], "json")
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_empty_list_is_empty_array(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Empty list renders as an empty JSON array."""
        format_output([], "json")
        assert json.loads(capsys.readouterr().out) == []

    def test_datetime_serialised_as_iso(self, capsys: pytest.CaptureFixture[str]) -> None:
        """datetime fields are serialised as ISO-8601 strings."""
        dt = datetime(2024, 3, 15, 12, 0, 0)
        row = _FakeRow(id=1, name="task", created=dt)
        format_output(row, "json")
        data = json.loads(capsys.readouterr().out)
        assert data["created"] == dt.isoformat()

    def test_none_datetime_serialised_as_null(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None datetime fields serialize as JSON null."""
        row = _FakeRow(id=1, name="task", created=None)
        format_output(row, "json")
        data = json.loads(capsys.readouterr().out)
        assert data["created"] is None

    def test_output_uses_two_space_indent(self, capsys: pytest.CaptureFixture[str]) -> None:
        """JSON output uses 2-space indentation."""
        format_output({"id": 1}, "json")
        out = capsys.readouterr().out
        # indent=2 means the second line starts with two spaces
        assert "  " in out

    def test_empty_non_list_gives_empty_object(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None input (non-list) with no rows renders as empty object."""
        format_output(None, "json")
        assert json.loads(capsys.readouterr().out) == {}


# ---------------------------------------------------------------------------
# CSV format
# ---------------------------------------------------------------------------


class TestCsvFormat:
    """Tests for the CSV output renderer."""

    def test_basic_header_and_row(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CSV output includes a header line followed by data rows."""
        format_output([{"id": 1, "name": "Task A"}], "csv")
        lines = capsys.readouterr().out.strip().splitlines()
        assert lines[0] == "id,name"
        assert lines[1] == "1,Task A"

    def test_multiple_rows(self, capsys: pytest.CaptureFixture[str]) -> None:
        """All rows appear in CSV output."""
        rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        format_output(rows, "csv")
        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 3  # header + 2 data rows
        assert lines[0] == "id,name"
        assert "1,A" in lines
        assert "2,B" in lines

    def test_empty_list_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Empty list produces no CSV output at all."""
        format_output([], "csv")
        assert capsys.readouterr().out == ""

    def test_columns_filter(self, capsys: pytest.CaptureFixture[str]) -> None:
        """columns parameter restricts which fields are included."""
        rows = [{"id": 1, "name": "A", "desc": "should-be-excluded"}]
        format_output(rows, "csv", columns=["id", "name"])
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        assert lines[0] == "id,name"
        assert "should-be-excluded" not in out

    def test_none_value_renders_as_empty_string(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None cell values render as empty strings in CSV."""
        format_output([{"id": 1, "name": None}], "csv")
        lines = capsys.readouterr().out.strip().splitlines()
        assert lines[1] == "1,"

    def test_comma_in_value_is_quoted(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Values containing commas are properly quoted by DictWriter."""
        format_output([{"id": 1, "name": "Alice, Bob"}], "csv")
        out = capsys.readouterr().out
        assert '"Alice, Bob"' in out

    def test_datetime_in_cell(self, capsys: pytest.CaptureFixture[str]) -> None:
        """datetime values in cells are rendered as ISO-8601 strings."""
        dt = datetime(2024, 6, 1, 9, 30, 0)
        row = _FakeRow(id=1, name="task", created=dt)
        format_output(row, "csv", columns=["id", "created"])
        out = capsys.readouterr().out
        assert dt.isoformat() in out

    def test_none_input_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None input produces no CSV output."""
        format_output(None, "csv")
        assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Quiet format
# ---------------------------------------------------------------------------


class TestQuietFormat:
    """Tests for the quiet (ID-only) output renderer."""

    def test_prints_ids_one_per_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Quiet format prints each id on its own line."""
        rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        format_output(rows, "quiet")
        lines = capsys.readouterr().out.strip().splitlines()
        assert lines == ["1", "2"]

    def test_rows_without_id_are_skipped(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Rows that lack an 'id' key are silently ignored."""
        rows = [{"id": 1}, {"name": "no-id"}, {"id": 3}]
        format_output(rows, "quiet")
        lines = capsys.readouterr().out.strip().splitlines()
        assert lines == ["1", "3"]

    def test_empty_list_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Empty list produces no output."""
        format_output([], "quiet")
        assert capsys.readouterr().out == ""

    def test_single_item(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Single item prints its id."""
        format_output({"id": 42, "name": "task"}, "quiet")
        assert capsys.readouterr().out.strip() == "42"

    def test_none_input_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None input produces no output."""
        format_output(None, "quiet")
        assert capsys.readouterr().out == ""

    def test_dataclass_id(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Dataclass with id field prints its id."""
        rows = [_FakeRow(id=7, name="Alpha"), _FakeRow(id=8, name="Beta")]
        format_output(rows, "quiet")
        lines = capsys.readouterr().out.strip().splitlines()
        assert lines == ["7", "8"]


# ---------------------------------------------------------------------------
# Table format
# ---------------------------------------------------------------------------


class TestTableFormat:
    """Tests for the rich table output renderer."""

    def test_table_contains_column_headers(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Table output includes column header names."""
        format_output([{"id": 1, "name": "Alpha"}], "table")
        out = capsys.readouterr().out
        assert "id" in out
        assert "name" in out

    def test_table_contains_row_data(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Table output includes the data values."""
        format_output([{"id": 1, "name": "Alpha"}], "table")
        out = capsys.readouterr().out
        assert "1" in out
        assert "Alpha" in out

    def test_table_multiple_rows(self, capsys: pytest.CaptureFixture[str]) -> None:
        """All rows appear in the table output."""
        rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        format_output(rows, "table")
        out = capsys.readouterr().out
        assert "A" in out
        assert "B" in out

    def test_table_columns_filter(self, capsys: pytest.CaptureFixture[str]) -> None:
        """columns parameter limits which columns are rendered."""
        rows = [{"id": 1, "name": "A", "secret": "hidden"}]
        format_output(rows, "table", columns=["id", "name"])
        out = capsys.readouterr().out
        assert "id" in out
        assert "name" in out
        assert "secret" not in out

    def test_table_empty_data_no_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Empty data renders without raising an exception."""
        format_output([], "table")  # must not raise
        capsys.readouterr()

    def test_table_none_cell_renders_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """None cell values do not crash table rendering."""
        format_output([{"id": 1, "name": None}], "table")
        out = capsys.readouterr().out
        assert "id" in out

    def test_table_dataclass_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Dataclass instances render correctly via asdict conversion."""
        format_output(_FakeRow(id=3, name="Gamma"), "table")
        out = capsys.readouterr().out
        assert "3" in out
        assert "Gamma" in out


# ---------------------------------------------------------------------------
# format_success
# ---------------------------------------------------------------------------


class TestFormatSuccess:
    """Tests for format_success."""

    def test_json_format_outputs_status_object(self, capsys: pytest.CaptureFixture[str]) -> None:
        """JSON mode outputs a {'status': 'ok', 'message': ...} object."""
        format_success("Task created", "json")
        data = json.loads(capsys.readouterr().out)
        assert data == {"status": "ok", "message": "Task created"}

    def test_json_format_uses_indentation(self, capsys: pytest.CaptureFixture[str]) -> None:
        """JSON success output uses 2-space indentation."""
        format_success("Done", "json")
        out = capsys.readouterr().out
        assert "  " in out

    def test_table_format_prints_checkmark(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Table mode prints checkmark + message."""
        format_success("Project saved", "table")
        out = capsys.readouterr().out
        assert "✓ Project saved" in out

    def test_csv_format_prints_checkmark(self, capsys: pytest.CaptureFixture[str]) -> None:
        """CSV mode also uses the checkmark message style."""
        format_success("Done", "csv")
        assert "✓ Done" in capsys.readouterr().out

    def test_quiet_format_prints_checkmark(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Quiet mode also uses the checkmark message style."""
        format_success("Done", "quiet")
        assert "✓ Done" in capsys.readouterr().out
