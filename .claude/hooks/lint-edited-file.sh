#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): format and lint the Python file Claude just edited.
# Exit 2 + stderr feeds lint errors back to Claude; exit 0 stays silent.
set -uo pipefail

file=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("file_path",""))' 2>/dev/null)

[[ -n "$file" && "$file" == *.py && -f "$file" ]] || exit 0
[[ -f "${CLAUDE_PROJECT_DIR:-.}/pyproject.toml" ]] || exit 0
command -v uv >/dev/null 2>&1 || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
uv run --quiet ruff format --quiet "$file" >/dev/null 2>&1 || true
if ! out=$(uv run --quiet ruff check --fix --quiet "$file" 2>&1); then
  echo "ruff found problems in $file — fix them before continuing:" >&2
  echo "$out" | tail -n 40 >&2
  exit 2
fi
exit 0
