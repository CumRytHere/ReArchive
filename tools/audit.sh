#!/usr/bin/env bash
# Create a frozen audit snapshot of a commit, outside the repository, and optionally run the headless auditor
# with a restricted tool list (no edits, staging, commits or mutation runs; it can still run Python, so the script
# checks the snapshot is unchanged afterwards).
#
#   tools/audit.sh [COMMIT] [--run] [--model opus] [--max-turns 150]
#
# The snapshot is a detached worktree at ../<repo>-audit-<sha7>. It cannot change while an audit reads it, and
# the auditor session runs there, not in your working tree. Owner-run; Claude sessions are blocked from removing
# worktrees. Remove later with: git worktree remove ../<repo>-audit-<sha7> && git worktree prune
set -euo pipefail

commit_arg="HEAD"; run=0; model="opus"; max_turns=150
while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) run=1 ;;
    --model) model="$2"; shift ;;
    --max-turns) max_turns="$2"; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) commit_arg="$1" ;;
  esac
  shift
done

root=$(git rev-parse --show-toplevel)
commit=$(git -C "$root" rev-parse --verify "${commit_arg}^{commit}")
short=${commit:0:7}
name=$(basename "$root")
dir="$(cd "$root/.." && pwd)/${name}-audit-${short}"

if [[ "$commit_arg" == "HEAD" ]] && [[ -n "$(git -C "$root" status --porcelain)" ]]; then
  echo "warning: uncommitted changes in $root are NOT part of the audit snapshot" >&2
fi

if [[ -e "$dir" ]]; then
  echo "reusing existing snapshot $dir"
else
  git -C "$root" worktree add --detach "$dir" "$commit" >/dev/null
fi

actual=$(git -C "$dir" rev-parse HEAD)
[[ "$actual" == "$commit" ]] || { echo "snapshot HEAD $actual != $commit" >&2; exit 1; }
[[ -z "$(git -C "$dir" status --porcelain)" ]] || { echo "snapshot $dir is not clean" >&2; exit 1; }
for required in src tests/unit tests/acceptance docs/DECISIONS.md; do
  [[ -e "$dir/$required" ]] || { echo "snapshot lacks $required: wrong commit?" >&2; exit 1; }
done
(cd "$dir" && uv sync --locked --quiet)

# The snapshot's guard must compare against the snapshot's own commit, not the live `main`, which moves on.
# settings.local.json is gitignored, so the snapshot stays clean.
mkdir -p "$dir/.claude"
printf '{\n  "env": {"REARCHIVE_PROTECTED_BASE": "HEAD"}\n}\n' > "$dir/.claude/settings.local.json"
if [[ -n "$(git -C "$dir" status --porcelain)" ]]; then
  echo "warning: .claude/settings.local.json is not ignored in this snapshot; the guard may compare against main" >&2
fi

echo "audit snapshot: $dir"
echo "commit:         $commit ($(git -C "$dir" log -1 --format=%s))"
echo "files tracked:  $(git -C "$dir" ls-files | wc -l | tr -d ' ')"

prompt_file="$dir/docs/prompts/audit.md"
[[ -f "$prompt_file" ]] || prompt_file="$root/docs/prompts/audit.md"
out="$(dirname "$dir")/${name}-audit-${short}.json"

if [[ $run -eq 0 ]]; then
  cat <<EOF

Interactive audit: open "$dir" in a NEW VS Code window, start Claude Code in Plan mode, and paste
$prompt_file (plus any focus notes from /audit-prep).

Headless audit: tools/audit.sh $short --run
EOF
  exit 0
fi

command -v claude >/dev/null || { echo "claude CLI not found" >&2; exit 1; }
echo "running headless auditor (model $model, max $max_turns turns) -> $out"
cd "$dir"
export REARCHIVE_PROTECTED_BASE=HEAD
claude -p "$(cat "$prompt_file")

Audit target: commit $commit in this directory." \
  --model "$model" --max-turns "$max_turns" --output-format json \
  --permission-mode default \
  --allowedTools "Read" "Grep" "Glob" \
    "Bash(git log:*)" "Bash(git show:*)" "Bash(git diff:*)" "Bash(git ls-files:*)" "Bash(git rev-parse:*)" \
    "Bash(uv run --no-sync pytest:*)" "Bash(uv run --no-sync ruff check:*)" "Bash(uv run --no-sync ruff format --check:*)" \
    "Bash(uv run --no-sync mypy:*)" "Bash(uv run --no-sync python:*)" "Bash(python3 tools/verify.py:*)" \
    "Bash(uv run --no-sync python tools/decision_constants.py:*)" "Bash(python3 tools/protected_paths.py:*)" \
  --disallowedTools "Edit" "Write" "NotebookEdit" "WebFetch" "WebSearch" \
    "Bash(git add:*)" "Bash(git commit:*)" "Bash(git switch:*)" "Bash(git checkout:*)" "Bash(git restore:*)" \
    "Bash(python3 tools/mutate.py:*)" "Bash(uv add:*)" "Bash(uv remove:*)" "Bash(uv lock:*)" \
  > "$out"
echo "audit transcript: $out"
python3 - "$out" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
print("\n" + str(data.get("result", data))[:20000])
PY
echo
if [[ -n "$(git -C "$dir" status --porcelain)" ]]; then
  echo "WARNING: the auditor changed the snapshot (it must be read-only). Treat its findings with care:" >&2
  git -C "$dir" status --porcelain >&2
else
  echo "snapshot unchanged by the audit (git status clean)"
fi
