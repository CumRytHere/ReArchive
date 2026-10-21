"""D-028: constants fixed by ratified decisions must equal the code.

Regression mode: blocks due before the current increment are enforced here, with every unit-test run, so they
can never break again. Blocks due at the current increment are enforced at closure (`tools/verify.py --close`).
"""

from __future__ import annotations

from pathlib import Path

import decision_constants as dc
import pytest

REPO = Path(__file__).resolve().parents[2]
DECISIONS = REPO / "docs" / "DECISIONS.md"
STATUS = REPO / "docs" / "STATUS.md"


def _outcomes() -> list[dc.Outcome]:
    return dc.run(DECISIONS, STATUS)


def test_blocks_are_well_formed() -> None:
    constants = dc.parse_blocks(DECISIONS.read_text(encoding="utf-8"))
    symbols = [c.symbol for c in constants]
    duplicates = sorted({s for s in symbols if symbols.count(s) > 1})
    assert not duplicates, f"a symbol is fixed by more than one decision block: {duplicates}"


def test_status_names_a_current_increment() -> None:
    dc.current_increment(STATUS.read_text(encoding="utf-8"))


def test_due_constants_match_the_code() -> None:
    failing = [o for o in _outcomes() if o.status in ("mismatch", "import_error")]
    lines = [
        f"{o.constant.decision} {o.constant.symbol} (due {'.'.join(map(str, o.constant.due))}): "
        f"expected {o.constant.expected!r}, got {o.detail or repr(o.actual)}"
        for o in failing
    ]
    assert not failing, "decision constants not honoured by the code:\n" + "\n".join(lines)


@pytest.mark.parametrize("symbol", ["rearchive.decode.dtypes.KAITAI_TO_CANONICAL"])
def test_kaitai_mapping_uses_only_d015_dtypes(symbol: str) -> None:
    """D-018 table values must be dtypes D-015 allows. Enforced once D-018's block is due."""
    by_symbol = {o.constant.symbol: o for o in _outcomes()}
    outcome = by_symbol.get(symbol)
    if outcome is None or outcome.status != "ok":
        return  # not ratified, not due, or still in progress: test_due_constants_match_the_code reports it
    allow = dc.resolve("rearchive.core.canonical.ALLOWED_DTYPES")
    mapping = dc.resolve(symbol)
    unknown = sorted(set(mapping.values()) - set(allow))
    assert not unknown, f"D-018 maps to dtypes D-015 does not allow: {unknown}"
