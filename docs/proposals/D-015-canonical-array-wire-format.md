# D-015 wire-format proposal — HISTORICAL

> ## HISTORICAL RECORD as of 2026-10-20. Not the active wire format.
>
> **§1 and §2 of this file describe Option A**, whose framing was
> `u64le(len(header)) + header + u64le(len(payload)) + payload` with
> `schema_version` INSIDE the JCS header. That is **not** the selected framing.
>
> The owner selected **Option B**, set out in §0.1 of this same file:
> `u16le(schema_version) + u64le(len(header)) + header + u64le(len(payload)) +
> payload`, with the header carrying exactly `dtype` and `shape`.
>
> **§0.1's Option A/Option B comparison remains useful and accurate** — it is
> why Option B was chosen. Everything in §1 onward predates that choice. This
> file was NOT rewritten to claim it always recommended Option B; its original
> content is preserved.
>
> **Status of Option B.** The implementation currently uses Option B, but
> Option B is **not normative merely because the code uses it**, and the older
> Option A material in this file is not normative either. The binding baseline
> remains the ratified decisions D-001 through D-014 in `docs/DECISIONS.md`,
> which as of this banner contains no D-015 entry.

**Status: PROPOSED, not accepted. §1 onward describes the superseded Option A.**

This file is a proposal, not a decision. `docs/DECISIONS.md` is a protected,
human-owned file (`.claude/settings.json` denies `Edit(/docs/DECISIONS.md)`, and
`.claude/agents/invariant-reviewer.md` treats any change to it as an automatic
FAIL), so this text was written here for review. Nothing becomes binding until a
human moves it into `docs/DECISIONS.md`.

**Correction (2026-10-20):** an earlier version of this paragraph said the
implementation "already follows §1–§8 below". That is **no longer true**.
`src/rearchive/core/canonical.py` implements the Option B framing of §0.1, not
the Option A framing of §1–§2. The blocking items in §0 concern how this
decision relates to **D-005**, not whether the bytes are well defined.

---

## 0. Blocking items for the human

### 0.1 This decision changes D-005 and must say so

`docs/DECISIONS.md` requires that each entry "names the spec section it changes"
and that changing a decision means adding "a new entry that supersedes it —
never edit an accepted entry silently." D-005 says:

> Arrays are hashed as: schema version, dtype string, shape, then little-endian
> packed bytes.

JCS sorts object keys, so the header serialises as `dtype`, `schema_version`,
`shape` — **dtype moves ahead of schema_version**. D-005's "then" reads as a
byte sequence, and for a hash contract the byte order *is* the contract: the
SHA-256 differs. Two framings are available:

**Option A — supersede D-005's ordering (what the implementation currently does).**
Add to this decision: *"D-015 supersedes the array-hashing clause of D-005
(changes §10.1). The enumeration in D-005 names the components that must be
covered; their serialised order is fixed by JCS."* `docs/STATUS.md` increment
0.1 must also change, because it currently reads "array hashing exactly as
D-005", which would be false.

**Option B — preserve D-005's order literally.**

```
canonical_bytes = u16le(schema_version)
                + u64le(len(header)) + header
                + u64le(len(payload)) + payload
header          = JCS({"dtype": <name>, "shape": [<dims>]})
```

Schema version comes first in the bytes, D-005 is untouched, and a second
problem disappears: under Option A `schema_version` lives *inside* a JCS header,
so version 1 can never legally change the header's own framing — a version field
buried in the thing it versions. Cost: regenerating the frozen vectors in
`tests/unit/test_canonical_arrays.py` (mechanical; one constant list).

**Recommendation: Option B.** It satisfies both documents and removes the
circularity. Option A was implemented only because the authorising instruction
specified that exact framing.

**Correction on cost.** An earlier draft of this file said Option B "costs
nothing today because no artifact has been frozen yet". That was false when
written, because the same change froze Option A into the repository. The real
cost of switching is: regenerate the 15 golden vectors in
`tests/unit/test_canonical_arrays.py`, and update
`test_header_key_order_is_jcs_not_d005_prose_order`, which deliberately pins the
implemented order and would fail under Option B. That is mechanical and
contained — the derivation script is independent of the implementation, so the
vectors can be regenerated without trusting the code — but it is not free, and
no golden hash has been committed to `tests/acceptance/golden/` yet, so nothing
outside the unit suite is affected. Freezing the vectors was itself instructed
("Freeze golden byte vectors for supported dtypes, dimensions, and
representative values"), so the fault is in the cost sentence, not the freezing.

### 0.2 Float arrays versus "raw integer codes"

D-005 bullet 1 and CLAUDE.md invariant 6 both say the canonical record is **raw
integer codes plus transform parameters**, and D-004 confines affine-scaled
physical values to "a derived view, never canonical". Admitting `float32` and
`float64` to this format creates a canonical encoding for exactly those physical
values.

The proposal's position: this format is a *serialisation primitive*; what the
canonical record is permitted to **contain** remains governed by D-005 and
invariant 6. Including a float dtype does not authorise storing physical values
in a canonical record. §2 states this normatively.

Worth noting for tier 0 specifically: the f8 fields (`sample_interval`, `gain`,
`offset`) are scalars that belong in the JCS metadata as transform parameters,
so **tier 0 needs no float array at all**.

---

## 1. Framing

```
canonical_bytes = u64le(len(header)) + header + u64le(len(payload)) + payload
header          = JCS({"dtype": <name>, "schema_version": 1, "shape": [<dims>]})
```

`u64le` is **exactly eight octets** encoding an unsigned integer, least
significant octet first, with no padding or alignment. Both length fields count
octets. `header` is RFC 8785 canonical JSON, UTF-8, no BOM. A reader can recover
all four parts without reference to anything outside the byte string, which is
what makes canonical blocks safe to concatenate — D-005 is silent on framing,
and without self-delimiting lengths a concatenation is ambiguous.

`schema_version` is **1**. Any change to the framing, the dtype set, the
traversal order, or the payload encoding requires a superseding decision and a
new version number.

## 2. Canonical dtypes

A closed set. Byte order is **not** part of a dtype name, because §4 fixes it
for every dtype; names such as `<i2` or `>i2` are invalid by construction.
Names are lowercase.

| Name | Octets | Representation | Range |
| --- | --- | --- | --- |
| `int8` | 1 | two's complement | −128 … 127 |
| `int16` | 2 | two's complement | −32768 … 32767 |
| `int32` | 4 | two's complement | −2³¹ … 2³¹−1 |
| `int64` | 8 | two's complement | −2⁶³ … 2⁶³−1 |
| `uint8` | 1 | unsigned | 0 … 255 |
| `uint16` | 2 | unsigned | 0 … 65535 |
| `uint32` | 4 | unsigned | 0 … 2³²−1 |
| `uint64` | 8 | unsigned | 0 … 2⁶⁴−1 |
| `float32` | 4 | IEEE 754 binary32 | see §5 |
| `float64` | 8 | IEEE 754 binary64 | see §5 |

Integer payload values are **not** bounded by the JSON safe-integer domain:
`uint64` carries values up to 2⁶⁴−1, because the payload holds octets rather
than JSON numbers. Only the header is JCS, and the header holds only dimensions
and the schema version.

A float dtype in this set is a serialisation primitive only. It does not
authorise a canonical record to contain physical values; D-005 bullet 1 and
invariant 6 continue to govern record content.

**Admitting a dtype** is a change to the wire format: it requires a superseding
decision and a `schema_version` bump. This matters for D-004's queued ops —
`unpack_bits` for the signed packed int24 of PROJECT_SPEC §8.1 R1 has a raw
width that is not a power of two, and whether that becomes a new `int24` dtype
or a sign-extended `int32` plus a recorded transform parameter is **not decided
here** (see §9).

## 3. Shape

`shape` is a JSON array of dimensions. Each dimension MUST be a JSON **integer**
(a JSON boolean is not an integer and MUST be rejected; so must a fractional
value), MUST be ≥ 0, and MUST be ≤ 2⁵³−1 so the header is always JCS-
serialisable. Element count is the product of the dimensions.

* **Scalar** is rank 0: `shape: []`. The empty product is 1, so a scalar carries
  exactly one element.
* **Empty array** is any shape containing a 0: element count 0, payload length 0.
  The header still records the full shape, so `[0]` and `[0, 3]` are distinct.

Because shape travels in a length-prefixed header, identical payloads under
different shapes never collide: `[2]`, `[1,2]` and `[2,1]` over the same two
values produce three different digests.

## 4. Payload

Elements are packed in **C order** (row-major: the last index varies fastest),
each element little-endian, with no padding between elements. `len(payload)`
MUST equal `element_count × octets_per_element`; a mismatch is an error (§7).

Little-endian is mandated rather than native so the bytes do not depend on the
host. All three environments declared by D-013 are little-endian anyway, so this
removes the only genuine cross-platform packing hazard.

## 5. Floating point

* **Signed zero is preserved.** `-0.0` and `+0.0` have distinct bit patterns and
  both are valid; the payload carries whichever was supplied. This is the one
  place where the array form and the metadata form deliberately disagree: JCS
  has no negative zero and serialises `-0.0` as `0`, so a signed zero survives
  in a payload but not in metadata. Implementations MUST NOT normalise it.
* **NaN and the infinities are refused**, not normalised. NaN has many bit
  patterns (quiet/signalling, payload bits) with no canonical choice among them;
  silently hashing an arbitrary one would make the digest depend on which
  operation produced the NaN, defeating D-013. The infinities have no
  unambiguous archival meaning. A format that genuinely stores either needs a
  superseding decision that fixes the encoding. Note this agrees with the
  metadata path, where JCS also refuses both.
* **Subnormals are valid** and are packed bit-exactly.
* A value offered for a float dtype MUST be exactly representable in it. An
  integer is accepted only if widening is lossless; a float64 that is not
  exactly a float32 is refused rather than rounded, because rounding here would
  be undeclared data loss.

## 6. Hashing

SHA-256 (D-005: SHA-256 everywhere), applied to **exactly** `canonical_bytes`
from §1 — the length prefixes and header included, and nothing else. Never over
`repr`, pickle, or container-file bytes (invariant 6).

## 7. Errors

Every condition below MUST raise, never degrade silently: unsupported or
misspelled dtype; a shape element that is not a non-negative integer, that is a
boolean, or that exceeds 2⁵³−1; element count disagreeing with the supplied
values; an integer outside its dtype's range; a bool offered as a numeric value
(it is an `int` subclass in Python and would otherwise pass a range check);
a float for an integer dtype; a non-finite float; a value not exactly
representable in a float dtype.

## 8. The normative artifact

The normative definition of this format is **this prose plus the frozen hex
vectors** in `tests/unit/test_canonical_arrays.py` — *not*
`src/rearchive/core/canonical.py`. Two consequences:

1. D-012 forbids `rearchive_bench` from importing `rearchive`, so any oracle or
   scoring comparison against canonical bytes must be re-implemented from this
   text. That is desirable: it makes the second implementation independent
   evidence under D-007. It only works if the spec, not the Python, is normative.
2. `canonical_bytes` MUST NOT depend on the version of the `rfc8785` package.
   The committed vectors support this claim rather than merely asserting it:
   they were derived by a throwaway script that hand-wrote the header JSON with
   no canonicalizer involved, so they pin the bytes independently of the library.

**Limit on the independence claim.** This prose was written *after* the
implementation, not before it, so for the array format it is a description of
working code rather than a specification the code was built to satisfy. A
re-implementation written from this text is therefore not fully independent
evidence under D-007 — it inherits whatever this text inherited from the code.
The frozen hex vectors are on firmer ground, because they were derived from the
D-015 prose by a script that imports neither `rearchive` nor `rfc8785`
(re-verified: all 15 reproduce exactly, with no project modules loaded). Treat
the vectors as the independent artifact and this prose as a paraphrase until a
human has reviewed and accepted it. Do not cite D-015 prose as independence in
increments 0.4 or 0.5 without that review.

## 9. Deliberately not decided here

Recorded so they are not mistaken for settled. These are also appended to the
open questions in `docs/STATUS.md`.

1. **Per-file canonical record composition.** This decision defines the bytes of
   *one* array. `tests/acceptance/test_gate_a.py` requires exactly one
   `canonical_sha256` per file, and D-005 defines the record as "raw integer
   codes + transform parameters + metadata". How multiple arrays and the JCS
   metadata compose into that single per-file digest — array naming, ordering,
   concatenation versus a Merkle construction, domain separation between block
   kinds — is **undefined**. Two implementations conforming to §1–§8 would
   produce different per-file hashes. This belongs to increment 0.4, which is
   the first increment with a consumer (D-002: contracts are extracted from a
   working slice).
2. **`schema_version` is not wired into artifact identity.** D-009 keys tasks by
   `hash(inputs, versions, runtime identity)` and PROJECT_SPEC §10.2 requires
   decoded-artifact identity to incorporate the output-schema version. Until
   that wiring exists, bumping `schema_version` would not invalidate task keys,
   so resume could keep stale artifacts and report them as current.
3. **Source byte order has nowhere to live yet.** D-004's `view` op carries a
   source byte order. §2 forbids encoding it in the dtype name and §4 fixes the
   canonical order, so it must be recorded as a transform parameter in the JCS
   metadata — but no metadata schema exists yet to hold it. If it is dropped, a
   big-endian and a little-endian source collapse to identical canonical bytes,
   losing a transform parameter D-005 requires the record to contain.
4. **Kaitai-to-canonical dtype mapping.** The tier-0 table in `docs/STATUS.md`
   names fields in Kaitai style (`u2`, `u4`, `f8`, `s2`); §2 uses explicit
   widths. The mapping is mechanical but unwritten.
5. **PROJECT_SPEC §10.1 coverage is partial.** §10.1 requires the canonical
   contract to define "field ordering, numeric encoding, treatment of missing
   values, timestamps, text encoding, and any floating-point normalization
   rules". This decision covers field ordering, numeric encoding and float
   rules. Missing values (masked or unreadable samples), timestamps and text
   encoding are unaddressed.
6. **Static versus runtime dtype checking.** Dtype names are validated at
   runtime with an explicit error rather than typed as a `Literal`, because a
   dtype generally arrives from a spec file as a string. A `Literal` would be
   statically checkable but would not constrain the real call sites.
