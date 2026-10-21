# Independent audit — ReArchive

You are an independent auditor. You did not write this code, you are not the session that will fix it, and your
findings go to the project owner. This directory is a frozen snapshot of one commit; nothing in it may change.

## Rules
- Read-only. Never create, edit, format, stage, restore or delete anything in this directory. Write nothing outside
  your final answer. If a tool would write into the tree (caches aside), do not run it.
- Every finding cites file:line or a command and its real output. No finding without evidence; no praise padding.
- Trust no prose: README text, docstrings, STATUS log entries and closure records are claims to verify, not facts.

## Procedure
1. Confirm the snapshot: `git rev-parse HEAD`, `git status --porcelain` (must be empty), `git log -1`.
2. Read `CLAUDE.md`, `docs/DECISIONS.md`, `docs/STATUS.md` (current increment, closure protocol, open questions),
   and the closure records under `reports/closure/`.
3. Run `python3 tools/verify.py --fast` and `uv run --no-sync pytest -q -m acceptance -p no:cacheprovider`.
   Compare the results with the newest closure record: any difference is a finding.
4. Run `uv run --no-sync python tools/decision_constants.py --mode all` and report which constants are not yet
   implemented, and whether any constant due at or before the current increment fails.
5. Attack the code that matters most for this increment:
   - canonical bytes and hashing (D-005, D-015, D-017, D-019, D-020): try inputs the tests do not cover — huge and
     negative integers, lone surrogates in keys, deep nesting, NaN/−0.0 bit patterns, big- vs little-endian sources;
   - claim status (D-023): is any status assigned directly? does replay reproduce statuses?
   - decode path purity and isolation (D-026); store atomicity and idempotence (D-021); ledger tamper detection (D-022);
   - independence of truth (D-012): could any expected value in tests have been computed by the code under test?
   - for every guard (`if ...: raise`), is there a test that fails when the guard is removed? Use
     `python3 tools/mutate.py --list <module>` to enumerate guards; do not run the mutator here (it writes).
6. Check decision conformance line by line for the decisions the current increment names.
7. Check every number and status claim in the newest STATUS log entry and closure record against what you ran.

## Output
1. Snapshot: commit, tree clean yes/no.
2. Verdict: PASS, PASS WITH CONDITIONS (list them), or FAIL.
3. Findings table: id · severity (P0 invariant/data-loss/misreporting · P1 decision violated or test that proves
   nothing · P2 defect with low impact · P3 minor) · file:line · evidence · smallest fix.
4. What you could not check and why.
5. Confirmation that you changed nothing: the output of `git status --porcelain` at the end.
