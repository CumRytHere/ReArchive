---
name: handoff
description: Write docs/HANDOFF.md for whoever picks the project up next, using only generated facts. Use at the end of a working day or before a long break.
disable-model-invocation: true
---

1. Run `python3 tools/verify.py` and `python3 tools/protected_paths.py check --json`.
2. Collect: `git log --oneline -15`, `git branch -vv`, `git worktree list`, `git status --porcelain`,
   current phase and increment from docs/STATUS.md, open questions (Q-NN lines), closure records under
   reports/closure/.
3. Write docs/HANDOFF.md with these sections and nothing else:
   1. Where things stand (three sentences: last closed increment, current increment and its state, the next action).
   2. Repository state (branch, HEAD, worktrees, uncommitted files) — command output, not paraphrase.
   3. Verification: the report markdown copied verbatim from reports/verify/<id>.md.
   4. Blockers: what is waiting on the owner (decisions, reviews, merges), each with the file it concerns.
   5. Open questions that gate the next two increments (id, gates, one line).
   6. Traps learned this session that are not yet in CLAUDE.md (propose CLAUDE.md wording; the owner adds it).
   7. Next actions, numbered, each naming who does it (owner / builder session / audit session).
4. Use the `claims-checker` subagent on docs/HANDOFF.md; fix every claim that is not SUPPORTED.
5. Commit nothing; tell the owner the file is ready.
