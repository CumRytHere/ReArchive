# ReArchive — instructions for Claude Code

## Precedence
1. docs/STATUS.md — the current phase and the ONE increment you are authorised to work on (imported below).
2. docs/DECISIONS.md — binding decisions. They OVERRIDE docs/PROJECT_SPEC.md wherever the two conflict (imported below).
3. docs/PROJECT_SPEC.md — product intent and principles. Background, not a task list. Read the sections relevant to the increment; do not import it whole.

Never start work outside the increment named in STATUS.md. If a task seems to need it, stop and ask.

## Commands
- Install / sync: `uv sync`
- Unit + property tests: `uv run pytest -q -m "not acceptance"`
- Acceptance gate (red until the gate is reached): `uv run pytest -q -m acceptance`
- Lint + format: `uv run ruff check --fix . && uv run ruff format .`
- Types: `uv run mypy src`

## Invariants — never violate; if a change would, stop and explain
1. AI proposes; deterministic code and a versioned policy decide. Model output is never evidence.
2. Source files are never modified, moved, renamed or re-written. Open them read-only; ingest copies bytes into the content-addressed store.
3. Structure is not semantics. A semantic claim with no anchor stays `unresolved`.
4. Claim status is computed by the policy from evidence. Code and data never assign a status directly.
5. Evidence that assumes claim C (directly or transitively) cannot support C. Every evidence item declares inputs, assumptions and lineage.
6. The canonical record is raw integer codes plus transform parameters. Hash canonical bytes only (RFC 8785 JSON; little-endian arrays with a dtype header) — never `repr`, pickle, or container-file bytes.
7. The decode path uses no network, no clock, no randomness, and no fused or transcendental floating-point operations.
8. Every task is idempotent and keyed by the hash of its inputs and versions. Outputs are written to a temp path and renamed atomically.
9. Specs are data (`.ksy` + sidecar YAML). No AI-written executable code ever parses untrusted bytes. New transform ops need a human-reviewed change.
10. `rearchive` (product) must never import `rearchive_bench` (generator, hidden truth, scoring).

## Working rules
- Plan before any change that touches more than one module: list files, dependencies and tests first, then wait for approval.
- Write the test first for new behaviour. Every transform op gets Hypothesis property tests.
- Never edit anything under `tests/acceptance/`. It is the human-owned gate. If a test there looks wrong, say why and stop.
- Never weaken, skip, `xfail` or delete a test to get green.
- Never say a test passed unless you ran it in this session and saw the output. Paste the summary line.
- Keep `src/rearchive/core/` free of I/O; filesystem, SQLite and subprocess code live in `src/rearchive/adapters/`.
- New dependency → justify purpose, licence and size in the plan before adding it.
- Before finishing: run the `invariant-reviewer` subagent on your diff and fix what it finds.
- Finish every task with: files changed, commands run with their real results, any deviation from `docs/DECISIONS.md`, open questions. Append a dated entry to the log in `docs/STATUS.md`.

## Out of scope until `docs/STATUS.md` says otherwise
Web UI, AI recovery agent, real-world formats (LeCroy etc.), industry packs, Go binaries, cloud/multi-tenant hosting, microservices, task queues.

## Imported context (loaded every session)
@docs/STATUS.md
@docs/DECISIONS.md
