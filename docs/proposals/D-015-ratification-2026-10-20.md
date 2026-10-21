# D-015 — owner-reviewed ratification text, 2026-10-20

> # OWNER-REVIEWED RATIFICATION DRAFT — NOT YET RATIFIED.
>
> - **`docs/DECISIONS.md` remains the sole authority for recorded decisions.** As of this file's date it contains no `## D-015` heading and ends at `## D-014`; its blob is byte-identical to the `c060158` starter commit.
> - **This file is a copy-ready proposal, not a ratification.** Writing it changes nothing normative. Nothing under `docs/proposals/` is binding.
> - **Option B MUST NOT be called normative merely because the implementation currently uses it.** The implementation's use of a framing is not a decision.
> - **The 15 Option B vectors in `tests/unit/test_canonical_arrays.py` remain provisional** until this decision is recorded, the vectors are reviewed, and the owner accepts them — all three.
> - **No acceptance golden file may be created under `tests/acceptance/golden/` before those conditions are satisfied.**
>
> **Supersedes as pasteable text, but does not replace as history:**
> `docs/proposals/D-015-RATIFICATION-DRAFT.md` (marked SUPERSEDED — DO NOT PASTE; retains rank-8 and 1024-octet statements as the record of what was caught) and `docs/proposals/D-015-canonical-array-wire-format.md` (marked HISTORICAL; §1 onward describes the superseded Option A framing, while its §0.1 Option A/B comparison remains accurate). Both are intact apart from their notices.
>
> **Verification basis.** Every dtype name, octet width, integer range and error type below was extracted from the running implementation on 2026-10-20 by execution, and all five header-size figures were recomputed independently. `src/rearchive/core/canonical.py` was blob `3310f878da89981863079e84e8cd66c5b4a3f34b` at that time. See "Verification matrix" at the end, and "Not verified" for the four items that could not be established from this repository.

---

## Block 1 — text proposed for `docs/DECISIONS.md`

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

---

## Block 2 — amendment to `docs/STATUS.md` line 19

Currently:

```
- `rearchive.core.canonical`: RFC 8785 JSON and array hashing exactly as D-005. Tests use the RFC 8785 test vectors.
```

Replace with:

```
- `rearchive.core.canonical`: RFC 8785 JSON, and array hashing as D-005 refined by D-015 (Option B). Tests use the RFC 8785 test vectors.
```

This line is human-owned (SETUP.md assigns the increment plan to the owner and the log and open questions to Claude), so it has not been amended by Claude. The implementation-conformance record that D-015 deliberately excludes from its normative rules is in the dated log entries in that file.

## Block 3 — no amendment to D-009 (deliberately)

**Do not append anything to D-009, and do not add a second entry for it.** The
preamble of `docs/DECISIONS.md` states: *"To change a decision, add a new entry
that supersedes it — never edit an accepted entry silently."* Appending a clause
to D-009 would be editing an accepted entry.

The task-key rule lives in §14 above, which names D-009 as the decision it
refines without superseding it. One new entry carries the change; D-009's text
stays as recorded. An earlier version of this package instructed an append to
D-009; that was procedurally wrong and is withdrawn here.

## Block 4 — amendment to `docs/PROJECT_SPEC.md` §10.2

Replace the "Decoded artifacts" sentence with:

> **Decoded artifacts** incorporate source identity, decoder identity and version, specification hash, canonical configuration, output-schema version, the canonical array wire-format `schema_version`, and runtime or dependency-lock identity.
>
> The canonical array wire-format version and the output-schema version are **distinct**: the former versions the byte framing from which canonical digests are computed (D-015 §2, §13), the latter versions the structure of the delivered decoded artifact. Either may change without the other, so both must appear in artifact identity. See D-015 §14.

---

## Contradiction inventory — four findings

| # | Finding | Classification |
| --- | --- | --- |
| 1 | An earlier draft defined a canonical measurement record as comprising "exactly" (a) and (b), omitting D-005's mandatory record-level metadata component | **Real contradiction** — directly contrary to D-005 bullet 1 |
| 2 | The measurement-role rule was exhaustive over "every canonical array within a record", leaving the metadata component with no admissible role | **Real contradiction** — the rule could not be satisfied as scoped |
| 3 | "Out of scope for `schema_version` 1" implied the version field tracks the float-source policy; the framing is byte-identical either way | **Misleading implication** — no requirement conflicted; the wording invited a false inference |
| 4 | §14 could be read as governing per-file record identity when it governs one array | **Scope gap** — nothing stated was false; a case was simply unaddressed |

Two of the four are real contradictions; one is a misleading implication; one is a scope gap. A fifth item — reconciling §6's roles with §12's "no measurement semantics in the bytes" — is a **clarification that introduces no new policy** and is not counted as a finding.

Nothing in this entry is both resolved and pending. Where a matter is settled but its mechanism deferred, the distinction is stated explicitly: §6's role **distinction** is binding from ratification while its **field schema** defers to U-7; OD-1's **policy** is resolved for version 1 while a **future extension** requires a superseding decision.

## OD-1 — RESOLVED for `schema_version` 1

**Selected policy:** natively floating-point measurement sources are **excluded** from `schema_version` 1, as stated normatively in §6. This is settled, not pending; no further owner decision is required to ratify D-015.

**To extend it later**, a superseding decision is required, together with any amendments needed to protected documents. Because D-005 bullet 1 and `CLAUDE.md` invariant 6 both state "raw **integer** codes" verbatim, an extension permitting float raw measurement codes must **amend those documents**, not reinterpret them. Both are human-owned.

**Interaction with versioning.** §6's restriction is a **usage rule**, not a byte-format rule: relaxing it changes no octet of `canonical_bytes`. Under §3 the version-bump triggers are the framing, the dtype allowlist, the header members, the traversal order and the payload encoding; §5 adds dtype admission. A relaxation touches none of these, because `float32` and `float64` are already in the allowlist. **No conflict with the existing version-bump rules arises, and this entry does not invent a bump those rules do not require.**

**Context, so an extension is not mistaken for a contradiction fix:** the tension pre-exists D-015. D-004 defines the `view` op as "integer/**float** dtype + byte order" while D-005 bullet 1 and invariant 6 admit only integer codes. D-015 neither creates nor resolves that; it declines to rely on either reading.

## Tracked future questions

| # | Question | Gate or target |
| --- | --- | --- |
| **U-5** | Kaitai-to-canonical dtype mapping. The tier-0 table uses `u2`/`u4`/`f8`/`s2`; §5 uses explicit widths. Mechanical but unwritten. | **Increment 0.4**, where the `.ksy` first needs it |
| **U-6** | Source byte order and transform metadata. §5 forbids byte order in the dtype name and §9 fixes the canonical order, so equal sample values from big- and little-endian sources produce identical canonical payloads. The source's own byte order must be carried as transform metadata, and no schema defines it. **Decision gate: no decoder depending on source byte order may be accepted until U-6 is decided.** | **Increment 0.4**, with the `view` op |
| **U-7** | Per-file canonical record composition. §2 defines one array's bytes; the Gate A suite requires one `canonical_sha256` per file. **Also carries the field-level schema for §6's role distinction**, the distinction itself being binding now. | **Increment 0.4**, first increment with a consumer (D-002) |
| **U-8** | PROJECT_SPEC §10.1 partly uncovered: missing values (masked or unreadable samples), timestamps and text encoding. | **Increment 0.5** for missing values; decision gate for timestamps and text encoding before P1 |

None of U-5 through U-8 is resolved by this entry.

---

## Verification matrix

Performed on 2026-10-20 against the live repository, by execution rather than recall.

| Claim | Method | Result |
| --- | --- | --- |
| Ten dtype names, widths, kinds and integer ranges (§5) | Read `DTYPES` from the running module; `struct.calcsize` per entry | **Verified** — exactly 10; every width and endpoint matches the table |
| `schema_version` 1, `u16le` prefix (§2, §3) | First two octets of a live canonical byte string | **Verified** — `0100` |
| Header carries exactly `dtype` and `shape`, JCS order, no `schema_version` (§4) | Live `canonical_array_header("int16", [2])` | **Verified** — `{"dtype":"int16","shape":[2]}` |
| `MAX_RANK` 64, `MAX_PAYLOAD_OCTETS` 2⁶⁴−1, dimension bound 2⁵³−1 (§7, §8) | Read module constants | **Verified** — 64, 18446744073709551615, 9007199254740991 |
| Shape-only upper bound **1117**, and unattainable | Recomputed; validity-checked against all three constraints | **Verified** — 1117, `valid=False` |
| Maximum valid empty header **1102** | Recomputed; searched all dtypes × ranks 1–64 for a longer valid header | **Verified** — 1102 is the maximum over valid arrays |
| Maximum valid non-empty header **175** | Recomputed from the witness; digit-budget bound computed per dtype | **Verified** — 175, attained by `float32` and `float64`; every other dtype ≤ 174 |
| Rank-60 **1034** and rank-59 **1017** | Recomputed; both validity-checked | **Verified** — 1034 > 1024 and legal; 1017 ≤ 1024 |
| Nine typed-error conditions (§11) | Triggered each against the live module | **Verified** — each raises the stated subclass |
| Exhaustive typed-error guarantee, lazy sequence (§11) | `values=range(10**8)`, `shape=[3]` | **Verified** — `PayloadLengthError`, not `MemoryError` |
| float64 accepts a value inexact in binary32 (§10) | `values=[0.1]` for `float64` and for `float32` | **Verified** — accepted for `float64`, `ValueRangeError` for `float32` |
| D-005's mandated wording quoted in §1 | Read `docs/DECISIONS.md` line 29 | **Verified** verbatim |
| D-004's `view` op wording quoted in OD-1 | Read `docs/DECISIONS.md` line 24 | **Verified** verbatim |
| CLAUDE.md invariant 6 wording quoted in §6, OD-1 | Read `CLAUDE.md` line 23 | **Verified** verbatim |
| `docs/DECISIONS.md` has no D-015 | `grep -c '^## D-015'` | **Verified** — 0; ends at D-014 |
| Option A vectors staged but never committed (§15) | `git rev-list --count HEAD` = 1; `git cat-file -e HEAD:tests/unit/test_canonical_arrays.py` fails | **Verified** |
| `[proposal §N]` citation targets exist | Listed the proposal's headings | **Verified** — numbering is 0, 0.1, 0.2, 1–9 |
| Internal `§N` cross-references resolve | Checked each, including `§1 item 4` and `§1 item 6` | **Verified** — item ordering preserved deliberately |

## Not verified — four items

1. **D-013 cross-environment determinism.** Linux x86-64 only. There is no git remote, so `.github/workflows/ci.yml` has never executed on any architecture. The workflow file is not evidence of a passing build.
2. **Normative conformance of Option B.** D-015 is unratified; no verdict is possible against an authority that does not exist in the repository.
3. **Whether `MAX_RANK = 64` and `MAX_PAYLOAD_OCTETS = 2**64 − 1` are the owner-approved values.** The only in-repository statements of these bounds are the superseded draft, which says rank 8 and no payload maximum, and the code itself. This file records them from the owner's review passes, which are not themselves in the repository.
4. **Independence of `canonical_bytes` from the `rfc8785` version** (§15). Recorded as a design intent with its limitation stated, not as an established property.
