#!/usr/bin/env python3
"""PostToolUse (Edit|Write|Bash) and Stop hook: protected paths must equal the owner's baseline (main).

However a change happened — editor tool, formatter, script, git command — if a protected path or a
protected STATUS line differs from the baseline, Claude is blocked and told to report, not repair.
Logic lives in tools/protected_paths.py so CI and tools/verify.py use exactly the same rule.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / "tools"))

try:
    import protected_paths
except ImportError:  # tools/ missing: fail loudly rather than silently allowing everything
    print("protected_guard: tools/protected_paths.py is missing; the owner must restore it.", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    if payload.get("stop_hook_active"):
        return 0  # already blocked once this stop; let Claude stop and the owner see the report

    try:
        if protected_paths.repo_root(ROOT) is None:
            return 0  # not a repository at all: nothing to protect
        result = protected_paths.check(ROOT)
    except Exception as exc:  # fail closed: an unverifiable state is treated as a changed one
        print(
            f"protected_guard could not verify protected paths ({type(exc).__name__}: {exc}).\n"
            "Stop and tell the owner; do not continue until the check runs again.",
            file=sys.stderr,
        )
        return 2
    if result.clean:
        return 0
    print(
        protected_paths.describe(result)
        + "\n\nDo NOT revert, restore, re-stage or edit these paths. Stop work now and tell the owner:\n"
        "  1. exactly which paths changed (list above);\n"
        "  2. the last commands or edits you made before this message.\n"
        "If the owner changed them, they commit on main and merge main into this branch.\n"
        "If main moved on, the owner runs `git merge main` on this branch.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
