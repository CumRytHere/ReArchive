"""Behavioural tests for tools/protected_paths.py, tools/decision_constants.py, tools/verify.py, tools/mutate.py."""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import decision_constants as dc
import mutate
import protected_paths as pp
import verify

# --------------------------------------------------------------------------- protected_paths


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "docs").mkdir()
    (tmp_path / "tests" / "acceptance").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "CLAUDE.md").write_text("rules\n")
    (tmp_path / "docs" / "DECISIONS.md").write_text("## D-001\n")
    (tmp_path / "docs" / "STATUS.md").write_text("**Current phase:** P0\n**Current increment:** 0.2\n\n## Log\n")
    (tmp_path / "tests" / "acceptance" / "test_gate.py").write_text("def test_x():\n    pass\n")
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "switch", "-q", "-c", "inc/0.2")
    return tmp_path


def test_clean_repo_is_clean(repo: Path) -> None:
    result = pp.check(repo)
    assert result.clean and result.base == "main"


def test_product_and_log_edits_are_allowed(repo: Path) -> None:
    (repo / "src" / "a.py").write_text("x = 2\n")
    with (repo / "docs" / "STATUS.md").open("a") as f:
        f.write("- 2026-10-22 — 0.2 — log entry\n")
    assert pp.check(repo).clean


def test_modified_gate_file_is_caught(repo: Path) -> None:
    (repo / "tests" / "acceptance" / "test_gate.py").write_text("def test_x():\n    assert True\n")
    assert pp.check(repo).changed == ["tests/acceptance/test_gate.py"]


def test_committed_change_on_branch_is_caught(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("weakened\n")
    git(repo, "commit", "-q", "-am", "agent commit")
    assert pp.check(repo).changed == ["CLAUDE.md"], "a commit on the branch must not launder a protected change"


def test_new_untracked_file_in_protected_dir_is_caught(repo: Path) -> None:
    (repo / "tests" / "acceptance" / "probe.py").write_text("")
    assert pp.check(repo).untracked == ["tests/acceptance/probe.py"]


def test_deleted_protected_file_is_caught(repo: Path) -> None:
    (repo / "docs" / "DECISIONS.md").unlink()
    assert pp.check(repo).changed == ["docs/DECISIONS.md"]


def test_current_increment_line_is_protected(repo: Path) -> None:
    status = repo / "docs" / "STATUS.md"
    status.write_text(status.read_text().replace("0.2", "0.3"))
    result = pp.check(repo)
    assert not result.clean and "Current increment" in result.lines[0]


def test_personal_and_generated_paths_are_ignored(repo: Path) -> None:
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.local.json").write_text("{}")
    (repo / ".claude" / "worktrees" / "x").mkdir(parents=True)
    (repo / ".claude" / "worktrees" / "x" / "f").write_text("")
    assert pp.check(repo).clean


def test_explicit_missing_base_is_not_clean(repo: Path) -> None:
    assert not pp.check(repo, "no-such-branch").clean


def test_no_commits_is_reported_not_crashed(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    result = pp.check(tmp_path)
    assert result.clean and result.base is None


# --------------------------------------------------------------------------- decision_constants

DECISIONS = textwrap.dedent(
    """\
    ## D-016 Paths
    text
    ```decision-constants due=0.2
    # comment lines are ignored
    json.decoder.__name__ = "json.decoder"
    ```
    ## D-017 Records
    ```decision-constants due=0.4
    os.sep = "/"
    rearchive_does_not_exist.X = 1
    ```
    """
)


def test_blocks_parse_with_owner_and_due() -> None:
    constants = dc.parse_blocks(DECISIONS)
    assert [(c.decision, c.due, c.symbol) for c in constants] == [
        ("D-016", (0, 2), "json.decoder.__name__"),
        ("D-017", (0, 4), "os.sep"),
        ("D-017", (0, 4), "rearchive_does_not_exist.X"),
    ]


def test_not_due_blocks_are_not_enforced() -> None:
    outcomes = dc.evaluate(dc.parse_blocks(DECISIONS), (0, 2), "closure")
    assert [o.status for o in outcomes] == ["ok", "not_due", "not_due"]


def test_current_increment_blocks_are_in_progress_in_regression_mode() -> None:
    outcomes = dc.evaluate(dc.parse_blocks(DECISIONS), (0, 4), "regression")
    assert [o.status for o in outcomes] == ["ok", "ok", "in_progress"]


def test_current_increment_blocks_are_enforced_at_closure() -> None:
    outcomes = dc.evaluate(dc.parse_blocks(DECISIONS), (0, 4), "closure")
    assert outcomes[2].status == "import_error"
    assert "rearchive_does_not_exist" in outcomes[2].detail


def test_earlier_increment_blocks_are_enforced_in_regression_mode() -> None:
    outcomes = dc.evaluate(dc.parse_blocks(DECISIONS), (0, 5), "regression")
    assert outcomes[2].status == "import_error", "a constant due in an earlier increment must never regress"


def test_missing_module_is_named_in_the_error() -> None:
    with pytest.raises(ModuleNotFoundError, match=r"json\.nonexistent_module"):
        dc.resolve("json.nonexistent_module.X")


def test_all_mode_enforces_future_blocks() -> None:
    outcomes = dc.evaluate(dc.parse_blocks(DECISIONS), (0, 1), "all")
    assert [o.status for o in outcomes] == ["ok", "ok", "import_error"]


@pytest.mark.parametrize(
    ("expected", "actual", "same"),
    [
        (1, 1, True),
        (1, 1.0, False),
        (True, 1, False),
        (True, True, True),
        (("a", "b"), ["a", "b"], True),
        (("a", "b"), ("b", "a"), False),
        (("a", "b"), frozenset({"a", "b"}), True),
        (("a", "a"), frozenset({"a"}), False),
        ({"u2": "uint16"}, {"u2": "uint16"}, True),
        ({"u2": "uint16"}, {"u2": "int16"}, False),
        (1e-9, 1e-9, True),
        ("x", "x", True),
        ("1", 1, False),
    ],
)
def test_equality_is_strict_about_types(expected: object, actual: object, same: bool) -> None:
    assert dc.equal(expected, actual) is same


@pytest.mark.parametrize(
    "bad",
    [
        "## D-001\n```decision-constants\nos.sep = '/'\n```\n",  # no due
        "## D-001\n```decision-constants due=0.4\nos.sep '/'\n```\n",  # no ' = '
        "## D-001\n```decision-constants due=0.4\nsep = '/'\n```\n",  # not dotted
        "## D-001\n```decision-constants due=0.4\nos.sep = open('x')\n```\n",  # not a literal
        "```decision-constants due=0.4\nos.sep = '/'\n```\n",  # no owning decision
        "## D-001\n```decision-constants due=x\nos.sep = '/'\n```\n",  # bad increment
    ],
)
def test_malformed_blocks_are_rejected(bad: str) -> None:
    with pytest.raises(dc.ConstantsFormatError):
        dc.parse_blocks(bad)


def test_current_increment_is_read_from_status() -> None:
    assert dc.current_increment("**Current increment:** 0.10\n") == (0, 10)
    assert dc.current_increment("**Current increment:** 1.2\n") > dc.current_increment("**Current increment:** 0.7\n")
    with pytest.raises(dc.ConstantsFormatError):
        dc.current_increment("no such line")


def test_shipped_decision_pack_parses() -> None:
    pack = Path(__file__).resolve().parents[2] / "docs" / "decisions-pack" / "D-016-to-D-030.md"
    if pack.exists():
        constants = dc.parse_blocks(pack.read_text(encoding="utf-8"))
        assert len({c.symbol for c in constants}) == len(constants)


# --------------------------------------------------------------------------- verify

JUNIT = """<?xml version="1.0"?>
<testsuites><testsuite name="pytest" tests="4">
  <testcase classname="t" name="a"/>
  <testcase classname="t" name="b"><failure message="x"/></testcase>
  <testcase classname="t" name="c"><error message="y"/></testcase>
  <testcase classname="t" name="d"><skipped message="z"/></testcase>
</testsuite></testsuites>"""


def test_junit_counts(tmp_path: Path) -> None:
    path = tmp_path / "r.xml"
    path.write_text(JUNIT)
    counts = verify.junit_counts(path)
    assert counts["summary"] == "1 passed, 1 failed, 1 errors, 1 skipped"
    assert counts["names"]["failed"] == ["t::b"] and counts["names"]["error"] == ["t::c"]


def test_junit_missing_file_is_unavailable(tmp_path: Path) -> None:
    assert verify.junit_counts(tmp_path / "none.xml") == {"available": False}


def test_render_never_hides_a_failing_check() -> None:
    report = {
        "schema": 1,
        "generated_at": "t",
        "branch": "inc/0.2",
        "gate": None,
        "state": {"id": "abc", "head": "abc", "dirty": False, "dirty_files": []},
        "environment": {
            "python": {"implementation": "CPython", "version": "3.12.15", "platform": "linux", "machine": "x86_64"},
            "uv": "uv 0.9",
        },
        "required": ["unit", "protected_paths"],
        "checks": {
            "unit": {"exit": 1, "counts": {"available": True, "summary": "1 passed, 1 failed, 0 errors, 0 skipped"}},
            "protected_paths": {
                "exit": 1,
                "clean": False,
                "changed": ["CLAUDE.md"],
                "untracked": [],
                "protected_lines": [],
            },
        },
        "failing": ["unit", "protected_paths"],
        "verdict": "FAIL",
    }
    text = verify.render(report)
    assert "**FAIL**" in text and "| unit | FAIL |" in text and "DIFFERS: CLAUDE.md" in text


# --------------------------------------------------------------------------- mutate

SAMPLE = textwrap.dedent(
    '''\
    """Docstring is not mutated."""

    LIMIT = 8


    def check(rank: int, ok: bool = True) -> int:
        if rank > LIMIT:
            raise ValueError("too big")
        if not ok and rank == 0:
            return -1
        return rank + 1
    '''
)


def test_sites_are_found_and_stable() -> None:
    sites = mutate.sites_for(SAMPLE, None, None)
    kinds = [s.kind for s in sites]
    assert kinds.count("if") == 4 and "raise" in kinds and "compare" in kinds and "boolop" in kinds
    assert mutate.sites_for(SAMPLE, None, None) == sites


def test_every_site_yields_a_valid_distinct_mutant() -> None:
    sites = mutate.sites_for(SAMPLE, None, None)
    original = ast.dump(ast.parse(SAMPLE))
    for site in sites:
        mutated = mutate.mutant_source(SAMPLE, None, None, site.index)
        assert mutated is not None, site
        assert ast.dump(ast.parse(mutated)) != original, f"site {site} produced no change"


def test_guard_removal_mutant_disables_the_raise() -> None:
    sites = mutate.sites_for(SAMPLE, None, None)
    [guard] = [s for s in sites if s.kind == "if" and "False" in s.description and s.line == 7]
    namespace: dict[str, object] = {}
    exec(mutate.mutant_source(SAMPLE, None, None, guard.index) or "", namespace)
    assert namespace["check"](100) == 101  # type: ignore[operator]


def test_function_filter_limits_sites() -> None:
    assert mutate.sites_for(SAMPLE, "nothing_called_this", None) == []
    assert all(s.line >= 6 for s in mutate.sites_for(SAMPLE, "check", None))


def test_refuses_to_mutate_tests_and_tools(capsys: pytest.CaptureFixture[str]) -> None:
    code = mutate.main(["tools/protected_paths.py", "--tests", "tools/tests"])
    assert code == 2 and "refusing" in capsys.readouterr().err


def test_cli_runs_without_project_environment() -> None:
    for tool in ("protected_paths.py", "decision_constants.py", "verify.py", "mutate.py"):
        proc = subprocess.run(
            [sys.executable, str(Path(pp.__file__).parent / tool), "--help"], capture_output=True, text=True
        )
        assert proc.returncode == 0, (tool, proc.stderr)


def test_backup_names_round_trip_for_dunder_files() -> None:
    from urllib.parse import quote, unquote

    for rel in ("src/rearchive/__init__.py", "src/a__b/c.py", "src/x y/%z.py"):
        assert unquote(quote(rel, safe="")) == rel
        assert "/" not in quote(rel, safe="")


def test_tool_caches_inside_protected_dirs_are_ignored(repo: Path) -> None:
    for rel in (
        "tests/acceptance/__pycache__/x.cpython-313.pyc",
        ".claude/hooks/__pycache__/y.pyc",
        "tools/.ruff_cache/0.16/abc",
        "tests/contract/.hypothesis/examples/z",
    ):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_bytes(b"cache")
    assert pp.check(repo).clean


def test_a_real_file_beside_caches_is_still_caught(repo: Path) -> None:
    (repo / "tests" / "acceptance" / "__pycache__").mkdir(parents=True)
    (repo / "tests" / "acceptance" / "__pycache__" / "x.pyc").write_bytes(b"cache")
    (repo / "tests" / "acceptance" / "probe.py").write_text("")
    assert pp.check(repo).untracked == ["tests/acceptance/probe.py"]
