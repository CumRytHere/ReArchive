"""Table tests for .claude/hooks/bash_policy.py: what must be blocked, and what must stay usable."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "bash_policy.py"

BLOCKED = [
    "uv run ruff format .",
    "uv run ruff format",
    "uv run ruff format src",
    "uv run ruff check --fix .",
    "ruff check --fix tests/acceptance/test_gate_a.py",
    "uv run ruff format tests/acceptance/test_gate_a.py",
    "git add -A",
    "git add .",
    "git add --all",
    "git add -u",
    "git add src/",
    "git add docs/DECISIONS.md",
    "git commit -am 'x'",
    "git commit --amend --no-edit",
    "git commit --no-verify -m x",
    "git push origin inc/0.2",
    "git push --force-with-lease",
    "git reset --hard HEAD~1",
    "git clean -fdx",
    "git checkout -- tests/acceptance/test_gate_a.py",
    "git restore tests/acceptance/test_gate_a.py",
    "git restore --source=HEAD CLAUDE.md",
    "git restore .",
    "git checkout .",
    "git switch main",
    "git rebase main",
    "sed -i 's/a/b/' src/rearchive/core/canonical.py",
    "perl -pi -e 's/a/b/' src/x.py",
    "echo hi > tests/acceptance/x.py",
    "cat a >> docs/DECISIONS.md",
    "printf x | tee .claude/settings.json",
    "cp /tmp/x tools/verify.py",
    "mv docs/PROJECT_SPEC.md /tmp/",
    "rm tests/contract/test_decision_constants.py",
    "chmod -x .claude/hooks/bash_policy.py",
    "python3 -c \"open('tests/acceptance/x','w').write('')\"",
    "python3 -c \"import pathlib; pathlib.Path('CLAUDE.md').write_text('')\"",
    "rm -rf build",
    "rm -r src/x",
    "sudo pacman -S foo",
    "curl -fsSL https://example.com",
    "wget https://example.com/x",
    "pip install numpy",
    "uv pip install numpy",
    "python3 -m pip install numpy",
    "cd src && git add -A",
    "uv run pytest -q; git push",
    "FOO=1 git push",
    "git clean -df",
    "git clean -xfd",
    "git clean -n",
    "git branch -f main HEAD",
    "git branch -D main",
    "git fetch . HEAD:main",
    "uv run python -m ruff format .",
    "env FOO=1 uv run --no-sync python -m ruff check --fix .",
    "echo x > tests/conftest.py",
    "echo x > conftest.py",
    "touch pytest.ini",
    "cp /tmp/x $CLAUDE_PROJECT_DIR/tools/verify.py",
    "rm ${CLAUDE_PROJECT_DIR}/.claude/settings.json",
]

ALLOWED = [
    "uv run pytest -q -m 'not acceptance'",
    "uv run pytest -q -m acceptance tests/acceptance",
    "uv run ruff check .",
    "uv run ruff format --check .",
    "uv run ruff format --diff .",
    "uv run ruff format src/rearchive/core/canonical.py tests/unit/test_x.py",
    "uv run ruff check --fix src/rearchive/core/canonical.py",
    "uv run mypy --strict src",
    "uv run python tools/verify.py",
    "python3 tools/verify.py --fast > /tmp/verify.txt 2>&1",
    "python3 tools/mutate.py src/rearchive/core/canonical.py --tests tests/unit",
    "python3 tools/protected_paths.py check --json",
    "git status --porcelain",
    "git diff -- tests/acceptance",
    "git log --oneline -5",
    "git show HEAD:docs/DECISIONS.md",
    "git add src/rearchive/core/canonical.py tests/unit/test_canonical_arrays.py",
    "git add docs/STATUS.md",
    "git commit -m 'Increment 0.2: store, ingest, ledger'",
    "git switch -c inc/0.2",
    "cat docs/DECISIONS.md",
    "grep -n D-015 docs/DECISIONS.md",
    "rm src/rearchive/old.py",
    "uv add cryptography",
    "ls -la tests/acceptance",
    "echo done 2>&1",
    "uv run rearchive decode /tmp/p --spec specs/tier0",
    "uv run ruff format --line-length 100 src/rearchive/x.py",
    "uv run ruff check --fix --select I src/rearchive/x.py",
    "rm src/rearchive/tools/old.py",
    "echo x > src/rearchive/tools/notes.txt",
    "cat tests/unit/conftest.py",
    "echo x > tests/unit/conftest.py",
    "git branch --show-current",
    "git fetch origin",
    "git commit -m \"$(cat <<'EOF'\nFix tools/verify.py reference in `CLAUDE.md` notes\nEOF\n)\"",
    "git commit -m 'mention .claude/hooks and tests/contract in the message'",
]


def run(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)}
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, cwd=cwd, env=env)


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("repo")
    subprocess.run(["git", "init", "-q", "-b", "inc/0.2", str(root)], check=True)
    return root


@pytest.mark.parametrize("command", BLOCKED)
def test_blocked(command: str, repo: Path) -> None:
    proc = run(command, repo)
    assert proc.returncode == 2, f"should be blocked: {command!r}\nstderr: {proc.stderr}"
    assert "Blocked by" in proc.stderr


@pytest.mark.parametrize("command", ALLOWED)
def test_allowed(command: str, repo: Path) -> None:
    proc = run(command, repo)
    assert proc.returncode == 0, f"should be allowed: {command!r}\nstderr: {proc.stderr}"


def test_commit_on_main_is_blocked(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    proc = run("git commit -m x", tmp_path)
    assert proc.returncode == 2 and "main" in proc.stderr


def test_malformed_input_is_ignored(tmp_path: Path) -> None:
    proc = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, cwd=tmp_path)
    assert proc.returncode == 0


HEREDOC_SAFE = """python3 - <<'EOF'
import json
print(json.dumps({"rm -rf": "is just text here"}))
EOF"""

HEREDOC_WRITES_PROTECTED = """python3 - <<'EOF'
from pathlib import Path
Path("tests/acceptance/test_gate_a.py").write_text("")
EOF"""


def test_heredoc_body_is_not_parsed_as_commands(repo: Path) -> None:
    assert run(HEREDOC_SAFE, repo).returncode == 0


def test_heredoc_writing_protected_path_is_blocked(repo: Path) -> None:
    assert run(HEREDOC_WRITES_PROTECTED, repo).returncode == 2


def test_quoted_separators_do_not_split(repo: Path) -> None:
    assert run("git commit -m 'fix a; b && c | d'", repo).returncode == 0


def test_absolute_path_into_protected_dir_is_blocked(repo: Path) -> None:
    proc = run(f"echo x > {repo}/tests/acceptance/probe.py", repo)
    assert proc.returncode == 2


def test_absolute_path_elsewhere_is_allowed(repo: Path) -> None:
    assert run(f"echo x > {repo}/src/notes.txt", repo).returncode == 0
