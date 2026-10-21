# D-015 ratification draft — SUPERSEDED, DO NOT PASTE

> ## SUPERSEDED on 2026-10-20. Historical record only.
>
> **Do not paste this file into `docs/DECISIONS.md`.** Its normative statements
> were superseded during the owner's review passes and now contradict both the
> approved decision and the implementation in three places:
>
> | This file | Owner-approved / implemented |
> | --- | --- |
> | §5 "Rank ... MUST satisfy `0 <= rank <= 8`" | `rank <= 64` (`canonical.py` `MAX_RANK = 64`) |
> | §8 table row "rank > 8" | `rank > 64` raises `InvalidShapeError` |
> | §9 "serialised header MUST NOT exceed 1024 octets" | No header cap. A **legal** rank-60 empty array has a 1034-octet header, so a 1024 cap would reject conforming input |
> | §9 "imposes no maximum payload length" | `element_count * element_size <= 2**64 - 1` (`MAX_PAYLOAD_OCTETS`) |
>
> It also still describes the **Option A** framing in places, whereas the
> approved framing is Option B: `u16le(schema_version) + u64le(len(header)) +
> header + u64le(len(payload)) + payload`, with `schema_version` outside the
> header.
>
> **Why it is kept.** The last six review rounds were largely about catching
> stale normative text. This file is the evidence of what the draft said when
> those defects were found, and deleting or rewriting it would destroy that
> record.
>
> **Where the current text is.** The owner-reviewed final text is **not in this
> repository**. It exists only in the session transcript of the correction
> passes. Nothing in `docs/proposals/` is a substitute for it, and nothing in
> this directory is normative — `docs/DECISIONS.md` alone is.

---

## Original content follows, unaltered

**Status: DRAFT for human review. Nothing here is binding.**
`docs/DECISIONS.md` and `docs/STATUS.md` line 19 are not edited by Claude.
Every dtype name, width, range and error type below was extracted from the
running implementation (`rearchive.core.canonical`), not from memory.

---

## Block 1 — paste into `docs/DECISIONS.md`

## D-015 Canonical array wire format (refines §10.1 and D-005)

Ratified: **Option B** of `docs/proposals/D-015-canonical-array-wire-format.md`.

This entry **refines** D-005 rather than superseding it. D-005 requires arrays to
be hashed as "schema version, dtype string, shape, then little-endian packed
bytes". Option B emits the schema version first, then a header whose JCS key
order is `dtype` before `shape`, then the payload — which is D-005's enumeration
in D-005's stated order. No clause of D-005 is overridden.

### 1. Framing

```
canonical_bytes = u16le(schema_version)
                + u64le(len(header)) + header
                + u64le(len(payload)) + payload
```

`u16le` is exactly 2 octets, unsigned, little-endian. `u64le` is exactly 8
octets, unsigned, little-endian. There is no padding, alignment or separator
anywhere in the framing. Both length fields count octets. `len(header)` counts
the header only and excludes the version field and both length fields.

### 2. Version field

`schema_version` is **1**, encoded as `u16le` — the two octets `0x01 0x00`.

Version 1 is the only value this decision defines. The field exists so that any
future framing yields different canonical bytes, and therefore a different
digest, for the same array. A change to the framing, the dtype set, the header
contents, the traversal order or the payload encoding requires a superseding
decision and a new version number.

Because of §10, this decision places no obligation on anything to read the field
back. No ReArchive component may branch on a version value recovered from a byte
string; the version is an input to the hash, not a dispatch key.

### 3. Header

The header is the RFC 8785 (JCS) serialisation of an object with exactly two
members:

```json
{"dtype": "<canonical dtype name>", "shape": [<dimensions>]}
```

JCS sorts object keys, so `dtype` precedes `shape`. The header is UTF-8 with no
BOM. `schema_version` is **not** a header member under this decision. No further
member may be added without a new `schema_version`.

### 4. Canonical dtypes

Exactly these ten names. Names are lowercase and carry no byte-order marker,
because §6 fixes the payload byte order for every dtype; `<i2`, `>i2`, `INT16`
and any other spelling are invalid.

| Name | Octets | Representation | Minimum | Maximum |
| --- | --- | --- | --- | --- |
| `int8` | 1 | two's complement | −128 | 127 |
| `int16` | 2 | two's complement | −32768 | 32767 |
| `int32` | 4 | two's complement | −2147483648 | 2147483647 |
| `int64` | 8 | two's complement | −9223372036854775808 | 9223372036854775807 |
| `uint8` | 1 | unsigned | 0 | 255 |
| `uint16` | 2 | unsigned | 0 | 65535 |
| `uint32` | 4 | unsigned | 0 | 4294967295 |
| `uint64` | 8 | unsigned | 0 | 18446744073709551615 |
| `float32` | 4 | IEEE 754 binary32 | see §7 | see §7 |
| `float64` | 8 | IEEE 754 binary64 | see §7 | see §7 |

Any other dtype is out of scope and is rejected with a typed error (§8).
Admitting a dtype changes the wire format and requires a superseding decision
and a `schema_version` bump.

Integer payload values are **not** bounded by the JSON safe-integer domain:
`uint64` carries values up to 2⁶⁴−1, because the payload holds octets rather
than JSON numbers. Only the header is JCS, and the header carries no values.

### 5. Shape and rank

`shape` is a JSON array of dimensions. Each dimension MUST be a JSON integer, so
a JSON boolean and a fractional value are both invalid. Each dimension MUST
satisfy `0 <= dimension <= 2**53 - 1`, the upper bound being the largest integer
JCS can serialise exactly.

Rank — the number of dimensions — MUST satisfy `0 <= rank <= 8`.

Element count is the product of the dimensions. The empty product is 1, so:

- **Scalar** is `rank 0`, written `shape: []`, and carries exactly one element.
- **Empty array** is any shape containing a `0`: element count 0, payload length
  0. The header still records the full shape, so `[0]` and `[0, 3]` are distinct
  canonical byte strings.

### 6. Payload

Elements are packed in **C order** — row-major, last index varying fastest —
each element little-endian, with no padding between elements. Little-endian is
mandated rather than native so that canonical bytes do not depend on the host.

`len(payload)` MUST equal `element_count × octets_per_element`. This equality
MUST be checked before any hashing occurs.

### 7. Floating point

- **Signed zero is preserved.** `-0.0` and `+0.0` have distinct bit patterns and
  both are valid; the payload carries whichever was supplied. Implementations
  MUST NOT normalise it. This differs deliberately from the JCS metadata path,
  where RFC 8785 has no negative zero and serialises `-0.0` as `0`.
- **Subnormals are valid** and are packed bit-exactly.
- **NaN and both infinities are rejected** with a typed error, not normalised.
  NaN has many bit patterns with no canonical choice among them, so hashing an
  arbitrary one would make the digest depend on which operation produced it,
  defeating D-013. The infinities have no unambiguous archival meaning. A format
  that genuinely stores either requires a superseding decision fixing its
  encoding.
- A value offered for a float dtype MUST be exactly representable in that dtype.
  An integer is accepted only where widening is lossless. A `float64` that is
  not exactly a `float32` MUST be rejected rather than rounded, because rounding
  here would be undeclared data loss.

### 8. Invalid input and overflow

Every condition below MUST raise a typed canonicalisation error. Nothing is
rounded, truncated, clamped or normalised silently, and no condition may be
reported through a return value.

| Condition | Error |
| --- | --- |
| dtype not in §4, including wrong case or a byte-order marker | `UnsupportedDtypeError` |
| dimension not a JSON integer, or a boolean, or negative, or > 2⁵³−1 | `InvalidShapeError` |
| rank > 8 | `InvalidShapeError` |
| serialised header longer than the §9 limit | `InvalidShapeError` |
| element count disagrees with the number of values supplied | `PayloadLengthError` |
| integer outside its dtype's range in §4 | `ValueRangeError` |
| value not exactly representable in a float dtype, including overflow | `ValueRangeError` |
| NaN or an infinity for a float dtype | `NonFiniteValueError` |
| a bool offered as a numeric value, or a float for an integer dtype | `UnsupportedTypeError` |

All of these are subclasses of a single `CanonicalizationError`, itself a
`ValueError`. ReArchive code catches that base class and never the exception
hierarchy of a third-party package, so the dependency stays replaceable.

### 9. Length limits

The serialised header MUST NOT exceed **1024 octets**. At rank 8 with maximal
dimensions the header is far below this, so the limit binds only pathological
input; it exists so that a header cannot be made unboundedly large by shape
alone.

This decision imposes no maximum payload length. The framing can express
2⁶⁴−1 octets, and a resource bound belongs with the decode worker's limits
(increment 0.4) rather than with the byte format. **See open question O-3.**

### 10. Canonical bytes are a hashing input only

Canonical array bytes exist to be hashed. No component is obliged to parse them,
no decoder behaviour is implied by this decision, and the format is not a storage
or interchange format. Storage and delivery formats — Parquet, HDF5, CSV and any
other — are defined separately, and D-005's requirement that the canonical hash
be independent of whichever writer produces delivery files is unaffected.

### 11. Hash algorithm and digest rendering

The digest is **SHA-256** (D-005: SHA-256 everywhere, matching the BagIt
manifests required by D-010), computed over **exactly** `canonical_bytes` as
defined in §1 — the version field and both length fields included, and nothing
else. Never over `repr`, pickle, or container-file bytes (CLAUDE.md invariant 6).

Where a digest is rendered as text — in canonical JSON, manifests, reports or
golden files — it is exactly **64 lowercase hexadecimal characters**, with no
prefix, separator or algorithm label.

### 12. The normative artifact

The normative definition of this format is this entry together with the frozen
hex vectors committed under `tests/unit/`. It is **not**
`src/rearchive/core/canonical.py`. Two consequences:

1. D-012 forbids `rearchive_bench` from importing `rearchive`, so any oracle or
   scoring comparison against canonical bytes must be re-implemented from this
   text. That is desirable: it makes the second implementation independent
   evidence under D-007. It only works if this entry, not the Python, is
   normative.
2. `canonical_bytes` MUST NOT depend on the version of the `rfc8785` package.
   The bytes must be reproducible from this text alone, with the library a
   convenience rather than the definition.

### 13. Vectors frozen under Option A are retired

The 15 golden vectors in `tests/unit/test_canonical_arrays.py` were frozen under
Option A, whose framing differs from §1 in every byte. They are retired and
regenerated under this decision. Regeneration MUST be performed by a derivation
independent of `rearchive.core.canonical`, so the replacement vectors do not
become a recording of the implementation.

No golden hash has been committed under `tests/acceptance/golden/`, so nothing
outside the unit suite is affected.

### 14. Standing rule

**No hash-affecting format may be frozen in test vectors or golden files before
its decision is ratified in this file.** Increment 0.1 froze 15 vectors under an
unratified framing and then recommended a different one; this rule exists so
that does not recur.

---

## Block 2 — amendment to `docs/STATUS.md` line 19

Current:

```
- `rearchive.core.canonical`: RFC 8785 JSON and array hashing exactly as D-005. Tests use the RFC 8785 test vectors.
```

Replace with:

```
- `rearchive.core.canonical`: RFC 8785 JSON and array hashing exactly as D-005 as refined by D-015. Tests use the RFC 8785 test vectors.
```

Lines 103 and 431 of `docs/STATUS.md` record that line 19 was false under the
shipped framing. Those are log and open-question entries written by Claude and
will be updated in the implementation step, once the amendment above is in place.

---

## Illustrative worked example (specification, not a vector)

For `dtype="int16"`, `shape=[4]`, `values=[0, 1, -1, 32767]`:

```
header              {"dtype":"int16","shape":[4]}          29 octets
u16le(version)      0100
u64le(len(header))  1d00000000000000
payload             00000100ffffff7f                        8 octets
total               55 octets = 2 + 8 + 29 + 8 + 8
canonical_bytes     01001d000000000000007b226474797065223a
                    22696e743136222c227368617065223a5b345d
                    7d080000000000000000000100ffffff7f
sha256              629bdaa56ba9806c4c0b5b66ec7e466893696f
                    97233e12948a461613d0937bd9
```

The replacement vector table is produced in the implementation step under §13,
not here.
