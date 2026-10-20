# ReArchive — binding decisions

These decisions override `docs/PROJECT_SPEC.md` where they conflict. Each one names the spec section it changes.
To change a decision, add a new entry that supersedes it — never edit an accepted entry silently.

---

## D-001 Precedence
`DECISIONS.md` > `STATUS.md` (scope of the current increment) > `PROJECT_SPEC.md` (intent and principles).
The spec's principles (§3), evidence model (§7) and honest-reporting rules (§13) remain fully binding.

## D-002 Walking skeleton first (changes §19 Phase 0 and Phase 1)
Phase 0 is one thin vertical slice: generate a tier-0 file → ingest → decode → validate → claims → ledger → package → verify.
Contracts are extracted from that working slice, not designed in the abstract. No model, schema or interface is added without a consumer in the slice.

## D-003 Structure specs are Kaitai Struct (changes §8.3)
Headers, counts, offsets, magic constants and repeated records are described in a `.ksy` file and compiled by the official Kaitai Struct compiler with `--read-pos`, so every parsed field carries its start and end offset.
- Pin the compiler version. Commit the generated Python under `src/rearchive/generated/` with the source `.ksy` hash in a header comment; CI regenerates and diffs.
- Large sample arrays are declared as raw byte ranges (`size: ...`), never parsed element by element.
- The `.ksy` must remain valid Kaitai (openable in the Kaitai Web IDE). ReArchive extensions live in a sidecar file.

## D-004 Sample transforms are a closed op set (changes §8.3)
A sidecar `<format>.rearchive.yaml` pipes raw byte ranges through named, vectorised ops.
- Tier 0 ops: `view` (integer/float dtype + byte order), `check` (CRC-32 over a byte range → evidence, not data), `affine` (gain/offset → a derived view, never canonical).
- Later ops (`unpack_bits`, `delta_decode`, `deinterleave`, `segment`, `legacy_float`, `bcd`, `ebcdic`, `rle`) are added one at a time, each with a reference implementation, contract tests, Hypothesis properties and a resource bound.

## D-005 Canonical record and hashing (changes §10.1)
- Canonical record = raw integer codes + transform parameters + metadata. Physical values are derived views.
- Metadata is serialised as RFC 8785 (JCS) JSON. Arrays are hashed as: schema version, dtype string, shape, then little-endian packed bytes.
- Hash algorithm: SHA-256 everywhere (matches BagIt manifests).
- The canonical hash is independent of whichever Parquet/HDF5/CSV writer produces delivery files.

## D-006 Claim status is computed by policy (refines §7.2)
Statuses: `candidate`, `supported`, `disputed`, `contradicted`, `unresolved` (spec §7.2).
A versioned policy computes status from typed evidence. Humans act only through recorded events (`attest`, `dispute`, `approve`, `override_with_reason`) that the policy consumes. Replaying the ledger under the same policy reproduces every status.

Policy v1 — what can make a claim `supported`:

| Claim type | Sufficient evidence | Never sufficient alone |
| --- | --- | --- |
| structure | checksum validates; cross-file length equation holds; byte coverage complete | one file looking plausible |
| transform | hidden truth (synthetic); independent reader; cross-file invariants | a plot looking right |
| value | hidden truth; independent implementation; analytic fixture | a reader of the same lineage |
| semantic | physical anchor; vendor documentation; companion log. Attestation → `supported` with basis `attestation` only, always displayed as attested | the bytes; any model's opinion |
| completeness | count reconciliation against structure and manifest | a job exiting 0 |
| fidelity | replay of canonical record vs delivery files | matching container hashes |
| integrity | hashes, signature, ledger chain | — |

## D-007 Evidence lineage and independence (refines §7.3)
Every evidence item declares `inputs` (artifact IDs), `assumes` (claim IDs) and `lineage` (implementation and upstream-document IDs).
- Circularity: evidence whose `assumes` closure contains C cannot support C.
- Independence for C: lineages relevant to C do not intersect and neither item assumes the other's conclusion. Sharing an input file is allowed.
- Model-proposed claims start as `candidate` and record model, version and run ID.

## D-008 Ledger (refines §10.3)
SQLite (WAL) table, append-only, SHA-256 hash chain. Event types map to PREMIS event types where one exists.
Wall-clock timestamps are recorded in events for audit but are excluded from every canonical artifact hash.

## D-009 Resumability is architectural (changes §19 Phase 4 timing)
Tasks are idempotent and keyed by hash(inputs, versions, runtime identity). Resume = skip keys whose artifacts exist and verify. Outputs go to a temp path, are fsynced, then renamed. Built in Phase 0, stress-tested later.

## D-010 Evidence package (refines §14)
BagIt 1.0 (RFC 8493) bag, SHA-256 manifests, Ed25519 signature over the tag manifest from day one.
`rearchive verify` reports integrity, replay and semantic results as separate verdicts, never one pass/fail.

## D-011 Benchmark is a procedural format family (changes §8.1–8.2)
A generator samples formats by difficulty tier instead of eight fixed releases. Tier 0 = fixed header, int16, affine scaling, count field, CRC-32.
Semantic-anchor variants (`anchored`, `attested`, `no-anchor`) apply from tier 0 onward.
The spec's release discipline (§8.2) applies at generator-version level: freeze, regress on all earlier tiers, retire exposed seeds.

## D-012 Hidden truth is physically separated (refines §7.4)
Generator, hidden truth, oracle and scoring live in package `rearchive_bench`. `rearchive` must never import it (enforced by a test).
Truth values are computed from generator parameters, never by calling decoder or scaling functions from `rearchive`.

## D-013 Determinism environments (refines §10.1)
Declared environments: Linux x86-64, Linux arm64, macOS arm64, Python version pinned by `uv`. CI runs the acceptance suite on all three and compares canonical hashes.

## D-014 Market focus (refines §4.5, §18)
Lead hypothesis: regulated laboratory instrument data. Second: industrial and aerospace test-and-measurement. These inform which tier-3 encodings come first; they do not authorise an industry pack (G3 still applies).
