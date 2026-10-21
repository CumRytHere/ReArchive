#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): format and lint ONLY the Python file Claude just edited.
# Never formats protected paths and never runs repo-wide (a repo-wide ruff run once rewrote the gate).
# Exit 2 + stderr feeds lint errors back to Claude; exit 0 stays silent.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
file=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("file_path",""))' 2>/dev/null)

[[ -n "$file" && "$file" == *.py && -f "$file" ]] || exit 0
[[ -f "$root/pyproject.toml" ]] || exit 0
command -v uv >/dev/null 2>&1 || exit 0

rel="${file#"$root"/}"
case "$rel" in
  CLAUDE.md|docs/DECISIONS.md|docs/PROJECT_SPEC.md|tests/acceptance/*|tests/contract/*|.claude/*|tools/*|.github/*|src/rearchive/generated/*)
    exit 0 ;;
esac

cd "$root" || exit 0
uv run --no-sync --quiet ruff format --quiet "$rel" >/dev/null 2>&1 || true
if ! out=$(uv run --no-sync --quiet ruff check --fix --quiet "$rel" 2>&1); then
  echo "ruff found problems in $rel — fix them before continuing:" >&2
  echo "$out" | tail -n 40 >&2
  exit 2
fi
exit 0
