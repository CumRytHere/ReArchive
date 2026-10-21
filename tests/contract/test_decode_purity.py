"""D-026 §2 and CLAUDE.md invariant 7: the decode path imports no network, clock, randomness or float maths.

Checked statically over every module that exists under the decode-path packages. Before increment 0.4 those
packages do not exist and the invariant holds vacuously.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DECODE_PATH = ("src/rearchive/decode", "src/rearchive/worker", "src/rearchive/worker.py", "src/rearchive/generated")
FORBIDDEN = {
    "socket",
    "ssl",
    "http",
    "urllib",
    "requests",
    "httpx",  # network
    "random",
    "secrets",
    "uuid",  # randomness
    "time",
    "datetime",  # clock
    "math",
    "cmath",  # floating-point maths: results can differ by platform (fused multiply-add, libm)
}
FORBIDDEN_CALLS = {("os", "urandom"), ("os", "getrandom")}


def _modules() -> list[Path]:
    found: list[Path] = []
    for rel in DECODE_PATH:
        path = REPO / rel
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            found.extend(sorted(path.rglob("*.py")))
    return found


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rel = path.relative_to(REPO).as_posix()
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [f"{rel}:{node.lineno} import {a.name}" for a in node.names if a.name.split(".")[0] in FORBIDDEN]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module.split(".")[0] in FORBIDDEN:
                bad.append(f"{rel}:{node.lineno} from {node.module} import ...")
            if node.module == "os" and any(a.name in {"urandom", "getrandom"} for a in node.names):
                bad.append(f"{rel}:{node.lineno} from os import urandom/getrandom")
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and (node.value.id, node.attr) in FORBIDDEN_CALLS
        ):
            bad.append(f"{rel}:{node.lineno} {node.value.id}.{node.attr}")
    return bad


def test_decode_path_is_pure() -> None:
    violations = [v for module in _modules() for v in _violations(module)]
    assert not violations, "decode path must not use network, clock or randomness:\n" + "\n".join(violations)
