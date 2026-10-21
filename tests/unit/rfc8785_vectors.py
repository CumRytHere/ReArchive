"""RFC 8785 conformance vectors, transcribed from the RFC with source locations.

Provenance
----------
Transcribed on 2026-10-20 from RFC 8785 (JSON Canonicalization Scheme) as
published at:

  * https://www.rfc-editor.org/rfc/rfc8785.txt
  * https://www.rfc-editor.org/rfc/rfc8785.html
  * https://datatracker.ietf.org/doc/html/rfc8785

Appendix B's table has 26 rows. It was extracted independently three times,
once from each of those renderings, and all three agreed on all 26. Those three
extractions were carried out by separate agents reading those URLs, not by the
author of this file, so the transcription chain contains an intermediary. That
is precisely why each row is also checked mechanically below instead of being
trusted.

Be clear about what that chain does and does not establish. The agreement of
three extractions, and the conformance of the APPENDIX_B column, DO rest on
agents having read those URLs; nothing committed here corroborates the reading
itself. The mechanical check narrows the exposure to a mistyped digit and
nothing more. The one vector that does not depend on the chain at all is the
array framing in tests/unit/test_canonical_arrays.py, whose goldens can be
re-derived from the D-015 prose, committed in this repository, without loading
any project module -- so unlike the RFC reading, anyone can repeat it. The 24 rows
that have a serialization live in APPENDIX_B; the 2 whose "JSON Representation"
cell is empty live in APPENDIX_B_ERRORS, together with negative infinity, which
is NOT an Appendix B row (see the note there).

Each APPENDIX_B row is additionally checked mechanically by
test_appendix_b_vectors_are_internally_consistent, which uses struct alone:
float(expected) must decode to exactly the double its hex bit pattern denotes.
That check never calls the canonicalizer, so a mistyped digit fails even if the
implementation agrees with the typo. It covers APPENDIX_B only and says nothing
about WORKED_EXAMPLE_OUTPUT_HEX.

WORKED_EXAMPLE_OUTPUT_HEX is guarded differently, by
test_worked_example_matches_the_section_324_byte_dump, which compares it against
the serializer's output. A hand-rewrapped copy of the RFC's hex dump did in fact
lose a byte during authoring (an extra "30", turning 1e+30 into 1e0+30) and that
test is what caught it. The dump is therefore stored space-separated and
stripped programmatically rather than re-wrapped by hand, so the octets can be
compared one at a time. Its line breaks are chosen for readability here; the
only statement this file makes about the RFC's own layout is the disclaimer
beside WORKED_EXAMPLE_OUTPUT_DUMP.

These are the RFC's own vectors, NOT the upstream json-canonicalization test
suite referenced by RFC 8785 Appendix I. That suite was never obtained or
executed, and nothing here should be read as claiming otherwise.

Escape-prone entries are built with chr() rather than written as backslash-u
escapes, so the committed source cannot be corrupted by an editing pipeline
that rewrites escape sequences.
"""

from __future__ import annotations

from typing import Final

#: A single reverse-solidus character.
BS: Final = chr(0x5C)

# ---------------------------------------------------------------------------
# Appendix B, Table 1: "ECMAScript-Compatible JSON Number Serialization
# Samples", 26 rows in document order.
#
# The two error rows carry an EMPTY "JSON Representation" cell in the RFC; the
# words NaN and Infinity come from the adjacent Comment column, where footnote
# (3) reads "Values out of range are not permitted in JSON. See Section
# 3.2.2.3." They are kept separately in APPENDIX_B_ERRORS below.
# ---------------------------------------------------------------------------

#: (ieee754_big_endian_hex, expected_jcs_serialization)
APPENDIX_B: Final[tuple[tuple[str, str], ...]] = (
    ("0000000000000000", "0"),  # Zero
    ("8000000000000000", "0"),  # Minus zero, sign dropped
    ("0000000000000001", "5e-324"),  # Min positive number
    ("8000000000000001", "-5e-324"),  # Min negative number
    ("7fefffffffffffff", "1.7976931348623157e+308"),  # Max positive number
    ("ffefffffffffffff", "-1.7976931348623157e+308"),  # Max negative number
    ("4340000000000000", "9007199254740992"),  # Max positive int, note (1)
    ("c340000000000000", "-9007199254740992"),  # Max negative int, note (1)
    ("4430000000000000", "295147905179352830000"),  # ~2**68, note (2)
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),  # last plain form below 1e21
    ("444b1ae4d6e2ef50", "1e+21"),  # exponential begins at 1e21
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),  # just below 1e-6
    ("3eb0c6f7a0b5ed8d", "0.000001"),  # at 1e-6, plain decimal
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),  # round half to even, note (4)
)

#: Appendix B rows whose JSON Representation cell is empty: RFC 8785 section
#: 3.2.2.3 requires a conforming implementation to terminate with an error.
#: fff0000000000000 is NOT an Appendix B row; it is added because section
#: 3.2.2.3 names "Infinity" without restricting the sign.
APPENDIX_B_ERRORS: Final[tuple[tuple[str, str], ...]] = (
    ("7fffffffffffffff", "NaN"),
    ("7ff0000000000000", "Infinity"),
    ("fff0000000000000", "-Infinity (not an Appendix B row; implied by 3.2.2.3)"),
)

# ---------------------------------------------------------------------------
# The worked example spans three subsections: the parsed input is in section
# 3.2.2, the canonical text form in section 3.2.3, and the same output as UTF-8
# bytes in section 3.2.4.
# ---------------------------------------------------------------------------

#: The parsed JSON object from section 3.2.2 ("Assume the following JSON object
#: is parsed:"). The string member's 12 code points are, in order:
#: U+20AC U+0024 U+000F U+000A A ' B U+0022 U+005C U+005C U+0022 /
WORKED_EXAMPLE_INPUT: Final[dict[str, object]] = {
    "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001],
    "string": (
        chr(0x20AC)
        + "$"
        + chr(0x0F)
        + chr(0x0A)
        + "A'B"
        + chr(0x22)
        + chr(0x5C)
        + chr(0x5C)
        + chr(0x22)
        + "/"
    ),
    "literals": [None, True, False],
}

#: Section 3.2.4, "UTF-8 Generation": the canonical output as 118 octets, in the
#: space-separated form the RFC prints. Stored separated so it can be compared
#: against the document octet by octet without mentally re-wrapping anything;
#: the compact form below is derived from it rather than typed a second time.
#: The octet VALUES and the count (118) come from three independent extractions
#: of the RFC that agreed, and were re-checked against the serializer's output;
#: the line grouping here is for readability and is not itself a claim about the
#: RFC's typesetting.
WORKED_EXAMPLE_OUTPUT_DUMP: Final = (
    "7b 22 6c 69 74 65 72 61 6c 73 22 3a 5b 6e 75 "
    "6c 6c 2c 74 72 75 65 2c 66 61 6c 73 65 5d 2c "
    "22 6e 75 6d 62 65 72 73 22 3a 5b 33 33 33 33 "
    "33 33 33 33 33 2e 33 33 33 33 33 33 33 2c 31 "
    "65 2b 33 30 2c 34 2e 35 2c 30 2e 30 30 32 2c "
    "31 65 2d 32 37 5d 2c 22 73 74 72 69 6e 67 22 "
    "3a 22 e2 82 ac 24 5c 75 30 30 30 66 5c 6e 41 "
    "27 42 5c 22 5c 5c 5c 5c 5c 22 2f 22 7d"
)

#: The same 118 octets with the separators removed. This is the strongest
#: single vector in the RFC, because it fixes the exact bytes and so leaves
#: no room for transcription ambiguity.
WORKED_EXAMPLE_OUTPUT_HEX: Final = WORKED_EXAMPLE_OUTPUT_DUMP.replace(" ", "")

#: Section 3.2.3 sorting test vector. This is the decisive case for the UTF-16
#: rule: U+1F600 has a LARGER code point than U+FB33 (0x1F600 > 0xFB33) but a
#: SMALLER UTF-16 lead surrogate (0xD83D < 0xFB33), so JCS sorts the emoji
#: BEFORE the Hebrew letter. Code-point order and UTF-8 byte order both put the
#: emoji last, so this vector fails under either of them.
SORTING_VECTOR: Final[dict[str, str]] = {
    chr(0x20AC): "Euro Sign",
    chr(0x0D): "Carriage Return",
    chr(0xFB33): "Hebrew Letter Dalet With Dagesh",
    "1": "One",
    chr(0x1F600): "Emoji: Grinning Face",
    chr(0x80): "Control",
    chr(0xF6): "Latin Small Letter O With Diaeresis",
}

#: Section 3.2.3, "Expected argument order after sorting property strings",
#: quoted in document order.
SORTING_VECTOR_EXPECTED_ORDER: Final[tuple[str, ...]] = (
    "Carriage Return",
    "One",
    "Control",
    "Latin Small Letter O With Diaeresis",
    "Euro Sign",
    "Emoji: Grinning Face",
    "Hebrew Letter Dalet With Dagesh",
)

#: Section 3.2.3's plain-English illustration of the comparison rule: the first
#: differing code unit decides, and where no index differs the shorter name
#: precedes the longer one.
SORTING_PREFIX_VECTOR: Final[tuple[str, ...]] = ("", "a", "aa", "ab")

# ---------------------------------------------------------------------------
# Section 3.2.2.2, "Serialization of Strings". Expected values are the escape
# text that must appear INSIDE the output quotes.
# ---------------------------------------------------------------------------

#: The five control characters section 3.2.2.2 requires in short form, plus the
#: two unconditional escapes. Every other code point below U+0020 uses the
#: \uhhhh form with LOWERCASE hex digits.
SHORT_FORM_ESCAPES: Final[tuple[tuple[str, str], ...]] = (
    (chr(0x08), BS + "b"),
    (chr(0x09), BS + "t"),
    (chr(0x0A), BS + "n"),
    (chr(0x0C), BS + "f"),
    (chr(0x0D), BS + "r"),
    (chr(0x22), BS + chr(0x22)),
    (chr(0x5C), BS + BS),
)

#: Control characters with no short form, which must use lowercase \uhhhh.
#: U+000B is the classic trap: a control character that is NOT one of the five.
LONG_FORM_ESCAPES: Final[tuple[tuple[str, str], ...]] = tuple(
    (chr(cp), BS + f"u{cp:04x}") for cp in (0x00, 0x01, 0x07, 0x0B, 0x0E, 0x0F, 0x1F)
)

#: Code points emitted "as is", never escaped. Section 3.2.2.2 escapes only the
#: C0 controls, U+0022 and U+005C; everything else passes through, and section
#: 3.2.4 then encodes the result as UTF-8.
LITERAL_PASSTHROUGH: Final[tuple[str, ...]] = (
    "/",  # solidus is never escaped, unlike many JSON writers
    chr(0x7F),  # DEL is not a C0 control
    chr(0x80),  # C1 controls are not escaped either
    chr(0xF6),  # o with diaeresis
    chr(0x20AC),  # euro sign -> literal e2 82 ac
    chr(0x2028),  # line separator: escaped by JS-safe writers, not by JCS
    chr(0x2029),  # paragraph separator
    chr(0x1F600),  # astral plane
)


# ---------------------------------------------------------------------------
# Derived views. These are built from the primary vectors above so that the
# transcription has exactly one source of truth.
# ---------------------------------------------------------------------------

#: The section 3.2.4 output as bytes.
WORKED_EXAMPLE_OUTPUT: Final = bytes.fromhex(WORKED_EXAMPLE_OUTPUT_HEX)

#: The section 3.2.3 canonical text form: the same octets, decoded as UTF-8.
WORKED_EXAMPLE_OUTPUT_TEXT: Final = WORKED_EXAMPLE_OUTPUT.decode("utf-8")

#: (input_string, complete_expected_canonical_output) pairs covering section
#: 3.2.2.2: the seven short forms, the lowercase \uhhhh long form, and the
#: "as is" passthrough rule.
STRING_ESCAPES: Final[tuple[tuple[str, str], ...]] = (
    *((char, '"' + escape + '"') for char, escape in SHORT_FORM_ESCAPES),
    *((char, '"' + escape + '"') for char, escape in LONG_FORM_ESCAPES),
    *((char, '"' + char + '"') for char in LITERAL_PASSTHROUGH),
)

#: Section 3.2.2.1: the three JSON literals.
LITERALS: Final[tuple[tuple[object, str], ...]] = (
    (None, "null"),
    (True, "true"),
    (False, "false"),
)

#: Section 3.2.2.2 requires invalid Unicode such as lone surrogates to
#: terminate with an error. U+DEAD is the RFC's own example.
LONE_SURROGATES: Final[tuple[str, ...]] = (
    chr(0xD800),
    chr(0xDEAD),
    chr(0xDFFF),
    "a" + chr(0xD83D) + "b",
)
