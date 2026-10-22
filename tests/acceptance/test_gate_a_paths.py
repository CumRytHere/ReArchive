"""Gate A — source path handling (D-016). Human-owned. Green from increment 0.4.

Legacy archives contain filenames that are not valid UTF-8, and names that differ
only in Unicode normalisation. Both must be ingested, decoded and reported as
distinct entries, with the display form defined by D-016 §3. Platforms whose
filesystems cannot hold such names (APFS rejects invalid UTF-8) skip that case.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO / "specs" / "tier0"


def _bin(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        pytest.fail(f"`{name}` is not on PATH. Run: uv run pytest -q -m acceptance")
    return path


def run(*args: str | Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [_bin(str(args[0])), *(str(a) for a in args[1:])]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if ok and proc.returncode != 0:
        pytest.fail(
            f"{' '.join(cmd)} exited {proc.returncode}\n"
            f"{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
        )
    return proc


def display(raw: bytes) -> str:
    """D-016 §3, written independently of the product.

    UTF-8 text; each byte of an invalid sequence and each control byte becomes
    \\xNN (lowercase hex); a backslash becomes two backslashes.
    """
    out: list[str] = []
    i = 0
    while i < len(raw):
        for width in (4, 3, 2, 1):
            chunk = raw[i : i + width]
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if len(text) == 1:
                ch = text
                if ch == "\\":
                    out.append("\\\\")
                elif ord(ch) < 0x20 or ord(ch) == 0x7F:
                    out.append(f"\\x{ord(ch):02x}")
                else:
                    out.append(ch)
                i += width
                break
        else:
            out.append(f"\\x{raw[i]:02x}")
            i += 1
    return "".join(out)


def generate_one(root: Path) -> bytes:
    files, truth, evidence = root / "files", root / "truth", root / "evidence"
    run(
        "rearchive-bench",
        "generate",
        "--tier",
        "0",
        "--variant",
        "no-anchor",
        "--seed",
        "11",
        "--count",
        "1",
        "--out",
        files,
        "--truth",
        truth,
        "--evidence",
        evidence,
    )
    [only] = [p for p in files.rglob("*") if p.is_file()]
    return only.read_bytes()


def try_create(directory: Path, raw_name: bytes, content: bytes) -> bool:
    path = os.path.join(os.fsencode(directory), raw_name)
    try:
        with open(path, "xb") as handle:
            handle.write(content)
    except (OSError, ValueError):
        return False
    return True


def pipeline(archive: Path, root: Path) -> dict[str, Any]:
    project = root / "project"
    run("rearchive", "init", project)
    run("rearchive", "ingest", project, archive)
    run("rearchive", "decode", project, "--spec", SPEC_DIR, ok=False)
    proc = run("rearchive", "report", project, "--json")
    report: dict[str, Any] = json.loads(proc.stdout)
    return report


def test_non_utf8_name_is_kept_and_displayed_with_escapes(tmp_path: Path) -> None:
    content = generate_one(tmp_path / "gen")
    archive = tmp_path / "archive"
    archive.mkdir()
    # A Latin-1 degree sign (invalid UTF-8) and a literal backslash.
    raw = b"mesure_\xb0C\\x.bin"
    if not try_create(archive, raw, content):
        pytest.skip("this filesystem cannot store a non-UTF-8 filename")
    report = pipeline(archive, tmp_path)
    [entry] = report["files"]
    assert entry["source_relpath"] == display(raw) == "mesure_\\xb0C\\\\x.bin"
    assert entry["sha256"] == hashlib.sha256(content).hexdigest()
    assert entry["canonical_sha256"], "the file must decode despite its name"


def test_normalisation_variants_are_two_entries(tmp_path: Path) -> None:
    content = generate_one(tmp_path / "gen")
    archive = tmp_path / "archive"
    archive.mkdir()
    nfc = unicodedata.normalize("NFC", "café.bin").encode("utf-8")
    nfd = unicodedata.normalize("NFD", "café.bin").encode("utf-8")
    assert nfc != nfd
    if not (try_create(archive, nfc, content) and try_create(archive, nfd, content)):
        pytest.skip("this filesystem treats NFC and NFD names as the same file")
    if len(os.listdir(os.fsencode(archive))) != 2:
        pytest.skip("this filesystem normalises names")
    report = pipeline(archive, tmp_path)
    names = sorted(f["source_relpath"] for f in report["files"])
    assert names == sorted([display(nfc), display(nfd)]), (
        "no Unicode normalisation may merge entries (D-016 §4)"
    )
    hashes = {f["canonical_sha256"] for f in report["files"]}
    assert len(hashes) == 1, (
        "same content decodes to the same canonical record (D-017 §5)"
    )
    assert None not in hashes, (
        "same content decodes to the same canonical record (D-017 §5)"
    )


def test_symlinks_are_recorded_not_followed(tmp_path: Path) -> None:
    content = generate_one(tmp_path / "gen")
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "real.bin").write_bytes(content)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"must never be read through the link")
    try:
        (archive / "link.bin").symlink_to(outside)
    except OSError:
        pytest.skip("cannot create symlinks here")
    report = pipeline(archive, tmp_path)
    by_name = {f["source_relpath"]: f for f in report["files"]}
    assert set(by_name) == {"real.bin", "link.bin"}
    link = by_name["link.bin"]
    assert link["kind"] == "symlink", "D-016 §5"
    assert link["sha256"] is None, "D-016 §5"
    assert link["outcome"] == "failed"
    assert by_name["real.bin"]["kind"] == "file"
    assert by_name["real.bin"]["canonical_sha256"]
