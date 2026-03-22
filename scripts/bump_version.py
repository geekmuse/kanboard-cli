#!/usr/bin/env python3
"""Version bump utility for kanboard-cli.

Uses only the standard library — no extra dependencies, instant startup.
Version is the single source of truth in pyproject.toml [project].version.

Usage:
    python scripts/bump_version.py patch          # 0.4.0 → 0.4.1
    python scripts/bump_version.py minor          # 0.4.0 → 0.5.0
    python scripts/bump_version.py major          # 0.4.0 → 1.0.0
    python scripts/bump_version.py 0.5.0          # set explicit version
    python scripts/bump_version.py --dry-run minor
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

# Matches: version = "1.2.3"  (only the [project] key, not arbitrary occurrences)
_VERSION_LINE_RE = re.compile(
    r'^(version\s*=\s*")([0-9]+\.[0-9]+\.[0-9]+)(")',
    re.MULTILINE,
)


def _parse_semver(v: str) -> tuple[int, int, int]:
    """Parse a semantic version string, exiting on failure."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        _die(f"invalid semantic version: {v!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _compute_new(current: str, directive: str) -> str:
    """Return the new version given *current* and a bump *directive*."""
    match directive:
        case "major":
            major, _, _ = _parse_semver(current)
            return f"{major + 1}.0.0"
        case "minor":
            major, minor, _ = _parse_semver(current)
            return f"{major}.{minor + 1}.0"
        case "patch":
            major, minor, patch = _parse_semver(current)
            return f"{major}.{minor}.{patch + 1}"
        case explicit:
            _parse_semver(explicit)  # validate
            return explicit


def _die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> None:  # noqa: D103
    args = (argv or sys.argv)[1:]

    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    if len(args) != 1:
        print(__doc__)
        sys.exit(1)

    directive = args[0]

    # Read current version from pyproject.toml
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    try:
        current = data["project"]["version"]
    except KeyError:
        _die("could not find [project].version in pyproject.toml")

    new = _compute_new(current, directive)

    if current == new:
        print(f"already at {current} — nothing to do.")
        sys.exit(0)

    print(f"  {current} → {new}")

    if dry_run:
        print("  (dry run — no files written)")
        return

    # Patch the version line in-place, preserving all formatting and comments
    text = PYPROJECT.read_text(encoding="utf-8")
    patched, n = _VERSION_LINE_RE.subn(rf"\g<1>{new}\g<3>", text, count=1)
    if n != 1:
        _die("could not locate version = \"...\" line in pyproject.toml")

    PYPROJECT.write_text(patched, encoding="utf-8")
    print("  updated pyproject.toml")

    msg = f"chore(release): bump version {current} → {new}"
    subprocess.run(
        ["git", "commit", "pyproject.toml", "--no-verify", "-m", msg],
        check=True,
        cwd=ROOT,
    )
    print(f"  committed: {msg}")


if __name__ == "__main__":
    main()
