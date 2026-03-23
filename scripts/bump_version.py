#!/usr/bin/env python3
"""Version bump utility for kanboard-cli and kanboard-sdk.

Uses only the standard library — no extra dependencies, instant startup.
Each package has its own pyproject.toml as the version source of truth.

Usage:
    python scripts/bump_version.py cli patch         # CLI: 1.1.0 → 1.1.1
    python scripts/bump_version.py sdk minor         # SDK: 1.1.0 → 1.2.0
    python scripts/bump_version.py cli 2.0.0         # CLI: set explicit version
    python scripts/bump_version.py sdk 2.0.0         # SDK: set explicit version
    python scripts/bump_version.py --dry-run sdk patch
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS: dict[str, Path] = {
    "cli": ROOT / "pyproject.toml",
    "sdk": ROOT / "sdk" / "pyproject.toml",
}

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

    if len(args) != 2 or args[0] not in TARGETS:
        print(__doc__)
        print(f"  targets: {', '.join(TARGETS)}")
        sys.exit(1)

    target, directive = args
    pyproject = TARGETS[target]

    # Read current version
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    try:
        current = data["project"]["version"]
    except KeyError:
        _die(f"could not find [project].version in {pyproject}")

    pkg_name = data["project"]["name"]
    new = _compute_new(current, directive)

    if current == new:
        print(f"  {pkg_name}: already at {current} — nothing to do.")
        sys.exit(0)

    print(f"  {pkg_name}: {current} → {new}")

    if dry_run:
        print("  (dry run — no files written)")
        return

    # Patch the version line in-place, preserving all formatting and comments
    text = pyproject.read_text(encoding="utf-8")
    patched, n = _VERSION_LINE_RE.subn(rf"\g<1>{new}\g<3>", text, count=1)
    if n != 1:
        _die(f'could not locate version = "..." line in {pyproject}')

    pyproject.write_text(patched, encoding="utf-8")
    print(f"  updated {pyproject.relative_to(ROOT)}")

    # If bumping the SDK, also update the CLI's minimum SDK dependency
    if target == "sdk":
        cli_pyproject = TARGETS["cli"]
        cli_text = cli_pyproject.read_text(encoding="utf-8")
        dep_re = re.compile(r'("kanboard-sdk>=)([0-9]+\.[0-9]+\.[0-9]+)(")')
        cli_patched, m = dep_re.subn(rf"\g<1>{new}\g<3>", cli_text, count=1)
        if m == 1:
            cli_pyproject.write_text(cli_patched, encoding="utf-8")
            print(f"  updated kanboard-sdk>={new} in {cli_pyproject.relative_to(ROOT)}")
            files = [str(pyproject), str(cli_pyproject)]
        else:
            files = [str(pyproject)]
    else:
        files = [str(pyproject)]

    msg = f"chore(release): bump {pkg_name} {current} → {new}"
    subprocess.run(
        ["git", "commit", *files, "--no-verify", "-m", msg],
        check=True,
        cwd=ROOT,
    )
    print(f"  committed: {msg}")


if __name__ == "__main__":
    main()
