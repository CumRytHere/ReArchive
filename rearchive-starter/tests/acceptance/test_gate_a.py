"""Gate A acceptance tests — human-owned. Claude Code must never edit this directory.

These are black-box tests: they drive the command-line tools below and read their JSON.
Internals are free to change; this contract is not, unless the human changes it.

CLI contract for Gate A
-----------------------
rearchive-bench generate --tier 0 --variant {anchored,attested,no-anchor} --seed N --count K \
    --out FILES_DIR --truth TRUTH_DIR --evidence EVIDENCE_DIR
rearchive-bench score PACKAGE_DIR --truth TRUTH_DIR --json
rearchive init PROJECT_DIR
rearchive ingest PROJECT_DIR FILES_DIR
rearchive decode PROJECT_DIR --spec SPEC_DIR          (may exit non-zero if some files failed,
                                                       but every file must still be recorded)
rearchive validate PROJECT_DIR --evidence EVIDENCE_DIR [--oracle TRUTH_DIR]
rearchive report PROJECT_DIR --json
rearchive package PROJECT_DIR --out PACKAGE_DIR
rearchive verify PACKAGE_DIR --json                  (exit 0 if and only if integrity passes)

Test hook: REARCHIVE_TASK_DELAY_MS=<int> makes `decode` sleep that long between files.

JSON fields the tests rely on (extra fields are fine):
  report: {"files":  [{"source_relpath", "sha256", "canonical_sha256", "outcome",
                       "coverage": {"explained", "padding", "unexplained"}}],
           "claims": [{"id", "type", "property", "file", "status", "bases": [...]}],
           "ledger": {"head", "valid"}}
  verify: {"integrity": "pass|fail", "replay": "pass|fail|not_run",
           "problems": [{"path", "reason"}]}
  score:  {"structural_recovery", "value_recovery", "semantic_overreach", "correct_abstention"}

Vocabularies (from docs/PROJECT_SPEC.md §7.2 and §13.12):
  claim status: candidate | supported | disputed | contradicted | unresolved
  evidence bases include: structural, hidden_ground_truth, analytic_oracle,
      independent_implementation, vendor_documentation, attestation, physical_anchor,
      reconciliation, plausibility, self_consistency
  file outcome: semantically_reconciled | documented_lossy | incomplete | unverified | failed
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO / "specs" / "tier0"
GOLDEN = Path(__file__).resolve().parent / "golden" / "tier0_seed7.json"
SEED = 7
COUNT = 6
VARIANTS = ("anchored", "attested", "no-anchor")
OUTCOMES = {"semantically_reconciled", "documented_lossy", "incomplete", "unverified", "failed"}
STATUSES = {"candidate", "supported", "disputed", "contradicted", "unresolved"}


# --------------------------------------------------------------------------- helpers


def _bin(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        pytest.fail(f"`{name}` is not on PATH. Run the gate with `uv run pytest -q -m acceptance`.")
    return path


def run(
    *args: str | Path, ok: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = [_bin(str(args[0])), *(str(a) for a in args[1:])]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, env={**os.environ, **(env or {})}, timeout=900
    )
    if ok and proc.returncode != 0:
        pytest.fail(
            f"{' '.join(cmd)} exited {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout[-4000:]}\n--- stderr ---\n{proc.stderr[-4000:]}"
        )
    return proc


def run_json(*args: str | Path, ok: bool = True) -> tuple[dict[str, Any], int]:
    proc = run(*args, ok=ok)
    try:
        return json.loads(proc.stdout), proc.returncode
    except json.JSONDecodeError as exc:
        pytest.fail(f"{args[0]} {args[1]} did not print JSON on stdout ({exc}):\n{proc.stdout[:2000]}")


def file_hashes(directory: Path) -> dict[str, str]:
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def snapshot(directory: Path) -> dict[str, tuple[str, int, int]]:
    out: dict[str, tuple[str, int, int]] = {}
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            st = p.stat()
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            out[p.relative_to(directory).as_posix()] = (digest, st.st_mtime_ns, stat.S_IMODE(st.st_mode))
    return out


def set_read_only(directory: Path, read_only: bool) -> None:
    paths = sorted(directory.rglob("*"), key=lambda p: len(p.parts), reverse=True) + [directory]
    for p in paths:
        if p.is_dir():
            p.chmod(0o555 if read_only else 0o755)
        else:
            p.chmod(0o444 if read_only else 0o644)


def generate(root: Path, variant: str, seed: int = SEED, count: int = COUNT) -> tuple[Path, Path, Path]:
    files, truth, evidence = root / "files", root / "truth", root / "evidence"
    run(
        "rearchive-bench", "generate", "--tier", "0", "--variant", variant,
        "--seed", str(seed), "--count", str(count),
        "--out", files, "--truth", truth, "--evidence", evidence,
    )  # fmt: skip
    return files, truth, evidence


@dataclass(frozen=True)
class Pipeline:
    files: Path
    truth: Path
    evidence: Path
    project: Path
    package: Path
    report: dict[str, Any]
    score: dict[str, Any]
    before: dict[str, tuple[str, int, int]]


def full_pipeline(root: Path, variant: str, *, read_only: bool = True) -> Pipeline:
    files, truth, evidence = generate(root, variant)
    if read_only:
        set_read_only(files, True)
    before = snapshot(files)
    project, package = root / "project", root / "package"
    run("rearchive", "init", project)
    run("rearchive", "ingest", project, files)
    run("rearchive", "decode", project, "--spec", SPEC_DIR)
    run("rearchive", "validate", project, "--evidence", evidence, "--oracle", truth)
    report, _ = run_json("rearchive", "report", project, "--json")
    run("rearchive", "package", project, "--out", package)
    score, _ = run_json("rearchive-bench", "score", package, "--truth", truth, "--json")
    return Pipeline(files, truth, evidence, project, package, report, score, before)


def canonical_hashes(report: dict[str, Any]) -> dict[str, str | None]:
    return {f["source_relpath"]: f["canonical_sha256"] for f in report["files"]}


def claims_for(report: dict[str, Any], *, type_: str, prop: str | None = None) -> list[dict[str, Any]]:
    return [
        c
        for c in report["claims"]
        if c["type"] == type_ and (prop is None or c.get("property") == prop)
    ]


@pytest.fixture(scope="session")
def runs(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Pipeline]]:
    result: dict[str, Pipeline] = {}
    try:
        for variant in VARIANTS:
            root = tmp_path_factory.mktemp(variant.replace("-", "_"))
            result[variant] = full_pipeline(root, variant)
        yield result
    finally:
        for p in result.values():
            set_read_only(p.files, False)


# --------------------------------------------------------------------------- boundaries


def _imports(package_dir: Path) -> set[tuple[str, str]]:
    if not package_dir.is_dir():
        pytest.fail(f"expected package directory {package_dir.relative_to(REPO)} to exist")
    found: set[tuple[str, str]] = set()
    for py in package_dir.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        rel = py.relative_to(REPO).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update((rel, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add((rel, node.module))
    return found


def test_product_never_imports_the_benchmark() -> None:
    offenders = {
        (f, m) for f, m in _imports(REPO / "src" / "rearchive") if m.split(".")[0] == "rearchive_bench"
    }
    assert not offenders, f"rearchive must not import rearchive_bench (D-012): {sorted(offenders)}"


def test_benchmark_never_imports_the_product() -> None:
    offenders = {
        (f, m) for f, m in _imports(REPO / "src" / "rearchive_bench") if m.split(".")[0] == "rearchive"
    }
    assert not offenders, (
        "rearchive_bench must talk to the product only through its CLI and files, so truth "
        f"is never computed with product code (D-012): {sorted(offenders)}"
    )


def test_generator_is_deterministic_per_seed(tmp_path: Path) -> None:
    a = generate(tmp_path / "a", "no-anchor")
    b = generate(tmp_path / "b", "no-anchor")
    c = generate(tmp_path / "c", "no-anchor", seed=SEED + 1)
    assert file_hashes(a[0]) == file_hashes(b[0]), "same seed must give byte-identical files"
    assert file_hashes(a[0]) != file_hashes(c[0]), "different seeds must give different files"
    assert not (set(file_hashes(a[0])) & set(file_hashes(a[1]))), "truth must not sit in the archive"


# --------------------------------------------------------------------------- preservation


def test_sources_are_never_modified(runs: dict[str, Pipeline]) -> None:
    for variant, p in runs.items():
        assert snapshot(p.files) == p.before, f"{variant}: source bytes, mtimes or modes changed"


def test_every_file_is_accounted_for(runs: dict[str, Pipeline]) -> None:
    for variant, p in runs.items():
        on_disk = set(file_hashes(p.files))
        reported = {f["source_relpath"] for f in p.report["files"]}
        assert reported == on_disk, f"{variant}: report must list exactly the files on disk"
        for f in p.report["files"]:
            assert f["sha256"] == file_hashes(p.files)[f["source_relpath"]]
            assert f["outcome"] in OUTCOMES


def test_every_byte_is_explained_on_tier0(runs: dict[str, Pipeline]) -> None:
    for variant, p in runs.items():
        for f in p.report["files"]:
            size = (p.files / f["source_relpath"]).stat().st_size
            cov = f["coverage"]
            assert cov["unexplained"] == 0, f"{variant}/{f['source_relpath']}: unexplained bytes"
            assert cov["explained"] + cov["padding"] == size


# --------------------------------------------------------------------------- correctness


def test_structure_and_values_match_hidden_truth(runs: dict[str, Pipeline]) -> None:
    for variant, p in runs.items():
        assert p.score["structural_recovery"] == 1.0, variant
        assert p.score["value_recovery"] == 1.0, variant
        for c in claims_for(p.report, type_="value"):
            assert c["status"] == "supported", (variant, c)
            assert "hidden_ground_truth" in c["bases"], (variant, c)


@pytest.mark.parametrize(
    ("variant", "expected_status", "must_include", "must_exclude"),
    [
        ("anchored", "supported", {"physical_anchor"}, {"attestation", "hidden_ground_truth"}),
        ("attested", "supported", {"attestation"}, {"physical_anchor", "hidden_ground_truth"}),
        ("no-anchor", "unresolved", set(), {"physical_anchor", "attestation", "hidden_ground_truth"}),
    ],
)
def test_unit_claim_follows_the_available_evidence(
    runs: dict[str, Pipeline],
    variant: str,
    expected_status: str,
    must_include: set[str],
    must_exclude: set[str],
) -> None:
    claims = claims_for(runs[variant].report, type_="semantic", prop="unit")
    assert claims, f"{variant}: no semantic unit claim produced"
    for c in claims:
        assert c["status"] == expected_status, (variant, c)
        bases = set(c["bases"])
        assert must_include <= bases, (variant, c)
        assert not (must_exclude & bases), (variant, c)


def test_no_semantic_overreach_and_correct_abstention(runs: dict[str, Pipeline]) -> None:
    for variant, p in runs.items():
        assert p.score["semantic_overreach"] == 0.0, variant
    assert runs["no-anchor"].score["correct_abstention"] == 1.0


def test_all_statuses_are_from_the_vocabulary(runs: dict[str, Pipeline]) -> None:
    for p in runs.values():
        assert {c["status"] for c in p.report["claims"]} <= STATUSES


# --------------------------------------------------------------------------- package


def test_package_verifies(runs: dict[str, Pipeline]) -> None:
    for variant, p in runs.items():
        result, code = run_json("rearchive", "verify", p.package, "--json")
        assert code == 0, variant
        assert result["integrity"] == "pass", variant
        assert result["replay"] == "pass", variant
        assert p.report["ledger"]["valid"] is True, variant


def test_tampering_is_detected(runs: dict[str, Pipeline], tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    shutil.copytree(runs["anchored"].package, pkg)
    payload = sorted(p for p in (pkg / "data").rglob("*") if p.is_file() and p.stat().st_size > 0)
    assert payload, "package has no payload under data/ (BagIt layout, D-010)"
    target = payload[0]
    raw = bytearray(target.read_bytes())
    raw[len(raw) // 2] ^= 0xFF
    target.write_bytes(bytes(raw))

    result, code = run_json("rearchive", "verify", pkg, "--json", ok=False)
    assert code != 0
    assert result["integrity"] == "fail"
    rel = target.relative_to(pkg).as_posix()
    assert any(rel in prob["path"] for prob in result["problems"]), result["problems"]


# --------------------------------------------------------------------------- determinism


def test_canonical_hashes_reproduce(runs: dict[str, Pipeline], tmp_path: Path) -> None:
    again = full_pipeline(tmp_path, "anchored")
    first = canonical_hashes(runs["anchored"].report)
    assert all(first.values()), "every tier-0 file must have a canonical hash"
    try:
        assert canonical_hashes(again.report) == first
    finally:
        set_read_only(again.files, False)


def test_golden_hashes_match_across_platforms(runs: dict[str, Pipeline]) -> None:
    current = {v: canonical_hashes(p.report) for v, p in runs.items()}
    if os.environ.get("REARCHIVE_WRITE_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pytest.fail(f"Golden file written to {GOLDEN}. Review it, commit it, then rerun without the flag.")
    if not GOLDEN.exists():
        pytest.fail(
            "Golden canonical hashes missing. Once everything else is green on one machine, a human runs "
            "`REARCHIVE_WRITE_GOLDEN=1 uv run pytest -q -m acceptance -k golden`, reviews and commits it."
        )
    assert current == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_rerunning_steps_changes_nothing(tmp_path: Path) -> None:
    p = full_pipeline(tmp_path, "no-anchor")
    try:
        run("rearchive", "ingest", p.project, p.files)
        run("rearchive", "decode", p.project, "--spec", SPEC_DIR)
        run("rearchive", "validate", p.project, "--evidence", p.evidence, "--oracle", p.truth)
        after, _ = run_json("rearchive", "report", p.project, "--json")

        def key(r: dict[str, Any]) -> tuple[Any, Any]:
            files = sorted(r["files"], key=lambda f: f["source_relpath"])
            claims = sorted(r["claims"], key=lambda c: c["id"])
            return files, claims

        assert key(after) == key(p.report), "re-running a step must not change files or claims"
        assert after["ledger"]["valid"] is True
    finally:
        set_read_only(p.files, False)


def test_decode_resumes_after_kill(tmp_path: Path) -> None:
    count = 40
    ref_root, kill_root = tmp_path / "ref", tmp_path / "kill"

    # Reference: uninterrupted run.
    files, _, _ = generate(ref_root, "anchored", count=count)
    run("rearchive", "init", ref_root / "project")
    run("rearchive", "ingest", ref_root / "project", files)
    run("rearchive", "decode", ref_root / "project", "--spec", SPEC_DIR)
    ref_report, _ = run_json("rearchive", "report", ref_root / "project", "--json")

    # Interrupted run: kill decode part-way, then resume.
    files_k, _, _ = generate(kill_root, "anchored", count=count)
    project = kill_root / "project"
    run("rearchive", "init", project)
    run("rearchive", "ingest", project, files_k)
    proc = subprocess.Popen(
        [_bin("rearchive"), "decode", str(project), "--spec", str(SPEC_DIR)],
        env={**os.environ, "REARCHIVE_TASK_DELAY_MS": "100"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    assert proc.poll() is None, "decode finished before the kill: REARCHIVE_TASK_DELAY_MS not honoured"
    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=30)

    run("rearchive", "decode", project, "--spec", SPEC_DIR)
    resumed, _ = run_json("rearchive", "report", project, "--json")

    assert len(resumed["files"]) == count
    assert canonical_hashes(resumed) == canonical_hashes(ref_report)
    assert all(canonical_hashes(resumed).values()), "every file decoded exactly once after resume"
    assert resumed["ledger"]["valid"] is True


# --------------------------------------------------------------------------- malformed input


def test_malformed_files_are_reported_not_dropped(tmp_path: Path) -> None:
    files, _, evidence = generate(tmp_path / "gen", "anchored", count=3)
    mixed = tmp_path / "mixed"
    shutil.copytree(files, mixed)
    good = sorted(p for p in mixed.rglob("*") if p.is_file())
    sample = good[0].read_bytes()

    (mixed / "zz_truncated.bin").write_bytes(sample[: len(sample) // 2])
    (mixed / "zz_empty.bin").write_bytes(b"")
    corrupted = bytearray(sample)
    corrupted[-len(corrupted) // 4] ^= 0xFF  # inside the sample block, which the CRC covers
    (mixed / "zz_crc_mismatch.bin").write_bytes(bytes(corrupted))

    project = tmp_path / "project"
    run("rearchive", "init", project)
    run("rearchive", "ingest", project, mixed)
    run("rearchive", "decode", project, "--spec", SPEC_DIR, ok=False)
    run("rearchive", "validate", project, "--evidence", evidence, ok=False)
    report, _ = run_json("rearchive", "report", project, "--json")

    by_name = {f["source_relpath"]: f for f in report["files"]}
    assert set(by_name) == set(file_hashes(mixed)), "every file, including broken ones, must be listed"
    for name in ("zz_truncated.bin", "zz_empty.bin"):
        assert by_name[name]["outcome"] in {"failed", "incomplete"}, by_name[name]
    assert by_name["zz_crc_mismatch.bin"]["outcome"] in {"failed", "incomplete", "unverified"}
    contradicted = [
        c for c in report["claims"] if c.get("file") == "zz_crc_mismatch.bin" and c["status"] == "contradicted"
    ]
    assert contradicted, "a CRC mismatch must produce a contradicted claim, not silent acceptance"
    for f in good:
        assert by_name[f.relative_to(mixed).as_posix()]["canonical_sha256"], f
