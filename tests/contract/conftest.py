"""Contract tests — owner-owned, always run with the unit tests, never edited by Claude.

They hold the code to ratified decisions (D-028) and to structural invariants. Unlike tests/acceptance, these are
expected to be green at all times; a failure means the code and the decisions disagree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_HERE = Path(__file__).resolve().parent

if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "contract: owner-owned decision/code consistency tests (tests/contract)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if _HERE in Path(item.path).resolve().parents:
            item.add_marker(pytest.mark.contract)
