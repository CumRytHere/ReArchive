#!/usr/bin/env python3
"""Machine-generated verification report — the only acceptable source of test numbers.

Every claim like "218 passed" in a log entry, closure record or handoff must be copied from a report
this script wrote for the exact tree it describes. Hand-typed numbers go stale; this does not.

Usage:
    python3 tools/verify.py                 # all checks, acceptance recorded but not required
    python3 tools/verify.py --gate A        # acceptance suite must pass too
    python3 tools/verify.py --fast          # skip acceptance (inner loop)
    python3 tools/verify.py --close         # closing an increment: its decision constants must hold
    python3 tools/verify.py --check-report reports/verify/<id>.json   # is that report about this tree?

Writes reports/verify/<tree-id>.json and .md, prints the .md, exits 0 iff the verdict is PASS.
Stdlib only; it drives the project environment through `uv run`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCHEMA = 1
ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "verify"
TIMEOUT_S = 1800
# uv/tool chatter that is never the reason a check failed
NOISE = re.compile(r"^warning: (The `UV_\w+` environment variable|`VIRTUAL_ENV=)")

sys.path.insert(0, str(ROOT / "tools"))
import protected_paths  # noqa: E402  (tools/ is not a package on purpose)


def sh(cmd: list[str], timeout: int = TIMEOUT_S, env: dict[str, str] | None = None) -> dict[str, Any]:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, **(env or {})},
        )
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as exc:
        code, stdout, stderr = 127, "", f"{exc}"
    except subprocess.TimeoutExpired:
        code, stdout, stderr = 124, "", f"timed out after {timeout}s"
    lines = [line for line in (stdout + "\n" + stderr).splitlines() if line.strip() and not NOISE.match(line)]
    return {
        "cmd": " ".join(cmd),
        "exit": code,
        "seconds": round(time.monotonic() - start, 2),
        "stdout": stdout.strip(),
        "tail": "\n".join(lines[-25:]),
    }


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True).stdout.strip()


def tree_state() -> dict[str, Any]:
    """Identify the exact tree a report describes, including uncommitted and untracked files."""
    head = git("rev-parse", "HEAD") or None
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    dirty = [line[3:] for line in status.splitlines() if line]
    if head and not dirty:
        return {
            "head": head,
            "tree": git("rev-parse", "HEAD^{tree}"),
            "dirty": False,
            "dirty_files": [],
            "id": head[:12],
        }
    digest = hashlib.sha256()
    digest.update((head or "no-head").encode())
    digest.update(
        subprocess.run(["git", "-C", str(ROOT), "diff", "HEAD", "--binary"], capture_output=True).stdout
        if head
        else b""
    )
    for rel in sorted(git("ls-files", "--others", "--exclude-standard").splitlines()):
        path = ROOT / rel
        digest.update(rel.encode() + b"\0")
        if path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    state_id = f"{(head or 'nohead')[:12]}-dirty-{digest.hexdigest()[:12]}"
    return {"head": head, "tree": None, "dirty": True, "dirty_files": sorted(dirty), "id": state_id}


def junit_counts(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    outcome: dict[str, list[str]] = {"passed": [], "failed": [], "error": [], "skipped": []}
    for suite in suites:
        for case in suite.iter("testcase"):
            name = f"{case.get('classname', '')}::{case.get('name', '')}"
            if case.find("failure") is not None:
                outcome["failed"].append(name)
            elif case.find("error") is not None:
                outcome["error"].append(name)
            elif case.find("skipped") is not None:
                outcome["skipped"].append(name)
            else:
                outcome["passed"].append(name)
    counts["tests"] = sum(len(v) for v in outcome.values())
    counts["failures"] = len(outcome["failed"])
    counts["errors"] = len(outcome["error"])
    counts["skipped"] = len(outcome["skipped"])
    passed = len(outcome["passed"])
    summary = f"{passed} passed, {counts['failures']} failed, {counts['errors']} errors, {counts['skipped']} skipped"
    return {
        "available": True,
        **counts,
        "passed": passed,
        "summary": summary,
        "names": {k: sorted(v) for k, v in outcome.items() if k != "passed"},
    }


def pytest(label: str, args: list[str], tmp: Path) -> dict[str, Any]:
    xml = tmp / f"{label}.xml"
    result = sh(
        [
            "uv",
            "run",
            "--no-sync",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "junit_family=xunit2",
            f"--junitxml={xml}",
            *args,
        ]
    )
    result["counts"] = junit_counts(xml)
    # pytest exit 5 = nothing collected: not a failure of the code, but never a pass either.
    result["ok"] = result["exit"] == 0
    result["nothing_collected"] = result["exit"] == 5
    return result


def strict(result: dict[str, Any]) -> dict[str, Any]:
    """Fail an owner-owned suite that skipped anything or ran nothing."""
    counts = result.get("counts", {})
    if result["exit"] == 0 and (not counts.get("available") or counts.get("skipped") or not counts.get("passed")):
        result["exit"] = 1
        result["tail"] = (result.get("tail", "") + "\nowner-owned suite skipped tests or ran none").strip()
        if counts.get("available"):
            counts["summary"] += " — skips or empty run not allowed"
    return result


def environment() -> dict[str, Any]:
    py = sh(
        [
            "uv",
            "run",
            "--no-sync",
            "python",
            "-c",
            "import platform,sys; print(platform.python_implementation(), platform.python_version(), "
            "sys.platform, platform.machine(), sep='|')",
        ],
        timeout=120,
    )
    parts = py["stdout"].splitlines()[-1].split("|") if py["exit"] == 0 and py["stdout"] else []
    uv = sh(["uv", "--version"], timeout=60)
    return {
        "python": {"implementation": parts[0], "version": parts[1], "platform": parts[2], "machine": parts[3]}
        if len(parts) == 4
        else {"error": py["tail"]},
        "uv": uv["stdout"] if uv["exit"] == 0 else None,
        "host": f"{platform.system()}-{platform.machine()}",
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    state = tree_state()
    checks: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="rearchive-verify-") as t:
        tmp = Path(t)
        checks["lockfile"] = sh(["uv", "lock", "--check"], timeout=300)
        checks["sync"] = sh(["uv", "sync", "--locked"], timeout=900)
        # --no-cache: ruff otherwise writes caches beside nested configs, inside sandbox-protected directories.
        checks["ruff_check"] = sh(["uv", "run", "--no-sync", "ruff", "check", "--no-cache", "."])
        checks["ruff_format"] = sh(["uv", "run", "--no-sync", "ruff", "format", "--no-cache", "--check", "."])
        checks["mypy"] = sh(["uv", "run", "--no-sync", "mypy", "--strict", "src"])
        checks["unit"] = pytest("unit", ["-m", "not acceptance", "tests", "--ignore=tests/contract"], tmp)
        # Owner-owned suites must run in full: a skip or an empty run is a failure, never a pass.
        checks["contract"] = strict(pytest("contract", ["tests/contract"], tmp))
        checks["tools"] = strict(pytest("tools", ["tools/tests"], tmp))
        if args.close:
            checks["constants_closure"] = sh(
                ["uv", "run", "--no-sync", "python", "tools/decision_constants.py", "--mode", "closure"]
            )
        if not args.fast:
            checks["acceptance"] = pytest("acceptance", ["-m", "acceptance", "tests/acceptance"], tmp)
    leftovers = (
        sorted(p.name for p in (ROOT / ".mutate-backup").glob("*")) if (ROOT / ".mutate-backup").is_dir() else []
    )
    checks["mutation_leftovers"] = {
        "exit": 1 if leftovers else 0,
        "tail": ("a mutation run did not finish; source may still be mutated: " + ", ".join(leftovers))
        if leftovers
        else "",
    }
    try:
        prot = protected_paths.check(ROOT)
        checks["protected_paths"] = {"exit": 0 if prot.clean else 1, **prot.as_dict()}
    except protected_paths.GitError as exc:
        checks["protected_paths"] = {
            "exit": 1,
            "clean": False,
            "changed": [f"<check failed: {exc}>"],
            "untracked": [],
            "protected_lines": [],
            "base": None,
            "note": str(exc),
        }

    required = [
        "lockfile",
        "sync",
        "ruff_check",
        "ruff_format",
        "mypy",
        "unit",
        "contract",
        "tools",
        "mutation_leftovers",
        "protected_paths",
    ]
    if args.close:
        required.append("constants_closure")
    if args.gate:
        required.append("acceptance")
    failing = [name for name in required if name in checks and checks[name]["exit"] != 0]
    if args.gate and "acceptance" not in checks:
        failing.append("acceptance (skipped by --fast)")
    return {
        "schema": SCHEMA,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "state": state,
        "branch": git("branch", "--show-current"),
        "environment": environment(),
        "gate": args.gate,
        "close": args.close,
        "required": required,
        "checks": checks,
        "failing": failing,
        "verdict": "PASS" if not failing else "FAIL",
    }


def render(report: dict[str, Any]) -> str:
    s, c = report["state"], report["checks"]
    env = report["environment"]["python"]
    lines = [
        f"## Verification report `{s['id']}`",
        "",
        f"- Verdict: **{report['verdict']}**"
        + (f" (gate {report['gate']})" if report["gate"] else "")
        + (" (closure)" if report.get("close") else ""),
        f"- Tree: HEAD `{(s['head'] or 'none')[:12]}` on `{report['branch'] or '?'}`"
        + (f", **dirty** ({len(s['dirty_files'])} files)" if s["dirty"] else ", clean"),
        f"- Python: {env.get('implementation', '?')} {env.get('version', '?')} on {env.get('platform', '?')}"
        f"-{env.get('machine', '?')}; {report['environment']['uv'] or 'uv ?'}",
        f"- Generated: {report['generated_at']} by tools/verify.py (schema {report['schema']})",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for name, check in c.items():
        ok = check.get("exit") == 0
        detail = ""
        if "counts" in check and check["counts"].get("available"):
            detail = check["counts"]["summary"]
        elif check.get("nothing_collected"):
            detail = "no tests collected"
        elif name == "protected_paths":
            detail = (
                "clean"
                if check["clean"]
                else "DIFFERS: " + ", ".join(check["changed"] + check["untracked"] + check["protected_lines"])
            )
        elif not ok:
            detail = (check.get("tail") or "").splitlines()[-1:][0] if check.get("tail") else ""
        required = "" if name in report["required"] else " (recorded)"
        lines.append(f"| {name}{required} | {'pass' if ok else 'FAIL'} | {detail.replace('|', '/')} |")
    acc = c.get("acceptance", {}).get("counts", {})
    if acc.get("available"):
        names = acc["names"]
        lines += ["", "Acceptance tests not passing:"] if names["failed"] or names["error"] else []
        lines += [f"- failed: `{n.split('::')[-1]}`" for n in names["failed"]]
        lines += [f"- error: `{n.split('::')[-1]}`" for n in names["error"]]
    if report["failing"]:
        lines += ["", "Failing required checks: " + ", ".join(report["failing"])]
    return "\n".join(lines) + "\n"


def check_report(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    current = tree_state()
    if report.get("state", {}).get("id") != current["id"]:
        print(f"STALE: report describes {report.get('state', {}).get('id')}, tree is {current['id']}")
        return 1
    print(f"CURRENT: report {path.name} describes this tree; verdict {report['verdict']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gate", choices=["A", "B", "C", "D"], help="also require the acceptance suite")
    parser.add_argument("--fast", action="store_true", help="skip the acceptance suite")
    parser.add_argument(
        "--close", action="store_true", help="closure gate: constants due at the current increment must hold too"
    )
    parser.add_argument("--check-report", type=Path, help="report to compare with the current tree")
    args = parser.parse_args(argv)
    if args.check_report:
        return check_report(args.check_report)

    report = build(args)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stem = REPORT_DIR / report["state"]["id"]
    stem.with_suffix(".json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = render(report)
    stem.with_suffix(".md").write_text(markdown, encoding="utf-8")
    (REPORT_DIR / "latest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(markdown)
    print(f"report: {stem.with_suffix('.json').relative_to(ROOT)}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
