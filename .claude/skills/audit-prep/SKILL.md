---
name: audit-prep
description: Prepare an independent audit of a committed snapshot (a frozen worktree and a separate read-only session). Usage /audit-prep [commit].
argument-hint: "[commit, default HEAD]"
disable-model-invocation: true
---

An audit must review a commit that cannot change underneath it, from a session that did not write the code.
You only prepare it; the owner runs it.

1. Check: `git status --porcelain` is empty (uncommitted work would not be in the snapshot). If not, list what is
   uncommitted and stop.
2. Resolve the commit: `git rev-parse ${ARGUMENTS:-HEAD}`.
3. Print, filled in, the commands for the owner:
   ```
   tools/audit.sh <commit>                 # creates ../<repo>-audit-<sha7>, verifies it, syncs its environment
   tools/audit.sh <commit> --run           # optional: headless auditor with restricted tools (docs/prompts/audit.md)
   ```
   and, for an interactive audit: open the printed directory in a new VS Code window, start Claude Code there in
   Plan mode, and paste docs/prompts/audit.md.
4. State what the audit should focus on for this increment (hash-affecting code, policy, verification, scope), in
   three bullets at most, so the owner can append it to the prompt.
