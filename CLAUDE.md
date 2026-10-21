# ReArchive — instructions for Claude Code

## Precedence (D-001)
1. `docs/DECISIONS.md` — binding decisions; they override the spec (imported below). Only text in DECISIONS.md is
   ratified. `docs/proposals/` and `docs/decisions-pack/` are drafts.
2. `docs/STATUS.md` — the current phase and the ONE increment you may work on, and its scope (imported below).
3. `docs/PROJECT_SPEC.md` — intent and principles. Read the sections the increment needs; never import it whole.

Work only on the increment named in STATUS.md, on branch `inc/<increment>`. If a task seems to need anything
else, stop and ask.

## Commands
- Environment: `uv sync --locked`
- Inner loop: `uv run pytest -q -m "not acceptance" -x` (unit + contract tests)
- Gate status: `uv run pytest -q -m acceptance` (red until its gate)
- Lint one file: `uv run ruff check --fix path/to/file.py && uv run ruff format path/to/file.py`
- Whole-repo checks are read-only: `uv run ruff check --no-cache .` · `uv run ruff format --no-cache --check .` ·
  `uv run mypy --strict src`
- Verification report (the ONLY source of numbers you may report): `python3 tools/verify.py` (`--fast` skips acceptance)
- Decision constants: `uv run python tools/decision_constants.py` (`--mode regression` shows this increment's to-do)
- Protected paths: `python3 tools/protected_paths.py check`
- Mutation test a module: `python3 tools/mutate.py src/... --tests tests/unit/...`
- Regenerate Kaitai parsers (asks first): `tools/ksc/regen.sh`

## Invariants — never violate; if a change would, stop and explain
1. AI proposes; deterministic code and a versioned policy decide. Model output is never evidence.
2. Source files are never modified, moved, renamed or re-written. Ingest opens them read-only and copies bytes
   into the content-addressed store.
3. Structure is not semantics. A semantic claim without an anchor is `unresolved`.
4. Claim status is computed by the policy from evidence (D-023). Code never assigns a status directly.
5. Evidence that assumes claim C, directly or transitively, cannot support C (D-007).
6. Canonical records hold raw integer codes and bit patterns; physical values are derived views (D-005, D-017,
   D-019). Hash canonical bytes only — never `repr`, pickle, dict order or container-file bytes.
7. The decode path uses no network, clock or randomness, and no floating-point arithmetic — so no fused or
   transcendental operations whose results differ by platform (D-026 §2).
8. Every task is idempotent and keyed by the hash of its inputs, versions and runtime (D-021). Writes are atomic.
9. Specs are data (`.ksy` + sidecar YAML). No AI-written executable code parses untrusted bytes. New transform ops
   arrive only through a ratified decision and a human-reviewed change (D-004, D-029 §2).
10. `rearchive` never imports `rearchive_bench`, and the benchmark never computes truth with product code (D-012).
11. Canonical records contain no JSON floats and no JSON `null` (D-017, D-019, D-020).
12. No hash-affecting format is frozen in vectors or golden files before its decision is in DECISIONS.md (D-028).

## Working rules
- Plan first (`/increment <n>` does this); write nothing until the owner approves the plan.
- Tests before code. Every transform op and every canonicalisation path gets Hypothesis property tests.
- Keep `src/rearchive/core/` free of I/O: filesystem, SQLite and subprocess code live in `src/rearchive/adapters/`.
- Edit files only with the Edit/Write tools. Never `sed -i`, `perl -i` or scripts that rewrite files: in-place
  rewrites have silently done nothing here and been reported as done.
- Run ruff only on named files when it may write. Never run a formatter or `--fix` over a directory.
- Stage files one by one. Never `git add -A`, `git add .`, `commit -a`, `--amend`, `push`, `rebase` or `reset --hard`.
- Commit only on `inc/<n>`, never on main; the owner approves commits and does all merges and pushes.
- Never edit, restore or re-stage protected paths: `CLAUDE.md`, `docs/DECISIONS.md`, `docs/PROJECT_SPEC.md`,
  `tests/acceptance/`, `tests/contract/`, `.claude/`, `tools/`, `.github/`, root and `tests/` `conftest.py`,
  `pytest.ini`/`tox.ini`/`setup.cfg`, the `[tool.pytest|ruff|mypy|hypothesis|coverage]` sections of
  `pyproject.toml`, and the "Current phase"/"Current increment" lines of STATUS.md. If one differs from main, stop
  and tell the owner what you ran last. Need a config change (e.g. a ruff exclude)? Ask the owner to make it.
- Never weaken, skip, `xfail` or delete a test, loosen a tolerance, or relax `[tool.*]` configuration to get green.
- A behaviour no decision covers is a gap: use the `decide` skill (`/decide <topic>`) and stop that thread. Never
  improvise a format, vocabulary, threshold or schema.
- Numbers you report come from a `tools/verify.py` report for the current tree, quoted with its id. Prefer
  "see report <id>" over retyping figures. A sentence that cannot cite a source is deleted, not reworded.
- Review: `invariant-reviewer` then `test-skeptic`, at most two rounds per increment; P0/P1 block, P2 fix if quick
  else open question, P3 note only.
- Finish every task with: files changed, verification report id and verdict, deviations from DECISIONS.md, open
  questions — and append the log entry to STATUS.md. Closing an increment is the owner's `/close <n>`; do not start
  the next increment.

## Out of scope until STATUS.md says otherwise
Web UI, AI recovery agent, real-world formats, industry packs, Go binaries, hosted services, multi-tenancy,
microservices, task queues, network access from product code.

## Imported context (loaded every session)
@docs/STATUS.md
@docs/DECISIONS.md
