"""Contract tests for the D-015 canonical array wire format (Option B).

The expected byte strings and digests in ``GOLDENS`` were derived independently
of :mod:`rearchive.core.canonical` by a throwaway script that hand-rolled the
framing straight from the D-015 prose and wrote the header JSON by hand, without
importing ``rearchive`` or ``rfc8785`` (verified: no such module was loaded).
They are committed as literals precisely so this test cannot be satisfied by the
code it constrains; regenerating them with the implementation would make it
tautological.

STATUS: these vectors are PROVISIONAL and NON-NORMATIVE. D-015 section 15
requires regeneration, review and owner acceptance before they restate the
decision normatively, and at the time of writing D-015 is not yet recorded in
``docs/DECISIONS.md``. They are nonetheless a real constraint on the code: they
pin the Option B framing byte for byte.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import subprocess
import sys

import pytest

from rearchive.core import canonical as canonical_module
from rearchive.core.canonical import (
    CANONICAL_ARRAY_SCHEMA_VERSION,
    DTYPES,
    HASH_ALGORITHM,
    JCS_SAFE_INTEGER_MAX,
    MAX_PAYLOAD_OCTETS,
    MAX_RANK,
    CanonicalizationError,
    InvalidShapeError,
    NonFiniteValueError,
    PayloadLengthError,
    UnsupportedDtypeError,
    ValueRangeError,
    canonical_array_bytes,
    canonical_array_header,
    hash_canonical_array,
)

# (dtype, shape, values, expected_canonical_bytes_hex, expected_sha256_hex)
GOLDENS: list[tuple[str, list[int], list[float], str, str]] = [
    (
        "int16",
        [4],
        [0, 1, -1, 32767],
        "01001d000000000000007b226474797065223a22696e743136222c227368617065223a5b345d7d08000000"
        "0000000000000100ffffff7f",
        "629bdaa56ba9806c4c0b5b66ec7e466893696f97233e12948a461613d0937bd9",
    ),
    (
        "int16",
        [],
        [-32768],
        "01001c000000000000007b226474797065223a22696e743136222c227368617065223a5b5d7d0200000000"
        "0000000080",
        "f6310db07093dba645993c744bcc374cc78912a2d4e1e037d2207ba4debe94b3",
    ),
    (
        "int16",
        [0],
        [],
        "01001d000000000000007b226474797065223a22696e743136222c227368617065223a5b305d7d00000000"
        "00000000",
        "7b88d19308830869e8465d863353b5fab1332cf74fa62bbb907e7033925dc3ac",
    ),
    (
        "uint8",
        [2, 3],
        [1, 2, 3, 4, 5, 6],
        "01001f000000000000007b226474797065223a2275696e7438222c227368617065223a5b322c335d7d0600"
        "000000000000010203040506",
        "367866ebdb193ac3c1219549b405cc65d87eaa8e1d6ecc9c19d2e73f634f7c3a",
    ),
    (
        "int8",
        [3],
        [-128, 0, 127],
        "01001c000000000000007b226474797065223a22696e7438222c227368617065223a5b335d7d0300000000"
        "00000080007f",
        "4ed9f2941887d66d06e88ef303856bab3d67af107d8416337f981385d7ceb969",
    ),
    (
        "uint16",
        [2],
        [0, 65535],
        "01001e000000000000007b226474797065223a2275696e743136222c227368617065223a5b325d7d040000"
        "00000000000000ffff",
        "aad23c159bd5e01cfab0a509d9566987c44c3eb17ec807c7b221d146e23dc3c0",
    ),
    (
        "int32",
        [2],
        [-2147483648, 2147483647],
        "01001d000000000000007b226474797065223a22696e743332222c227368617065223a5b325d7d08000000"
        "0000000000000080ffffff7f",
        "8b9eaa1ec50882916b7213dc6c7a8060339d62dbd52bc83ea20d9b824bfb9178",
    ),
    (
        "uint32",
        [2],
        [0, 4294967295],
        "01001e000000000000007b226474797065223a2275696e743332222c227368617065223a5b325d7d080000"
        "000000000000000000ffffffff",
        "db3e5fa8a6b88152039f2d12aecf26a2fe611c63c11bfd42e646ca84b8223f15",
    ),
    (
        "int64",
        [2],
        [-9223372036854775808, 9223372036854775807],
        "01001d000000000000007b226474797065223a22696e743634222c227368617065223a5b325d7d10000000"
        "000000000000000000000080ffffffffffffff7f",
        "640e3a6d559ceac7033bd03199b48dab38ebf4c6386437a9e1d69c5e61b6b3b3",
    ),
    (
        "uint64",
        [2],
        [0, 18446744073709551615],
        "01001e000000000000007b226474797065223a2275696e743634222c227368617065223a5b325d7d100000"
        "00000000000000000000000000ffffffffffffffff",
        "88193f49361838af86b696dac9a965116a8c61e9fee5f2e6cd5dd1900ce771dd",
    ),
    (
        "float64",
        [3],
        [0.0, -0.0, 1.0],
        "01001f000000000000007b226474797065223a22666c6f61743634222c227368617065223a5b335d7d1800"
        "00000000000000000000000000000000000000000080000000000000f03f",
        "4308514e6ffd8dc6e12d9394a89d04ccb2156d00a4d2d8f286f627b55984d4ed",
    ),
    (
        "float32",
        [2],
        [0.0, -0.0],
        "01001f000000000000007b226474797065223a22666c6f61743332222c227368617065223a5b325d7d0800"
        "0000000000000000000000000080",
        "0c4d3ae3aedc01f906d1c36d5bdfcbf1d92988a079a71d385c51e731c3fa89b6",
    ),
    (
        "int16",
        [1, 2],
        [7, 8],
        "01001f000000000000007b226474797065223a22696e743136222c227368617065223a5b312c325d7d0400"
        "00000000000007000800",
        "e5ad9abdb3219940e645646b1c01db676e28c3c685b16d7623218b5788fb9a6e",
    ),
    (
        "int16",
        [2, 1],
        [7, 8],
        "01001f000000000000007b226474797065223a22696e743136222c227368617065223a5b322c315d7d0400"
        "00000000000007000800",
        "f98a222d2f88b04360803e1e8e1bcb1a8d1de62c2b80ae53b37af9fb5ac1658f",
    ),
    (
        "int16",
        [2],
        [7, 8],
        "01001d000000000000007b226474797065223a22696e743136222c227368617065223a5b325d7d04000000"
        "0000000007000800",
        "7ae3407f4cf830c0c899ea521886ffaf5f106c3008b4f1b91cf7ccac678ece5e",
    ),
]


@pytest.mark.parametrize(("dtype", "shape", "values", "want_hex", "want_digest"), GOLDENS)
def test_golden_canonical_bytes(
    dtype: str, shape: list[int], values: list[float], want_hex: str, want_digest: str
) -> None:
    """Frozen wire format: bytes and digest must match the independent derivation."""
    got = canonical_array_bytes(dtype=dtype, shape=shape, values=values)
    assert got.hex() == want_hex
    assert hash_canonical_array(dtype=dtype, shape=shape, values=values) == want_digest


@pytest.mark.parametrize(("dtype", "shape", "values", "want_hex", "want_digest"), GOLDENS)
def test_hash_is_sha256_of_exactly_the_canonical_bytes(
    dtype: str, shape: list[int], values: list[float], want_hex: str, want_digest: str
) -> None:
    """D-015 item 6: the digest covers exactly canonical_bytes, nothing more."""
    raw = canonical_array_bytes(dtype=dtype, shape=shape, values=values)
    assert raw.hex() == want_hex, "the digest must cover these exact bytes"
    assert hashlib.sha256(raw).hexdigest() == want_digest
    assert HASH_ALGORITHM == "sha256"


@pytest.mark.parametrize(("dtype", "shape", "values", "want_hex", "_want_digest"), GOLDENS)
def test_the_two_public_paths_build_the_same_header(
    dtype: str, shape: list[int], values: list[float], want_hex: str, _want_digest: str
) -> None:
    """``canonical_array_header`` and ``canonical_array_bytes`` must not drift.

    The header is a normative constant of the wire format. This test exists
    because the two entry points once built it from two separate literal dicts,
    which the golden vectors could not have caught: they only exercise
    ``canonical_array_bytes``.
    """
    raw = canonical_array_bytes(dtype=dtype, shape=shape, values=values)
    (header_len,) = struct.unpack_from("<Q", raw, 2)
    embedded = raw[10 : 10 + header_len]
    assert canonical_array_header(dtype, shape) == embedded
    assert raw.hex() == want_hex


def test_canonical_array_header_validates_its_arguments() -> None:
    """The public header function must reject what the byte function rejects."""
    with pytest.raises(UnsupportedDtypeError):
        canonical_array_header("float16", [1])
    with pytest.raises(InvalidShapeError):
        canonical_array_header("int16", [-1])
    with pytest.raises(InvalidShapeError):
        canonical_array_header("int16", [True])  # type: ignore[list-item]


def test_framing_is_version_then_length_prefixed_header_then_payload() -> None:
    """D-015 section 2: the framing must parse back into its five declared parts."""
    raw = canonical_array_bytes(dtype="int16", shape=[2], values=[7, 8])
    (version,) = struct.unpack_from("<H", raw, 0)
    (header_len,) = struct.unpack_from("<Q", raw, 2)
    header = raw[10 : 10 + header_len]
    (payload_len,) = struct.unpack_from("<Q", raw, 10 + header_len)
    payload = raw[18 + header_len :]

    assert version == CANONICAL_ARRAY_SCHEMA_VERSION == 1
    assert raw[:2] == bytes.fromhex("0100"), "u16le little-endian version prefix"
    assert header == b'{"dtype":"int16","shape":[2]}'
    assert payload_len == len(payload) == 4
    assert payload == bytes.fromhex("07000800")
    assert len(raw) == 2 + 8 + header_len + 8 + payload_len


def test_header_carries_only_dtype_and_shape_in_jcs_order() -> None:
    """D-015 section 4: exactly two members, JCS-sorted, no schema_version.

    Under Option B the version precedes the header in the canonical bytes
    (section 2), so the header itself carries no version. That is what keeps
    section 2's byte order equal to D-005's stated component order -- schema
    version, dtype, shape, payload -- and is why D-015 refines D-005 rather
    than superseding it.
    """
    raw = canonical_array_bytes(dtype="int16", shape=[2], values=[7, 8])
    (header_len,) = struct.unpack_from("<Q", raw, 2)
    header = raw[10 : 10 + header_len].decode()
    assert header == '{"dtype":"int16","shape":[2]}'
    assert "schema_version" not in header
    assert header.index('"dtype"') < header.index('"shape"')


def test_shape_is_disambiguated_by_the_framing() -> None:
    """Identical payloads under different shapes must never collide."""
    digests = {
        tuple(shape): hash_canonical_array(dtype="int16", shape=shape, values=[7, 8])
        for shape in ([2], [1, 2], [2, 1])
    }
    assert len(set(digests.values())) == 3, digests


def test_scalar_shape_holds_exactly_one_value() -> None:
    """Rank 0: prod([]) == 1, so a scalar carries exactly one element."""
    raw = canonical_array_bytes(dtype="int16", shape=[], values=[5])
    # Derive the expected length from the framing rather than hard-coding a
    # header size, which would silently encode one candidate framing.
    header = canonical_array_header("int16", [])
    assert len(raw) == 2 + 8 + len(header) + 8 + 2
    with pytest.raises(PayloadLengthError):
        canonical_array_bytes(dtype="int16", shape=[], values=[])
    with pytest.raises(PayloadLengthError):
        canonical_array_bytes(dtype="int16", shape=[], values=[1, 2])


def test_empty_array_has_a_zero_length_payload() -> None:
    """A zero in the shape means zero elements, but the header still describes it."""
    raw = canonical_array_bytes(dtype="int16", shape=[0], values=[])
    assert raw.endswith(bytes(8))  # payload length 0, then no payload
    assert hash_canonical_array(dtype="int16", shape=[0], values=[]) != hash_canonical_array(
        dtype="int16", shape=[0, 3], values=[]
    )


def test_c_order_traversal() -> None:
    """D-015 item 4: row-major, last index varies fastest."""
    raw = canonical_array_bytes(dtype="uint8", shape=[2, 3], values=[1, 2, 3, 4, 5, 6])
    assert raw.endswith(bytes.fromhex("010203040506"))


# --------------------------------------------------------------------- errors


def test_unsupported_dtype_is_rejected() -> None:
    for bad in ("float16", "int24", "<i2", "INT16", "complex128", ""):
        with pytest.raises(UnsupportedDtypeError):
            canonical_array_bytes(dtype=bad, shape=[1], values=[0])


def test_dtype_names_do_not_encode_byte_order() -> None:
    """Endianness is fixed by the spec, so it must not appear in the name."""
    for name in DTYPES:
        assert not name.startswith(("<", ">", "|")), name
        assert name == name.lower()


def test_invalid_shapes_are_rejected() -> None:
    for bad in ([-1], [2, -3], [1.0], ["2"], [True]):
        with pytest.raises(InvalidShapeError):
            canonical_array_bytes(dtype="int16", shape=bad, values=[0] * 2)  # type: ignore[arg-type]


def test_shape_dimension_beyond_the_jcs_integer_domain_is_rejected() -> None:
    """A dimension that JCS could not serialize must fail loudly, not silently."""
    with pytest.raises(InvalidShapeError):
        canonical_array_bytes(dtype="int16", shape=[2**53], values=[])


def test_payload_length_mismatch_is_rejected() -> None:
    with pytest.raises(PayloadLengthError):
        canonical_array_bytes(dtype="int16", shape=[3], values=[1, 2])
    with pytest.raises(PayloadLengthError):
        canonical_array_bytes(dtype="int16", shape=[2, 2], values=[1, 2, 3, 4, 5])


@pytest.mark.parametrize(
    ("dtype", "bad"),
    [
        ("int8", -129),
        ("int8", 128),
        ("uint8", -1),
        ("uint8", 256),
        ("int16", -32769),
        ("int16", 32768),
        ("uint16", -1),
        ("uint16", 65536),
        ("int32", 2**31),
        ("uint32", 2**32),
        ("int64", 2**63),
        ("uint64", 2**64),
        ("uint64", -1),
    ],
)
def test_out_of_range_integers_are_rejected(dtype: str, bad: int) -> None:
    with pytest.raises(ValueRangeError):
        canonical_array_bytes(dtype=dtype, shape=[1], values=[bad])


def test_booleans_are_not_accepted_as_integers() -> None:
    """bool is an int subclass; accepting it would be a silent type coercion."""
    with pytest.raises(CanonicalizationError):
        canonical_array_bytes(dtype="int16", shape=[1], values=[True])  # type: ignore[list-item]


def test_floats_are_not_accepted_for_integer_dtypes() -> None:
    for bad in (1.0, 1.5):
        with pytest.raises(CanonicalizationError):
            canonical_array_bytes(dtype="int16", shape=[1], values=[bad])


def test_non_finite_floats_are_rejected() -> None:
    """NaN has no single canonical bit pattern, so it is refused, not normalized."""
    for bad in (math.nan, math.inf, -math.inf):
        for dtype in ("float32", "float64"):
            with pytest.raises(NonFiniteValueError):
                canonical_array_bytes(dtype=dtype, shape=[1], values=[bad])


def test_signed_zero_is_preserved_and_distinct_from_positive_zero() -> None:
    """Contrast with the JCS metadata path, where -0.0 serializes as "0"."""
    neg = canonical_array_bytes(dtype="float64", shape=[1], values=[-0.0])
    pos = canonical_array_bytes(dtype="float64", shape=[1], values=[0.0])
    assert neg != pos
    assert neg.endswith(bytes.fromhex("0000000000000080"))
    assert pos.endswith(bytes.fromhex("0000000000000000"))


def test_float32_rejects_values_it_cannot_represent_exactly() -> None:
    """Silently rounding a float64 into float32 would be undeclared data loss."""
    with pytest.raises(ValueRangeError):
        canonical_array_bytes(dtype="float32", shape=[1], values=[0.1])
    # A value that IS exactly a float32 round-trips fine.
    exact = struct.unpack("<f", struct.pack("<f", 0.1))[0]
    raw = canonical_array_bytes(dtype="float32", shape=[1], values=[exact])
    assert raw.endswith(struct.pack("<f", exact))


def test_integers_are_accepted_for_float_dtypes_only_when_exact() -> None:
    raw = canonical_array_bytes(dtype="float64", shape=[1], values=[3])
    assert raw.endswith(struct.pack("<d", 3.0))
    with pytest.raises(ValueRangeError):
        canonical_array_bytes(dtype="float64", shape=[1], values=[2**53 + 1])


def test_float32_overflow_is_a_value_range_error_not_an_overflow_error() -> None:
    """A float64 too large for float32 must raise our typed error, not struct's."""
    with pytest.raises(ValueRangeError):
        canonical_array_bytes(dtype="float32", shape=[1], values=[1e300])
    with pytest.raises(ValueRangeError):
        canonical_array_bytes(dtype="float32", shape=[1], values=[-1e300])


def test_every_declared_dtype_has_consistent_metadata() -> None:
    for name, spec in DTYPES.items():
        assert spec.name == name
        assert spec.itemsize == struct.calcsize("<" + spec.struct_code)
        assert spec.kind in {"int", "uint", "float"}
        if spec.kind == "float":
            assert spec.min is None
            assert spec.max is None
        else:
            assert spec.min is not None
            assert spec.max is not None
            assert spec.max - spec.min == 2 ** (spec.itemsize * 8) - 1


# --------------------------------------------------------------- dtype scope
#
# These lock the dtype set and the byte order of the packing code. They are
# independent of the array framing, so they hold under any framing decision.


def test_the_dtype_set_is_exactly_the_ten_documented_names() -> None:
    """The dtype set is closed. Widening it changes the wire format.

    Admitting a dtype requires a superseding decision and a schema-version bump,
    so this test exists to make an accidental addition fail loudly rather than
    silently alter what canonical bytes can express.
    """
    assert set(DTYPES) == {
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float32",
        "float64",
    }
    assert len(DTYPES) == 10


def test_every_struct_format_in_the_canonical_module_is_explicitly_little_endian() -> None:
    """Static guarantee: no packing call may use platform-native byte order.

    ``struct`` uses native size and alignment unless the format starts with an
    explicit byte-order character. A single missing ``<`` would make canonical
    bytes depend on the host, which D-013 forbids. Checking the source rather
    than the behaviour catches a format string on a path no test exercises.
    """
    import ast
    import pathlib

    source_path = pathlib.Path(canonical_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

    packing = {"pack", "unpack", "unpack_from", "pack_into", "calcsize", "Struct"}
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in packing):
            continue
        if not (isinstance(func.value, ast.Name) and func.value.id == "struct"):
            continue
        assert node.args, f"struct.{func.attr} called with no format at line {node.lineno}"
        fmt = node.args[0]
        if isinstance(fmt, ast.Constant):
            literal = fmt.value
        elif isinstance(fmt, ast.JoinedStr):
            head = fmt.values[0]
            assert isinstance(head, ast.Constant), (
                f"struct.{func.attr} format at line {node.lineno} does not begin with a "
                "literal byte-order character"
            )
            literal = head.value
        else:
            raise AssertionError(
                f"struct.{func.attr} format at line {node.lineno} is not a literal; "
                "its byte order cannot be checked statically"
            )
        assert isinstance(literal, str)
        assert literal.startswith("<"), (
            f"struct.{func.attr} format {literal!r} at line {node.lineno} does not start "
            "with '<'; it would use native byte order and alignment"
        )
        checked += 1
    assert checked >= 4, f"expected several struct calls to check, found {checked}"


def test_canonical_bytes_do_not_depend_on_the_source_byte_order() -> None:
    """Equal values packed from either host order must give identical bytes.

    The canonical payload is defined by VALUES plus a dtype, never by how the
    producer happened to hold them in memory. Reading the same logical samples
    out of a big-endian and a little-endian source must converge.
    """
    values = [0, 1, -1, 32767, -32768]
    big = [struct.unpack(">h", struct.pack(">h", v))[0] for v in values]
    little = [struct.unpack("<h", struct.pack("<h", v))[0] for v in values]
    assert big == little == values
    from_big = canonical_array_bytes(dtype="int16", shape=[5], values=big)
    from_little = canonical_array_bytes(dtype="int16", shape=[5], values=little)
    assert from_big == from_little
    # And the payload really is little-endian on the wire, whatever the host is.
    assert from_big.endswith(struct.pack("<5h", *values))


def test_integers_too_large_for_the_float_dtype_raise_a_typed_error() -> None:
    """An int beyond binary64's range must not escape as OverflowError.

    ``float(10**400)`` raises ``OverflowError``, which is an ``ArithmeticError``
    -- not a ``ValueError`` and not a ``CanonicalizationError``. Code that
    catches the module's own base class would miss it entirely. The float32
    overflow path was already covered, but only for float inputs, which is why
    this hole survived.
    """
    for dtype in ("float32", "float64"):
        for huge in (10**400, -(10**400)):
            with pytest.raises(ValueRangeError):
                canonical_array_bytes(dtype=dtype, shape=[1], values=[huge])


# ------------------------------------------------- D-015 rank and payload limits
#
# Both bounds are NEW requirements introduced by D-015. Neither was present in
# the proposal nor in the implementation before this increment, so these tests
# are the first thing holding them.


def test_rank_64_is_accepted_and_rank_65_is_rejected() -> None:
    """D-015 section 7: 0 <= rank <= 64. The bound is inclusive."""
    assert MAX_RANK == 64
    at_bound = canonical_array_bytes(dtype="int8", shape=[1] * MAX_RANK, values=[0])
    assert at_bound.endswith(b"\x00")
    with pytest.raises(InvalidShapeError):
        canonical_array_bytes(dtype="int8", shape=[1] * (MAX_RANK + 1), values=[0])


def test_payload_representability_is_enforced() -> None:
    """D-015 section 8: element_count * element_size must fit the u64le field."""
    assert MAX_PAYLOAD_OCTETS == 2**64 - 1
    # `match` is load-bearing. Both of these pass `values=[]`, so if the
    # representability branch were removed the NEXT check -- the length mismatch
    # -- would raise the SAME class, and an unmatched `pytest.raises` would still
    # go green. A mutation run with the branch replaced by `if False:` left all
    # 88 array tests passing before these matchers were added.
    with pytest.raises(PayloadLengthError, match="not representable in the u64le"):
        canonical_array_bytes(dtype="int8", shape=[2] * 64, values=[])
    with pytest.raises(PayloadLengthError, match="not representable in the u64le"):
        canonical_array_bytes(dtype="int8", shape=[JCS_SAFE_INTEGER_MAX] * 2, values=[])


def test_the_three_shape_constraints_are_independent() -> None:
    """D-015 section 8: rank, per-dimension and representability each bind alone."""
    # Satisfies rank and per-dimension, violates representability. Matched on the
    # message so the length-mismatch branch cannot satisfy this assertion.
    with pytest.raises(PayloadLengthError, match="not representable in the u64le"):
        canonical_array_bytes(dtype="int8", shape=[2] * 64, values=[])
    # Satisfies per-dimension and representability, violates rank.
    with pytest.raises(InvalidShapeError):
        canonical_array_bytes(dtype="int8", shape=[1] * 65, values=[0])
    # Satisfies rank and representability, violates per-dimension.
    with pytest.raises(InvalidShapeError):
        canonical_array_bytes(dtype="int8", shape=[JCS_SAFE_INTEGER_MAX + 1], values=[])


def test_a_zero_dimension_makes_the_count_zero_whatever_else_is_present() -> None:
    """D-015 section 7: the zero test precedes the product.

    ``[2**53-1, 2**53-1, 0]`` is a LEGAL empty array. An implementation that
    multiplied left to right under fixed-width checked arithmetic would reject
    it, because the first two factors already exceed the payload bound. This is
    the regression test for that specific mistake.
    """
    raw = canonical_array_bytes(
        dtype="float64", shape=[JCS_SAFE_INTEGER_MAX, JCS_SAFE_INTEGER_MAX, 0], values=[]
    )
    (payload_len,) = struct.unpack_from(
        "<Q",
        raw,
        2
        + 8
        + len(canonical_array_header("float64", [JCS_SAFE_INTEGER_MAX, JCS_SAFE_INTEGER_MAX, 0])),
    )
    assert payload_len == 0
    assert raw.endswith(bytes(8)), "a zero dimension yields an empty payload"


def test_derived_header_size_bounds() -> None:
    """D-015 section 8: three derived maxima, computed from the bounds not hard-coded.

    The figures are pinned because a change to the dtype allowlist, the rank
    bound or the per-dimension bound must force them to be revisited.
    """
    longest = max(DTYPES, key=len)
    assert len(longest) == 7, longest
    fixed = len('{"dtype":"') + len(longest) + len('","shape":[') + len("]}")
    digits_max = len(str(JCS_SAFE_INTEGER_MAX))
    assert digits_max == 16

    # (1) shape-only upper bound: rank 64, every dimension maximal. NOT a valid
    # array -- its element count violates representability by a huge margin.
    shape_only = fixed + digits_max * MAX_RANK + (MAX_RANK - 1)
    assert shape_only == 1117
    with pytest.raises(PayloadLengthError):
        canonical_array_bytes(dtype=longest, shape=[JCS_SAFE_INTEGER_MAX] * MAX_RANK, values=[])

    # (2) maximum header of a VALID array: an empty one, since a zero dimension
    # removes the representability cap while the rest stay maximal.
    empty_max_shape = [0] + [JCS_SAFE_INTEGER_MAX] * (MAX_RANK - 1)
    empty_max = fixed + 1 + digits_max * (MAX_RANK - 1) + (MAX_RANK - 1)
    assert empty_max == 1102
    assert len(canonical_array_header(longest, empty_max_shape)) == 1102

    # (3) maximum header of a valid NON-EMPTY array, per the digit budget:
    # D = rank + sum(k_i) with sum(k_i) <= floor(log10(MAX_PAYLOAD_OCTETS / size)).
    witness = [1000000000000000, 1000] + [1] * 62
    assert len(witness) == MAX_RANK
    assert len(canonical_array_header("float64", witness)) == 175
    # The shape is representable -- 10**18 elements * 8 octets = 8e18 <= 2**64-1 --
    # so it passes the section 8 check and fails only on the element count, which
    # is the right failure: 10**18 values cannot be materialised. That the error
    # is PayloadLengthError about the COUNT, not about representability, is the
    # evidence that representability accepted this shape.
    with pytest.raises(PayloadLengthError, match="value\\(s\\) were supplied"):
        canonical_array_bytes(dtype="float64", shape=witness, values=[])


def test_rank_60_empty_array_exceeds_a_1024_octet_cap() -> None:
    """D-015 section 8: why a fixed 1024-octet header limit is not acceptable.

    Rank 60 is the first rank at which a VALID array's header passes 1024, so a
    1024 cap would reject a conforming empty array. Rank 59 stays under it.
    """
    longest = max(DTYPES, key=len)
    r60 = [0] + [JCS_SAFE_INTEGER_MAX] * 59
    r59 = [0] + [JCS_SAFE_INTEGER_MAX] * 58
    assert len(canonical_array_header(longest, r60)) == 1034
    assert len(canonical_array_header(longest, r59)) == 1017
    # Both are legal: a zero dimension means zero elements.
    canonical_array_bytes(dtype=longest, shape=r60, values=[])
    canonical_array_bytes(dtype=longest, shape=r59, values=[])


def test_a_lazy_sequence_is_rejected_without_materialising_it() -> None:
    """A declared length that cannot match the shape must be refused up front.

    `range` satisfies the `Sequence[int]` annotation and has a cheap `__len__`,
    so this is legitimately-typed input. The implementation previously ran
    `list(values)` before any length check, so this raised a bare `MemoryError`
    -- a plain `Exception`, neither a `ValueError` nor a `CanonicalizationError`
    -- and escaped every caller catching the module's base class.
    """
    for size in (10**8, 10**9):
        with pytest.raises(PayloadLengthError, match="value\\(s\\) were supplied"):
            canonical_array_bytes(dtype="int8", shape=[3], values=range(size))


def test_array_digest_survives_python_hash_randomization() -> None:
    """The array digest must not vary with PYTHONHASHSEED (D-013).

    The equivalent test for the JCS path covers `canonical_json` only; nothing
    held this for the array path. The header is built from a dict, so a
    serializer sensitive to insertion or hash order would show up here.
    """
    program = (
        "from rearchive.core.canonical import hash_canonical_array;"
        "print(hash_canonical_array(dtype='int16', shape=[2, 3],"
        " values=[0, 1, -1, 32767, -32768, 7]))"
    )
    digests = set()
    for seed in ("0", "1", "42", "982451653", "random"):
        proc = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        digests.add(proc.stdout.strip())
    assert len(digests) == 1, f"array digest varied with PYTHONHASHSEED: {digests}"
    assert len(digests.pop()) == 64
