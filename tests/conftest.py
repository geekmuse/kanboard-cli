"""Shared pytest fixtures for all test suites."""

import sys
from pathlib import Path

# Ensure the local src/ package takes priority over any installed kanboard-sdk.
# The pre-commit hook runs `pip install -e '.[dev]'` which re-installs
# kanboard-sdk from PyPI creating a physical kanboard/ directory in
# site-packages that would shadow the local src/kanboard/ otherwise.
_src = str(Path(__file__).parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
