# ReArchive — prompt book

Copy-paste prompts for VS Code + Claude Code. Each increment starts the same way, in a **new tab** (`Ctrl+Shift+Esc`)
or after `/clear`:

```
/model opus
(switch to Plan mode: click the mode indicator under the prompt box, or type /plan)
/increment <n>
<paste the focus text for <n> below>
```

The `/increment` command carries the generic procedure (preconditions, plan, test-first, verify, review, log). The
focus text adds what is specific to the increment. Prompts are numbered so the playbook can refer to them.

---

## P-00 — Day 0 guardrail smoke test (run once, on a throwaway branch)

```
This is a guardrail test, not real work. Run each command below exactly as written, one at a time, and report for
each whether it ran, was blocked by a hook (quote the message), was refused by the permission system, or failed with
an operating-system error (quote it). Do not try alternatives or workarounds. Do not edit any file yourself.

1. git add -A
2. uv run ruff format .
3. git push origin HEAD
4. sed -i 's/x/y/' src/rearchive/cli.py
5. echo test >> tests/acceptance/test_gate_a.py
6. git restore CLAUDE.md
7. curl -sI https://example.com
8. python3 -c "import pathlib; pathlib.Path('tools/sandbox-probe').touch()"
9. cd tests/contract && touch sandbox-probe.py
10. uv run --no-sync pytest -q tests/contract
11. uv run ruff check --no-cache .

Then try to use the Edit tool to add a blank line at the end of docs/DECISIONS.md, and report what happened.
Finally run: python3 tools/protected_paths.py check
```
Expected:
- 1–7 blocked by `bash_policy.py` or the permission system.
- 8 and 9 pass the hook (it cannot see them) and must fail with a read-only or permission error **from the sandbox**.
  If either file gets created, the sandbox is not active: run `/sandbox`, check bubblewrap and socat, and do not build
  until it is.
- 10 and 11 succeed. This proves uv and ruff can write their caches inside the sandbox.
- The Edit is refused, and the final check is clean.

If anything wrote a file, run `git status`, then delete only the probe files it lists. Never use a blanket
`git checkout -- .`, which would also discard your own work.

---

## P-01 — close increment 0.1 (focus text after `/increment 0.1`)

```
Increment 0.1 is implemented; this session closes it. D-015 and D-016..D-029 are now ratified in docs/DECISIONS.md:
read D-015, D-016 §7, D-018 §4 and D-028 first. Plan, wait for approval, then:

1. Draft D-030 (the constants of D-015; see the D-030 template in docs/decisions-pack/D-016-to-D-030.md). Write a
   ready-to-paste entry to docs/proposals/D-030-d015-constants.md: heading "## D-030 Normative constants of D-015
   (changes §10.1)", one paragraph, and a `decision-constants due=0.1` block — schema version, dtype allowlist
   (rearchive.core.canonical.ALLOWED_DTYPES), rank/header/payload caps, digest format. Beside each line, name the
   D-015 sentence it encodes and the code symbol that holds it. Where code and D-015 disagree, report it as a P1
   finding; do not resolve it by editing either. Then tell me it is ready and continue with step 2 while I review it.
2. Expose the D-015 dtype allowlist as rearchive.core.canonical.ALLOWED_DTYPES (alias if it exists under another
   name) and add JSON_MAX_DEPTH = 64 with typed rejection of deeper nesting (D-016 §7).
3. Audit F-01: canonical_json must raise the typed error for lone surrogates in KEYS as well as values. Extend the
   Hypothesis strategies to generate surrogates in keys. Check first whether this is already fixed; add the test
   either way.
4. Audit F-06: a test that big-endian and little-endian typed inputs with equal values give identical canonical
   bytes; a test that every struct format literal in the canonical module starts with "<".
5. A test that the installed rfc8785 version equals the pin in pyproject.toml.
6. In docs/STATUS.md open questions, mark as resolved, with the decision: Q-04 D-017, Q-05 D-019, Q-07 D-020,
   Q-08 D-019, Q-09 D-018, Q-11 D-018, Q-12 D-020, Q-13 arm64 runners in CI, Q-14 sandbox and Bash policy,
   Q-17 D-015 ratified. Do not touch the "Current" lines.
7. Use the test-skeptic subagent on src/rearchive/core/canonical.py with the canonical unit tests; add tests for P1
   gaps.
Then stop. I will ratify D-030, merge main into this branch, record acceptance of the 15 vectors, and run /close 0.1.
```

---

## P-02 — paths, store, ingest, ledger, report skeleton

```
Focus for 0.2. Decisions: D-016, D-021, D-022, D-026 §4–5. Constants due at 0.2 are listed by
`uv run python tools/decision_constants.py --mode regression`; your plan must name the symbol satisfying each.
- relpath_display: implement D-016 §3 exactly; test it byte by byte against a table that includes invalid UTF-8,
  truncated sequences, surrogate encodings (ED A0 80), C0 controls, 0x7F and backslash. Expected values come from
  the decision text, not from calling the function.
- Layout: pure logic in rearchive.core (paths, keys, ledger chain, report outcome rules); filesystem, store and
  SQLite in rearchive.adapters. core stays free of I/O.
- Ingest opens sources read-only and never follows symlinks (lstat). Run the ingest tests with the source directory
  chmod-ed read-only.
- Store: a temp file in the same directory, fsync, rename, fsync directory; an existing key is never overwritten;
  a differing object under an existing key raises the typed integrity error. Test with a fault injected between
  write and rename.
- Ledger: SQLite in WAL mode. Tests for edit, delete and reorder of events, each detected by the chain; tail
  truncation is NOT detectable by the chain alone (D-022 §5) — test that it is reported as such, not hidden.
- report --json at this stage: files with source_relpath, sha256, canonical_sha256 null, outcome "unverified",
  state "ingested", plus ledger {head, valid}.
Done when re-ingesting the same read-only directory is a no-op recorded as `task_reused` in the ledger. Then stop;
I will run /close 0.2.
```

## P-03 — generator, truth, evidence documents, oracle

```
Focus for 0.3, all in rearchive_bench. Decisions: D-011, D-012, D-024 §1–3, D-027; the Tier-0 format v1 table in
STATUS.md.
- `rearchive-bench generate` exactly per the CLI contract at the top of tests/acceptance/test_gate_a.py.
- Truth is computed from generator parameters (amplitude, frequency, offset, gain, quantisation) in the benchmark's
  own code. Grep-check that rearchive_bench imports nothing from rearchive.
- Evidence documents: stimulus.json (anchored), attestation.yaml (attested), nothing (no-anchor), exact schemas from
  D-024 §2–3. The sine's frequency must be consistent with sample_interval and sample_count.
- `rearchive-bench oracle --truth DIR`: JSON Lines protocol of D-024 §1; answers structure and value checks with
  pass/fail only; refuses semantic checks. Test that no response ever contains a truth value (search responses for
  every truth number).
Turns green: test_generator_is_deterministic_per_seed. Then stop; I will run /close 0.3.
```

## P-04a — spec, sidecar, ops, records (session 1 of 2)

```
Focus for 0.4, session 1 of 2: spec, sidecar, ops, records. Decisions: D-003, D-004, D-017, D-019, D-020, D-029.
- Use specs/tier0/tier0.ksy as shipped (change it only through a decision); write
  specs/tier0/tier0.rearchive.yaml per D-029. Run `tools/ksc/regen.sh` (it asks for approval; the compiler's
  node_modules were installed on Day 0 — if missing, ask me to run `npm ci --prefix tools/ksc`, which the sandbox
  will not let you do). Commit the generated parser. I have already excluded src/rearchive/generated/** from ruff in
  pyproject.toml ([tool.ruff] is protected); if it is missing, stop and ask.
- Dependencies: kaitaistruct==0.11 and PyYAML (safe_load only). Justify both in the plan.
- Sidecar loader: unknown keys and unknown ops are load errors (D-029 §1–2).
- Ops view (dtype + byte order) and crc32 (evidence only) in rearchive.decode; the affine derived view in
  rearchive.views, outside the decode path (no floating point there, D-026 §2). Hypothesis properties: view
  round-trips arbitrary bytes for every dtype and byte order; affine output never enters a record.
- Records (D-017, D-019, D-020): float fields' bits read from the source bytes at the Kaitai _debug offsets, never
  from the parsed float; integers as decimal strings; no JSON floats or null anywhere (the record builder rejects
  them). Tests: NaN with payload, signalling NaN, -0.0 and +inf survive bit-exactly; equal values from big- and
  little-endian sources give equal canonical_sha256.
Stop after records are complete and green; session 2 does the worker, descriptors, resume and report.
```

## P-04b — worker, descriptors, resume, report (session 2 of 2)

```
Focus for 0.4, session 2 of 2, same branch. Read the STATUS log entry from session 1 first. Decisions: D-018,
D-021, D-026.
- Decode descriptor and coverage (D-018): explained + padding + unexplained == size, tested on the tier-0 file,
  truncated files and files with trailing bytes.
- Worker subprocess (D-026 §1): `python -I -m rearchive.worker`, scrubbed environment, temporary working directory,
  CPU, wall-clock and (Linux) address-space limits; unenforced limits recorded in the descriptor. A test that an
  infinite loop in a spec-driven decode is killed and reported as `timeout`.
- Decode keys and resume (D-021): rerunning decode reuses every completed key; a kill between files leaves no
  partial artifact; REARCHIVE_TASK_DELAY_MS honoured.
- report --json gains canonical_sha256, coverage and outcome.
Turns green: test_decode_resumes_after_kill and tests/acceptance/test_gate_a_paths.py. Then stop; I will run /close 0.4
I will run an audit.
```

## P-05 — claims, evidence, policy v1, validate

```
Focus for 0.5. Decisions: D-006, D-007, D-023, D-024, D-026 §4.
- Claim and evidence ids are deterministic (D-023 §1); test that two runs produce identical claim sets.
- Policy v1 is a pure function of (claims, evidence, human events); status is never assigned anywhere else. Grep for
  any assignment of a status literal outside the policy module and report it.
- Circularity (D-007): a test where evidence assumes the claim it supports, directly and through a chain of two,
  and is rejected.
- Physical anchor (D-024 §2): the estimator computes physical values itself from canonical raw codes and the bit
  patterns of gain and offset; it must not import decoder scaling code. Test the estimator on synthetic sines,
  then record a gain-error sweep (smallest detectable relative gain error for tier 0) in the STATUS log.
- Oracle client spawns `rearchive-bench oracle` as a subprocess (never imports it).
- Variants: anchored → unit claim supported via physical_anchor; attested → supported via attestation;
  no-anchor → unresolved. Never hidden_ground_truth on a semantic claim.
Turns green: test_malformed_files_are_reported_not_dropped. Then stop; I will run /close 0.5.
```

## P-06 — package, verify, score, report

```
Focus for 0.6. Decisions: D-010, D-025, D-027.
- Package layout exactly per D-025 §1; every path inside the bag is ASCII; sources by content hash.
- rearchive-signature.json is NOT in tagmanifest-sha256.txt; verify reports integrity, replay and trust separately;
  exit 0 iff integrity passes.
- Development signing key lives in ~/.config/rearchive/, never in the repository; tests use a temporary key.
- Dependency: cryptography (Ed25519). Justify it in the plan.
- `rearchive-bench score` reads only the package and the truth directory; every score reported with numerator and
  denominator (D-027).
- Tamper tests: flip one byte in each kind of payload file and in the tag manifest; each must fail integrity with
  the path named.
Turns green: the remaining Gate A tests except the golden test. Then stop; I will run /close 0.6 and an audit.
```

## P-07 — Gate A

```
Focus for 0.7. Make `python3 tools/verify.py --gate A` fail on nothing but the golden test. Do not create
tests/acceptance/golden/ yourself — I generate and commit the golden file. Once I have merged it into this branch,
run `python3 tools/verify.py --close --gate A` and stop; I will run /close 0.7. Report CI status for all three
platforms from the
latest run (I will paste it if you cannot see it).
```

---

## P-10 — P1 kickoff (after Gate A; one session, drafts only)

```
We are starting P1 (weeks 5–6, Gate B). This session drafts; it implements nothing. Number each decision with the
next free D-number after the last one in docs/DECISIONS.md (shown below as D-0NN). Read docs/PROJECT_SPEC.md §8–9,
§17, docs/DECISIONS.md and the Gate A closure record. Produce, under docs/proposals/:
1. D-0NN Procedural format family (generator v2): the sampled format parameters for tiers 0–1 (field order, magic,
   header size, byte order, signedness, packed 12/24-bit, float32/64, interleaved channels), seeds, the frozen
   generator version, clean controls, and how truth stays sealed. Constants block due=1.1.
2. D-0NN Investigation tool server (MCP): tool list and exact JSON schemas (inventory, clusters, hexdump, diff,
   stats_map, solve_lengths, checksum_search, try_view, propose_spec, run_spec on the dev split only), byte-range
   logging as audit evidence, no network or filesystem access beyond the workspace.
3. D-0NN Non-AI search baseline: search space and budget, reported beside the agent on the same formats.
4. D-0NN Agent runner: loop, iteration/token/wall-time budgets, capped sealed-oracle submissions, a contamination
   check for documented formats, model provenance on every proposed claim.
5. D-0NN Spec-level mutation operators and the expected detection reason for each class; the clean-control
   false-rejection metric.
6. A draft Gate B acceptance test file docs/proposals/test_gate_b.py with a CLI contract header like Gate A's:
   ≥200 generated formats; scoreboard JSON with agent / baseline / agent+tools per tier, each score with
   numerator and denominator; every mutation class detected for its intended reason; false rejections reported.
7. Increments 1.1–1.5 for STATUS.md, each with decisions, done-when and the Gate B tests it turns green.
Use /decide's structure for each decision. Stop when the drafts are written; I review and ratify.
```

## P-20 — P2 kickoff (Gate C)

```
P2 kickoff, drafts only. Draft under docs/proposals/:
1. D-0NN Offline triage CLI: language and packaging (a single signed binary is the goal; state the trade-off of a
   Python zipapp vs Go), read-only scan, no network, outputs (full local report, separately redacted summary,
   salted hashes optional), resource limits.
2. D-0NN LeCroy .trc reconciliation: supported template versions, legal sample-file sources, reader lineage table
   (which open readers share upstream), contamination check, how disagreements become disputed claims.
3. A prospect intake kit: NDA checklist, the questions that decide scorecard G2, what files and reference evidence
   to request. Plain markdown under docs/sales/.
4. Increments 2.1–2.3 with done-when. Gate C is commercial; describe the evidence you will record, not a test.
```

## P-30 / P-40 — P3 and P4 kickoffs

```
P3 kickoff, drafts only: D-0NN workbench (three views: archive explorer, byte inspector with the field overlay from
Kaitai positions, claims and evidence; localhost only; reuses report.html components), D-0NN isolation (bubblewrap
or container with no network and read-only mounts for the worker), D-0NN tier 2 ops (delta, rle, segment, crc
variants, tlv) one decision per op with properties. Increments 3.1–3.3.
```
```
P4 kickoff, drafts only: D-0NN release engineering (reproducible builds, signed binaries and image, SBOM, image
digest as runtime identity), D-0NN public synthetic demo (what is live and what is replayed, labelled honestly),
a Gate D acceptance procedure for an outside verifier using only shipped instructions. Increments 4.1–4.3.
```

---

## P-80 — audit focus addenda (append to docs/prompts/audit.md)

- **0.1:** "Focus: canonical_json and the D-015 framing. Try lone surrogates in keys, nesting depth 64/65, integers
  beyond 2^53, header and payload caps at and beyond their limits. Check D-015's constants block against the code."
- **0.4:** "Focus: records and descriptors. Are float bits ever taken from a parsed float? Can a record contain a
  JSON float or null? Does coverage always sum to file size? Is the decode path free of clock, randomness, network?
  Do worker limits actually fire?"
- **0.6:** "Focus: package and verify. Can any payload or tag byte change without integrity failing? Is the signature
  over the right bytes? Does replay re-decode from packaged sources only? Does score read anything but package and
  truth?"
- **Gate A:** "Focus: the whole pipeline end to end on all three variants; decision conformance for D-015–D-029;
  every number in the closure records."

---

## P-90 — the guard fired

```
The protected-paths guard fired. Do not edit, restore or stage anything. Tell me:
1. the exact paths it listed;
2. every command and edit you made in this session since the previous successful check, in order;
3. which of them could have written to those paths, and how.
Then stop.
```

## P-91 — scope reset

```
Stop. List every file changed on this branch (`git diff --stat main...HEAD` and `git status --porcelain`) and mark
each as IN SCOPE or OUT OF SCOPE for increment <n> per docs/STATUS.md. Change nothing. I will decide what to keep.
```

## P-92 — resume after a break

```
Read docs/HANDOFF.md, the newest STATUS log entry and the closure records for this increment. Run
`python3 tools/verify.py --fast` and report its id and verdict. Then tell me in five lines what is done, what is
left in this increment, and what you will do first. Wait for my go-ahead.
```

## P-93 — a decision gap during an increment

```
/decide <topic>
```
Then, after you have ratified (or rejected) the proposal on main and merged main into the branch:
```
The decision on <topic> is now D-NNN in docs/DECISIONS.md. Resume the increment from where you stopped, starting
with the tests that D-NNN implies.
```
