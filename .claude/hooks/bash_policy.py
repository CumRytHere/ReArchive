#!/usr/bin/env python3
"""PreToolUse hook for Bash: block command shapes that have already caused damage in this project.

Exit 2 with a reason on stderr blocks the command and shows the reason to Claude (also inside subagents).
Exit 0 lets the permission system and the sandbox decide. This is a tripwire for honest mistakes, not a
security boundary: the sandbox and the protected-paths guard are the backstops.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTECTED = (
    "CLAUDE.md",
    "docs/DECISIONS.md",
    "docs/PROJECT_SPEC.md",
    "tests/acceptance",
    "tests/contract",
    ".claude",
    "tools",
    ".github",
    "conftest.py",
    "tests/conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
)
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
RUFF_VALUE_OPTIONS = {
    "--select",
    "--extend-select",
    "--ignore",
    "--extend-ignore",
    "--fixable",
    "--unfixable",
    "--line-length",
    "--target-version",
    "--config",
    "--output-format",
    "-o",
    "--output-file",
    "--per-file-ignores",
    "--exclude",
    "--extend-exclude",
    "--cache-dir",
    "--stdin-filename",
    "--range",
}
INLINE_WRITE = re.compile(
    r"\bopen\(|write_text|write_bytes|\.unlink|shutil\.|os\.remove|os\.rename|"
    r"os\.replace|writeFile|>\s*\S"
)
REDIRECT = re.compile(r"\d*>>?(?!&)\s*([^\s;|&<>]+)")


def write_targets(cmd: str, argv: list[str], raw: str) -> list[str]:
    """Best-effort list of paths a command would create, modify or delete."""
    targets = [m.group(1) for m in REDIRECT.finditer(raw)]
    positional = [a for a in argv[1:] if not a.startswith("-")]
    if cmd == "tee":
        targets += positional
    elif cmd in ("cp", "install", "ln", "rsync") and positional:
        targets.append(positional[-1])
    elif cmd == "mv" or cmd in ("rm", "rmdir", "unlink", "chmod", "chown", "touch", "truncate"):
        targets += positional
    elif cmd == "dd":
        targets += [a[3:] for a in argv[1:] if a.startswith("of=")]
    elif cmd in ("tar", "unzip", "patch"):
        targets.append(raw)
    return targets


def block(reason: str) -> None:
    print(f"Blocked by .claude/hooks/bash_policy.py: {reason}", file=sys.stderr)
    sys.exit(2)


def mentions_protected(text: str) -> str | None:
    """A protected path named relative to the project root, absolutely, or via $CLAUDE_PROJECT_DIR.

    Only path *starts* count: `src/rearchive/tools/x.py` is not `tools/`.
    """
    prefixes = [r"(^|[\s'\"=(])(\./)?", r"\$\{?CLAUDE_PROJECT_DIR\}?/"]
    if ROOT:
        prefixes.append(re.escape(ROOT.rstrip("/")) + "/")
    for path in PROTECTED:
        for prefix in prefixes:
            if re.search(prefix + re.escape(path) + r"($|[\s'\"/*);])", text):
                return path
    return None


def words(segment: str) -> list[str]:
    try:
        return shlex.split(segment, comments=False, posix=True)
    except ValueError:
        return segment.split()


def strip_env(argv: list[str]) -> list[str]:
    """Unwrap launchers so the command that actually runs is inspected: env assignments, `env`, `uv run`,
    `uvx`, `python -m`, `npx`, `exec`, `nice`, `time` — repeatedly, in any combination."""
    while True:
        before = list(argv)
        i = 0
        while i < len(argv) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[i]):
            i += 1
        argv = argv[i:]
        if argv[:1] in (["env"], ["exec"], ["nice"], ["time"], ["command"]):
            argv = argv[1:]
        elif argv[:2] == ["uv", "run"]:
            rest = argv[2:]
            while rest and rest[0].startswith("-"):
                takes_value = rest[0] in ("--with", "--python", "--package", "--group", "--env-file", "--directory")
                rest = rest[2:] if takes_value else rest[1:]
            argv = rest
        elif argv[:1] in (["uvx"], ["npx"]):
            argv = argv[1:]
        elif len(argv) >= 3 and Path(argv[0]).name.startswith("python") and argv[1] == "-m":
            argv = argv[2:]
        if argv == before:
            return argv


def current_branch() -> str:
    proc = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    return proc.stdout.strip()


def check_git(argv: list[str], raw: str) -> None:
    sub = argv[1] if len(argv) > 1 else ""
    args = argv[2:]
    if sub == "add":
        blanket = {"-A", "--all", ".", "-u", "--update", ":/", "*", "--no-ignore-removal"}
        if blanket & set(args) or any(a.startswith(":/") or a.endswith("/") for a in args):
            block(
                "stage files one by one (`git add path/to/file.py`); blanket adds have changed the index "
                "under a running reviewer before."
            )
        if any(mentions_protected(a) for a in args):
            block("protected paths are committed by the owner, not staged by Claude.")
    if sub == "push":
        block("publishing is owner-only. Report the branch and commit; the owner pushes.")
    if sub == "commit":
        if any(a in ("-a", "--all", "--amend", "--no-verify", "-n") or re.match(r"^-[a-zA-Z]*a", a) for a in args):
            block("no `commit -a`, `--amend` or `--no-verify`: stage named files and make a new commit.")
        if current_branch() in ("main", "master"):
            block("never commit on main. Work on the increment branch `inc/<n>`; the owner merges.")
    if sub == "clean" or (sub == "reset" and "--hard" in args):
        block("destructive git command. Describe what you want undone and let the owner do it.")
    if sub == "branch" and (
        any(a in ("-f", "--force", "-D", "-M", "-C", "--delete") for a in args) or {"main", "master"} & set(args)
    ):
        block("branch surgery is owner-only (it can move the protected-paths baseline).")
    if sub == "fetch" and any(re.search(r":(refs/heads/)?(main|master)$", a) for a in args):
        block("fetching into main moves the protected-paths baseline; the owner updates main.")
    if sub in ("checkout", "restore", "rm", "mv") and mentions_protected(" ".join(args)):
        block("do not restore, remove or move protected paths. If one changed, stop and tell the owner.")
    if sub in ("checkout", "restore") and any(a in (".", ":/", "*") for a in args):
        block("blanket restore would discard work, including owner edits. Name the files, or ask the owner.")
    if sub in ("checkout", "switch") and any(a in ("main", "master") for a in args):
        block("stay on the increment branch; the owner handles main.")
    if sub in ("rebase", "filter-branch", "filter-repo", "update-ref", "replace"):
        block("history rewriting is owner-only.")
    if sub == "worktree" and args[:1] == ["remove"]:
        block("worktrees are created and removed by the owner (tools/audit.sh).")


def check_ruff(argv: list[str]) -> None:
    mode = "format" if "format" in argv[1:3] else ("check" if "check" in argv[1:3] else "")
    writes = (mode == "format" and not {"--check", "--diff"} & set(argv)) or (
        mode == "check" and {"--fix", "--unsafe-fixes"} & set(argv) and "--diff" not in argv
    )
    if not writes:
        return
    targets: list[str] = []
    skip = False
    for a in argv[1:]:
        if skip:
            skip = False
        elif a in RUFF_VALUE_OPTIONS:
            skip = True
        elif not a.startswith("-") and a not in ("format", "check"):
            targets.append(a)
    if not targets or any(not t.endswith(".py") or Path(t).is_dir() for t in targets):
        block(
            "ruff may only rewrite named .py files (`uv run ruff format src/x.py`). Repo-wide ruff rewrote "
            "tests/acceptance/test_gate_a.py once; use `--check` for whole-repo checks."
        )
    if any(mentions_protected(t) for t in targets):
        block("ruff must not rewrite protected files.")


def check_segment(segment: str) -> None:
    raw = segment.strip()
    if not raw:
        return
    argv = strip_env(words(raw))
    if not argv:
        return
    cmd = Path(argv[0]).name

    if cmd in ("sudo", "su", "doas"):
        block("no privilege escalation.")
    if cmd in ("curl", "wget", "nc", "ncat", "scp", "ssh", "ftp"):
        block("no network tools. If a document is needed, ask the owner to download it into docs/references/.")
    if (
        cmd in ("pip", "pip3")
        or (cmd in ("python", "python3") and argv[1:3] == ["-m", "pip"])
        or (argv[:2] == ["uv", "pip"])
    ):
        block("dependencies change only through `uv add` / `uv remove` (which ask the owner).")
    if cmd == "rm" and any(re.match(r"^-[a-zA-Z]*[rR]", a) or a == "--recursive" for a in argv[1:]):
        block("no recursive delete. Name the files, or ask the owner.")
    if cmd == "git":
        check_git(argv, raw)
    if cmd == "ruff":
        check_ruff(argv)
    if cmd in ("sed", "perl") and any(re.match(r"^-[a-zA-Z]*i", a) or a.startswith("--in-place") for a in argv[1:]):
        block("edit files with the Edit tool, never `sed -i`/`perl -i`: those have silently no-op'd here.")
    if cmd in ("claude",) and any("dangerously" in a for a in argv):
        block("no permission bypass.")
    for target in write_targets(cmd, argv, raw):
        protected = mentions_protected(target)
        if protected:
            block(
                f"this command writes to protected path `{protected}`. Protected paths change only by owner "
                "commits; if one needs to change, say so and stop."
            )


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
INLINE_SCRIPT = re.compile(r"(^|[\s;&|(])(python3?|node|ruby|perl|bash|sh|zsh)\b[^\n;&|]*?\s(-c|-e|-)(\s|$)|<<")


def strip_heredocs(command: str) -> str:
    """Remove heredoc bodies so their lines are not mistaken for commands."""
    out, lines, i = [], command.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        match = HEREDOC.search(line)
        i += 1
        if match:
            delimiter = match.group(2)
            while i < len(lines) and lines[i].strip() != delimiter:
                i += 1
            i += 1
    return "\n".join(out)


def split_commands(command: str) -> list[str]:
    """Split on ; && || | and newlines, but not inside quotes."""
    segments, current, quote, i = [], [], "", 0
    while i < len(command):
        ch = command[i]
        if quote:
            current.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(command):
                current.append(command[i + 1])
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
            current.append(ch)
        elif ch == "\\" and i + 1 < len(command):
            current.append(ch + command[i + 1])
            i += 1
        elif command.startswith(("&&", "||"), i):
            segments.append("".join(current))
            current = []
            i += 1
        elif ch in ";|\n":
            segments.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    segments.append("".join(current))
    return [seg for seg in segments if seg.strip()]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not isinstance(command, str):
        return 0
    # A commit message may legitimately mention protected paths, backticks or heredocs; it writes nothing.
    is_commit_message = bool(re.match(r"^\s*git\s+commit\b", command))
    if not is_commit_message:
        if re.search(r"\$\(|`", command) and mentions_protected(command):
            block("command substitution touching protected paths; run the parts separately.")
        if INLINE_SCRIPT.search(command) and mentions_protected(command) and INLINE_WRITE.search(command):
            block("inline script that appears to write near a protected path. Use the Edit tool on product files.")
    for segment in split_commands(strip_heredocs(command)):
        check_segment(segment)
    return 0


if __name__ == "__main__":
    sys.exit(main())
