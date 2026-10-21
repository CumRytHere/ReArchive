---
name: close
description: Owner-run. Prepare the closure record for the current increment so the owner can review and merge it. Usage /close <number>.
argument-hint: "<increment number>"
disable-model-invocation: true
---

Prepare closure of increment $ARGUMENTS. You do not merge, push or change STATUS's current increment; the owner does.

1. Preconditions: branch `inc/$ARGUMENTS`; `python3 tools/protected_paths.py check` clean. Commit everything,
   including the STATUS log entry, per file with the owner's approval, so the working tree is clean. Call this
   commit C.
2. Run `python3 tools/verify.py --close` (add `--gate A` for increment 0.7). It must be PASS on clean commit C:
   `--close` also requires every decision constant due at this increment (D-028).
3. Use the `invariant-reviewer` subagent. It must return PASS. If it fails, stop and report; do not loop.
4. Use the `claims-checker` subagent on the newest STATUS log entry. Every claim must be SUPPORTED. If a claim must
   change, fix it, commit, and go back to step 2 (the report must describe the commit the record cites).
5. Write `reports/closure/$ARGUMENTS.md` containing exactly:
   - increment, branch, commit C (the commit the verification report describes), date;
   - the verification report's markdown, copied from `reports/verify/<id>.md` (not retyped);
   - the reviewer's verdict and its P2/P3 findings with their disposition (fixed / open question Q-NN);
   - decision constants enforced for this increment (output of `uv run python tools/decision_constants.py`);
   - acceptance tests green after this increment (names from the report);
   - open questions added or closed.
6. Stage and commit `reports/closure/$ARGUMENTS.md` alone (owner approves). It is the only file after commit C, and it
   describes C.
7. Print the owner's merge commands, filled in:
   ```
   git switch main && git merge --no-ff inc/$ARGUMENTS -m "Increment $ARGUMENTS"
   python3 tools/verify.py --fast         # on main, must be PASS
   git push origin main
   # then edit docs/STATUS.md "Current increment" to the next one, commit, push, and:
   git switch -c inc/<next>
   ```
Then stop.
