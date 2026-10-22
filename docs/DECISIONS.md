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

## D-015 Canonical array wire format (changes §10.1 and §10.2)

Ratifies **Option B** of `docs/proposals/D-015-canonical-array-wire-format.md` §0.1. Every clause is labelled **[D-005]** (existing binding rule), **[proposal §N]** (existing proposal rule), or **[owner]** (new owner decision introduced here). This entry states normative rules only; the implementation's conformance status is recorded in `docs/STATUS.md`.

### 1. Relationship to D-005 — what D-005 mandates, what it leaves open, and the scope of its metadata rule

**[owner]** This entry **refines** D-005 and supersedes no clause of it. D-005 fixes a logical component order and several encoding requirements; D-015 supplies the remaining framing detail.

**[D-005]** D-005 **mandates**, verbatim: "Arrays are hashed as: schema version, dtype string, shape, then little-endian packed bytes", "Hash algorithm: SHA-256 everywhere", "Metadata is serialised as RFC 8785 (JCS) JSON", and that the canonical hash is independent of whichever delivery-file writer is used. So the component sequence, the **little-endian packing of the payload**, the hash algorithm, and **JCS for metadata** are already binding and are not D-015's to choose.

**[owner] Scope of D-005's metadata rule, as it applies to the array header.** D-005's first bullet defines the canonical record as "raw integer codes + transform parameters + metadata", making `metadata` a record-level component alongside the other two. Its second bullet separately enumerates `dtype string` and `shape` as components of the **array hash**. This entry establishes:

- The `{"dtype": ..., "shape": [...]}` object of §4 is a **dedicated wire-framing structure**, not "metadata" within the meaning of D-005's first bullet. It describes the array's own encoding, is carried inside the hashed region defined by §2, and holds no record-level descriptive content — per §5 the header carries no values.
- D-005 names `dtype string` and `shape` but **does not state how they are serialised**. D-015 therefore **selects RFC 8785 (JCS) JSON for this structural header** as a new choice under this entry.
- That selection **neither weakens nor supersedes** D-005's general metadata rule. Record-level metadata remains governed by D-005 and remains JCS-serialised independently of this entry.
- Consequence, stated so it cannot become a silent coupling: ReArchive has **two distinct JCS uses** — D-005's record-level metadata serialisation, and D-015 §4's structural array header. They agree today but are separate selections made for separate reasons. A future decision changing one does **not** automatically change the other, and any decision intending to change both must say so explicitly.

**[owner]** With that scope settled, D-005 **leaves unspecified**, and D-015 therefore supplies:

1. the octet width and endianness of the `schema_version` field itself;
2. whether length prefixes exist at all, and if so their width and endianness;
3. the serialisation of the `dtype string` and `shape` components D-005 names — resolved above by selecting JCS for the dedicated structural header;
4. the element traversal order for a multi-dimensional array, which "packed bytes" does not determine;
5. padding and alignment, if any;
6. the textual rendering of a digest.

Option B emits schema version, then dtype, then shape, then the little-endian payload — D-005's sequence and D-005's payload encoding, unchanged — and adds only items 1–6 above.

### 2. Framing

**[proposal §0.1 Option B]**

```
canonical_bytes = u16le(schema_version)
                + u64le(len(header)) + header
                + u64le(len(payload)) + payload
header          = JCS({"dtype": <name>, "shape": [<dims>]})
```

`u16le` is exactly 2 octets and `u64le` exactly 8 octets, both unsigned, least-significant-octet-first. No padding, alignment or separator appears anywhere in the framing. Both length fields count octets. `len(header)` covers the header alone and excludes the version field and both length fields.

### 3. Version field

**[proposal §0.1 Option B]** `schema_version` is **1**, encoded `u16le` as the octets `0x01 0x00`. Version 1 is the only value this entry defines.

**[owner]** The field exists so that any future framing yields different canonical bytes, and therefore a different digest, for the same array. Changing the framing, the dtype allowlist, the header members, the traversal order or the payload encoding requires a superseding decision and a new version number. Per §12 nothing is obliged to read the field back, and no ReArchive component may branch on a version recovered from a byte string.

### 4. Header, and the public header accessor

**[proposal §1]** The header is the RFC 8785 (JCS) serialisation of an object with exactly two members, `dtype` and `shape`. JCS sorts keys, so `dtype` precedes `shape`. UTF-8, no BOM. `schema_version` is **not** a header member. No member may be added without a new `schema_version`.

**[owner]** `canonical_array_header()` is **retained** as a public accessor. It returns **only the JCS header octets** defined above, excluding the `u16le` version field, both `u64le` length fields and the payload. Its return value is therefore **not** a canonical byte string, MUST NOT be hashed as one, and MUST NOT be used as a task key or artifact identity (see §14). Callers needing canonical bytes use the full-array entry point.

### 5. dtype allowlist and `element_size`

**[proposal §2]** Exactly these ten names. Names are lowercase and carry no byte-order marker, because §9 fixes the canonical payload byte order for every dtype; `<i2`, `>i2`, `INT16` and every other spelling are invalid.

| Name | `element_size` (octets) | Representation | Minimum | Maximum |
| --- | --- | --- | --- | --- |
| `int8` | 1 | two's complement | −128 | 127 |
| `int16` | 2 | two's complement | −32768 | 32767 |
| `int32` | 4 | two's complement | −2147483648 | 2147483647 |
| `int64` | 8 | two's complement | −9223372036854775808 | 9223372036854775807 |
| `uint8` | 1 | unsigned | 0 | 255 |
| `uint16` | 2 | unsigned | 0 | 65535 |
| `uint32` | 4 | unsigned | 0 | 4294967295 |
| `uint64` | 8 | unsigned | 0 | 18446744073709551615 |
| `float32` | 4 | IEEE 754 binary32 | §10 | §10 |
| `float64` | 8 | IEEE 754 binary64 | §10 | §10 |

**[owner]** `element_size` is the **fixed octet width of the selected dtype**, taken from the column above. It is a property of the dtype alone and is **independent of shape, rank and element count**.

**[proposal §2]** Integer payload values are not bounded by the safe-integer domain: `uint64` carries values to 2⁶⁴−1, because the payload holds octets rather than JSON numbers. Only the header is JCS, and the header carries no values.

**[proposal §2]** Admitting a dtype changes the wire format and requires a superseding decision and a `schema_version` bump.

### 6. Float dtypes are a serialisation primitive only — resolution of Q-05

**[proposal §2, §0.2]** A float dtype in this allowlist is a serialisation primitive only. It does not authorise a canonical record to contain physical values; D-005 bullet 1 and CLAUDE.md invariant 6 continue to govern record content.

**[D-005]** A complete canonical record retains **all three** components D-005 requires: **raw integer sample codes**, **transform parameters**, and **record-level metadata**. This entry does not alter that composition, does not replace it, and does not make any of the three optional.

**[owner]** A **canonical measurement record** is a canonical record whose subject is sampled measurement data recovered from a source file. Its **measurement-data components** — which are *not* an exhaustive definition of the complete record — are:

- **(a) raw sample codes** — the **integer sample values decoded from the immutable source bytes according to the source format**, retaining their source numeric meaning, with no scaling, offset, gain, calibration, unit or epoch transformation applied.
- **(b) transform parameters** — the values needed to derive physical quantities from (a), such as gain, offset, sample interval and vendor unit codes, never merged into (a).

and the record MUST NOT contain, in any component:

- **(c) derived physical values** — any value obtained by applying (b) to (a). Derived physical values MUST NOT be stored as canonical measurement data; **[D-004]** they remain derived views, never canonical.

**[D-005]** **The metadata component remains mandatory** and is **serialised independently under D-005's record-level metadata JCS rule**, per the scope rule in §1. It is not a measurement-data component.

**[owner]** **Two separate JCS selections, and what each governs.** D-015 §4's JCS rule governs the **structural header of an individual canonical array**. It does **not** govern the serialisation of the complete record, and it does not govern the record-level metadata component. D-005's rule governs record-level metadata. The two are **separate selections that happen to use the same serialisation standard**: changing one does **not** automatically change the other.

**[owner]** **Raw sample codes versus canonical payload encoding — separate concerns.** (a) concerns *which integers the source encodes*, preserved without physical transformation. **[D-005]** §9's payload encoding concerns *how those integers are re-encoded for hashing*: **all** canonical array payloads use the specified little-endian encoding, **regardless of the source's byte order**. A big-endian source and a little-endian source holding equal sample values therefore produce the **same** canonical payload. The source's own byte order is consequently not recoverable from canonical bytes and must be carried as a transform parameter, for which no schema yet exists. See **U-6**, which carries a decision gate: **no decoder that depends on source byte order may be accepted until U-6 is decided.**

**[owner]** **Float dtypes under `schema_version` 1.** A float dtype MAY carry **(b)** transform parameters. A float dtype MUST NOT carry **(a)** raw measurement codes, and MUST NOT carry **(c)** derived physical values.

**[owner]** **Natively floating-point measurement sources are out of scope for `schema_version` 1.** Where a source encodes its samples natively as IEEE 754 binary32 or binary64, this entry provides no canonical representation for them, and such a source MUST NOT be ingested into a canonical measurement record. D-005 bullet 1 and invariant 6 say "raw **integer** codes" verbatim, and permitting a float array to carry (a) would redefine that quoted binding term; this entry does not do so. Tier 0 is unaffected, its samples being `s2`. This is the selected policy — see **OD-1**, resolved for version 1.

**[owner]** **Array bytes do not encode semantic measurement roles.** The framing of §2 is identical whether a float array carries transform parameters or raw sample codes; no role is recorded in `canonical_bytes`, consistently with §12. Conformance with this section therefore **cannot be established from canonical bytes** and MUST be established through the record/schema layer.

**[owner]** **Measurement-role rule.** Every canonical **array** belonging to the **measurement-data components** of a canonical measurement record is either raw sample codes or transform parameters, and none may be derived physical values. The rule is exhaustive over those arrays and applies to nothing else; in particular it does **not** classify the record-level metadata component as a measurement array. The **field-level schema** recording the role — its name, location and encoding — is **deferred to U-7** in increment 0.4. The distinction is binding from ratification; only its field representation is open.

### 7. Shape, rank, and element count

**[proposal §3]** `shape` is a JSON array of dimensions. Each dimension MUST be a JSON integer — a JSON boolean and a fractional value are both invalid — and MUST satisfy `0 <= dimension <= 2**53 - 1`, the upper bound being the **maximum safe integer under the ECMAScript Number model**.

**[owner]** Rank, the number of dimensions, MUST satisfy `0 <= rank <= 64`. This is a **new ReArchive constraint introduced by this entry**: it is not inherited from D-005 and was not present in the proposal.

**[owner]** `element_count` is defined as:

- rank 0 (`shape: []`) — the product is empty and `element_count` is **1**: a scalar carries exactly one element. **[proposal §3]**
- **any** dimension equal to `0` — `element_count` is **0**, regardless of every other dimension. **[owner]**
- otherwise — the product of the dimensions. **[proposal §3]**

**[owner]** An implementation using fixed-width overflow-checked arithmetic MUST test for a zero dimension **before** multiplying. Multiplying left to right without that test spuriously reports overflow for legal empty arrays: for `[2**53-1, 2**53-1, 0]` the true `element_count` is 0, but the first two factors already exceed 2⁶⁴−1. Arbitrary-precision arithmetic satisfies this inherently.

### 8. Payload representability, constraint independence, and the derived header bounds

**[owner]** `element_count × element_size` MUST be `<= 2**64 - 1`, so that `len(payload)` is representable in the `u64le` field §2 mandates. The product MUST be computed with arbitrary-precision or overflow-checked arithmetic, subject to §7's zero-dimension rule, and tested **before any allocation, packing or hashing**. An implementation MUST NOT rely on wraparound, and MUST NOT materialise the supplied values before the length checks: a declared length that cannot match the shape is to be rejected without allocating for it. This is a **new ReArchive constraint introduced by this entry**.

**[owner]** Three constraints apply **independently**, and a shape MUST satisfy all three. None implies another:

| Constraint | Bound |
| --- | --- |
| Rank | `rank <= 64` |
| Per-dimension | `0 <= dimension <= 2**53 - 1` |
| Payload representability | `element_count × element_size <= 2**64 - 1` |

Illustrations: rank 64 with every dimension 2 satisfies rank and per-dimension and **violates** representability; rank 1 with a single dimension of 2⁵³−1 and dtype `float64` satisfies all three; rank 65 with every dimension 1 satisfies per-dimension and representability and **violates** rank.

**[owner]** **There is no fixed header-length limit.** Three distinct maxima follow from §4, §5 and §7. A test MUST compute each from those bounds and pin all three figures:

| Figure | Value | Meaning |
| --- | --- | --- |
| Shape-only upper bound | **1117 octets** | rank 64, every dimension 2⁵³−1, 7-character dtype name. **No valid array attains it**: `element_count` is (2⁵³−1)⁶⁴, violating representability by an enormous margin. A bound on the header's grammar alone, not a reachable header. |
| Maximum header of a valid **empty** array | **1102 octets** | rank 64, one dimension `0` and 63 dimensions of 2⁵³−1, dtype `float32` or `float64`. `element_count` is 0, so representability is trivially satisfied and the array is legal. This is the maximum over **all** valid arrays. |
| Maximum header of a valid **non-empty** array | **175 octets** | dtype `float64`, rank 64, `shape = [1000000000000000, 1000] + [1] * 62`. `element_count` is 10¹⁸, payload length 8 × 10¹⁸ ≤ 2⁶⁴−1, header `30 + 82 + 63 = 175`. |

Derivation of the valid **empty**-array maximum:

```
max_empty_header = len('{"dtype":"') + max_dtype_name_len + len('","shape":[')
                 + digits(0) + (max_rank - 1) * digits(2**53 - 1)
                 + (max_rank - 1) + len(']}')
                 = 10 + 7 + 11 + 1 + 63*16 + 63 + 2
                 = 1102
```

**Digit-budget derivation of the non-empty maximum.** Write the header length as `fixed + D + (rank - 1)`, where `fixed = 10 + len(dtype_name) + 11 + 2` and `D` is the total digit count across the dimensions. With `k_i = floor(log10(d_i))`, each dimension contributes `k_i + 1` digits, so `D = rank + Σ k_i`, while `element_count >= 10**(Σ k_i)`. Representability therefore caps the digit budget at `Σ k_i <= floor(log10((2**64 - 1) / element_size))`. Maximising over the allowlist:

- `element_size` 8, 7-character name (`float64`): `Σ k_i <= 18`, `D <= 82`, bound `30 + 82 + 63 = 175`.
- `element_size` 4, 7-character name (`float32`): `Σ k_i <= 18`, same bound of **175**.
- `element_size` 1, 4-character name (`int8`): `Σ k_i <= 19` so `D <= 83`, but `fixed` is 27, giving 173.
- Every 5- and 6-character name yields 173 or 174.

The maximum is **175**, attained by `float32` and `float64`; the witness above realises it, so the bound is tight. The empty-array maximum of 1102 is far larger because a zero dimension removes the representability cap while the remaining dimensions stay maximal.

**[owner]** **Why a 1024-octet cap is not acceptable.** It would reject legal arrays. The smallest valid counter-example is rank 60: `shape = [0] + [2**53-1] * 59`, whose `element_count` is 0, which satisfies all three constraints, and whose header is **1034 octets** — `10 + 7 + 11 + 1 + 59*16 + 59 + 2 = 1034`. Rank 60 is the first rank at which a valid array's header exceeds 1024; at rank 59 the maximum valid header is **1017** octets. A 1024-octet cap would make a conforming empty array unrepresentable, which is why this entry derives its bounds rather than fixing one.

The test must fail if the dtype allowlist, the rank bound or the per-dimension bound changes without all three figures being revisited.

### 9. Payload

**[D-005]** Each element is packed **little-endian**. This is D-005's existing requirement, not a D-015 choice, and it applies to every dtype in §5.

**[proposal §4]** Elements are packed in **C order** — row-major, last index varying fastest — with no padding between elements. The traversal order is supplied by this entry, D-005 having left it open (§1 item 4). `len(payload)` MUST equal `element_count × element_size`, checked before hashing.

**[proposal §3]** **Scalar** is rank 0, written `shape: []`, carrying exactly one element. **Empty array** is any shape containing a `0`: element count 0, payload length 0, with the full shape still recorded in the header, so `[0]` and `[0, 3]` are distinct canonical byte strings.

### 10. Floating point

**[proposal §5]**

- **Signed zero is preserved.** `-0.0` and `+0.0` have distinct bit patterns and both are valid; the payload carries whichever was supplied, and implementations MUST NOT normalise it. This differs deliberately from the JCS metadata path, where RFC 8785 has no negative zero and serialises `-0.0` as `0`.
- **Subnormals are valid** and are packed bit-exactly.
- **NaN and both infinities are rejected**, not normalised. NaN has many bit patterns with no canonical choice among them, so hashing an arbitrary one would make the digest depend on which operation produced it, defeating D-013. A format that genuinely stores either requires a superseding decision fixing its encoding.

**[owner]** **Exact representability is judged against the selected dtype, and only that dtype:**

- a value destined for `float32` MUST be exactly representable in IEEE 754 **binary32**;
- a value destined for `float64` MUST be exactly representable in IEEE 754 **binary64**.

A value offered for `float64` is **not** required to be representable in binary32. An integer is accepted only where widening to the selected dtype is lossless, including the case of an integer too large to convert to that dtype at all. A value not exactly representable in the selected dtype MUST be rejected rather than rounded, because rounding here would be undeclared data loss.

### 11. Invalid-input contract

**[proposal §7]** Every condition below MUST raise a typed canonicalisation error, a subclass of a single `CanonicalizationError` which is itself a `ValueError`. Nothing is rounded, truncated, clamped or normalised silently, and no condition may be signalled through a return value. ReArchive code catches that base class, never a third-party package's hierarchy, so the dependency stays replaceable.

| Condition | Error |
| --- | --- |
| dtype not in §5, including wrong case or a byte-order marker | `UnsupportedDtypeError` |
| dimension not a JSON integer, or a boolean, or negative, or > 2⁵³−1 | `InvalidShapeError` |
| `rank > 64` | `InvalidShapeError` |
| `element_count × element_size > 2**64 - 1` | `PayloadLengthError` |
| element count disagrees with the number of values supplied | `PayloadLengthError` |
| integer outside its dtype's range in §5 | `ValueRangeError` |
| value not exactly representable in the **selected** float dtype, including overflow and an integer too large to convert | `ValueRangeError` |
| NaN or an infinity for a float dtype | `NonFiniteValueError` |
| a bool offered as a numeric value, or a float for an integer dtype | `UnsupportedTypeError` |

**[owner]** The guarantee is **exhaustive**: no built-in exception may escape in place of one of these. In particular a lazy but legitimately-typed sequence must not be materialised before the length checks, and deeply nested or self-referential metadata must not surface a `RecursionError`.

### 12. Canonical bytes are a hashing input only

**[owner]** Canonical array bytes exist to be hashed. No component is obliged to parse them; no decoder behaviour is implied; and no scientific or measurement semantics are implied by any dtype, shape or value in them. This format is not a storage or interchange format. Storage and delivery formats — Parquet, HDF5, CSV and others — are defined separately, and **[D-005]** the requirement that the canonical hash be independent of whichever writer produces delivery files is unaffected.

### 13. Hash definition and digest representation

**[D-005]** The digest is **SHA-256**, matching the BagIt manifests D-010 requires.

**[proposal §6]** It is computed over **exactly** `canonical_bytes` as defined in §2 — the version field and both length fields included, and nothing else. Never over `repr`, pickle, or container-file bytes (**[D-005]** invariant 6).

**[owner]** Where rendered as text, a digest is exactly **64 lowercase hexadecimal characters**, with no prefix, separator or algorithm label. D-005 leaves the textual rendering open (§1 item 6).

### 14. Version sensitivity of task keys and artifact identities

**[owner]** **Scope: one canonical array.** This section governs identity derived from a single canonical array. It does **not** define how all arrays and the record-level metadata component compose into one per-file identity.

**[owner]** Every task key and artifact identity derived from a canonical array MUST incorporate the **complete canonical SHA-256 digest** of §13 as the **input identity** for that array. "Complete" means the digest is computed over the entire prescribed `canonical_bytes` of §2 — the **schema-version field, the header-length field, the header, the payload-length field and the payload** — and nothing less. Because the version field lies inside that region, the digest is inherently sensitive to `schema_version`.

**[owner]** A digest of **`canonical_array_header()` alone MUST NOT be substituted** for the complete array digest, and MUST NOT be treated as an equivalent input identity. Per §4 that accessor returns only the JCS header octets, carries no version field, and is not a canonical byte string. The same prohibition applies to a digest over any other subset of `canonical_bytes`.

**[owner]** This digest occupies the **inputs** position of a task key. Decoder identity and version, specification hash, runtime identity and dependency-lock identity remain **separate identity components** and are not folded into the input identity.

**[owner]** This section refines **D-009**'s `hash(inputs, versions, runtime identity)` by fixing what occupies the `inputs` position for a canonical array. It does **not** supersede D-009 and does not alter its resume semantics, its temp-write-then-rename rule, or its Phase 0 timing. D-009's text is unchanged: per the preamble of this file, a decision is changed by adding a new entry, never by editing an accepted one in place.

**[owner]** **Per-file record composition remains deferred to U-7.** Until that decision is made, **no per-file identity may be claimed to satisfy this section merely because each constituent array individually satisfies it.**

The consequence this closes: without the complete digest, a `schema_version` bump would leave existing task keys valid, so D-009 resume would skip recomputation and report artifacts built under a retired framing as current.

### 15. The normative artifact, and the status of the array vectors

**[proposal §8]** The normative definition of this format is **this entry**. `src/rearchive/core/canonical.py` is never normative.

**[owner]** **Vector history and current status.** An earlier set of 15 array vectors was produced under Option A. Those vectors were **staged but never committed**, and they have since been **replaced** in the working tree by 15 vectors derived under the Option B framing of §2. The replacement set was derived by a routine importing neither `rearchive` nor `rfc8785`, with the JCS header written by hand.

**[owner]** The current Option B vectors are **provisional** and are **not normative**. They become a normative restatement of this entry only once **all** of the following hold: this decision is recorded in `docs/DECISIONS.md`; the vectors have been reviewed; and the owner has accepted them. Until then they constrain the implementation without restating a decision, and no golden file may be written under `tests/acceptance/golden/`.

**[owner]** Any future regeneration MUST likewise be performed by a derivation importing neither `rearchive` nor `rfc8785`, so the vectors never become a recording of the implementation.

**[proposal §8]** A re-implementation written from this entry is a second implementation but **not automatically independent evidence under D-007**: the proposal this entry ratifies was itself reconstructed from the first implementation, so the lineages intersect. The hex vectors, derived without importing `rearchive` or `rfc8785`, are the independent artifact. D-015 prose MUST NOT be cited as independence in increments 0.4 or 0.5 without a separate review.

**[proposal §8]** `canonical_bytes` SHOULD be reproducible from this entry alone, with the `rfc8785` library a convenience rather than the definition. **Known limitation, recorded rather than asserted away:** the header is in fact produced by `rfc8785` via the implementation's JCS call, so independence from that library's version is a design intent, not an enforced property. The exposure is narrow — the header contains only ASCII keys and small non-negative integers, where JCS output is unambiguous — but the requirement is not mechanically guaranteed.

### 16. Standing rule

**[owner]** **No hash-affecting format becomes normative through golden vectors or golden files until its decision has been recorded in this file.** Increment 0.1 produced vectors under an unratified framing and then changed the framing; this rule exists so that does not recur.

### 17. Review checkpoint

**[owner]** Rank 64, the per-dimension bound of 2⁵³−1 and the payload-representability bound are **binding, and remain binding unless and until an explicitly approved superseding decision altering them is recorded in `docs/DECISIONS.md`.**

Before the Gate A golden file is created in increment 0.7, a scheduled review reconsiders whether rank 64 is the right headroom, given that any rank-64 shape with all dimensions ≥ 2 violates representability and the valid-array header maximum is driven entirely by empty arrays.

**The review is an opportunity to consider a future change. It does not automatically suspend, reopen, weaken or modify the current rule, and confers no authority to alter it.** Reaching the checkpoint without a recorded superseding decision leaves all three limits in force, unchanged.

## D-016 Source path representation (changes §6 Stage 2)
Resolves audit F-01 at the root: legacy archives routinely contain filenames that are not valid UTF-8.

1. A source entry's identity is its raw relative path bytes plus the SHA-256 of its content.
2. Canonical JSON carries the path as `relpath_b64`: base64url (RFC 4648 §5, no padding) of the raw bytes, components
   joined by `/` (0x2F), plus `path_platform`: `posix` (bytes as returned by the OS) or `windows` (UTF-16LE code
   units, unpaired surrogates preserved). `windows` is defined here but not implemented until Windows is a declared
   environment; its constant is added then by a superseding decision.
3. `relpath_display` is a human rendering: decode as UTF-8; render each byte of an invalid sequence, each C0 control
   byte (0x00–0x1F) and 0x7F as `\xNN` (lowercase hex); render `\` as `\\`. It is never hashed and never an identifier.
   The Gate A report field `source_relpath` is `relpath_display`.
4. No Unicode normalisation (NFC/NFD) is ever applied. Two names that differ only in normalisation are two entries.
5. Ingest walks in ascending order of raw relpath bytes. Symlinks are never followed (`lstat`); symlinks and special
   files are recorded — in the manifest and in the report — with `kind` (`symlink`, `fifo`, `socket`, `device`,
   `other`) and `sha256: null` (symlinks also carry `target_b64`). They are never decoded; their outcome is `failed`
   with diagnostic `not_a_regular_file` at every stage (this takes precedence over D-026 §4). Regular files have
   `kind: "file"`. Empty files are ordinary entries.
6. Duplicate content is stored once; every path stays in the manifest; later paths carry `duplicate_of` = the first
   path in walk order (as `relpath_b64`). Re-ingesting an entry with the same (`relpath_b64`, `sha256`) is a no-op
   logged as `task_reused` (D-021, D-022); a changed file at a known path is a new entry version, never an overwrite.
7. `canonical_json` rejects, with a typed `CanonicalizationError` subclass, any string (key or value) that is not a
   sequence of Unicode scalar values, and any nesting deeper than 64. No untyped exception may escape it.
8. Pure encoding and display functions live in `rearchive.core.paths`; the directory walk and file reads live in
   `rearchive.adapters`.

```decision-constants due=0.2
rearchive.core.canonical.JSON_MAX_DEPTH = 64
rearchive.core.paths.RELPATH_ENCODING = "base64url-nopad"
rearchive.core.paths.PATH_PLATFORMS = ("posix",)
```

## D-017 Per-file canonical record (changes §10.1)
Resolves Q-04 / U-7: the gate needs one `canonical_sha256` per file; D-015 defines one array's bytes and stops.

1. Every source file whose structural decode completes yields exactly one canonical record: a JSON object serialised
   with `canonical_json` (RFC 8785). `canonical_sha256` = SHA-256 of those bytes, rendered as 64 lowercase hex characters.
2. Record schema 1:
   ```json
   {
     "record_schema": 1,
     "fields": { "<field path>": <typed raw value> },
     "arrays": { "<array name>": { "sha256": "<D-015 digest>", "dtype": "<D-015 dtype>", "shape": [<int>, ...],
                                   "interpretation": "<see D-019>" } }
   }
   ```
3. Field paths are slash-separated Kaitai attribute paths from the top-level type (`/gain`, `/header/gain`); array
   names are the sidecar's output names (`samples`). Typed raw values are defined by D-019 and D-020.
4. Array bytes are D-015 canonical array bytes, stored in the content-addressed store under their SHA-256. The record
   references them; it never inlines them.
5. The record contains **content only**. Source identity, spec identity, engine and library versions, platform,
   timestamps, coverage, diagnostics and claims are excluded; they live in the decode descriptor (D-018), artifact
   keys (D-021) and the ledger (D-022). Consequence, intended: identical content decoded from different files,
   encodings or spec revisions with the same field names has the same `canonical_sha256`.
6. If structural decoding does not complete (truncation, validation failure, resource limit), no record exists for that
   file: `canonical_sha256` is `null` in the report and partial fields appear only as diagnostics. Checksum results do
   not block a record; they are evidence (D-024).
7. Records never contain JSON `null` or JSON floats (see D-019, D-020); the record builder rejects both.

```decision-constants due=0.4
rearchive.records.RECORD_SCHEMA = 1
rearchive.records.DIGEST_HEX_LENGTH = 64
```

## D-018 Decode descriptor and encoding provenance (changes §10.2)
Resolves Q-09 / U-6 (source byte order has nowhere to live) and Q-11 / U-5 (Kaitai-to-canonical dtype mapping).

1. Every completed decode also yields a decode descriptor, serialised with `canonical_json`:
   ```json
   {
     "descriptor_schema": 1,
     "source_sha256": "...",
     "record_sha256": "...",
     "spec": { "id": "tier0", "ksy_sha256": "...", "sidecar_sha256": "..." },
     "engine": { "rearchive": "...", "ksc": "0.11.0", "kaitaistruct": "0.11" },
     "fields": { "/gain": { "kaitai_type": "f8", "source_byte_order": "le", "offset": 20, "length": 8 } },
     "arrays": { "samples": { "from": "/samples_raw", "kaitai_type": "bytes", "offset": 48, "length": 2048,
                              "ops": [ { "op": "view", "dtype": "int16", "byte_order": "le" } ] } },
     "coverage": { "size": 2096, "explained": 2088, "padding": 8, "unexplained": 0 },
     "diagnostics": [ { "code": "...", "offset": 0, "detail": "..." } ]
   }
   ```
   The descriptor names no source path: duplicates share one descriptor, and paths are never hashed (D-016 §3).
   Reports add the path when they list diagnostics.
2. Source byte order, source offsets, widths and the op pipeline live here and nowhere in the record. Canonical array
   payloads are always little-endian (D-015), so equal values from big- and little-endian sources give equal records by
   design. Byte order of an array is the `byte_order` of its `view` op. Byte-order claims (type `transform`) cite the
   descriptor. A decoder that depends on source byte order is acceptable because its dependence is recorded here.
3. Kaitai type → canonical dtype:

   | Kaitai | canonical dtype | notes |
   | --- | --- | --- |
   | `u1` `u2` `u4` `u8` | `uint8` `uint16` `uint32` `uint64` | `le`/`be` suffix or `meta/endian` → `source_byte_order` |
   | `s1` `s2` `s4` `s8` | `int8` `int16` `int32` `int64` | as above |
   | `f4` `f8` | `uint32` `uint64` with interpretation `ieee754_binary32` / `ieee754_binary64` | D-019 |
   | `bN` (bit-sized) | smallest of `uint8/16/32/64` that holds N | descriptor records `bit_width: N` |
   | `str`, `strz`, `size:` byte ranges | bytes (D-020) | unless a sidecar op transforms the range |

4. D-015's dtype allowlist is importable as `rearchive.core.canonical.ALLOWED_DTYPES` (tuple or frozenset); every
   value in the table above must be in it (contract test).
5. `coverage`: `explained` = bytes inside parsed fields not declared padding; `padding` = bytes in fields the sidecar
   declares padding **and** whose constant value the spec validates; `unexplained` = everything else.
   `explained + padding + unexplained = size`.

```decision-constants due=0.4
rearchive.decode.dtypes.KAITAI_TO_CANONICAL = {"u1": "uint8", "u2": "uint16", "u4": "uint32", "u8": "uint64", "s1": "int8", "s2": "int16", "s4": "int32", "s8": "int64", "f4": "uint32", "f8": "uint64"}
rearchive.decode.descriptor.DESCRIPTOR_SCHEMA = 1
```

## D-019 Floating-point and legacy-numeric raw data (changes §10.1)
Resolves Q-05 (float dtypes had no enforcement point) and Q-08 (a NaN gain raised instead of producing a diagnostic).
Keeps CLAUDE.md invariant 6 and D-005 ("raw integer codes") literally true.

1. Floating-point source data is canonicalised as its bit pattern, never as a number:
   - scalar fields: `{"dtype": "uint64", "interpretation": "ieee754_binary64", "bits": "<16 lowercase hex>"}`
     (`uint32` / 8 hex digits for binary32); `bits` is the unsigned integer value of the pattern, most significant first;
   - arrays: a D-015 array of dtype `uint32` / `uint64` with `"interpretation": "ieee754_binary32" | "ieee754_binary64"`;
   - integer arrays carry `"interpretation": "int"` (signed dtypes) or `"uint"` (unsigned dtypes).
2. Bits are taken from the source bytes at the field's recorded offset (D-018), never from a parsed Python float.
   NaN payloads, signalling NaNs, infinities and −0.0 are therefore preserved exactly, and canonicalisation never raises
   on them.
3. The record builder is the enforcement point: it rejects float canonical dtypes and Python `float` values anywhere in
   a record. D-015's dtype allowlist is unchanged; this decision restricts what records may use.
4. Non-finite or zero `gain`, or non-finite `offset`, is not an error: the `affine` derived view is unavailable for that
   file, the decoder emits diagnostic `non_finite_scaling`, and claims that need physical values become `unresolved`.
5. Legacy numeric formats will follow the same rule (bit pattern in the next wider unsigned dtype, `bit_width` in the
   descriptor, conversion to IEEE values only as a derived view). Their interpretation names (for example `vax_f`,
   `ibm_hfp32`, `mbf32`, `mil1750a48`, `bcd`) are added to the constant by a superseding decision when tier 3 needs them,
   not before (D-002: no vocabulary without a consumer).
6. This lifts STATUS OD-1's exclusion of natively floating-point sources: they are representable under D-015
   `schema_version` 1 with integer dtypes.

```decision-constants due=0.4
rearchive.records.INTERPRETATIONS = ("int", "uint", "ieee754_binary32", "ieee754_binary64")
```

## D-020 Integers, absent values, time and text in records (changes §10.1; refines §13)
Resolves Q-07 (integers above 2^53) and Q-12 / U-8.

1. Integer field values are `{"dtype": "<canonical int dtype>", "int": "<decimal string>"}` — always a string, so no
   value depends on JSON number precision. No leading zeros; `-0` is never produced.
2. Byte strings are `{"bytes": "<base64url, no padding>"}`.
3. A field the spec declares but which is legitimately not present (a Kaitai `if:` evaluating false) is
   `{"absent": "not_present"}`. JSON `null` never appears in records. Truncation is not "absent": it prevents the record
   (D-017 §6).
4. Time: records hold raw time fields as raw integers or bit patterns. Epoch, tick duration, time unit and timezone are
   `semantic` claims (`time_origin`, `tick_duration`, `time_unit`, `timezone`). Absolute timestamps exist only as derived
   views, only when those claims are `supported`. Wall-clock time never enters a record.
5. Text: records hold bytes. Character encoding is a `semantic` claim (`text_encoding`); decoded text is a derived view,
   never hashed, and is displayed with D-016 escaping for undecodable bytes.

## D-021 Artifact keys and runtime identity (changes §10.2)
Refines D-009's `hash(inputs, versions, runtime identity)` for every task kind; D-015 §14 already fixes what occupies
`inputs` for a canonical array. D-009's text and resume semantics are unchanged.

1. Every artifact key is the SHA-256 of `canonical_json` of a key object:
   - stored object: the content's SHA-256 (no key object);
   - ingest: `{"kind":"ingest","relpath_b64":<b64>,"sha256":<sha>}`;
   - decode: `{"kind":"decode","source":<sha>,"ksy":<sha>,"sidecar":<sha>,"config":<sha>,"engine":<version>,"runtime":<runtime_id>}`;
   - validate: `{"kind":"validate","decode":<key>,"policy":<policy version>,"evidence":[<sorted evidence document sha256>],"oracle":<oracle id or "none">,"validator":<version>,"runtime":<runtime_id>}`;
   - package: `{"kind":"package","manifest":<sha of manifest-sha256.txt>}`. A package contains the ledger, so this is
     the only key that covers `recorded_at` timestamps (D-022 §2).
   `config` is the SHA-256 of `canonical_json` of the decode options object; in P0 the object is `{}`.
2. `runtime_id` = SHA-256 of `canonical_json` of
   `{"implementation":"cpython","python":"3.12.15","platform":"<sys.platform>-<machine>","uv_lock":<sha>,"ksc":"0.11.0"}`.
   Platform is included on purpose: artifacts are never reused across platforms. Cross-platform equality of
   `canonical_sha256` is established by the gate's golden test, never assumed by the cache.
3. Resume: a task whose key has stored outputs that re-hash to their recorded digests is skipped and logged as reused;
   otherwise it is recomputed. Writes go temp file → fsync file → rename → fsync directory. An existing object key is
   never overwritten; a differing object under an existing key is an integrity failure.
4. Key derivation and `runtime_id` are pure functions in `rearchive.core.keys`; the store's file operations live in
   `rearchive.adapters`.

```decision-constants due=0.2
rearchive.core.keys.HASH_ALGORITHM = "sha256"
```

## D-022 Ledger events (changes §10.3)
Refines D-008.

1. SQLite table `events(seq INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL, body TEXT NOT NULL)`.
   `body` = `canonical_json(event body)`. `event_hash` = SHA-256 of `bytes.fromhex(prev_hash) || body_bytes`.
   Genesis `prev_hash` = 64 × `0`.
2. Event body: `{"type", "premis_type" (only when a mapping exists), "subject", "payload", "actor": {"kind": "engine" |
   "human" | "model", "id"}, "recorded_at"}`. `recorded_at` is RFC 3339 UTC with milliseconds; it is inside the hash
   chain (audit) and excluded from every ingest, decode and validate key, every record and every projection.
3. Event types v1 → PREMIS (`id.loc.gov/vocabulary/preservation/eventType`):
   `project_created` → creation · `file_ingested` → ingestion · `fixity_checked` → fixity check ·
   `format_identified` → format identification · `task_reused` → none · `file_decoded` → none ·
   `decode_failed` → none ·
   `evidence_recorded` → none · `claim_proposed` → none · `claims_evaluated` → validation ·
   `human_attested` / `human_disputed` / `human_approved` / `human_override` → none ·
   `package_created` → information package creation · `package_signed` → digital signature generation.
4. Projections (file states, claim statuses, outcomes) are pure functions of (events, policy version). Replay rebuilds
   them from an empty state and must equal the stored projections.
5. The chain detects edits, deletions and reordering. Tail truncation is detected only against the signed head hash and
   event count in the package (D-025); `verify` reports which protection applied.
6. Chain hashing and event validation are pure (`rearchive.core.ledger`); SQLite access lives in `rearchive.adapters`.

```decision-constants due=0.2
rearchive.core.ledger.GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
rearchive.core.ledger.EVENT_TYPES = ("project_created", "file_ingested", "fixity_checked", "format_identified", "task_reused", "file_decoded", "decode_failed", "evidence_recorded", "claim_proposed", "claims_evaluated", "human_attested", "human_disputed", "human_approved", "human_override", "package_created", "package_signed")
```

## D-023 Claims: identity, schema and policy engine (refines §7.1 and §7.2)
Refines D-006 and D-007.

1. Claim id = `C-` + the first 20 hex characters of SHA-256 of `canonical_json({"type", "property", "subject"})`.
   Evidence id = `E-` + the first 20 hex characters of SHA-256 of `canonical_json(evidence body)`. Ids are therefore
   identical across reruns, which the gate's rerun test requires.
2. `subject` is `{"source": <relpath_b64>, "sha256": <content sha>, "path": <field path or array name>}` for file-level
   claims and `{"scope": "project"}` for project-level claims. In report JSON, `file` is `relpath_display`.
3. Claim types and v1 properties:
   - `structure`: `layout`, `field_value`, `byte_coverage`, `checksum`;
   - `transform`: `sample_encoding`, `byte_order`, `scaling`;
   - `value`: `raw_samples`, `header_fields`;
   - `semantic`: `unit`, `time_origin`, `tick_duration`, `time_unit`, `timezone`, `text_encoding`;
   - `completeness`: `record_count`; `fidelity`: `replay`; `integrity`: `package`, `ledger`.
4. Evidence item: `{kind (a basis), supports | contradicts: <claim id>, inputs: [artifact ids], assumes: [claim ids],
   lineage: [ids], produced_by: actor, details}`. Bases: `structural`, `hidden_ground_truth`, `analytic_oracle`,
   `independent_implementation`, `vendor_documentation`, `attestation`, `physical_anchor`, `reconciliation`,
   `plausibility`, `self_consistency`, `human_override`.
5. Policy v1 is a pure function `(claims, evidence, human events) → {claim id: (status, bases)}`, implementing D-006's
   table and D-007's circularity and independence rules, plus:
   - before evaluation a claim is `candidate`; after evaluation, a claim without sufficient support is `unresolved`;
   - sufficient contradicting evidence and no sufficient support → `contradicted`; sufficient both ways, or a
     `human_disputed` event → `disputed`;
   - `human_override` sets a status only with a recorded reason, adds basis `human_override`, and is always displayed;
   - `bases` lists the kinds of the evidence that decided the status, not every evidence item attached.
6. Model-proposed claims record `{"kind": "model", "id": "<model>@<version>#<run id>"}` as `proposed_by` and never
   count as evidence (CLAUDE.md invariant 1).

```decision-constants due=0.5
rearchive.claims.POLICY_VERSION = "v1"
rearchive.claims.STATUSES = ("candidate", "supported", "disputed", "contradicted", "unresolved")
rearchive.claims.CLAIM_ID_HEX = 20
rearchive.claims.BASES = ("structural", "hidden_ground_truth", "analytic_oracle", "independent_implementation", "vendor_documentation", "attestation", "physical_anchor", "reconciliation", "plausibility", "self_consistency", "human_override")
```

## D-024 Validation: oracle protocol, anchors and tolerances (refines §7.4 and §7.5; changes §8.4)
Refines D-012.

1. `rearchive validate --oracle DIR` spawns `rearchive-bench oracle --truth DIR` and speaks JSON Lines over
   stdin/stdout. Request: `{"check": "structure" | "value", "source_sha256", "record": <canonical record>}`.
   Response: `{"check", "source_sha256", "result": "pass" | "fail" | "unknown", "fields": {<path>: "pass" | "fail"}}`.
   Responses never contain truth values. Semantic checks are answered `{"result": "refused"}`. Oracle evidence has basis
   `hidden_ground_truth` and lineage `rearchive_bench.oracle@<version>`.
2. Physical anchor: an evidence document `stimulus.json`
   `{"kind": "physical_stimulus", "quantity": "voltage", "unit": "volt", "waveform": "sine", "amplitude": <V>,
   "frequency_hz": <Hz>, "offset": <V>, "unit_code": <int>, "applies_to": [<content sha256>]}`.
   The validator computes physical values `gain × raw + offset` itself from the record's raw codes and bit patterns
   (it must not call decoder scaling code), fits `a·sin(2πft) + b·cos(2πft) + c` by least squares at the stated
   frequency with `t = i × sample_interval`, and takes amplitude `√(a² + b²)`. This assumes `sample_interval` is the
   time between samples in seconds, which holds for tier 0 by construction; for real formats the time base is itself a
   `semantic` claim that must be supported before an anchor can use it.
   Tolerance: `|A_fit − A_stimulus| ≤ 3·|gain| + 1e-9·A_stimulus`. Within → evidence `physical_anchor` supporting the
   `semantic/unit` claim "unit_code → volt"; outside → contradicting.
   The estimator has its own tests on synthetic sines, including a gain-error sweep that records the smallest detectable
   gain error for tier 0.
3. Attestation: an evidence document `attestation.yaml` `{who, role, date, scope: [<content sha256>] | "all",
   statement: {unit_code: <int>, unit: <name>}}` → evidence `attestation`, which D-006 lets reach `supported`, always
   displayed as attested.
4. No anchor → no evidence → `unresolved`. The oracle is never consulted for semantic claims.
5. CRC: the sidecar `check` op yields evidence `structural` for the claim `structure/checksum`; a mismatch contradicts
   it, so the claim is `contradicted` and the file outcome is at best `unverified`.

```decision-constants due=0.5
rearchive.validate.anchors.AMPLITUDE_TOLERANCE_LSB = 3
rearchive.validate.anchors.AMPLITUDE_TOLERANCE_REL = 1e-9
```

## D-025 Evidence package and signing (changes §14)
Refines D-010.

1. Layout (BagIt 1.0, SHA-256):
   ```
   bagit.txt  bag-info.txt  manifest-sha256.txt  tagmanifest-sha256.txt  rearchive-signature.json
   data/sources/<sha256>          raw source bytes, by content hash (default on; --no-sources omits them)
   data/sources-manifest.json     relpath_b64, relpath_display, sha256, kind, duplicate_of
   data/records/<sha256>.json     canonical records
   data/arrays/<sha256>.bin       D-015 canonical array bytes
   data/descriptors/<sha256>.json decode descriptors
   data/specs/...                 .ksy and sidecars used
   data/evidence/<sha256>.<ext>   evidence documents
   data/ledger/events.jsonl       {seq, prev_hash, event_hash, body}
   data/claims.json  data/report.json  data/report.html
   ```
   Paths inside the bag are ASCII by construction, so BagIt's UTF-8 path rules never meet a non-UTF-8 source name.
2. `bag-info.txt` adds `ReArchive-Package-Schema: 1`, `ReArchive-Ledger-Head`, `ReArchive-Ledger-Count`,
   `ReArchive-Policy-Version`.
3. `rearchive-signature.json` is a tag file deliberately **not** listed in `tagmanifest-sha256.txt` (it signs that file):
   `{"alg": "ed25519", "signed_file": "tagmanifest-sha256.txt", "public_key_b64", "key_fingerprint": <sha256 of the raw
   public key, hex>, "signature_b64"}`.
4. Development key: `~/.config/rearchive/dev-signing.ed25519`, created on first `package` if absent, never inside the
   repository (the kit's sandbox settings allow sessions to write that one directory). `--key PATH` selects another.
   Library: `cryptography`.
5. `rearchive verify --json` reports four separate verdicts (D-010):
   - `integrity`: `pass`/`fail` — manifests, tag manifest, signature, ledger chain, ledger head and count against
     bag-info;
   - `replay`: `pass`/`fail`/`not_run` — re-decode packaged sources with packaged specs and compare record hashes;
     re-evaluate claims under the packaged policy version and compare statuses; `not_run` when sources are omitted;
   - `semantic`: `reconciled` (every file `semantically_reconciled`), `partial` or `unreconciled`, with claim counts
     by type and status — what the evidence supports, as distinct from whether the bytes are intact;
   - `trust`: `trusted` only when `--trusted-key-fingerprint` matches; otherwise `untrusted-key`.
   Exit 0 iff integrity passes.

```decision-constants due=0.6
rearchive.package.PACKAGE_SCHEMA = 1
rearchive.package.SIGNATURE_FILE = "rearchive-signature.json"
```

## D-026 Decode worker, diagnostics and exit codes (changes §6 Stage 7 and §15)

1. `decode` runs each file in a worker subprocess (`python -I -m rearchive.worker`) with a scrubbed environment, a
   temporary working directory, stdin closed, CPU limit 30 s, wall-clock timeout 60 s, and address-space limit 2 GiB
   where the OS enforces it (Linux). Unenforced limits are recorded in the descriptor. This is fault containment, not a
   security boundary; OS-level isolation arrives in P3.
2. Modules under `rearchive.decode`, `rearchive.worker` and `rearchive.generated` import none of `socket`, `ssl`,
   `http`, `urllib`, `random`, `secrets`, `time`, `datetime`, `uuid`, `math`, `cmath`; a contract test checks this
   statically. The decode path does integer and byte operations only: no floating-point arithmetic, and therefore no
   fused multiply-add or transcendental functions whose results differ by platform. Derived views (`affine`) are
   computed in `rearchive.views`, outside the decode path.
3. Diagnostic codes v1: `empty_file`, `truncated`, `magic_mismatch`, `validation_failed`, `checksum_mismatch`,
   `trailing_bytes`, `non_finite_scaling`, `resource_limit`, `timeout`, `worker_crash`, `not_a_regular_file`. A
   diagnostic is `{code, offset (optional), detail}`; reports add `file` (`relpath_display`) when they list it.
4. Outcome (spec §13.12) per file, first matching rule wins:
   1. not a regular file → `failed` (D-016 §5);
   2. decode attempted, no record → `incomplete` when partial fields were recovered, else `failed`;
   3. every claim about the file `supported` → `semantically_reconciled`;
   4. otherwise (not yet decoded or validated, anything contradicted, disputed or unresolved) → `unverified`.
   `documented_lossy` is reserved for sources declared lossy. Each report entry also carries `state`, one of
   `ingested`, `decoded`, `decode_failed`, `validated`, `skipped` (non-regular files).
5. Exit codes for both CLIs: `0` success · `1` finished, some files failed (all recorded) — only `decode` and
   `validate` use it; every other command exits 0 when it completes, whatever per-file outcomes it records ·
   `2` usage error · `3` verification failed · `70` not implemented or internal error.
6. `REARCHIVE_TASK_DELAY_MS` is honoured by the decode orchestrator (in `rearchive.adapters`, not the decode path) between
   files and documented as a test hook.

```decision-constants due=0.2
rearchive.core.report.FILE_STATES = ("ingested", "decoded", "decode_failed", "validated", "skipped")
```


```decision-constants due=0.4
rearchive.worker.CPU_LIMIT_SECONDS = 30
rearchive.worker.WALL_TIMEOUT_SECONDS = 60
rearchive.worker.ADDRESS_SPACE_LIMIT_BYTES = 2147483648
rearchive.decode.diagnostics.CODES = ("empty_file", "truncated", "magic_mismatch", "validation_failed", "checksum_mismatch", "trailing_bytes", "non_finite_scaling", "resource_limit", "timeout", "worker_crash", "not_a_regular_file")
rearchive.cli.EXIT_CODES = {"ok": 0, "partial": 1, "usage": 2, "verification_failed": 3, "internal": 70}
```

## D-027 Benchmark scoring definitions (refines §13)
Refines D-011. Scoring reads only a package and a truth directory.

- `structural_recovery` = header fields whose canonical raw value equals truth ÷ all truth header fields, over all files
  (integers exactly, floats by bit pattern).
- `value_recovery` = files whose sample-array digest equals the digest of the truth raw codes ÷ files.
- `semantic_overreach` = semantic claims that are `supported` although the truth condition is `no-anchor` or the
  statement is false ÷ semantic claims; `null` when there are none.
- `correct_abstention` = semantic claims under a `no-anchor` condition that are `unresolved` ÷ semantic claims under a
  `no-anchor` condition; `null` when there are none.
- `anchored_resolution` = semantic claims under `anchored`/`attested` conditions that are `supported` with the matching
  basis ÷ such claims; `null` when there are none.
- `false_rejection` (from P1) = clean-control files with outcome `failed` or any contradicted claim ÷ clean-control files.
- Each score is a top-level JSON number (or `null`), with sibling fields `<score>_numerator` and
  `<score>_denominator` (integers), so `score["structural_recovery"] == 1.0` reads the score itself.

## D-028 Normative constants and decision–code consistency (refines §3.10)

1. A decision that fixes a number, size, version string or vocabulary the code must match carries a fenced block with
   info string `decision-constants due=<increment>`, one `python.dotted.symbol = <Python literal>` per line.
2. Enforcement, by the current increment in `docs/STATUS.md`:
   - blocks due **before** it: always enforced — `tests/contract/test_decision_constants.py` (owner-owned) runs with
     every unit-test run, so a constant can never regress;
   - blocks due **at** it: enforced at closure — `tools/verify.py --close` must PASS before an increment closes;
     until then they are reported as in progress, so `main` stays green when the owner starts an increment;
   - later blocks: checked for well-formedness only.
   "Enforced" means each symbol imports and equals its literal under strict type comparison.
3. No hash-affecting format may be frozen in test vectors or golden files before its decision, with its constants block,
   is in `docs/DECISIONS.md`.
4. A decision is "implemented" only when its block is enforced and green.

## D-029 Sidecar schema v1 (changes §8.3)
Refines D-003 and D-004: what the `<format>.rearchive.yaml` beside a `.ksy` may say.

```yaml
sidecar_schema: 1
spec: tier0                 # must equal the .ksy meta/id
padding: [/reserved]        # fields counted as verified padding; each must have `contents:` in the .ksy
arrays:
  samples:                  # array name used in records (D-017)
    from: /samples_raw      # a raw byte range located by the .ksy
    ops:
      - view: {dtype: int16, byte_order: le}
checks:
  - id: samples_crc
    op: crc32               # zlib CRC-32 (ISO-HDLC); D-004 `check`
    over: /samples_raw
    expect: /crc32
derived:                    # derived views: never canonical, never hashed
  physical:
    op: affine
    input: samples
    gain: /gain
    offset: /offset
claims:                     # claims the engine proposes for every decoded file (D-023)
  - {type: semantic, property: unit, path: /unit_code}
```

1. Loaded with a YAML safe loader; unknown keys are an error; strings that YAML 1.1 could read as booleans
   (`no`, `on`, `off`, `yes`) must be quoted. `byte_order` is `le` or `be`.
2. Ops come only from closed sets that grow one reviewed op at a time (D-004): tier 0 has array op `view`, check op
   `crc32` and derived op `affine`. The first op of every array is `view`. An unknown op is a load error, not a
   runtime error. Adding an op means a superseding decision that extends these constants.
3. `checks` produce evidence (D-024 §5), never data. `derived` produces views, never canonical content.
4. The sidecar's SHA-256 is part of the decode key (D-021) and the descriptor (D-018).

```decision-constants due=0.4
rearchive.decode.sidecar.SIDECAR_SCHEMA = 1
rearchive.decode.sidecar.ARRAY_OPS = ("view",)
rearchive.decode.sidecar.CHECK_OPS = ("crc32",)
rearchive.decode.sidecar.DERIVED_OPS = ("affine",)
```
