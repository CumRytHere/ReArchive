---
name: increment
description: Plan and implement exactly one ReArchive increment from docs/STATUS.md, then review and report. Usage /increment [number].
disable-model-invocation: true
---

Work on increment $ARGUMENTS (if empty, use "Current increment" in docs/STATUS.md). If $ARGUMENTS differs from the current increment in STATUS.md, stop and ask.

## 1. Plan — then stop and wait for approval
- Read the increment's bullets and "done when" in docs/STATUS.md, the relevant decisions in docs/DECISIONS.md, the relevant spec sections, and tests/acceptance/test_gate_a.py (the CLI contract at the top).
- Inspect the existing code before proposing anything new.
- Present: files to create or change; each new dependency with purpose, licence and size; the tests you will write first and the invariant each one proves; which acceptance tests should turn green; risks and genuine ambiguities.
- Do not write files until the human approves the plan.

## 2. Implement
- Tests first, then code. Small steps; run `uv run pytest -q -m "not acceptance"` after each.
- Stay inside the increment. Nothing speculative.

## 3. Verify
- Run `uv run pytest -q -m "not acceptance"`, `uv run pytest -q -m acceptance`, `uv run ruff check .` and `uv run mypy src`. Keep the real summary lines.
- Run the `invariant-reviewer` subagent on the diff. Fix every blocking finding, then run it again.

## 4. Report and stop
- Report: files changed; commands with their real results; acceptance tests now green; deviations from DECISIONS.md; open questions.
- Append the log entry and any open questions to docs/STATUS.md.
- Propose a commit message. Do not commit and do not start the next increment.
