# ReArchive — handoff, 2026-10-21

Written by the implementation session for whoever picks this up next, human or agent.
Every figure below was produced by running the command named beside it, in the
state described. Nothing here is recalled from an earlier report.

**Read this first:** increment 0.1's code is written and passing, and increment
0.1 is **not closed**. Those are different things, and the gap between them is
the whole content of this document.

---

## 1. One-paragraph summary

Increment 0.1 ("Tooling and canonical bytes") is implemented: a `uv` project with
two packages, honest not-implemented CLI stubs, RFC 8785 JCS canonicalisation via
a pinned third-party library behind a ReArchive-owned API, and a canonical array
wire format with its own typed error contract. 218 unit tests pass; ruff, ruff
format and strict mypy are clean; the two acceptance tests the increment targets
are green. **Nothing is committed** — the repository still has exactly one commit,
the starter kit. **The decision the array format implements (D-015) has never been
recorded in `docs/DECISIONS.md`**, so the format is provisional, its 15 vectors are
non-normative, no golden file may be written, and the increment cannot close.

---

## 2. Status, in the only taxonomy that matters here

These are not interchangeable. The project has been bitten by collapsing them.

| Status | Holds? | Evidence |
| --- | --- | --- |
| **Implemented** | **Yes** | 6 source files under `src/`, 413 lines of canonical logic |
| **Unit-tested** | **Yes** | `218 passed, 19 deselected` |
| **Static checks passed** | **Yes** | ruff clean, `11 files already formatted`, mypy strict clean on 6 files |
| **Acceptance-tested** | **Partly** | 2 of 19 gate tests pass — exactly the two 0.1 targets. The other 17 are future-increment stubs |
| **Reproducible from a clean clone** | **Yes** | verified by export + `uv sync --locked` + pytest, twice, by two different sessions |
| **Reviewed by the project's invariant-reviewer** | **Stale** | the completed review inspected `canonical.py` blob `bc3734ac`; the current blob is `3310f878` because its own findings were then fixed |
| **Independently audited** | **No** | impossible today: the implementation exists only in the index, so no worktree can see it |
| **Owner-ratified** | **No** | `docs/DECISIONS.md` has **0** `## D-015` headings and ends at `## D-014` |
| **Committed** | **No** | `git rev-list --count HEAD` = **1** (`c060158`, the starter kit) |
| **Increment formally closed** | **No** | see §4 |

---

## 3. Exact repository state

```
branch    main
HEAD      c0601584f173ab4a19e721039374ae94fed9dba9   ("Add ReArchive starter kit")
commits   1
staged    34      unstaged 5      untracked 1      stash 0
worktrees /home/s1/projects/rearchive  c060158 [main]
          /tmp/rearchive-audit-0.1     c060158 (detached)
```

Key blobs, for anyone comparing against a review report:

| Blob | File |
| --- | --- |
| `3310f878da89` | `src/rearchive/core/canonical.py` |
| `eaa335c9cc02` | `tests/unit/test_canonical_arrays.py` |
| `892846d77e86` | `docs/DECISIONS.md` — identical to the `c060158` blob |
| `a9225fe41af0` | `tests/acceptance/test_gate_a.py` — identical to the `c060158` blob |

**`/tmp/rearchive-audit-0.1` is useless as an audit snapshot.** It is pinned to
`c060158` and contains only `rearchive-starter/` — no `src/`, no `tests/unit/`.
An audit run against it reviews nothing, which is why an earlier audit returned
INDETERMINATE. It cannot be fixed without a commit, because a detached worktree
can only check out a commit and the implementation has never been committed. It
was preserved rather than deleted; do not treat it as evidence.

### Unstaged vs staged

The 34 staged files are the increment-0.1 implementation. The 5 unstaged files
are later corrections that were never re-staged (per-file staging only; this
project has banned `git add -A`, see §9):

```
src/rearchive/core/canonical.py          defect fixes, §7
tests/unit/test_canonical_arrays.py      regression tests, §7
docs/STATUS.md                           log entry, Q-17, corrected pointer
docs/proposals/D-015-RATIFICATION-DRAFT.md          SUPERSEDED banner
docs/proposals/D-015-canonical-array-wire-format.md HISTORICAL banner
docs/proposals/D-015-ratification-2026-10-20.md     (untracked) the current draft
```

---

## 4. Why increment 0.1 is not closed

`docs/STATUS.md:13` requires: *"unit tests green, `invariant-reviewer` run, log
entry below, human review, human commit."* Line 22 adds the clean-clone gate and
names the two acceptance tests.

| Criterion | Status | Who closes it |
| --- | --- | --- |
| Unit tests green | **Verified** | — |
| Clean clone → `uv sync && pytest` | **Verified** | — |
| Two import-boundary tests green | **Verified** | — |
| `invariant-reviewer` run | **Stale** — reviewed `bc3734ac`, code is now `3310f878` | engineer: re-run |
| Log entry | **Done** | — |
| `array hashing exactly as D-005` (line 19) | **False** — the format adds a version prefix, two length fields, a JCS header and two caps that appear in no ratified decision | **owner**: ratify D-015, amend line 19 |
| Human review | **Pending** | **owner** |
| Human commit | **Pending** | **owner** |

Two blockers, in dependency order: **ratify D-015**, then **re-run the reviewer**
on the current blob. Everything else is verified or is yours to sign off.

---

## 5. The D-015 situation — read before touching the wire format

The canonical array format implements a decision that **does not exist in the
decision log**. This is disclosed, not concealed: `docs/STATUS.md` Q-01, Q-02,
Q-17 and the log's Deviation list all say so.

What happened, briefly: Option A was implemented first (`schema_version` inside
the JCS header), which conflicted with D-005's stated component order. The owner
selected **Option B** — `u16le(schema_version) + u64le(len(header)) + header +
u64le(len(payload)) + payload` — which puts the version genuinely first and so
matches D-005's order. The implementation was switched and all 15 vectors
regenerated. The decision text went through several owner correction passes.
**The resulting text was never filed.**

### Which document is which — this has already caused one near-miss

| File | Role | Safe to paste? |
| --- | --- | --- |
| `docs/DECISIONS.md` | **The only authority.** Ends at D-014 | n/a |
| `docs/proposals/D-015-ratification-2026-10-20.md` | **Current draft**, 377 lines, owner-reviewed | **Yes**, with the two corrections in §6 |
| `docs/proposals/D-015-RATIFICATION-DRAFT.md` | **SUPERSEDED — DO NOT PASTE.** Still says rank ≤ 8, a 1024-octet header cap, and "no maximum payload length" | **No** |
| `docs/proposals/D-015-canonical-array-wire-format.md` | **HISTORICAL.** §1 onward describes Option A; its §0.1 Option A/B comparison is still accurate and is why Option B was chosen | **No** |

The two superseded files are kept deliberately as the record of what was caught.
`docs/STATUS.md` Q-17 previously pointed at the superseded draft as "the pasteable
text"; that pointer was wrong and is corrected. Had it been followed, the ratified
decision would have contradicted the code in three places on day one.

---

## 6. To ratify: exactly what to do

Paste Block 1 of `docs/proposals/D-015-ratification-2026-10-20.md` after D-014.
**That file is copy-ready as of 2026-10-21**: the two governance corrections below
have been applied to it, and its Block 3 no longer instructs an edit to D-009.
They are recorded here so the reasoning survives, not as outstanding work.

**A — the heading.** Replace
`## D-015 Canonical array wire format (refines D-005, changes §10.1)`
with
`## D-015 Canonical array wire format (changes §10.1 and §10.2)`.
All fourteen existing headings name a `PROJECT_SPEC` section and never another
decision; D-005's own heading is `(changes §10.1)`.

**B — §14 must name what it refines.** Append to §14:

> This section refines **D-009**'s `hash(inputs, versions, runtime identity)` by
> fixing what occupies the `inputs` position for a canonical array. It does not
> supersede D-009 and does not alter its resume semantics, its
> temp-write-then-rename rule, or its Phase 0 timing. D-009's text is unchanged.

**Do not append anything to D-009 itself.** The preamble forbids it: *"To change a
decision, add a new entry that supersedes it — never edit an accepted entry
silently."* An earlier draft of the package instructed exactly that; it was wrong
and has been withdrawn in the file's Block 3.

### Order of application

| # | Action | File | Required? |
| --- | --- | --- | --- |
| 1 | Append D-015 with corrections A and B | `docs/DECISIONS.md` | **Yes** |
| 2 | Line 19 → "as D-005 refined by D-015 (Option B)" | `docs/STATUS.md` | **Yes — apply with step 1** |
| 3 | §10.2 amendment (Block 4 of the draft) | `docs/PROJECT_SPEC.md` | **Optional** — D-001 makes DECISIONS override the spec, so §14 binds anyway |
| 4 | Review the 15 vectors, record acceptance | `docs/STATUS.md` log | Before any golden file |
| 5 | Re-run the invariant reviewer on `3310f878` | — | Before closure |
| 6 | Commit, then create an audit worktree at that hash | — | For independent audit |

Steps 1 and 2 must land together: between them, line 19 contradicts the entry.

---

## 7. Defects found and fixed

Three real defects, all found by adversarial review rather than by the test suite,
and all verified by execution before and after the fix.

**Tests that proved nothing.** Three assertions claimed to enforce the payload
representability bound. A mutation run replacing `if octets > MAX_PAYLOAD_OCTETS:`
with `if False:` left **88 array tests green**, because every case passed
`values=[]` and the next check raised the *same* `PayloadLengthError` class with
no test matching on the message. Fixed with `match="not representable in the u64le"`
on three sites; the same mutant now gives **2 failed, 88 passed**.

**`MemoryError` escaped the typed contract.** `flat = list(values)` ran before both
length checks, so `values=range(10**8), shape=[3]` — legitimately typed, since
`range` is a `Sequence` with cheap `__len__` — raised bare `MemoryError`, neither a
`ValueError` nor a `CanonicalizationError`. Fixed by checking `len(values)` before
materialising. Now `PayloadLengthError`.

**`RecursionError` escaped `canonical_json`.** Deep nesting and self-referential
containers surfaced an untyped exception, contradicting the base class's "every
canonicalisation failure" claim. Wrapped as `UnsupportedTypeError`.

Also fixed earlier in the increment: an int beyond binary64's range escaped
`_checked_float` as bare `OverflowError` — the existing overflow test only covered
*float* inputs, which is why six review rounds missed it.

---

## 8. What exists

```
src/rearchive/core/canonical.py   413   JCS wrapper + array wire format + 8 error classes
src/rearchive/cli.py               64   stub CLI, exits 70, empty stdout
src/rearchive_bench/cli.py         60   stub CLI, deliberately duplicated (D-012)
tests/unit/test_canonical_json.py 363   110 tests — RFC 8785 conformance
tests/unit/test_canonical_arrays.py 688  90 tests — D-015 framing + 15 vectors
tests/unit/rfc8785_vectors.py     267   RFC vectors with provenance
tests/unit/test_cli_stubs.py      153   18 tests — CLI honesty
tests/unit/conftest.py             29   derandomised Hypothesis profile (Q-15)
pyproject.toml / uv.lock / .python-version / .github/workflows/ci.yml
```

One runtime dependency: `rfc8785==0.1.4` (Trail of Bits, Apache-2.0, 9.2 kB, zero
transitive deps), wrapped behind ReArchive's own error hierarchy. No NumPy.
Python pinned to **3.12.15** via `.python-version` (bare `3.12` does not fix a
patch version and would let the three D-013 legs drift).

### Verification, as of 2026-10-21

```
uv run ruff check .                    ->  All checks passed!
uv run ruff format --check .           ->  11 files already formatted
uv run mypy src                        ->  Success: no issues found in 6 source files
uv run pytest -q -m "not acceptance"   ->  218 passed, 19 deselected
uv run pytest -q -m acceptance         ->  4 failed, 2 passed, 218 deselected, 13 errors
```

**Acceptance, classified individually** — not labelled "expected" wholesale.
Passing: `test_product_never_imports_the_benchmark`,
`test_benchmark_never_imports_the_product`. The other 17 share one root cause
(`rearchive-bench generate` exits 70 "not implemented") and map to increments
0.2 (ingest), 0.3 (generator), 0.4 (decode), 0.5 (claims), 0.6 (package),
0.7 (golden file). None is masking a different defect.

**CI has never run**, on any architecture. There is no git remote.
`.github/workflows/ci.yml` is not evidence of a passing build, and D-013's
cross-environment claim is unverified — everything above is Linux x86-64 only.

All **11** protected paths are byte-identical to `c060158`:
`docs/DECISIONS.md`, `docs/PROJECT_SPEC.md`, `CLAUDE.md`, all six under
`.claude/`, and both files under `tests/acceptance/`.

---

## 9. Traps — things that have already gone wrong here

Read these before running anything broad.

**`ruff format .` can rewrite protected files.** Ruff formats Python code blocks
inside Markdown, so the command named in `CLAUDE.md` had `CLAUDE.md`,
`docs/DECISIONS.md`, `docs/PROJECT_SPEC.md` and `.claude/**` in scope. It
**actually rewrote `tests/acceptance/test_gate_a.py`** (41 insertions, 12
deletions) during this increment, restored byte-identically from the index. Root
cause: `[tool.ruff.format] exclude` does **not** match a bare directory —
`tests/acceptance` is ignored, `tests/acceptance/**` works. Now fixed with the
working pattern plus `force-exclude = true`. **Never run a repository-wide
formatter; format named files only.**

**Never `git add -A` or `git add .`.** Stage per file. A blanket add changed the
index under a running reviewer mid-audit.

**Subagents are not bound by the Bash deny list.** A subagent fetched a public RFC
with `curl`, which `.claude/settings.json` denies. Benign here, but the guardrail
is narrower than it appears (Q-14).

**Edits can silently no-op.** Two "fixes" targeted strings that did not match the
file on disk; the replace did nothing and was reported as done. Every edit now
goes through a helper that asserts the target string exists.

**Prose goes stale faster than code.** Across six review rounds, every blocking
finding after round 1 was a sentence — in a comment, docstring or log — asserting
something the code did not do. Numbers that were correct when written went stale
when the thing they described changed, inside a block headed "Commands run, with
their real output". Defence: grep a distinctive word from each claim across all
authored files and check every hit for consistency.

---

## 10. Open questions

`docs/STATUS.md` carries **17** (Q-01…Q-17). The ones that gate future work:

| ID | Gates | Substance |
| --- | --- | --- |
| **Q-17** | 0.1 closure | D-015 approved but unrecorded |
| **Q-04 / U-7** | **0.4** | Per-file canonical record composition is undefined. The gate requires one `canonical_sha256` per file; D-015 defines one array's bytes and stops. Two conforming implementations would disagree today |
| **Q-09 / U-6** | **0.4** | Source byte order has nowhere to live. Canonical payloads are always little-endian, so big- and little-endian sources with equal values collapse to identical bytes. **No decoder depending on source byte order may be accepted until this is decided** |
| **Q-11 / U-5** | 0.4 | Kaitai-to-canonical dtype mapping unwritten (`u2` vs `uint16`) |
| **Q-05** | 0.4 | Float dtypes are in the allowlist with no enforcement point; D-015 §6 states the rule, nothing in code enforces it |
| **Q-08** | 0.4 | A NaN `gain`/`offset` would raise rather than produce a diagnostic, which 0.4 requires |
| **Q-07** | tier 1+ | Integers above 2⁵³ cannot live in JCS metadata at all |
| **Q-10** | tier 1+ | No `int24`; D-004 queues `unpack_bits` and the raw codes are 24-bit |
| **Q-12 / U-8** | 0.5 / pre-P1 | Missing values, timestamps, text encoding unaddressed |
| **Q-13** | 0.7 | arm64 CI on a private repo is a paid runner; no remote exists |
| **Q-16** | optional | An in-repo independent ECMA-262 formatter would make the RFC conformance claim reproducible by anyone |

**OD-1 is resolved** for `schema_version` 1: natively floating-point measurement
sources are out of scope. Extending that needs a superseding decision **and**
amendments to `docs/DECISIONS.md` D-005 and `CLAUDE.md` invariant 6, both of which
say "raw **integer** codes" verbatim. Note the tension pre-exists D-015: D-004
defines `view` as "integer/**float** dtype".

---

## 11. Deliberately not done

- **Nothing committed.** The owner commits.
- **Protected-path guard not installed.** A patch supplies
  `.claude/hooks/protected-paths-unchanged.sh`; its permissions are byte-identical
  to the current ones and the hook is read-only (verified). **Install it only
  after the first commit** — it compares against `HEAD`, and on the current
  uncommitted tree it fires on all 11 protected paths and hard-blocks every
  Edit/Write/Bash, because `HEAD` still has them at `rearchive-starter/…`.
- **Increment 0.2 not started.**
- **No golden file.** `tests/acceptance/golden/` does not exist and must not until
  D-015 is recorded and the vectors are accepted.
- **No NumPy, no network, no telemetry.**

---

## 11a. Publishing is blocked by project policy, not by a missing step

As of 2026-10-21 this repository **cannot be pushed from an agent session**, by
the project's own configuration:

- **No remote is configured.** `git remote -v` is empty.
- **`Bash(git push:*)` is in the deny list** in `.claude/settings.json`. That file
  is itself deny-listed for editing, and it must not be edited to work around its
  own rule.
- **`gh` is not installed**, and `Bash(curl:*)` / `Bash(wget:*)` are also denied,
  so a repository cannot be created through the GitHub API either.

Any of those three could be changed by the owner; none may be circumvented from a
session. Publishing therefore requires the owner to create the GitHub repository,
add the remote, and run the push, or to relax the deny rule deliberately.

**Also check before publishing:** `git config user.email` is
`shreshthf2503gmail.com` — it has no `@`. Commits made with it will not attribute
to a GitHub account. Left unchanged because git identity is the owner's to set.

## 12. Next actions, in order

1. **Owner:** ratify D-015 (§6), applying corrections A and B, and amend
   `docs/STATUS.md` line 19 in the same change.
2. **Engineer:** re-run the `invariant-reviewer` against blob `3310f878`. The
   completed review inspected the pre-fix blob, so its PASS/FAIL does not apply
   to the current code.
3. **Owner:** review the 15 Option B vectors and record acceptance in the
   `docs/STATUS.md` log. Only then may a golden file exist.
4. **Owner:** authorise a commit. Stage per file; inspect both diffs first.
5. **Engineer:** create an audit worktree at the new commit hash, confirm its
   `HEAD` and that it contains `src/` and `tests/unit/`, then start a separate
   read-only session. Do not reuse `/tmp/rearchive-audit-0.1` without inspecting it.
6. **Then, and only then:** set "Current increment" to 0.2 and begin its own
   requirements register. 0.2 is the content-addressed store, ingest and ledger.

---

## 13. One thing worth knowing about this record

Six adversarial review rounds found **zero defects in the canonical bytes
themselves**. The vectors re-derive independently, the RFC conformance column was
confirmed canonical by an independent ECMA-262 implementation, and the framing
parses back exactly. Every blocking finding after the first round was prose
claiming more than the code did — including, twice, prose written while fixing
the previous round's prose.

The code has been trustworthy longer than the documents about it. Treat any
confident summary in this repository, including this one, as a claim to re-verify
rather than a fact to inherit. The commands in §8 are cheap; run them.
