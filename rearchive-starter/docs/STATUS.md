# ReArchive — status

**Current phase:** P0 — walking skeleton (weeks 1–4) → Gate A
**Current increment:** 0.1
**Gate A test suite:** `tests/acceptance/test_gate_a.py` (human-owned; red until Gate A)

Only the current increment is authorised. The human updates "Current increment" after reviewing and committing each one.

---

## P0 increments — one Claude Code session each

Each increment ends with: unit tests green, `invariant-reviewer` run, log entry below, human review, human commit.
Acceptance tests that should turn green are listed; the rest may stay red.

### 0.1 Tooling and canonical bytes
- `uv` project with `src/rearchive/` and `src/rearchive_bench/`; console scripts `rearchive` and `rearchive-bench` (stub commands may exit non-zero with "not implemented", never fake success).
- ruff, mypy (strict on `src/`), pytest + Hypothesis; pytest config must not break the `acceptance` marker in `tests/acceptance/conftest.py`.
- `rearchive.core.canonical`: RFC 8785 JSON and array hashing exactly as D-005. Tests use the RFC 8785 test vectors.
- CI workflow running unit tests on Linux x86-64, Linux arm64 and macOS arm64 (check arm64 runner availability for a private repo; a local arm64 machine is acceptable).
- Done when: clean clone → `uv sync && uv run pytest -q -m "not acceptance"` passes. Turns green: the two import-boundary tests.

### 0.2 Content-addressed store, ingest, ledger
- Store: SHA-256 keyed; write temp → fsync → rename; never overwrite an existing key.
- `rearchive init`, `rearchive ingest`: sources opened read-only; manifest keeps relative paths; duplicates recorded, not removed; empty and truncated files kept.
- Ledger: SQLite append-only, hash chain, replay to projections; tamper tests for edit, delete, reorder, truncate.
- Done when: ingesting a read-only directory works and re-ingesting is a no-op.

### 0.3 Tier-0 generator and sealed truth (`rearchive_bench`)
- `rearchive-bench generate` per the CLI contract in the gate file, implementing the tier-0 layout below.
- Truth computed from generator parameters only; written only to `--truth`. Evidence documents written only to `--evidence`.
- Done when: turns green `test_generator_is_deterministic_per_seed`.

### 0.4 Spec and decode
- `specs/tier0/tier0.ksy` + `specs/tier0/tier0.rearchive.yaml` (D-003, D-004). Pinned Kaitai compiler; generated Python committed with source hash.
- Ops: `view`, `check` (CRC-32), `affine` (derived only). Property tests for each.
- `rearchive decode`: canonical record per file, byte coverage (explained / padding / unexplained), diagnostics. Runs in a worker subprocess with CPU, memory and time limits and no network. Honours `REARCHIVE_TASK_DELAY_MS`.
- Done when: malformed inputs produce diagnostics, never crashes or silent drops.

### 0.5 Claims, evidence, policy v1, validate
- Models per D-006 and D-007; circular-evidence rejection tested.
- `rearchive validate --evidence DIR [--oracle DIR]`. `validate` never reads the truth directory itself: it spawns `rearchive-bench oracle` (or equivalent) as a subprocess that returns per-check pass/fail for **structure and value checks only**. Semantic truth is visible to scoring, never to validation.
- Physical-anchor check uses an analytic estimator written independently of the decoder, with its own tests on synthetic sines.
- Done when: the three unit-claim variants behave as the gate expects.

### 0.6 Package, verify, report, score
- `rearchive package` (BagIt + Ed25519, D-010), `rearchive verify` (separate integrity / replay verdicts), `rearchive report --json`.
- `rearchive-bench score PACKAGE --truth DIR` reads only the package and the truth.
- Signing key for development generated locally, listed in `.gitignore`, never committed.

### 0.7 Gate A
- All of `tests/acceptance` green on one machine → human writes and commits the golden file → green on all three CI environments.
- Human records the Gate A result and the date below, then sets the phase to P1.

---

## Tier-0 format v1 (generator and spec must both follow this)

All little-endian. Header 48 bytes, then samples.

| Offset | Size | Field | Notes |
| --- | --- | --- | --- |
| 0 | 4 | magic | ASCII `RAT0` |
| 4 | 2 | version | u2, = 1 |
| 6 | 2 | unit_code | u2 vendor code; its meaning is NOT derivable from the file |
| 8 | 4 | sample_count | u4, 1,024–4,096 |
| 12 | 8 | sample_interval | f8 |
| 20 | 8 | gain | f8 |
| 28 | 8 | offset | f8 |
| 36 | 4 | crc32 | zlib CRC-32 of the sample block |
| 40 | 8 | reserved | all zero → verified padding |
| 48 | 2·n | samples | s2 raw codes |

Signal: a sine of known amplitude, frequency and offset, quantised to int16 through gain and offset.

Evidence variants written to `--evidence`:
- `anchored`: `stimulus.json` — kind `physical_stimulus`, amplitude in volts, frequency in hertz, files it applies to.
- `attested`: `attestation.yaml` — who, role, date, scope, statement mapping the unit code to volts.
- `no-anchor`: nothing.

Format-level randomisation (field order, magic, widths, byte order) arrives with generator v2 in P1.

## Later phases (not authorised yet)
- **P1 (weeks 5–6) → Gate B:** generator v2 with tier 1; MCP tool server; agent loop; non-AI search baseline; spec-level mutations; clean controls.
- **P2 (weeks 7–8) → Gate C (commercial):** LeCroy reconciliation; offline triage CLI to prospects.
- **P3 (weeks 9–10):** local workbench (three views); kill-loop stress; fuzzing; tier 2.
- **P4 (weeks 11–12) → Gate D:** hardening, signed releases, demo, outside verification.

## Open questions
- (Claude appends questions here; the human answers and moves resolved ones into DECISIONS.md.)

## Log
<!-- Newest first. One entry per increment: date — increment — what changed — exact test summary lines — deviations. -->
