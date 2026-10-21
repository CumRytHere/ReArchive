"""Marks everything in tests/acceptance/ with the `acceptance` marker.

Run the gate with:      uv run pytest -q -m acceptance
Run everything else:    uv run pytest -q -m "not acceptance"
"""

from __future__ import annotations

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "acceptance: human-owned gate tests in tests/acceptance (never edited by Claude)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if _HERE in Path(item.path).resolve().parents:
            item.add_marker(pytest.mark.acceptance)
