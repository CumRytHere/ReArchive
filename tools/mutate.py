#!/usr/bin/env python3
"""Targeted mutation testing: does any test notice when this code is wrong?

For one source file, generate small semantic mutants (flip a comparison, disable a guard, change a constant,
swap and/or, return None, ...) and run the given tests against each. A mutant that every test survives
marks code whose behaviour no test pins down. The increment-0.1 review found exactly this by hand: deleting
a bounds check left 88 tests green.

Usage:
    python3 tools/mutate.py SRC_FILE --tests TEST_PATH [TEST_PATH ...] [--function NAME] [--lines A-B]
                            [--max N] [--timeout S] [--json OUT]

Safety: the file is mutated in place and restored after every mutant. The original bytes are kept in
.mutate-backup/; a run that finds a backup from a crashed run restores it and stops. The final
SHA-256 of the file is checked against the original. Never run two instances at once.
Exit 0 when no mutant survived, 1 when any did, 2 on usage or safety errors. Stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / ".mutate-backup"

COMPARE_SWAP: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}
BINOP_SWAP: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.FloorDiv: ast.Mult,
    ast.LShift: ast.RShift,
    ast.RShift: ast.LShift,
    ast.BitAnd: ast.BitOr,
    ast.BitOr: ast.BitAnd,
    ast.Mod: ast.FloorDiv,
}


@dataclass
class Site:
    index: int
    line: int
    kind: str
    description: str


@dataclass
class Result:
    index: int
    line: int
    kind: str
    description: str
    outcome: str  # killed | survived | timeout | invalid
    seconds: float


class Collector(ast.NodeVisitor):
    """Find mutation sites in a deterministic order."""

    def __init__(self, function: str | None, lines: tuple[int, int] | None) -> None:
        self.sites: list[Site] = []
        self.function = function
        self.lines = lines
        self._stack: list[str] = []

    def _in_scope(self, node: ast.AST) -> bool:
        line = getattr(node, "lineno", 0)
        if self.lines and not (self.lines[0] <= line <= self.lines[1]):
            return False
        return self.function is None or self.function in self._stack

    def _add(self, node: ast.AST, kind: str, description: str) -> None:
        if self._in_scope(node):
            self.sites.append(Site(len(self.sites), getattr(node, "lineno", 0), kind, description))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_Compare(self, node: ast.Compare) -> None:
        for op in node.ops:
            if type(op) in COMPARE_SWAP:
                self._add(node, "compare", f"{type(op).__name__} -> {COMPARE_SWAP[type(op)].__name__}")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if type(node.op) in BINOP_SWAP:
            self._add(node, "binop", f"{type(node.op).__name__} -> {BINOP_SWAP[type(node.op)].__name__}")
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self._add(node, "boolop", "and -> or" if isinstance(node.op, ast.And) else "or -> and")
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if isinstance(node.op, ast.Not):
            self._add(node, "not", "drop `not`")
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._add(node, "if", "condition -> False (guard never fires)")
        self._add(node, "if", "condition -> True (guard always fires)")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, bool):
            self._add(node, "constant", f"{node.value} -> {not node.value}")
        elif isinstance(node.value, int):
            self._add(node, "constant", f"{node.value} -> {node.value + 1}")

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
            self._add(node, "return", "return value -> None")
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        self._add(node, "raise", "raise -> pass")
        self.generic_visit(node)


class Mutator(ast.NodeTransformer):
    """Re-walks the tree in the Collector's order and applies mutation number `target`."""

    def __init__(self, function: str | None, lines: tuple[int, int] | None, target: int) -> None:
        self.collector = Collector(function, lines)
        self.target = target
        self.applied: str | None = None

    def _hit(self, node: ast.AST, kind: str, description: str) -> bool:
        before = len(self.collector.sites)
        self.collector._add(node, kind, description)
        return len(self.collector.sites) > before and before == self.target

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.collector._stack.append(node.name)
        self.generic_visit(node)
        self.collector._stack.pop()
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.collector._stack.append(node.name)
        self.generic_visit(node)
        self.collector._stack.pop()
        return node

    def visit_Compare(self, node: ast.Compare) -> Any:
        for i, op in enumerate(node.ops):
            if type(op) in COMPARE_SWAP and self._hit(node, "compare", ""):
                node.ops[i] = COMPARE_SWAP[type(op)]()
                self.applied = "compare"
        self.generic_visit(node)
        return node

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if type(node.op) in BINOP_SWAP and self._hit(node, "binop", ""):
            node.op = BINOP_SWAP[type(node.op)]()
            self.applied = "binop"
        self.generic_visit(node)
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if self._hit(node, "boolop", ""):
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            self.applied = "boolop"
        self.generic_visit(node)
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if isinstance(node.op, ast.Not) and self._hit(node, "not", ""):
            self.applied = "not"
            return self.visit(node.operand)
        self.generic_visit(node)
        return node

    def visit_If(self, node: ast.If) -> Any:
        if self._hit(node, "if", ""):
            node.test = ast.Constant(value=False)
            self.applied = "if"
        if self._hit(node, "if", ""):
            node.test = ast.Constant(value=True)
            self.applied = "if"
        self.generic_visit(node)
        return node

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, bool):
            if self._hit(node, "constant", ""):
                self.applied = "constant"
                return ast.Constant(value=not node.value)
        elif isinstance(node.value, int) and self._hit(node, "constant", ""):
            self.applied = "constant"
            return ast.Constant(value=node.value + 1)
        return node

    def visit_Return(self, node: ast.Return) -> Any:
        returns_value = node.value is not None and not (
            isinstance(node.value, ast.Constant) and node.value.value is None
        )
        if returns_value and self._hit(node, "return", ""):
            self.applied = "return"
            return ast.Return(value=ast.Constant(value=None))
        self.generic_visit(node)
        return node

    def visit_Raise(self, node: ast.Raise) -> Any:
        if self._hit(node, "raise", ""):
            self.applied = "raise"
            return ast.Pass()
        self.generic_visit(node)
        return node


def sites_for(source: str, function: str | None, lines: tuple[int, int] | None) -> list[Site]:
    tree = ast.parse(source)
    collector = Collector(function, lines)
    collector.visit(tree)
    return collector.sites


def mutant_source(source: str, function: str | None, lines: tuple[int, int] | None, target: int) -> str | None:
    tree = ast.parse(source)
    mutator = Mutator(function, lines, target)
    new = mutator.visit(copy.deepcopy(tree))
    if mutator.applied is None:
        return None
    ast.fix_missing_locations(new)
    return ast.unparse(new) + "\n"


def run_tests(tests: list[str], timeout: int) -> tuple[str, float]:
    start = time.monotonic()
    cmd = ["uv", "run", "--no-sync", "pytest", "-x", "-q", "-p", "no:cacheprovider", "--no-header", *tests]
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(os.environ),
        )
    except subprocess.TimeoutExpired:
        return "timeout", time.monotonic() - start
    elapsed = time.monotonic() - start
    if proc.returncode == 0:
        return "survived", elapsed
    if proc.returncode in (1, 2, 3):  # failed / collection broke (mutant made the import fail) / internal
        return "killed", elapsed
    return "invalid", elapsed  # 4 usage error, 5 no tests collected


def parse_lines(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    a, _, b = value.partition("-")
    return int(a), int(b or a)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--tests", nargs="+", help="test paths to run against each mutant (required unless --list)")
    parser.add_argument("--function", help="only mutate inside this function or class")
    parser.add_argument("--lines", help="only mutate within A-B")
    parser.add_argument("--max", type=int, default=200, help="stop after this many mutants")
    parser.add_argument("--timeout", type=int, default=300, help="seconds per mutant test run")
    parser.add_argument("--json", type=Path, help="write results here")
    parser.add_argument("--list", action="store_true", help="list mutation sites and exit")
    args = parser.parse_args(argv)

    source_path = (ROOT / args.source).resolve() if not args.source.is_absolute() else args.source
    if not source_path.is_file() or ROOT not in source_path.parents:
        print(f"not a file inside the repository: {args.source}", file=sys.stderr)
        return 2
    rel = source_path.relative_to(ROOT)
    if rel.parts[0] in ("tests", "tools", ".claude", ".github") or rel.name == "CLAUDE.md":
        print(f"refusing to mutate {rel}: only product source is mutated", file=sys.stderr)
        return 2

    backup = BACKUP_DIR / (quote(rel.as_posix(), safe="") + ".orig")  # reversible: unquote() restores the path
    if BACKUP_DIR.exists() and any(BACKUP_DIR.iterdir()):
        for leftover in BACKUP_DIR.iterdir():
            target = ROOT / unquote(leftover.name.removesuffix(".orig"))
            target.write_bytes(leftover.read_bytes())
            leftover.unlink()
            print(
                f"restored {target.relative_to(ROOT)} from a crashed run; check `git diff`, then rerun", file=sys.stderr
            )
        return 2

    original = source_path.read_bytes()
    original_sha = hashlib.sha256(original).hexdigest()
    source = original.decode("utf-8")
    lines = parse_lines(args.lines)
    sites = sites_for(source, args.function, lines)
    if args.list:
        for s in sites:
            print(f"#{s.index:3} line {s.line:4} {s.kind:8} {s.description}")
        return 0

    if not args.tests:
        print("--tests is required (unless --list)", file=sys.stderr)
        return 2
    BACKUP_DIR.mkdir(exist_ok=True)
    backup.write_bytes(original)

    def restore(*_: object) -> None:
        source_path.write_bytes(original)
        if backup.exists():
            backup.unlink()
        if BACKUP_DIR.exists() and not any(BACKUP_DIR.iterdir()):
            BACKUP_DIR.rmdir()

    def on_signal(signum: int, _frame: object) -> None:
        restore()
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    results: list[Result] = []
    try:
        baseline, _ = run_tests(args.tests, args.timeout)
        if baseline != "survived":
            print(f"tests do not pass on the unmutated code ({baseline}); fix that first", file=sys.stderr)
            return 2
        for site in sites[: args.max]:
            mutated = mutant_source(source, args.function, lines, site.index)
            if mutated is None:
                continue
            source_path.write_text(mutated, encoding="utf-8")
            outcome, seconds = run_tests(args.tests, args.timeout)
            source_path.write_bytes(original)
            results.append(Result(site.index, site.line, site.kind, site.description, outcome, round(seconds, 2)))
            mark = {"killed": ".", "survived": "S", "timeout": "T", "invalid": "?"}[outcome]
            print(mark, end="", flush=True)
        print()
    finally:
        restore()

    if hashlib.sha256(source_path.read_bytes()).hexdigest() != original_sha:
        print(
            f"SAFETY: {rel} does not match its original bytes; restore with `git checkout -- {rel}`",
            file=sys.stderr,
        )
        return 2

    survivors = [r for r in results if r.outcome == "survived"]
    counts = {k: sum(r.outcome == k for r in results) for k in ("killed", "survived", "timeout", "invalid")}
    print(f"{rel}: {len(results)} mutants — " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    for r in survivors:
        print(f"  SURVIVED line {r.line}: {r.kind} {r.description}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "source": str(rel),
                    "sha256": original_sha,
                    "tests": args.tests,
                    "counts": counts,
                    "results": [asdict(r) for r in results],
                },
                indent=2,
            )
        )
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
