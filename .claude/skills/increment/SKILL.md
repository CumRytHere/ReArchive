---
name: increment
description: Plan and implement exactly one ReArchive increment from docs/STATUS.md, then verify, review and report. Usage /increment <number>.
argument-hint: "<increment number, e.g. 0.2>"
disable-model-invocation: true
---

Work on increment $ARGUMENTS. If it is empty or differs from "Current increment" in docs/STATUS.md, stop and ask.

## 0. Preconditions — stop and report if any fails
- Branch is `inc/$ARGUMENTS` (`git branch --show-current`). Never work on main.
- `python3 tools/protected_paths.py check` is clean.
- Every decision this increment depends on is in docs/DECISIONS.md (check the increment's "Decisions" line in
  STATUS). A decision that exists only under docs/proposals/ or docs/decisions-pack/ is NOT ratified.

## 1. Plan — then stop and wait for approval
Read the increment's section in docs/STATUS.md, every decision it names, the relevant PROJECT_SPEC sections, the
Gate A CLI contract at the top of tests/acceptance/test_gate_a.py, and the existing code you will touch.
Present, in this order:
1. Files to create or change, one line each.
2. New dependencies: purpose, licence, size, transitive dependencies. Prefer none.
3. Tests you will write first, each with the invariant or decision clause it proves.
4. Acceptance tests expected to turn green.
5. Decision constants due at this increment (`uv run python tools/decision_constants.py --mode regression`
   lists them as `in_progress`), with the module and symbol that will satisfy each.
6. Genuine gaps: any behaviour no decision covers. For each, propose to use the `decide` skill — do not improvise it.
7. Risks.
Write nothing until the owner approves the plan.

## 2. Implement — small steps, tests first
- After each step: `uv run pytest -q -m "not acceptance" -x` on the relevant tests.
- Stage and commit at coherent points on the branch with per-file `git add` (the owner approves each commit).
- Gap discovered mid-way → stop that thread, use the `decide` skill, continue only with what does not depend on it.

## 3. Verify and review
1. `python3 tools/verify.py` — the report it prints is the only source of numbers from now on.
2. Use the `invariant-reviewer` subagent on the branch. Fix every P0/P1 finding; P2 per its rule.
3. Use the `test-skeptic` subagent on the changed modules (it runs mutation tests in bounded batches; give its Bash
   calls a long timeout). Add the tests it identifies as P1 gaps.
4. Re-run `python3 tools/verify.py`. At most two review rounds; a third needs the owner's say-so.

## 4. Report and stop
- Append a log entry to docs/STATUS.md: date, increment, what changed (files), the verification report id and its
  summary table copied verbatim, deviations from DECISIONS.md (should be none), new open questions.
- Use the `claims-checker` subagent on your final report and the new log entry; fix what it flags.
- Final message: files changed; the verification report id and verdict; acceptance tests now green; open
  questions. Then stop: the owner reviews and runs `/close <n>`. Do not start the next increment.
