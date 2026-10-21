# ReArchive — operating playbook (kit v2)

How to build ReArchive from here to Gate D in VS Code with Claude Code: who does what, in which order, with which
command or prompt. Read sections 1–3 once. After that you live in section 5, one increment at a time, and copy
prompts from `docs/PROMPTS.md`.

---

## 1. Where you are, and what changes

**State on 2026-10-21 (from HANDOFF.md, commit `077bf57`).** Increment 0.1's code is done and strong: six adversarial
rounds found no defect in the canonical bytes. It is not closed: D-015 is unratified, the reviewer's PASS is stale,
the 15 vectors are unaccepted. CI has never run.

**Why kit v2.** The code was trustworthy before the documents and processes around it were. Each problem the handoff
records now gets a mechanism instead of a rule someone has to remember:

| Problem in the handoff | Mechanism in kit v2 |
| --- | --- |
| Every blocking finding after round 1 was prose claiming more than the code did; numbers went stale | `tools/verify.py` writes a report tied to the exact tree; logs quote it by id; the `claims-checker` subagent rejects any claim without a current source |
| Increments stop mid-session on design gaps (Q-04, Q-09, Q-11, …) | Decision pack D-016–D-029 settles every known gap up to Gate A now; `/decide` turns a new gap into a proposal and stops |
| Decision text drifted from code (D-015 near-miss: the draft contradicted the code in three places) | `decision-constants` blocks plus a contract test (D-028): a decision's numbers are checked against the code from the increment they are due |
| `ruff format .` rewrote the gate; deny rules did not stop a tool the project told Claude to run | `PreToolUse` Bash policy blocks repo-wide writers before they run; the OS sandbox denies writes to protected paths; the guard compares against `main`, so even a committed change is caught |
| Edits that silently did nothing were reported as done | Edits only through the Edit tool (which fails loudly); `sed -i`, `perl -i` and inline rewrites are blocked |
| A deleted bounds check left 88 tests green; found by hand | `tools/mutate.py` and the `test-skeptic` subagent make that check routine |
| Audits read trees that changed under them | `tools/audit.sh` makes a detached snapshot outside the repo; the auditor runs there, read-only |
| Six review rounds on one increment | Two-round cap; P0/P1 block, P2 quick-fix or open question, P3 note only |

---

## 2. The operating scheme

### 2.1 Roles
| Who | Does | Never does |
| --- | --- | --- |
| **You (owner)** | Ratify decisions; approve plans; review diffs; commit protected files; merge to `main`; push; set the current increment; run audits; discovery calls | Let a Claude session edit protected files |
| **Builder session** (Claude Code in VS Code, one per increment) | Plan, test-first implementation, verify, review loop, log entry, closure record on `inc/<n>` | Work outside its increment; touch protected paths; merge or push |
| **`invariant-reviewer`** (Opus subagent) | Checks the branch against invariants, decisions, scope, weakened checks | Edit anything |
| **`test-skeptic`** (Opus subagent) | Mutation-tests changed modules, names missing tests | Write the tests |
| **`claims-checker`** (Sonnet subagent, plan mode) | Checks every claim in a report or log entry against sources | Edit anything |
| **Auditor session** (separate session in a frozen snapshot) | Independent audit at hash-affecting increments and gates | Run in your working tree |

### 2.2 Branches and commits
- `main` holds only owner-merged, verified work. It is the baseline the guard compares protected paths against.
- Each increment lives on `inc/<n>`. The builder commits there (you approve each commit prompt). You merge with
  `git merge --no-ff inc/<n>` and push.
- Protected paths change only in your own commits on `main`. If an increment branch is open when you change one,
  run `git switch inc/<n> && git merge main` before resuming the session.

### 2.3 The increment loop
```
 YOU   set "Current increment: N" on main, commit, push  ──►  git switch -c inc/N
 YOU   new Claude tab (/clear), /model opus, Plan mode   ──►  /increment N  (+ focus text from PROMPTS.md)
 CLAUDE  plan: files, deps, tests-first list, constants due, gaps                     [stops]
 YOU   challenge the plan; approve                                                   (≈15 min, the best time you spend)
 CLAUDE  test-first implementation; hooks lint each edit and block a red Stop
 CLAUDE  verify.py → invariant-reviewer → test-skeptic → fix (≤2 rounds) → log entry → claims-checker
 YOU   read the report and the diff (git diff main...inc/N)
 YOU   /close N (same session) → verify --close PASS, reviewer PASS, closure record committed
 YOU   (hash-affecting increments) tools/audit.sh → audit session → disposition findings
 YOU   merge --no-ff, verify --fast on main, push; next increment
```
Typical cost: one increment = one or two working sessions. Increment 0.4 is planned as two sessions on one branch.

### 2.4 Protected paths
`CLAUDE.md`, `docs/DECISIONS.md`, `docs/PROJECT_SPEC.md`, `tests/acceptance/`, `tests/contract/`, `.claude/`,
`tools/`, `.github/`; the root and `tests/` `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`; the
`[tool.pytest|ruff|mypy|hypothesis|coverage]` sections of `pyproject.toml`; and the "Current phase" and "Current
increment" lines of `docs/STATUS.md`.

Different layers cover different kinds of write. None is complete alone, and you are the last one:
| Write attempted through | Stopped before it happens by | Detected afterwards by |
| --- | --- | --- |
| Claude's Edit/Write tools | permission deny rules (`Edit(/tests/acceptance/**)` …) | the guard |
| A shell command whose shape is known to be dangerous (formatters, blanket git, restores, redirects) | the `PreToolUse` Bash policy | the guard |
| Any other shell command or script | the sandbox's write-deny (bubblewrap on Linux, Seatbelt on macOS), for the directories it lists | the guard |
| Config sections and STATUS lines (inside editable files) | nothing — they are compared, not blocked | the guard and `verify.py` |

The guard (`PostToolUse` on Edit, Write and Bash, plus `Stop`) diffs every protected path against `main`, including
changes committed on the branch, and blocks the session from continuing until you resolve it. It reports a write; it
cannot prevent one.

To change a protected file yourself: close Claude sessions, edit on `main`, commit, push, merge `main` into the open
increment branch, then resume.

### 2.5 Decisions
- Only `docs/DECISIONS.md` is binding. `docs/proposals/` and `docs/decisions-pack/` are drafts until you paste them.
- A decision that fixes values carries a `decision-constants due=<n>` block (D-028). Constants due **before** the
  current increment are enforced on every test run. Constants due **at** it are the increment's to-do list
  (`uv run python tools/decision_constants.py --mode regression` shows them as `in_progress`) and are enforced by
  `tools/verify.py --close`. `main` stays green when you start an increment.
- A gap no decision covers: the builder runs `/decide <topic>`, writes `docs/proposals/D-NNN-<slug>.md`, adds an open
  question and stops that thread. You ratify (paste the text) or answer differently, commit on `main`, merge into the
  branch.
- Never freeze vectors or golden files for a hash-affecting format before its decision is in DECISIONS.md (D-028 §3).

### 2.6 Numbers come from reports
`tools/verify.py` runs lockfile, sync, ruff, format check, `mypy --strict`, unit, contract, tools and acceptance
tests and the protected-paths check. It writes `reports/verify/<tree-id>.{json,md}`. The id names the exact tree,
including uncommitted files, so a report about another tree is detectably stale
(`--check-report reports/verify/latest.json`). Log entries and closure records copy the markdown verbatim. If a
sentence cannot cite a report, a file:line or a decision, delete it.

### 2.7 Review protocol
- Order: `invariant-reviewer` → fix → `test-skeptic` → fix → `verify.py` → `claims-checker`.
- Cap: two review rounds per increment. A third needs your explicit go-ahead.
- Severity: **P0** (invariant, protected path, data loss, misreported results) and **P1** (decision violated, a
  test that proves nothing, scope creep) block. **P2**: fix if under 30 minutes, else open question. **P3**: note.
- Fix prose findings by deleting the claim or replacing a number with a report id, not by writing more prose.

### 2.8 Audits
Run an independent audit after increments that change hashes or verdicts (0.1, 0.4, 0.6), and at every gate.
`/audit-prep` prints the commands. `tools/audit.sh <commit>` makes `../<repo>-audit-<sha7>`. Open it in a new VS Code
window, start Claude Code in Plan mode, paste `docs/prompts/audit.md`. Or run `tools/audit.sh <commit> --run`
headless with a restricted tool list (no edits, no staging, no mutation runs; it can still run Python, so check
`git status` in the snapshot afterwards — the script does). The snapshot compares protected paths against its own
commit, not your moving `main`. Findings go into the closure record with a disposition. Remove snapshots afterwards
with `git worktree remove ../<repo>-audit-<sha7> && git worktree prune`.

### 2.9 Models and usage
- Plans and reviews: **Opus** (`/model opus`; both reviewer subagents pin `model: opus`).
- Straightforward implementation: **Sonnet** (`/model sonnet`) once the plan is approved. Keep Opus for hashing,
  policy and verification code (0.4 part 1, 0.5).
- Your Max plan's usage is shared between Claude Code and claude.ai. Heavy chat elsewhere reduces coding budget.
- `/clear` between increments, and between the two sessions of 0.4. Everything a session needs is in `CLAUDE.md`,
  `STATUS.md`, `DECISIONS.md` and the session briefing, not in old conversation history.

---

## 3. Day 0 — one-time setup (≈90 minutes)

### 3.1 Machine prerequisites (Arch Linux)
```bash
sudo pacman -S --needed git python uv nodejs npm bubblewrap socat jq
uv python install 3.12.15          # the version .python-version pins
claude --version && claude doctor  # CLI; the VS Code extension bundles its own copy
```
The sandbox needs `bubblewrap` and `socat` on Linux. The kit sets `failIfUnavailable: true`, so Claude Code refuses
to run unsandboxed rather than silently dropping protection. Sandboxed commands may write only inside the project, a
temporary directory, `~/.cache/uv` (uv's cache) and `~/.config/rearchive` (the development signing key, D-025).

### 3.2 Repository housekeeping (from the handoff)
```bash
cd ~/projects/rearchive && git switch main && git pull --ff-only
git worktree remove /tmp/rearchive-audit-0.1 2>/dev/null; git worktree remove /tmp/rearchive-audit-077bf57 2>/dev/null
git worktree prune
# Authorship (handoff §11a): your git email has no "@". Cheap to fix now, before anyone clones:
git config user.email "you@example.com"          # your real GitHub email
git commit --amend --reset-author --no-edit && git push --force-with-lease
# (that fixes the last commit; to fix all: git rebase -r --root --exec 'git commit --amend --no-edit --reset-author')
```

### 3.3 Apply the kit
```bash
~/Downloads/rearchive-kit-v2/apply-kit.sh        # checks the 11 starter files, creates kit/v2, one commit
git diff --stat main kit/v2
git diff main kit/v2 -- CLAUDE.md .claude/settings.json .github/workflows/ci.yml
```
Read the CLAUDE.md and CI diffs fully. The kit replaces your `.github/workflows/ci.yml`; if yours had steps you rely
on, port them into the new file before merging.
```bash
git switch main && git merge --no-ff kit/v2 -m "Adopt kit v2" && git branch -d kit/v2
npm ci --prefix tools/ksc                        # pinned Kaitai compiler (no Java)
uv run --no-sync pytest -q tools/tests tests/contract
python3 tools/verify.py --fast                   # expect PASS; it now also lints tools/ and the hooks
git push origin main
```
If `verify.py` flags the kit's own files under your ruff rules, the kit's directories carry standalone `ruff.toml`
files. Only `tests/acceptance/test_gate_a_paths.py` is linted by your root config; adjust per-file-ignores if needed.

### 3.4 VS Code
1. Open the repository folder. Open the Claude Code panel. Check the briefing appears at the start of the session
   (it begins "ReArchive session briefing").
2. Run `/sandbox` and confirm: sandbox enabled, the protected paths under write-deny, network limited to PyPI and npm.
3. Smoke-test the guardrails with prompt **P-00** in `docs/PROMPTS.md`. It checks all three layers: hook blocks,
   sandbox write-denials, and that uv and ruff still work inside the sandbox. If any check fails, fix it before
   building.
4. Repository settings on GitHub: Actions enabled. Leave repository variable `ACCEPTANCE_REQUIRED` unset until
   Gate A.

---

## 4. Day 1 — close increment 0.1

### 4.1 Your ratification commit (on `main`, no Claude session open)
1. **D-015.** Paste Block 1 of `docs/proposals/D-015-ratification-2026-10-20.md` after D-014, with the handoff's
   corrections A (heading) and B (§14 names D-009). Its constants do **not** get added to it later: an accepted entry
   is never edited. They arrive as D-030 (step 4.2).
2. **D-016 – D-029.** Read `docs/decisions-pack/D-016-to-D-030.md`. Check its one assumption: the canonical dtype
   spellings in D-018 must match D-015's allowlist. Edit anything you disagree with, then paste from "## D-016" up to,
   not including, the D-030 template. Ratifying all of them now is the point: increments 0.2–0.7 then never stop for
   a decision.
3. **STATUS.md.** Replace the P0 increments section with `docs/kit/STATUS-increments-v2.md`. That replacement also
   removes the old "array hashing exactly as D-005" line; grep STATUS.md to make sure no other line still says it.
   Keep "Current increment: 0.1".
4. Commit: `git add docs/DECISIONS.md docs/STATUS.md && git commit -m "Ratify D-015..D-029; increments v2"`, push.
5. `python3 tools/verify.py --fast` must still PASS. Nothing in the pack is due before 0.1.

### 4.2 Builder session
`git switch -c inc/0.1` → new Claude tab → `/model opus` → Plan mode → `/increment 0.1` + **P-01**.
When the session reports `docs/proposals/D-030-d015-constants.md` ready: check every line against D-015, paste it
into DECISIONS.md on `main`, commit, push, then `git switch inc/0.1 && git merge main`. Record your acceptance of the
15 vectors in the STATUS log (only now: D-028 §3). When the session stops, run `/close 0.1` in it, audit (2.8) the
closing commit, merge, push.

### 4.3 Open questions the pack resolves
Ask the 0.1-close session to mark these in STATUS.md as "resolved by D-NNN" (P-01 does):
Q-04 → D-017 · Q-05 → D-019 · Q-07 → D-020 · Q-08 → D-019 · Q-09 → D-018 · Q-11 → D-018 · Q-12 → D-020 ·
Q-13 → arm64 runners (CI) · Q-14 → sandbox + Bash policy · Q-17 → D-015 ratified.

---

## 5. Increments 0.2 – 0.7 (Gate A)

For every increment:
- **You first:** set "Current increment" on `main`, commit, push, `git switch -c inc/<n>`.
- **Session:** new tab, `/model opus`, Plan mode, `/increment <n>`, plus the focus text for `<n>` from
  `docs/PROMPTS.md`.
- **Plan review:** use the checklist under the increment below. Reject plans that add modules without consumers,
  dependencies without need, or anything a decision does not cover.
- **Close:** your diff review, then `/close <n>` in the same session, then merge and push.
- **Before 0.4:** add `"src/rearchive/generated/**"` to `extend-exclude` under `[tool.ruff]` in pyproject.toml on
  `main` (the section is protected, so the builder cannot).

| Inc | Scope (detail in STATUS.md) | Gate A tests turning green | Plan review: insist on | Audit |
| --- | --- | --- | --- | --- |
| 0.2 | paths, store, ingest, ledger, report skeleton | none (contract constants for 0.2) | D-016 display rules tested byte by byte; store never overwrites; ledger tamper tests for edit/delete/reorder; sources opened read-only | no |
| 0.3 | generator, truth, evidence docs, oracle | `test_generator_is_deterministic_per_seed` | truth from generator parameters only; oracle never prints truth; bench never imports product | no |
| 0.4 | spec, ksc, sidecar, ops, records, descriptors, worker, resume | `test_decode_resumes_after_kill`, `test_gate_a_paths.py` | bits taken from source bytes; no floats/null in records; coverage arithmetic; worker limits; generated code excluded from ruff | **yes** |
| 0.5 | claims, policy v1, validate, anchors | `test_malformed_files_are_reported_not_dropped` | deterministic claim ids; policy is a pure function; estimator independent of decoder; replay equality | no |
| 0.6 | package, verify, score, report | 13 more (all but golden) | BagIt paths ASCII; signature excluded from tag manifest; verify verdicts separate; score reads only package + truth | **yes** |
| 0.7 | golden file, CI on three platforms, audit | the golden test | golden written only by you; all three CI legs green | **yes (Gate A)** |

### Gate A, step by step (0.7)
1. Builder: everything green except golden (`python3 tools/verify.py --gate A` shows only the golden test failing).
2. You, with no Claude session open: generate the golden file from the **final code**, then commit it on `main`
   (it is a protected path):
   ```bash
   git switch inc/0.7
   REARCHIVE_WRITE_GOLDEN=1 uv run pytest -q -m acceptance -k golden      # writes it, then fails on purpose
   cp tests/acceptance/golden/tier0_seed7.json /tmp/ && rm -r tests/acceptance/golden
   git switch main && mkdir -p tests/acceptance/golden && cp /tmp/tier0_seed7.json tests/acceptance/golden/
   less tests/acceptance/golden/tier0_seed7.json                           # read it: 3 variants x 6 hashes
   git add tests/acceptance/golden/tier0_seed7.json && git commit -m "Gate A golden hashes" && git push
   git switch inc/0.7 && git merge main
   ```
3. CI must be green on `ubuntu-24.04`, `ubuntu-24.04-arm` and `macos-15` for the merged branch.
4. `/close 0.7` (runs `verify.py --close --gate A`). Audit the commit. Disposition every finding.
5. Merge. Set repository variable `ACCEPTANCE_REQUIRED=true`. Record "Gate A passed <date> at <commit>" in the
   STATUS log. Phase → P1.

---

## 6. P1 – P4

Each phase starts with a **kickoff session** (prompts P-10, P-20, P-30, P-40) that drafts that phase's decisions and
gate tests into `docs/proposals/`. You review and ratify them before the first increment, so every gate exists before
the code it judges.

| Phase | Weeks | Increments | Gate |
| --- | --- | --- | --- |
| P1 | 5–6 | 1.1 generator v2 (tiers 0–1, clean controls) · 1.2 ops `unpack_bits`, `deinterleave`; spec-level mutations · 1.3 MCP investigation tool server · 1.4 non-AI search baseline · 1.5 agent runner + scoreboard | **B**: agent, baseline and agent+tools scored on ≥200 formats; every mutation class caught for the intended reason; false rejections reported |
| P2 | 7–8 | 2.1 offline triage CLI · 2.2 LeCroy `.trc` reconciliation and reader lineage · 2.3 prospect intake kit | **C** (commercial): a qualified prospect shares files under NDA |
| P3 | 9–10 | 3.1 workbench (three views) · 3.2 kill-loop stress, fuzzing, OS isolation · 3.3 tier 2 | — |
| P4 | 11–12 | 4.1 clean-install tests and signed releases · 4.2 public synthetic demo · 4.3 outside verification | **D**: someone outside the team verifies a signed package |

The AI recovery agent arrives only in P1, after the deterministic engine it drives is gated. That ordering is
deliberate.

---

## 7. When things go wrong

| Symptom | Do this |
| --- | --- |
| "PROTECTED PATHS differ from baseline" | Stop the session. `git diff main -- <path>`. If it is your edit: commit on main, merge into the branch. If not: `git checkout main -- <path>` yourself, then ask the session what it ran (P-90). |
| Briefing says "branch is not inc/<n>" | Switch branches yourself, then `/clear`. |
| Stop hook keeps reporting failing tests | It fires once per stop by design. Read the failure; never accept a fix that skips or loosens a test. |
| Contract test fails for a constant due **before** the current increment | A regression. Fix it on the branch before anything else. |
| `verify.py` says the contract or tools suite skipped tests or ran none | Someone added a skip or a conftest; owner-owned suites must run in full. Find it with `git diff main -- '*conftest.py' pyproject.toml`. |
| `verify.py` fails `mutation_leftovers` | A mutation run was killed. Run `python3 tools/mutate.py --list <any module>` once (it restores and stops), then `git diff -- src/`. |
| The plan improvises a format, threshold or vocabulary | Reject it: "That is a gap. Run /decide." |
| Review round 3 looks necessary | Decide yourself: merge with open questions, or narrow the increment. Don't let the loop run on. |
| Usage limits hit mid-increment | `/handoff`, commit what is green on the branch, resume later in a new session from the handoff. |
| A sandbox prompt asks to run a command unsandboxed | Deny it. `allowUnsandboxedCommands` is false; a request to bypass is itself a finding. |
| Session went off-scope | `git diff --stat main...HEAD`; keep what belongs (`git restore -p` yourself), `/clear`, restart with `/increment <n>`. |
| CI red on arm64 or macOS only | A determinism finding: the canonical bytes differ by platform. Treat it as P0. |

---

## 8. Calendar and the non-code track

| Dates (2026) | Build | Discovery (you) |
| --- | --- | --- |
| Oct 22 | Day 0 setup; ratification; 0.1 closed and audited | Write the target list: 40 QA, lab-informatics and validation-consultancy contacts |
| Oct 23 – Oct 27 | 0.2, 0.3 | First 8 conversations booked |
| Oct 28 – Nov 2 | 0.4 (two sessions) + audit; 0.5 | 8 conversations held; score each on the spec's 8-factor scorecard |
| Nov 3 – Nov 9 | 0.6 + audit; 0.7 → **Gate A** | 15 held; triage-CLI interest noted per prospect |
| Nov 10 – Nov 23 | P1 → **Gate B** | 25 held; at least 3 at G2 |
| Nov 24 – Dec 7 | P2 → **Gate C** | NDA and sample files from one prospect |
| Dec 8 – Dec 21 | P3 | Paid-assessment proposal drafted |
| Jan 4 – Jan 17, 2027 | P4 → **Gate D** | Assessment signed, or pivot decision (verdict kill criteria) |

The dates hold only if discovery runs in parallel. Gate C is commercial, and no amount of code passes it.

---

## 9. Reference

**Slash commands:** `/increment <n>` · `/close <n>` · `/verify [fast|gate-A]` · `/gate` · `/decide <topic>` ·
`/mutate <module> [tests]` · `/audit-prep [commit]` · `/handoff`

**Subagents:** `invariant-reviewer` · `test-skeptic` · `claims-checker`

**Your commands:**
```bash
python3 tools/verify.py [--fast] [--close] [--gate A]     # report in reports/verify/
python3 tools/verify.py --check-report reports/verify/latest.json
python3 tools/protected_paths.py check [--base REF]
uv run python tools/decision_constants.py [--mode regression|closure|all]
python3 tools/mutate.py src/... --tests tests/unit/... [--function NAME]
tools/audit.sh [COMMIT] [--run]
tools/ksc/regen.sh                                       # .ksy → src/rearchive/generated/
```

**Files the kit added:** `.claude/hooks/{session_start,bash_policy,protected_guard}.py`, the updated lint and stop
hooks, three agents, eight skills, `tools/` (verify, protected_paths, decision_constants, mutate, audit, ksc, tests),
`tests/contract/`, `tests/acceptance/test_gate_a_paths.py`, `specs/tier0/tier0.ksy`, `docs/prompts/audit.md`,
`docs/decisions-pack/`, `docs/kit/`, this playbook and `docs/PROMPTS.md`.
