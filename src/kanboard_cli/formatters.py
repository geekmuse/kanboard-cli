"""Output formatters for the Kanboard CLI.

Provides :func:`format_output` and :func:`format_success` for rendering
SDK results in multiple output modes — table (rich), JSON, CSV, and quiet
(ID-only).
"""

from __future__ import annotations

import csv
import dataclasses
import io
import json
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table


def _normalize(data: Any) -> list[dict[str, Any]]:
    """Normalise *data* to a flat list of plain :class:`dict` objects.

    Handles ``None``, individual items, and lists.  Dataclass instances are
    recursively expanded via :func:`dataclasses.asdict`.

    Args:
        data: Raw value from an SDK call — a dataclass, dict, list, or None.

    Returns:
        A (possibly empty) list of dicts ready for formatting.
    """
    if data is None:
        return []
    items: list[Any] = data if isinstance(data, list) else [data]
    rows: list[dict[str, Any]] = []
    for item in items:
        if dataclasses.is_dataclass(item) and not isinstance(item, type):
            rows.append(dataclasses.asdict(item))
        elif isinstance(item, dict):
            rows.append(item)
        else:
            rows.append({"value": str(item)})
    return rows


def _get_columns(rows: list[dict[str, Any]], columns: list[str] | None) -> list[str]:
    """Return the effective column list for *rows*.

    Uses *columns* when explicitly supplied; otherwise falls back to the keys
    of the first row, or an empty list when *rows* is empty.

    Args:
        rows: Normalised list of dicts.
        columns: Explicit column selection, or ``None`` for auto-detection.

    Returns:
        Ordered list of column names to render.
    """
    if columns:
        return columns
    if not rows:
        return []
    return list(rows[0].keys())


def _cell_str(value: Any) -> str:
    """Convert *value* to a display-safe string for table and CSV cells.

    Args:
        value: Raw cell value from a row dict.

    Returns:
        Formatted string; empty string for ``None``, ISO-8601 for
        :class:`~datetime.datetime`, ``str()`` for everything else.
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class _DatetimeEncoder(json.JSONEncoder):
    """JSON encoder that serialises :class:`~datetime.datetime` as ISO-8601 strings."""

    def default(self, o: Any) -> Any:
        """Return a JSON-serialisable representation of *o*.

        Args:
            o: Object to encode.

        Returns:
            ISO-8601 string for :class:`~datetime.datetime`; delegates to the
            parent encoder for all other types.
        """
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def format_output(
    data: Any,
    format: str,
    columns: list[str] | None = None,
) -> None:
    """Format and print *data* to stdout in the requested output *format*.

    Dataclass instances are automatically converted to plain dicts before
    rendering.  ``None`` and empty lists are handled gracefully in every
    mode.

    Args:
        data: A single dataclass / dict, a list thereof, or ``None``.
        format: Output mode — ``"table"``, ``"json"``, ``"csv"``, or
            ``"quiet"``.
        columns: Optional ordered list of field names to include.
            Auto-detected from the first row when omitted.  Ignored by
            the ``"json"`` and ``"quiet"`` renderers.
    """
    rows = _normalize(data)
    if format == "table":
        _format_table(rows, columns)
    elif format == "json":
        _format_json(rows, isinstance(data, list))
    elif format == "csv":
        _format_csv(rows, columns)
    elif format == "quiet":
        _format_quiet(rows)


def _format_table(rows: list[dict[str, Any]], columns: list[str] | None) -> None:
    """Render *rows* as a rich table and print to the console.

    Uses a cyan bold header style with auto-width columns.

    Args:
        rows: Normalised list of dicts.
        columns: Explicit column selection, or ``None`` for auto-detection.
    """
    cols = _get_columns(rows, columns)
    table = Table(show_header=True, header_style="bold cyan")
    for col in cols:
        table.add_column(col)
    for row in rows:
        table.add_row(*[_cell_str(row.get(col)) for col in cols])
    console = Console()
    console.print(table)


def _format_json(rows: list[dict[str, Any]], is_list: bool) -> None:
    """Render *rows* as pretty-printed JSON and write to stdout.

    When *is_list* is ``False`` and exactly one row exists, the output is a
    single JSON object rather than a one-element array.

    Args:
        rows: Normalised list of dicts.
        is_list: Whether the original caller input was a Python list.
    """
    if is_list:
        payload: Any = rows
    elif rows:
        payload = rows[0]
    else:
        payload = {}
    print(json.dumps(payload, indent=2, cls=_DatetimeEncoder))


def _format_csv(rows: list[dict[str, Any]], columns: list[str] | None) -> None:
    """Render *rows* as CSV and write to stdout.

    Args:
        rows: Normalised list of dicts.
        columns: Explicit column selection, or ``None`` for auto-detection.
    """
    cols = _get_columns(rows, columns)
    if not cols:
        return
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=cols,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({col: _cell_str(row.get(col)) for col in cols})
    print(buf.getvalue(), end="")


def _format_quiet(rows: list[dict[str, Any]]) -> None:
    """Print only the ``id`` field of each row, one per line.

    Rows that do not have an ``id`` key are silently skipped.

    Args:
        rows: Normalised list of dicts.
    """
    for row in rows:
        if "id" in row:
            print(row["id"])


def format_success(message: str, format: str) -> None:
    """Print a success or confirmation message in the requested *format*.

    Outputs ``{"status": "ok", "message": ...}`` as indented JSON when
    *format* is ``"json"``; prints ``✓ {message}`` for all other modes.

    Args:
        message: Human-readable success description.
        format: Output mode — ``"table"``, ``"json"``, ``"csv"``, or
            ``"quiet"``.
    """
    if format == "json":
        print(json.dumps({"status": "ok", "message": message}, indent=2))
    else:
        print(f"✓ {message}")
