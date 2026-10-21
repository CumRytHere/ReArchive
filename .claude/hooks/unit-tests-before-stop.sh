#!/usr/bin/env bash
# Stop hook: Claude may not finish a turn with failing unit or contract tests.
# Runs only when Python files changed; the acceptance gate is excluded (red until its gate).
# Exit 2 + stderr makes Claude continue and see the failures; the loop guard lets it stop on the retry.
set -uo pipefail

input=$(cat)
active=$(printf '%s' "$input" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active", False)).lower())' 2>/dev/null)
[[ "$active" == "true" ]] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
[[ -f pyproject.toml ]] || exit 0
command -v uv >/dev/null 2>&1 || exit 0

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git status --porcelain -- '*.py' '*.ksy' '*.yaml' | grep -q . || exit 0
fi

out=$(uv run --no-sync --quiet pytest -q -m "not acceptance" -x --no-header -p no:cacheprovider 2>&1)
code=$?
# 0 = passed, 5 = no tests collected yet
if [[ $code -ne 0 && $code -ne 5 ]]; then
  echo "Unit or contract tests are failing. Fix them (never by weakening, skipping or deleting tests) before finishing:" >&2
  echo "$out" | tail -n 40 >&2
  exit 2
fi
exit 0
