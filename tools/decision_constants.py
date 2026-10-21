#!/usr/bin/env python3
"""Decision–code consistency (D-028).

A decision that fixes a value the code must match carries a fenced block:

    ```decision-constants due=0.4
    rearchive.records.RECORD_SCHEMA = 1
    ```

Blocks due BEFORE the current increment in docs/STATUS.md are always enforced (regression mode, run with the
unit tests). Blocks due AT the current increment are enforced at closure (closure mode, `tools/verify.py --close`).
Later blocks are only checked for well-formedness.

Usage:
    uv run python tools/decision_constants.py [--mode regression|closure|all]
Exit 0 when every enforced constant matches, 1 otherwise. Stdlib only, but symbols import from the
project, so run it inside the project environment.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BLOCK_RE = re.compile(r"^```decision-constants(?P<attrs>[^\n]*)\n(?P<body>.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
HEADING_RE = re.compile(r"^## (?P<id>D-\d{3})\b", re.MULTILINE)
INCREMENT_RE = re.compile(r"^\*\*Current increment:\*\*\s*(?P<inc>\d+(?:\.\d+)*)", re.MULTILINE)
SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")


class ConstantsFormatError(ValueError):
    """A decision-constants block is malformed."""


@dataclass(frozen=True)
class Constant:
    decision: str
    due: tuple[int, ...]
    symbol: str
    expected: Any
    line: int


@dataclass(frozen=True)
class Outcome:
    constant: Constant
    status: str  # ok | mismatch | import_error | not_due
    actual: Any = None
    detail: str = ""


def parse_increment(text: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)*", text):
        raise ConstantsFormatError(f"not an increment number: {text!r}")
    return tuple(int(part) for part in text.split("."))


def current_increment(status_text: str) -> tuple[int, ...]:
    match = INCREMENT_RE.search(status_text)
    if not match:
        raise ConstantsFormatError("docs/STATUS.md has no '**Current increment:** N.N' line")
    return parse_increment(match.group("inc"))


def parse_blocks(decisions_text: str) -> list[Constant]:
    headings = [(m.start(), m.group("id")) for m in HEADING_RE.finditer(decisions_text)]
    constants: list[Constant] = []
    for block in BLOCK_RE.finditer(decisions_text):
        owner = [d for pos, d in headings if pos < block.start()]
        if not owner:
            raise ConstantsFormatError("decision-constants block appears before any '## D-NNN' heading")
        attrs = dict(item.split("=", 1) for item in block.group("attrs").split() if "=" in item)
        if "due" not in attrs:
            raise ConstantsFormatError(f"{owner[-1]}: block has no due=<increment>")
        due = parse_increment(attrs["due"])
        first_line = decisions_text.count("\n", 0, block.start("body")) + 1
        for offset, raw in enumerate(block.group("body").splitlines()):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if " = " not in line:
                raise ConstantsFormatError(f"{owner[-1]} line {first_line + offset}: expected 'symbol = literal'")
            symbol, literal = (part.strip() for part in line.split(" = ", 1))
            if not SYMBOL_RE.match(symbol):
                raise ConstantsFormatError(f"{owner[-1]} line {first_line + offset}: bad symbol {symbol!r}")
            try:
                expected = ast.literal_eval(literal)
            except (ValueError, SyntaxError) as exc:
                raise ConstantsFormatError(
                    f"{owner[-1]} line {first_line + offset}: not a Python literal: {literal!r} ({exc})"
                ) from exc
            constants.append(Constant(owner[-1], due, symbol, expected, first_line + offset))
    return constants


def resolve(symbol: str) -> Any:
    parts = symbol.split(".")
    missing: ModuleNotFoundError | None = None
    for split in range(len(parts) - 1, 0, -1):
        module_name, attrs = ".".join(parts[:split]), parts[split:]
        try:
            obj: Any = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name and (module_name == exc.name or module_name.startswith(exc.name + ".")):
                missing = missing or exc
                continue
            raise
        try:
            for attr in attrs:
                obj = getattr(obj, attr)
        except AttributeError:
            if missing is not None:
                raise missing from None
            raise
        return obj
    raise missing or ModuleNotFoundError(f"no importable module prefix in {symbol!r}")


def equal(expected: Any, actual: Any) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, (tuple, list)):
        if isinstance(actual, (set, frozenset)):
            return set(expected) == actual and len(set(expected)) == len(expected)
        return (
            isinstance(actual, (tuple, list))
            and len(expected) == len(actual)
            and all(equal(e, a) for e, a in zip(expected, actual))
        )
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and expected.keys() == actual.keys()
            and all(equal(expected[k], actual[k]) for k in expected)
        )
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return type(expected) is type(actual) and expected == actual
    return type(expected) is type(actual) and expected == actual


MODES = ("regression", "closure", "all")


def evaluate(constants: list[Constant], current: tuple[int, ...], mode: str = "regression") -> list[Outcome]:
    """regression: enforce blocks due before the current increment (they must never break again);
    blocks due at the current increment are `in_progress`.
    closure: also enforce blocks due at the current increment (an increment closes only when they hold).
    all: enforce every block."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    outcomes: list[Outcome] = []
    for constant in constants:
        if mode != "all" and constant.due > current:
            outcomes.append(Outcome(constant, "not_due"))
            continue
        try:
            actual = resolve(constant.symbol)
        except (ImportError, AttributeError) as exc:
            status, detail, actual = "import_error", f"{type(exc).__name__}: {exc}", None
        else:
            status, detail = ("ok" if equal(constant.expected, actual) else "mismatch"), ""
        if status != "ok" and mode == "regression" and constant.due == current:
            status = "in_progress"
        outcomes.append(Outcome(constant, status, actual=actual, detail=detail))
    return outcomes


FAILING = ("mismatch", "import_error")


def run(decisions: Path, status: Path, mode: str = "regression") -> list[Outcome]:
    constants = parse_blocks(decisions.read_text(encoding="utf-8"))
    current = current_increment(status.read_text(encoding="utf-8"))
    return evaluate(constants, current, mode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--decisions", type=Path, default=Path("docs/DECISIONS.md"))
    parser.add_argument("--status", type=Path, default=Path("docs/STATUS.md"))
    parser.add_argument(
        "--mode",
        choices=MODES,
        default="closure",
        help="regression: earlier increments only; closure (default): up to the current one; all",
    )
    args = parser.parse_args(argv)
    try:
        outcomes = run(args.decisions, args.status, args.mode)
    except ConstantsFormatError as exc:
        print(f"FORMAT ERROR: {exc}")
        return 1
    failed = 0
    for o in outcomes:
        c = o.constant
        due = ".".join(map(str, c.due))
        if o.status in FAILING:
            failed += 1
        line = f"{o.status:12} {c.decision} due={due:5} {c.symbol}"
        if o.status in (*FAILING, "in_progress"):
            line += f": expected {c.expected!r}, got {o.detail or repr(o.actual)}"
        print(line)
    pending = sum(o.status == "in_progress" for o in outcomes)
    print(f"{len(outcomes)} constants ({args.mode} mode): {failed} failing, {pending} in progress")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
