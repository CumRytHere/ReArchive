"""Canonical serialisation and hashing.

Two canonical forms exist, and they are deliberately different (D-005, D-015).

**Metadata** is serialised as RFC 8785 (JCS) JSON. JCS is a JSON text format, so
it inherits JSON's number model: every number is an IEEE 754 double, there is no
negative zero, and NaN and the infinities cannot be represented at all.

**Arrays** are serialised as a length-prefixed header plus a raw little-endian
payload. The payload carries bit patterns, not JSON numbers, so it *does*
distinguish ``-0.0`` from ``0.0``.

That asymmetry is intentional and is the single most surprising property of this
module:

    canonical_json(-0.0)                                    -> b"0"
    canonical_array_bytes(dtype="float64", shape=[1],
                          values=[-0.0])[-8:]               -> bytes ending 0x80

Both forms are hashed with SHA-256 (D-005), over exactly the canonical bytes and
nothing else -- never over ``repr``, pickle, or container-file bytes (CLAUDE.md
invariant 6).

This module performs no I/O and consults no clock, no randomness and no network.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

import rfc8785

#: Hash algorithm for every canonical artifact (D-005: SHA-256 everywhere, which
#: also matches the BagIt manifests required by D-010).
HASH_ALGORITHM: Final = "sha256"

#: Version of the canonical *array* framing defined by D-015. Any change to the
#: framing, the dtype set, the traversal order or the payload encoding requires a
#: new decision and a bump here.
CANONICAL_ARRAY_SCHEMA_VERSION: Final = 1

#: The maximum safe integer under the ECMAScript Number model, which is the
#: bound on a single shape dimension (D-015 section 7). Beyond it, RFC 8785
#: serialisation is refused rather than silently rounded.
JCS_SAFE_INTEGER_MAX: Final = 2**53 - 1

#: Maximum rank, i.e. number of dimensions (D-015 section 7). A new ReArchive
#: constraint introduced by D-015; it is not inherited from D-005.
MAX_RANK: Final = 64

#: ``element_count * element_size`` must not exceed this, so that the payload
#: length is representable in the u64le field the framing mandates
#: (D-015 section 8). Also a new constraint introduced by D-015.
MAX_PAYLOAD_OCTETS: Final = 2**64 - 1

type JsonValue = bool | int | float | str | Sequence[JsonValue] | Mapping[str, JsonValue] | None

type ArrayValue = int | float


# --------------------------------------------------------------------- errors


class CanonicalizationError(ValueError):
    """Base class for every canonicalisation failure raised by ReArchive.

    ReArchive code catches this, never the third-party package's own exception
    hierarchy, so the dependency stays replaceable.
    """


class UnsupportedTypeError(CanonicalizationError):
    """A value or object key cannot be carried by canonical JSON at all."""


class IntegerDomainError(CanonicalizationError):
    """An integer lies outside the exactly-representable JSON number domain."""


class NonFiniteValueError(CanonicalizationError):
    """NaN or an infinity was supplied where no canonical encoding exists."""


class UnsupportedDtypeError(CanonicalizationError):
    """The requested array dtype is not in the closed, documented set."""


class InvalidShapeError(CanonicalizationError):
    """An array shape is not a list of non-negative, serialisable dimensions."""


class PayloadLengthError(CanonicalizationError):
    """The number of values supplied disagrees with the declared shape."""


class ValueRangeError(CanonicalizationError):
    """A value is not exactly representable in the declared dtype."""


# ---------------------------------------------------------------- canonical JSON


def canonical_json(obj: JsonValue) -> bytes:
    """Serialise ``obj`` to RFC 8785 (JCS) canonical JSON bytes.

    Invalid input is refused, never coerced. In particular NaN, the infinities,
    integers beyond the JSON-safe domain, non-string object keys and types with
    no JSON counterpart all raise a :class:`CanonicalizationError` subclass.

    Note that JCS cannot distinguish an integer from an integral float: both
    ``1`` and ``1.0`` serialise to ``b"1"``. Metadata must therefore never rely
    on int-versus-float typing to carry meaning.
    """
    try:
        return rfc8785.dumps(obj)
    except rfc8785.FloatDomainError as exc:
        raise NonFiniteValueError(str(exc)) from exc
    except rfc8785.IntegerDomainError as exc:
        raise IntegerDomainError(str(exc)) from exc
    except rfc8785.CanonicalizationError as exc:
        raise UnsupportedTypeError(str(exc)) from exc
    except RecursionError as exc:
        # Deeply nested or self-referential input recurses past CPython's limit.
        # RecursionError is a RuntimeError, so without this it would escape the
        # "every canonicalisation failure" guarantee this module's base class
        # makes. A depth bound belongs with the decode path in increment 0.4.
        raise UnsupportedTypeError(
            "input is nested too deeply to canonicalise, or contains a cycle"
        ) from exc


def hash_canonical_json(obj: JsonValue) -> str:
    """Return the SHA-256 hex digest of ``obj``'s canonical JSON bytes."""
    return hashlib.sha256(canonical_json(obj)).hexdigest()


# -------------------------------------------------------------- canonical arrays


@dataclass(frozen=True, slots=True)
class Dtype:
    """One member of the closed canonical dtype set.

    ``struct_code`` is always used with an explicit ``<`` prefix, which selects
    standard sizes and little-endian order rather than platform-native layout.
    """

    name: str
    struct_code: str
    itemsize: int
    kind: Literal["int", "uint", "float"]
    min: int | None
    max: int | None


def _int_dtype(name: str, code: str, size: int, *, signed: bool) -> Dtype:
    bits = size * 8
    lo = -(2 ** (bits - 1)) if signed else 0
    hi = 2 ** (bits - 1) - 1 if signed else 2**bits - 1
    return Dtype(name, code, size, "int" if signed else "uint", lo, hi)


#: The closed canonical dtype set. Names are lowercase and carry no byte-order
#: marker, because D-015 fixes the payload byte order as little-endian for every
#: dtype. Adding a member is a change to the wire format and needs a decision.
DTYPES: Final[Mapping[str, Dtype]] = {
    d.name: d
    for d in (
        _int_dtype("int8", "b", 1, signed=True),
        _int_dtype("int16", "h", 2, signed=True),
        _int_dtype("int32", "i", 4, signed=True),
        _int_dtype("int64", "q", 8, signed=True),
        _int_dtype("uint8", "B", 1, signed=False),
        _int_dtype("uint16", "H", 2, signed=False),
        _int_dtype("uint32", "I", 4, signed=False),
        _int_dtype("uint64", "Q", 8, signed=False),
        Dtype("float32", "f", 4, "float", None, None),
        Dtype("float64", "d", 8, "float", None, None),
    )
}


def _resolve_dtype(dtype: str) -> Dtype:
    spec = DTYPES.get(dtype)
    if spec is None:
        raise UnsupportedDtypeError(
            f"unsupported dtype {dtype!r}; canonical dtypes are {', '.join(sorted(DTYPES))}"
        )
    return spec


def _validate_shape(shape: Sequence[int]) -> tuple[int, ...]:
    dims: list[int] = []
    rank = len(shape)
    if rank > MAX_RANK:
        raise InvalidShapeError(f"rank {rank} exceeds the maximum of {MAX_RANK} (D-015 section 7)")
    for index, dim in enumerate(shape):
        # bool is an int subclass; allowing it would make True a valid dimension.
        if isinstance(dim, bool) or not isinstance(dim, int):
            raise InvalidShapeError(f"shape[{index}] must be an int, got {type(dim).__name__}")
        if dim < 0:
            raise InvalidShapeError(f"shape[{index}] must be non-negative, got {dim}")
        if dim > JCS_SAFE_INTEGER_MAX:
            raise InvalidShapeError(
                f"shape[{index}]={dim} exceeds the JSON-safe integer domain "
                f"({JCS_SAFE_INTEGER_MAX}) and could not be serialised in the header"
            )
        dims.append(dim)
    return tuple(dims)


def _element_count(dims: tuple[int, ...]) -> int:
    """Number of elements a shape describes (D-015 section 7).

    Three cases, in this order:

    * rank 0 -- the empty product is 1, so a scalar carries exactly one element;
    * any dimension 0 -- the count is 0 regardless of every other dimension;
    * otherwise -- the product of the dimensions.

    The zero test comes FIRST deliberately. An implementation that multiplied
    left to right under fixed-width overflow-checked arithmetic would report a
    spurious overflow for a legal empty array such as
    ``[2**53-1, 2**53-1, 0]``, whose true count is 0 but whose first two
    factors already exceed ``MAX_PAYLOAD_OCTETS``. Python's integers are
    arbitrary precision, so the early return is not strictly required here; it
    is kept so this function reads as the normative rule it implements.
    """
    if any(dim == 0 for dim in dims):
        return 0
    count = 1
    for dim in dims:
        count *= dim
    return count


def _checked_int(spec: Dtype, value: ArrayValue, index: int) -> int:
    if isinstance(value, bool):
        raise UnsupportedTypeError(
            f"values[{index}] is a bool; {spec.name} requires an int, and "
            "accepting bool would be a silent type coercion"
        )
    if not isinstance(value, int):
        raise UnsupportedTypeError(
            f"values[{index}] must be an int for dtype {spec.name}, got {type(value).__name__}"
        )
    low, high = spec.min, spec.max
    if low is None or high is None:  # pragma: no cover - int dtypes always have bounds
        raise UnsupportedDtypeError(f"dtype {spec.name} declares no integer bounds")
    if not low <= value <= high:
        raise ValueRangeError(
            f"values[{index}]={value} is outside the range of {spec.name} [{low}, {high}]"
        )
    return value


def _checked_float(spec: Dtype, value: ArrayValue, index: int) -> float:
    if isinstance(value, bool):
        raise UnsupportedTypeError(f"values[{index}] is a bool; {spec.name} requires a real number")
    if isinstance(value, int):
        # float() of an int beyond binary64's range raises OverflowError, which is
        # an ArithmeticError -- neither a ValueError nor a CanonicalizationError --
        # so it would escape every caller that catches this module's own base class.
        try:
            widened = float(value)
        except OverflowError as exc:
            raise ValueRangeError(
                f"values[{index}]={value} is too large to represent as {spec.name}"
            ) from exc
        if widened != value:
            raise ValueRangeError(
                f"values[{index}]={value} is not exactly representable as {spec.name}"
            )
    elif isinstance(value, float):
        widened = value
    else:
        raise UnsupportedTypeError(
            f"values[{index}] must be a real number for dtype {spec.name}, got "
            f"{type(value).__name__}"
        )

    if not math.isfinite(widened):
        raise NonFiniteValueError(
            f"values[{index}]={widened!r} is not finite. NaN has many bit patterns "
            "and no canonical choice among them, and the infinities have no "
            "unambiguous archival meaning, so both are refused rather than "
            "normalised. A format that genuinely stores them needs an explicit "
            "decision fixing their encoding."
        )

    if spec.name == "float32":
        try:
            narrowed: float = struct.unpack("<f", struct.pack("<f", widened))[0]
        except OverflowError as exc:
            raise ValueRangeError(f"values[{index}]={widened!r} overflows {spec.name}") from exc
        if narrowed != widened:
            raise ValueRangeError(
                f"values[{index}]={widened!r} is not exactly representable as "
                f"{spec.name} (nearest is {narrowed!r}); rounding it here would be "
                "undeclared data loss"
            )
        return narrowed
    return widened


def _pack_payload(spec: Dtype, values: Sequence[ArrayValue]) -> bytes:
    """Pack ``values`` little-endian in C order, validating every element."""
    if spec.kind == "float":
        checked: list[ArrayValue] = [
            _checked_float(spec, value, index) for index, value in enumerate(values)
        ]
    else:
        checked = [_checked_int(spec, value, index) for index, value in enumerate(values)]
    if not checked:
        return b""
    return struct.pack(f"<{len(checked)}{spec.struct_code}", *checked)


def _header_bytes(spec: Dtype, dims: tuple[int, ...]) -> bytes:
    """The one and only definition of the D-015 header.

    Both public entry points route through here. The header is a normative
    constant of the wire format, so a second copy that could drift from this
    one would be a defect even if both copies happened to agree today.
    """
    return canonical_json({"dtype": spec.name, "shape": list(dims)})


def canonical_array_header(dtype: str, shape: Sequence[int]) -> bytes:
    """Return the JCS header bytes describing an array (D-015).

    Returns ONLY the JCS header octets: the version field and both length
    fields of the framing are excluded, so the result is NOT a canonical byte
    string. It must never be hashed as one, and never used as a task key or
    artifact identity (D-015 section 4 and section 14). Callers needing
    canonical bytes use :func:`canonical_array_bytes`.

    JCS sorts object keys, so the serialised order is ``dtype`` then ``shape``.
    ``schema_version`` is not a header member under Option B.

    Under Option B the schema version precedes the header in the canonical
    bytes, which is D-005's stated component order, so the earlier Option A
    conflict with D-005 no longer applies.
    """
    return _header_bytes(_resolve_dtype(dtype), _validate_shape(shape))


def canonical_array_bytes(
    *, dtype: str, shape: Sequence[int], values: Sequence[ArrayValue]
) -> bytes:
    """Return the canonical byte string for an array, per D-015.

    The framing is (D-015 section 2, Option B)::

        u16le(schema_version)
            + u64le(len(header)) + header
            + u64le(len(payload)) + payload

    ``values`` is a *flat* sequence in C order (row-major, last index varying
    fastest) whose length must equal the product of ``shape``. A rank-0 shape
    (``[]``) describes a scalar and therefore carries exactly one value.

    Raises a :class:`CanonicalizationError` subclass for an unsupported dtype,
    an invalid shape, a length mismatch, or any value not exactly representable
    in ``dtype``. Nothing is rounded, truncated or normalised silently.
    """
    spec = _resolve_dtype(dtype)
    dims = _validate_shape(shape)
    expected = _element_count(dims)
    octets = expected * spec.itemsize
    if octets > MAX_PAYLOAD_OCTETS:
        raise PayloadLengthError(
            f"shape {list(dims)} with dtype {spec.name} describes {expected} element(s) "
            f"of {spec.itemsize} octet(s) = {octets} octets, which exceeds "
            f"{MAX_PAYLOAD_OCTETS} and is therefore not representable in the u64le "
            "payload-length field (D-015 section 8)"
        )
    # Check the supplied length BEFORE materialising. ``values`` is a Sequence, so
    # len() is available without consuming it, and a declared length that cannot
    # match the shape must be rejected without allocating for it: materialising
    # first let a legitimately-typed lazy sequence such as range(10**8) raise a
    # bare MemoryError, which is not a CanonicalizationError and so escaped every
    # caller that catches this module's base class.
    supplied = len(values)
    if supplied != expected:
        raise PayloadLengthError(
            f"shape {list(dims)} describes {expected} element(s) but "
            f"{supplied} value(s) were supplied"
        )
    flat = list(values)
    payload = _pack_payload(spec, flat)
    header = _header_bytes(spec, dims)
    return b"".join(
        (
            struct.pack("<H", CANONICAL_ARRAY_SCHEMA_VERSION),
            struct.pack("<Q", len(header)),
            header,
            struct.pack("<Q", len(payload)),
            payload,
        )
    )


def hash_canonical_array(*, dtype: str, shape: Sequence[int], values: Sequence[ArrayValue]) -> str:
    """Return the SHA-256 hex digest of an array's canonical bytes (D-015)."""
    return hashlib.sha256(
        canonical_array_bytes(dtype=dtype, shape=shape, values=values)
    ).hexdigest()
