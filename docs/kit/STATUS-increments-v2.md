<!--
Owner: replace the "P0 increments" section of docs/STATUS.md (from "## P0 increments" up to, not including,
"## Tier-0 format v1") with everything below the next line. Keep your Open questions and Log sections as they are.
-->
## Closure protocol (every increment)

An increment is **closed** only when all of these hold, in this order:
1. `python3 tools/verify.py --close` → PASS on the clean closing commit, log entry included (`--gate A` too for
   0.7); `--close` requires the decision constants due at this increment (D-028).
2. `invariant-reviewer` → PASS on that HEAD; `test-skeptic` run on changed modules, P1 gaps fixed.
3. `claims-checker` → every claim in the log entry SUPPORTED.
4. `reports/closure/<n>.md` committed on the branch on top of the commit it describes (the owner runs `/close <n>`).
5. Owner reviews the diff, merges `inc/<n>` into main with `--no-ff`, pushes, sets "Current increment" to the next one.

Review rounds are capped at two per increment; a third needs the owner. P0/P1 findings block; P2 are fixed if quick
or recorded as open questions; P3 are noted only.

## P0 increments — one Claude Code session each, on branch `inc/<n>`

### 0.1 Tooling and canonical bytes — implemented, closing
- Remaining: D-015 ratified by the owner (handoff §6); D-030 (D-015's constants) drafted by the session and ratified
  by the owner before closure; audit F-01 (lone surrogates in **keys** raise the typed error), F-06 (BE/LE equal-value
  inputs give equal canonical bytes; every struct format literal in the canonical module starts with `<`); `rfc8785`
  installed version equals the pin; `JSON_MAX_DEPTH = 64` enforced (D-016 §7); D-015 allowlist exposed as
  `rearchive.core.canonical.ALLOWED_DTYPES` (D-018 §4); owner records acceptance of the 15 vectors **after** D-030 is
  ratified (D-028 §3); reviewer re-run on the current blob.
- Decisions: D-005, D-015, D-016 §7, D-028, D-030.
- Turns green: `test_product_never_imports_the_benchmark`, `test_benchmark_never_imports_the_product` (already green).

### 0.2 Paths, store, ingest, ledger, report skeleton
- Pure (`rearchive.core`): `core.paths` (D-016: `relpath_b64`, `relpath_display` with exact escaping rules),
  `core.keys` (D-021: key objects, `runtime_id`), `core.ledger` (D-022: event bodies, chain hashing, replay to
  projections), `core.report` (D-026 §4: outcome rules, `FILE_STATES`).
- I/O (`rearchive.adapters`): directory walk with `lstat` (walk order, symlink/special-file entries, duplicates),
  content-addressed store (D-021 §3: temp → fsync → rename → fsync dir; never overwrite; mismatch is an integrity
  failure), SQLite ledger (WAL; tamper tests for edit, delete, reorder).
- CLI: `rearchive init`, `rearchive ingest` (sources opened read-only; re-ingest is a logged no-op), `rearchive report
  --json` listing files with `source_relpath`, `kind`, `sha256`, `canonical_sha256: null`, `outcome`, `state`,
  plus `ledger`.
- Hypothesis: arbitrary byte filenames (where the OS allows) round-trip through `relpath_b64`; display never raises.
- Decisions: D-016, D-021, D-022, D-026 §4–5.
- Done when: ingesting a read-only directory twice is a no-op the second time (ledger shows `task_reused`), and
  `tools/verify.py --close` passes (the constants due at 0.2 hold).
- Turns green: none in Gate A (all need the generator); contract tests for 0.2 constants.

### 0.3 Tier-0 generator, sealed truth, evidence documents, oracle
- `rearchive-bench generate` per the gate's CLI contract and the Tier-0 format v1 below; signals are sines whose
  parameters are drawn from the seed; truth computed from generator parameters only (D-012).
- Evidence documents per D-024 §2–3: `stimulus.json` (anchored), `attestation.yaml` (attested), none (no-anchor).
- `rearchive-bench oracle --truth DIR` speaking the D-024 §1 protocol; refuses semantic checks; never emits truth.
- Decisions: D-011, D-012, D-024 §1–3, D-027 (truth needed for scoring).
- Turns green: `test_generator_is_deterministic_per_seed`.

### 0.4 Spec, decode, records, descriptors
- `specs/tier0/tier0.ksy` (ship the kit's version) and `specs/tier0/tier0.rearchive.yaml` (D-029).
- Generated parser via `tools/ksc/regen.sh` into `src/rearchive/generated/` (owner approves the npm/node run).
  Runtime dependency `kaitaistruct==0.11`; `PyYAML` for sidecars. The **owner** adds `src/rearchive/generated/**` to
  ruff's `extend-exclude` in pyproject.toml on main before this increment starts ([tool.ruff] is protected; generated
  code trips lint and format; mypy is satisfied by its `# type: ignore` header). Large increment: run it as two
  sessions on the same branch (part 1: spec, sidecar, ops, records; part 2: worker, descriptors, resume, report),
  `/clear` between, close once.
- `rearchive.decode`: sidecar loader (D-029), ops `view` and `crc32` with property tests, records (D-017, D-019,
  D-020), descriptors and coverage (D-018), diagnostics (D-026 §3). `rearchive.views`: the `affine` derived view,
  outside the decode path (D-026 §2).
- `rearchive.worker` subprocess with limits (D-026 §1); `decode` keys and resume (D-021); `REARCHIVE_TASK_DELAY_MS`.
- `report --json` adds `canonical_sha256`, `coverage`, `outcome`.
- Decisions: D-003, D-004, D-017, D-018, D-019, D-020, D-021, D-026, D-029.
- Turns green: `test_decode_resumes_after_kill`; owner's `tests/acceptance/test_gate_a_paths.py` (D-016 end to end).

### 0.5 Claims, evidence, policy v1, validate
- `rearchive.claims` (D-023): deterministic ids, schema, policy v1 as a pure function, replay equality.
- `rearchive validate --evidence DIR [--oracle DIR]` (D-024): oracle client (subprocess, JSON Lines), CRC evidence,
  attestation, physical-anchor estimator with its own tests and a recorded gain-error sweep.
- Outcomes per D-026 §4; `report --json` adds `claims`.
- Decisions: D-006, D-007, D-023, D-024, D-026 §4.
- Turns green: `test_malformed_files_are_reported_not_dropped`.

### 0.6 Package, verify, score, report
- `rearchive package` (D-025), `rearchive verify --json` (integrity / replay / trust), static `report.html`.
- `rearchive-bench score PACKAGE --truth DIR --json` (D-027) reading only the package and the truth.
- Decisions: D-010, D-025, D-027.
- Turns green: the 13 remaining Gate A tests except the golden test.

### 0.7 Gate A
- Everything green on one machine except golden → owner writes, reviews and commits the golden file
  (`REARCHIVE_WRITE_GOLDEN=1 uv run pytest -q -m acceptance -k golden`).
- CI green on `ubuntu-24.04`, `ubuntu-24.04-arm`, `macos-15`; owner sets the `ACCEPTANCE_REQUIRED` repository
  variable to `true`.
- Independent audit of the Gate A commit (`/audit-prep`), findings dispositioned.
- Owner records Gate A in the log and moves to P1.

## Later phases (increments drafted at each phase kickoff with docs/PROMPTS.md)
- **P1 (weeks 5–6) → Gate B:** 1.1 procedural generator v2, tiers 0–1, clean controls · 1.2 ops `unpack_bits`,
  `deinterleave`; spec-level mutation operators · 1.3 MCP investigation tool server · 1.4 non-AI search baseline ·
  1.5 agent runner with budgets and the agent/baseline/agent+tools scoreboard on ≥200 formats.
- **P2 (weeks 7–8) → Gate C (commercial):** 2.1 offline triage CLI · 2.2 LeCroy `.trc` reconciliation with reader
  lineage audit · 2.3 prospect intake kit.
- **P3 (weeks 9–10):** 3.1 local workbench (three views) · 3.2 kill-loop stress, Atheris fuzzing, OS-level isolation ·
  3.3 tier 2 (delta, RLE, segments, CRC variants, TLV).
- **P4 (weeks 11–12) → Gate D:** 4.1 clean-install tests and signed releases · 4.2 public synthetic demo ·
  4.3 outside verification of a signed package.
