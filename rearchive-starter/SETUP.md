# ReArchive starter kit — setup and working routine (for you, not Claude)

## What is in the kit

| Path | Purpose | Who may edit |
| --- | --- | --- |
| `CLAUDE.md` | Invariants, commands, working rules; auto-imports STATUS and DECISIONS every session | You |
| `docs/DECISIONS.md` | Binding decisions that override the spec (from the build verdict) | You |
| `docs/STATUS.md` | Current increment, increment plan, tier-0 format, open questions, log | You set the increment; Claude appends log and questions |
| `docs/PROJECT_SPEC.md` | Your original specification — intent and principles | You |
| `tests/acceptance/` | Gate A: 19 black-box tests and the CLI contract they define | You only (Claude is denied) |
| `.claude/settings.json` | Permissions and hooks | You only |
| `.claude/hooks/` | Lint after every edit; unit tests must pass before Claude finishes a turn | You only |
| `.claude/agents/invariant-reviewer.md` | Independent reviewer subagent (Opus), read-only | You |
| `.claude/skills/increment`, `.claude/skills/gate` | `/increment` and `/gate` commands | You |

## 1. Install
- VS Code 1.94 or later, plus the **Claude Code** extension by Anthropic (`anthropic.claude-code`).
- CLI: `curl -fsSL https://claude.ai/install.sh | bash`, then `claude --version` and `claude doctor`. Arch is not on the documented distro list; if the native install misbehaves, use `npm install -g @anthropic-ai/claude-code` (Node.js 22+, no `sudo`).
- `uv`, `git`, Python 3.11+. The Kaitai compiler is needed from increment 0.4 (the plan for 0.4 will pin it).
- Sign in to both with your Max account. Usage is shared with claude.ai, so heavy chat elsewhere eats coding budget.

## 2. Create the repository
```bash
mkdir -p ~/projects && cd ~/projects
unzip ~/Downloads/rearchive-starter.zip     # creates ./rearchive-starter
mv rearchive-starter rearchive && cd rearchive
chmod +x .claude/hooks/*.sh
git init && git add -A
git commit -m "Starter kit: decisions, status, Gate A tests, Claude Code guardrails"
code .
```
Committing the gate before any code exists is the point: any later change to `tests/acceptance/` shows up in `git log`.

## 3. First session
1. Open the Claude Code panel. Run `/model opus`.
2. Switch to Plan mode (mode indicator at the bottom of the prompt box, or type `/plan`).
3. Type `/increment 0.1`.
4. Review the plan hard: directory layout, every dependency, the exact canonical-hashing rules. Push back before approving.
5. Optionally `/model sonnet` for implementation to save Opus usage; the reviewer subagent still runs on Opus.
6. When Claude reports, check the reviewer's verdict, then run `uv run pytest -q -m "not acceptance"` yourself and read `git diff`.
7. Commit, change "Current increment" in `docs/STATUS.md` to 0.2, run `/clear`, and start the next one.

## 4. The routine, every increment
Plan (Opus) → you approve → implement → hooks lint and test → `invariant-reviewer` → you verify → you commit → bump STATUS → `/clear`.
One increment per session. Never let a session roll into the next increment.

## 5. When things go wrong
- **Claude wants to change an acceptance test.** It is blocked. If the test really is wrong, change it yourself in a separate commit whose message says why.
- **Scope creep.** Stop it, `git stash` or `git restore`, restate the increment.
- **Stop hook keeps firing.** It lets Claude stop on the second attempt by design; fix the failing test yourself if needed.
- **Limits of the guardrails.** Deny rules match command text, so a determined workaround (for example a script that writes a file) can slip past. Git history and your diff review are the real backstop.

## 6. Reaching Gate A (increment 0.7)
1. Everything in `uv run pytest -q -m acceptance` green except the golden test.
2. `REARCHIVE_WRITE_GOLDEN=1 uv run pytest -q -m acceptance -k golden` — review `tests/acceptance/golden/tier0_seed7.json`, commit it.
3. Green on Linux x86-64, Linux arm64 and macOS arm64 in CI. Record the date in STATUS.md and move to P1.

## 7. The non-code track (do not skip)
Block time every week for discovery: target 25 conversations by week 6 with QA heads, lab-informatics leads and validation consultancies. Score each prospect on the spec's eight-factor scorecard (§18.1). Gate C at week 8 is commercial: at least one prospect sharing sample files under NDA.

## Fallback if `/increment` does not appear
Paste this instead:
> Read CLAUDE.md and docs/STATUS.md. Work only on increment 0.1. First present a plan — files, dependencies with justification, tests first and the invariant each proves, which acceptance tests should turn green — and wait for my approval. Then implement test-first, run unit and acceptance tests, run the invariant-reviewer subagent and fix its findings, report real test output, append to the STATUS.md log, propose a commit message, and stop.
