#!/usr/bin/env python3
"""Owner-controlled paths: the single source of truth used by hooks, CI and tools/verify.py.

A protected path may change only through an owner commit on the baseline branch (default `main`).
Anything else — an agent edit, a formatter, a script, a git command — shows up here as a difference
between the working tree and the baseline, and the hooks block until the owner resolves it.

Usage:
    python3 tools/protected_paths.py check [--base REF] [--json]
Exit codes: 0 clean (or not a git repository / no commits), 1 protected paths differ, 2 usage error.
Stdlib only; must run under any python3 >= 3.9 without the project environment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROTECTED_PATHS: tuple[str, ...] = (
    "CLAUDE.md",
    "docs/DECISIONS.md",
    "docs/PROJECT_SPEC.md",
    "tests/acceptance",
    "tests/contract",
    ".claude",
    "tools",
    ".github",
    # Test-runner configuration that could silently skip or weaken the owner's tests.
    "conftest.py",
    "tests/conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
)

# Paths inside protected directories that are personal or generated, never compared.
IGNORED_PREFIXES: tuple[str, ...] = (
    ".claude/settings.local.json",
    ".claude/worktrees/",
    "tools/ksc/node_modules/",
)

# Single lines in otherwise editable files that only the owner may change.
PROTECTED_LINES: tuple[tuple[str, str], ...] = (
    ("docs/STATUS.md", r"^\*\*Current phase:\*\*.*$"),
    ("docs/STATUS.md", r"^\*\*Current increment:\*\*.*$"),
)

# Sections of otherwise editable TOML files that configure the checks themselves (pytest, ruff, mypy, hypothesis,
# coverage). Weakening them must go through the owner. Compared as text, header to next header.
PROTECTED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", r"tool\.(pytest|ruff|mypy|hypothesis|coverage)\b"),
)

DEFAULT_BASES: tuple[str, ...] = ("main", "master")


class GitError(RuntimeError):
    """git failed in a way that makes the check meaningless; callers must treat this as NOT clean."""


@dataclass
class Result:
    base: str | None
    changed: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def clean(self) -> bool:
        return not (self.changed or self.untracked or self.lines)

    def as_dict(self) -> dict[str, object]:
        return {
            "base": self.base,
            "clean": self.clean,
            "changed": self.changed,
            "untracked": self.untracked,
            "protected_lines": self.lines,
            "note": self.note,
        }


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # quotePath=true keeps every path ASCII-safe; surrogateescape keeps undecodable bytes instead of raising.
    return subprocess.run(
        ["git", "-c", "core.quotePath=true", "-C", str(root), *args],
        capture_output=True,
        text=True,
        errors="surrogateescape",
        check=False,
    )


def _git_ok(root: Path, *args: str) -> str:
    proc = _git(root, *args)
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args[:3])} failed ({proc.returncode}): {proc.stderr.strip()[:300]}")
    return proc.stdout


def repo_root(start: Path | None = None) -> Path | None:
    """The repository root, or None when `start` is genuinely not inside a repository.

    Raises GitError when git is missing or cannot read a directory that does contain a repository, so that callers
    fail closed instead of reporting "clean".
    """
    start = start or Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    try:
        proc = _git(start, "rev-parse", "--show-toplevel")
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc
    if proc.returncode == 0:
        return Path(proc.stdout.strip())
    if (start / ".git").exists():
        raise GitError(f"git cannot read the repository at {start}: {proc.stderr.strip()[:300]}")
    return None


def baseline_ref(root: Path, explicit: str | None = None) -> str | None:
    candidates = [explicit] if explicit else [os.environ.get("REARCHIVE_PROTECTED_BASE"), *DEFAULT_BASES]
    for ref in candidates:
        if ref and _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0:
            return ref
    if explicit:
        return None
    return "HEAD" if _git(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode == 0 else None


# Tool caches that may appear inside protected directories (hooks and tools run outside the sandbox).
CACHE_SEGMENTS: tuple[str, ...] = ("__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache", ".hypothesis")


def _ignored(path: str) -> bool:
    if any(path == p or path.startswith(p) for p in IGNORED_PREFIXES):
        return True
    return path.endswith((".pyc", ".pyo")) or any(segment in CACHE_SEGMENTS for segment in path.split("/")[:-1])


def _sections(text: str | None, header_pattern: str) -> list[str]:
    """Text of every [header] block whose name matches header_pattern, header line included."""
    if text is None:
        return []
    blocks: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        header = re.match(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$", line)
        if header:
            if current is not None:
                blocks.append("\n".join(current).rstrip())
            current = [line.strip()] if re.match(header_pattern, header.group(1)) else None
        elif current is not None:
            current.append(line.rstrip())
    if current is not None:
        blocks.append("\n".join(current).rstrip())
    return blocks


def _protected_line_values(text: str | None, pattern: str) -> list[str]:
    if text is None:
        return []
    return re.findall(pattern, text, flags=re.MULTILINE)


def check(root: Path, base: str | None = None) -> Result:
    """Compare protected paths with the baseline. Raises GitError when the comparison cannot be made."""
    try:
        return _check(root, base)
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc


def _check(root: Path, base: str | None) -> Result:
    ref = baseline_ref(root, base)
    if ref is None:
        if base:
            return Result(base=base, note=f"baseline {base!r} not found", changed=["<baseline missing>"])
        return Result(base=None, note="no commits yet; nothing to compare")

    diff = _git_ok(root, "diff", "--name-only", "--no-renames", ref, "--", *PROTECTED_PATHS)
    changed = sorted(p for p in diff.splitlines() if p and not _ignored(p))

    others = _git_ok(root, "ls-files", "--others", "--exclude-standard", "--", *PROTECTED_PATHS)
    untracked = sorted(p for p in others.splitlines() if p and not _ignored(p))

    def texts(rel: str) -> tuple[str | None, str | None]:
        shown = _git(root, "show", f"{ref}:{rel}")
        base_text = shown.stdout if shown.returncode == 0 else None
        path = root / rel
        work_text = path.read_text(encoding="utf-8", errors="surrogateescape") if path.exists() else None
        return base_text, work_text

    lines: list[str] = []
    for rel, pattern in PROTECTED_LINES:
        base_text, work_text = texts(rel)
        before = _protected_line_values(base_text, pattern)
        after = _protected_line_values(work_text, pattern)
        if before != after:
            lines.append(f"{rel}: {before or ['<absent>']} -> {after or ['<absent>']}")
    for rel, pattern in PROTECTED_SECTIONS:
        base_text, work_text = texts(rel)
        if _sections(base_text, pattern) != _sections(work_text, pattern):
            lines.append(f"{rel}: a [tool.*] section that configures the checks changed")

    return Result(base=ref, changed=changed, untracked=untracked, lines=lines)


def describe(result: Result) -> str:
    out = [f"PROTECTED PATHS differ from baseline {result.base!r}:"]
    out += [f"  changed:   {p}" for p in result.changed]
    out += [f"  untracked: {p}" for p in result.untracked]
    out += [f"  line:      {line}" for line in result.lines]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="compare protected paths with the baseline")
    c.add_argument("--base", help="baseline ref (default: $REARCHIVE_PROTECTED_BASE, main, master, HEAD)")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        root = repo_root()
        if root is None:
            print(json.dumps({"clean": True, "note": "not a git repository"}) if args.json else "not a git repository")
            return 0
        result = check(root, args.base)
    except (GitError, OSError) as exc:
        message = f"protected-paths CHECK FAILED, treat as not clean: {exc}"
        print(json.dumps({"clean": False, "error": str(exc)}) if args.json else message)
        return 1
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    elif result.clean:
        print(f"protected paths clean (baseline {result.base}){'; ' + result.note if result.note else ''}")
    else:
        print(describe(result))
    return 0 if result.clean else 1


if __name__ == "__main__":
    sys.exit(main())
