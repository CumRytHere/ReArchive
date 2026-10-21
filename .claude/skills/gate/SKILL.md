---
name: gate
description: Show where the project stands against its acceptance gate, test by test. Read-only. Usage /gate [A].
argument-hint: "[A]"
---

1. Run `python3 tools/verify.py` and read `reports/verify/latest.json` → `checks.acceptance.counts.names`.
2. Produce a table: acceptance test · pass/fail/error · one-line reason for each non-pass (quote the assertion or
   `pytest.fail` message from the check's output; run `uv run pytest -q -m acceptance -rA -k <name>` for detail).
3. Group the non-passing tests by the increment in docs/STATUS.md expected to turn them green ("Turns green" lines).
   Flag any test that should already be green for the current or an earlier increment: that is a regression.
4. Do not edit anything. Never propose changing a test in tests/acceptance/; if one looks wrong, say exactly why
   and leave the decision to the owner.
