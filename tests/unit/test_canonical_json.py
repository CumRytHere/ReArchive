"""RFC 8785 (JCS) conformance tests for :func:`rearchive.core.canonical.canonical_json`.

The vectors live in ``tests/unit/rfc8785_vectors.py`` with their RFC section
references. See that module's docstring for provenance and for what these
vectors do and do not establish.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from rfc8785_vectors import (
    APPENDIX_B,
    APPENDIX_B_ERRORS,
    LITERALS,
    LONE_SURROGATES,
    SORTING_PREFIX_VECTOR,
    SORTING_VECTOR,
    SORTING_VECTOR_EXPECTED_ORDER,
    STRING_ESCAPES,
    WORKED_EXAMPLE_INPUT,
    WORKED_EXAMPLE_OUTPUT,
    WORKED_EXAMPLE_OUTPUT_TEXT,
)

from rearchive.core.canonical import (
    JCS_SAFE_INTEGER_MAX,
    CanonicalizationError,
    IntegerDomainError,
    NonFiniteValueError,
    UnsupportedTypeError,
    canonical_json,
    hash_canonical_json,
)


def _double(bits_hex: str) -> float:
    """Decode an IEEE 754 binary64 big-endian bit pattern."""
    return struct.unpack(">d", bytes.fromhex(bits_hex))[0]


# ------------------------------------------------- the vectors themselves


@pytest.mark.parametrize(("bits_hex", "expected"), APPENDIX_B)
def test_appendix_b_vectors_are_internally_consistent(bits_hex: str, expected: str) -> None:
    """Validate the transcription itself, without consulting the implementation.

    Every Appendix B expected string must parse back to exactly the double its
    hex column denotes. This catches a mistyped digit in the table, and it does
    so without consulting the implementation.

    It does NOT establish that the table is canonical, and must not be cited for
    that. A non-shortest decimal form parses back to the same double, so this
    test would pass on one -- meaning it could not detect an expected value
    laundered out of the serializer. What rules that out is that the column was
    extracted from the RFC three times independently rather than computed.
    """
    value = _double(bits_hex)
    parsed = float(expected)
    if bits_hex.startswith("8") and value == 0.0:
        # Minus zero: JCS deliberately drops the sign, so only magnitude survives.
        assert parsed == 0.0
    else:
        assert struct.pack(">d", parsed) == struct.pack(">d", value), (
            f"{bits_hex} denotes {value!r} but the table says {expected!r}"
        )


@pytest.mark.parametrize(("bits_hex", "name"), APPENDIX_B_ERRORS)
def test_appendix_b_error_rows_really_are_non_finite(bits_hex: str, name: str) -> None:
    """The error rows must genuinely be the bit patterns the RFC names."""
    value = _double(bits_hex)
    assert not math.isfinite(value)
    assert math.isnan(value) if name == "NaN" else math.isinf(value)


# ------------------------------------------------------------- conformance


@pytest.mark.parametrize(("bits_hex", "expected"), APPENDIX_B)
def test_appendix_b_number_serialization(bits_hex: str, expected: str) -> None:
    """Appendix B, Table 1: ECMAScript-compatible number serialization."""
    assert canonical_json(_double(bits_hex)) == expected.encode()


@pytest.mark.parametrize(("bits_hex", "name"), APPENDIX_B_ERRORS)
def test_non_finite_numbers_terminate_with_an_error(bits_hex: str, name: str) -> None:
    """Section 3.2.2.3: NaN and Infinity are not permitted in JSON."""
    value = _double(bits_hex)
    assert not math.isfinite(value), f"{name} row {bits_hex} should not be finite"
    with pytest.raises(NonFiniteValueError):
        canonical_json(value)


def test_worked_example_matches_the_section_324_byte_dump() -> None:
    """Section 3.2.2 input -> Section 3.2.4 output, byte for byte."""
    produced = canonical_json(WORKED_EXAMPLE_INPUT)
    assert produced == WORKED_EXAMPLE_OUTPUT, (
        f"\nproduced: {produced.decode()}\nexpected: {WORKED_EXAMPLE_OUTPUT.decode()}"
    )
    # The Section 3.2.3 text form must describe the same bytes.
    assert produced.decode("utf-8") == WORKED_EXAMPLE_OUTPUT_TEXT
    assert len(produced) == 118


def test_worked_example_emits_the_euro_sign_as_literal_utf8() -> None:
    """Section 3.2.2.2: non-ASCII printable characters are never \\uhhhh-escaped."""
    produced = canonical_json(WORKED_EXAMPLE_INPUT)
    assert b"\xe2\x82\xac" in produced
    assert b"\\u20ac" not in produced


def test_property_names_sort_by_utf16_code_unit() -> None:
    """Section 3.2.3, the decisive vector.

    U+1F600 has a larger code point than U+FB33 but a smaller UTF-16 lead
    surrogate, so it must sort first. This assertion fails under code-point or
    UTF-8 ordering, which is the point of including it.
    """
    decoded: dict[str, str] = json.loads(canonical_json(SORTING_VECTOR))
    assert tuple(decoded.values()) == SORTING_VECTOR_EXPECTED_ORDER


def test_utf16_ordering_actually_differs_from_code_point_ordering_here() -> None:
    """Guard the guard: prove the vector above can tell the two apart."""
    by_code_point = tuple(SORTING_VECTOR[key] for key in sorted(SORTING_VECTOR))
    assert by_code_point != SORTING_VECTOR_EXPECTED_ORDER


def test_shorter_property_name_precedes_a_longer_one_that_extends_it() -> None:
    """Section 3.2.3: with no differing index, the shorter name comes first."""
    obj = {name: index for index, name in enumerate(reversed(SORTING_PREFIX_VECTOR))}
    decoded: dict[str, int] = json.loads(canonical_json(obj))
    assert tuple(decoded) == SORTING_PREFIX_VECTOR


def test_sorting_uses_the_raw_property_name_not_the_escaped_form() -> None:
    """Section 3.2.3: "a newline character is treated as U+000A".

    Raw U+000A (0x0A) sorts before "!" (0x21). Had the escaped form "\\n" been
    compared, the leading backslash (0x5C) would have sorted it last instead.
    """
    decoded: dict[str, int] = json.loads(canonical_json({"!": 1, "\n": 2, "~": 3}))
    assert tuple(decoded) == ("\n", "!", "~")


@pytest.mark.parametrize(("value", "expected"), STRING_ESCAPES)
def test_string_escaping(value: str, expected: str) -> None:
    """Section 3.2.2.2: escapes, lowercase \\uhhhh, and "as is" for the rest."""
    assert canonical_json(value) == expected.encode()


def test_control_character_hex_escapes_are_lowercase() -> None:
    """Section 3.2.2.2 says "lowercase hexadecimal Unicode notation"."""
    produced = canonical_json("\u001a\u001b\u001c\u001d\u001e\u001f")
    assert produced == rb'"\u001a\u001b\u001c\u001d\u001e\u001f"'
    assert b"\\u001A" not in produced


def test_unicode_normalization_is_not_applied() -> None:
    """Section 3.1: string data is preserved "as is"."""
    precomposed = canonical_json("é")
    decomposed = canonical_json("é")
    assert precomposed != decomposed


@pytest.mark.parametrize("value", LONE_SURROGATES)
def test_lone_surrogates_are_rejected(value: str) -> None:
    """Section 3.2.2.2: invalid Unicode must terminate with an error."""
    with pytest.raises(CanonicalizationError):
        canonical_json(value)


@pytest.mark.parametrize(("value", "expected"), LITERALS)
def test_literals(value: object, expected: str) -> None:
    """Section 3.2.2.1: null, true, false."""
    assert canonical_json(value) == expected.encode()  # type: ignore[arg-type]


def test_no_whitespace_between_tokens() -> None:
    """Section 3.2.1: insignificant whitespace is not emitted."""
    produced = canonical_json({"a": [1, 2, {"b": None}], "c": "d"})
    assert produced == b'{"a":[1,2,{"b":null}],"c":"d"}'
    assert b" " not in produced
    assert b"\n" not in produced


def test_nested_objects_are_sorted_recursively() -> None:
    """Section 3.2.3: child objects have their properties sorted too."""
    produced = canonical_json({"z": {"b": 1, "a": 2}, "y": [{"d": 3, "c": 4}]})
    assert produced == b'{"y":[{"c":4,"d":3}],"z":{"a":2,"b":1}}'


def test_array_element_order_is_never_changed() -> None:
    """Section 3.2.3: arrays are scanned for objects but not reordered."""
    assert canonical_json([3, 1, 2]) == b"[3,1,2]"
    assert canonical_json(["b", "a"]) == b'["b","a"]'


# ----------------------------------------------------------- domain limits


def test_integers_at_the_edge_of_the_safe_domain() -> None:
    """Section 3.1 / Appendix B note (1): JSON numbers are binary64."""
    assert canonical_json(JCS_SAFE_INTEGER_MAX) == b"9007199254740991"
    assert canonical_json(-JCS_SAFE_INTEGER_MAX) == b"-9007199254740991"
    for beyond in (2**53, -(2**53), 10**30):
        with pytest.raises(IntegerDomainError):
            canonical_json(beyond)


def test_an_integral_float_and_an_int_are_indistinguishable() -> None:
    """A documented consequence of JCS, pinned so it cannot surprise us later.

    Canonical metadata therefore must never rely on int-versus-float typing to
    carry meaning: 2**53 is rejected as an int but accepted as a float.
    """
    assert canonical_json(1) == canonical_json(1.0) == b"1"
    assert canonical_json(float(2**53)) == b"9007199254740992"
    with pytest.raises(IntegerDomainError):
        canonical_json(2**53)


def test_negative_zero_loses_its_sign_in_json() -> None:
    """Appendix B: 8000000000000000 serializes as "0".

    Contrast :mod:`tests.unit.test_canonical_arrays`, where the array payload
    preserves the sign bit. The asymmetry is intentional.
    """
    assert canonical_json(-0.0) == b"0"
    assert canonical_json(0.0) == b"0"


def test_non_string_object_keys_are_rejected() -> None:
    for bad in ({1: "a"}, {None: "a"}, {(1, 2): "a"}):
        with pytest.raises(CanonicalizationError):
            canonical_json(bad)  # type: ignore[arg-type]


def test_types_with_no_json_counterpart_are_rejected() -> None:
    for bad in ({1, 2}, b"bytes", complex(1, 2), object()):
        with pytest.raises(UnsupportedTypeError):
            canonical_json(bad)  # type: ignore[arg-type]


def test_hash_covers_exactly_the_canonical_bytes() -> None:
    obj = {"b": [1, 2], "a": "x"}
    assert hash_canonical_json(obj) == hashlib.sha256(canonical_json(obj)).hexdigest()
    assert (
        hash_canonical_json(WORKED_EXAMPLE_INPUT)
        == hashlib.sha256(WORKED_EXAMPLE_OUTPUT).hexdigest()
    )


# A canonical hasher must not be sensitive to dict iteration order, and CPython
# randomises string hashing per process unless PYTHONHASHSEED is fixed. No
# single-process assertion can detect that, because every call in one
# interpreter shares one seed. This runs the serializer in fresh interpreters
# under different seeds and compares against the RFC's own byte dump, so the
# oracle is external to the implementation.
_CHILD_PROGRAM = """
import hashlib, sys
sys.path.insert(0, {vectors_dir!r})
from rfc8785_vectors import WORKED_EXAMPLE_INPUT
from rearchive.core.canonical import canonical_json
sys.stdout.write(hashlib.sha256(canonical_json(WORKED_EXAMPLE_INPUT)).hexdigest())
"""


@pytest.mark.parametrize("hash_seed", ["0", "1", "42", "982451653", "random"])
def test_canonical_bytes_survive_python_hash_randomization(hash_seed: str) -> None:
    """Different PYTHONHASHSEED values must not change the canonical digest."""
    program = _CHILD_PROGRAM.format(vectors_dir=str(Path(__file__).resolve().parent))
    proc = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == hashlib.sha256(WORKED_EXAMPLE_OUTPUT).hexdigest()


# -------------------------------------------------------- properties
#
# These are supplemental. A round-trip property cannot establish that a
# serialization is CANONICAL -- only that it is faithful. Conformance is
# established by the RFC vectors above; these properties guard determinism and
# catch crashes on inputs the vectors do not reach.

_SAFE_TEXT = st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=40)
_SAFE_INT = st.integers(min_value=-JCS_SAFE_INTEGER_MAX, max_value=JCS_SAFE_INTEGER_MAX)
_SAFE_FLOAT = st.floats(allow_nan=False, allow_infinity=False)
_SCALARS = st.one_of(st.none(), st.booleans(), _SAFE_INT, _SAFE_FLOAT, _SAFE_TEXT)


@given(_SAFE_FLOAT)
def test_property_finite_doubles_round_trip(value: float) -> None:
    """Faithfulness: the canonical text parses back to the same double."""
    assert float(canonical_json(value).decode()) == value


@given(_SAFE_FLOAT)
def test_property_number_output_never_uses_a_forbidden_form(value: float) -> None:
    """No uppercase exponent, no trailing ".0", no "+" on the mantissa."""
    text = canonical_json(value).decode()
    assert "E" not in text
    assert not text.endswith(".0")
    assert not text.startswith("+")
    if "e" in text:
        mantissa, _, exponent = text.partition("e")
        assert exponent[0] in "+-"
        assert exponent[1] != "0" or len(exponent) == 2
        assert "+" not in mantissa


@given(st.dictionaries(_SAFE_TEXT, _SCALARS, max_size=12))
def test_property_insertion_order_cannot_affect_the_bytes(obj: dict[str, Any]) -> None:
    """Determinism: canonical bytes depend on content, never on insertion order.

    The keys come from a dict so they are unique; rebuilding from a reversed
    item list therefore changes only the insertion order, never the content.
    An earlier version of this test built the dict from a raw list of pairs and
    was unsound: Hypothesis found [("", False), ("", 0)], where de-duplication
    leaves {"": 0} and {"": False}. Python calls those equal because
    0 == False, but JCS correctly serializes them as 0 and false. That
    distinction is now pinned by its own test below.
    """
    items = list(obj.items())
    assert canonical_json(dict(items)) == canonical_json(dict(reversed(items)))


def test_booleans_and_integers_are_distinguished_despite_python_equality() -> None:
    """``0 == False`` in Python, but the canonical bytes must differ.

    Metadata holding False must never hash the same as metadata holding 0.
    """
    # Python considers 0 == False; the canonical bytes must not.
    assert canonical_json({"a": 0}) != canonical_json({"a": False})
    assert canonical_json({"a": 0}) == b'{"a":0}'
    assert canonical_json({"a": False}) == b'{"a":false}'
    # Python considers 1 == True; the canonical bytes must not.
    assert canonical_json({"a": 1}) != canonical_json({"a": True})


@given(st.dictionaries(_SAFE_TEXT, _SCALARS, max_size=10))
def test_property_object_keys_come_out_in_utf16_order(obj: dict[str, Any]) -> None:
    """The emitted key order must equal a UTF-16BE sort of the raw keys."""
    decoded: dict[str, Any] = json.loads(canonical_json(obj))
    assert list(decoded) == sorted(obj, key=lambda k: k.encode("utf-16-be"))
