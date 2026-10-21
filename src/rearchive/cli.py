"""Command-line entry point for the ``rearchive`` product.

Increment 0.1 provides the entry point only. Every command exits non-zero with
an explicit "not implemented" message. Nothing here may report success, print a
report-shaped JSON document, or otherwise simulate work that did not happen
(``docs/STATUS.md`` increment 0.1; CLAUDE.md honest-reporting rules).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

#: Exit status used for a command that exists but is not implemented yet.
#: 70 is ``EX_SOFTWARE`` from ``sysexits.h`` -- an internal/unavailable
#: condition, deliberately distinct from argparse's usage error (2).
EXIT_NOT_IMPLEMENTED = 70

#: The command surface defined by the Gate A CLI contract, documented at the top
#: of ``tests/acceptance/test_gate_a.py``. Listed here so that an unknown command
#: is rejected as a usage error rather than reported as "not implemented".
COMMANDS: tuple[str, ...] = (
    "init",
    "ingest",
    "decode",
    "validate",
    "report",
    "package",
    "verify",
)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="rearchive",
        description="Evidence-based recovery of data from legacy file formats.",
    )
    parser.add_argument("command", choices=COMMANDS, help="the command to run")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="arguments for the command (not parsed in this increment)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``rearchive`` CLI, returning a process exit status."""
    parser = build_parser()
    namespace = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    print(
        f"rearchive {namespace.command}: not implemented.\n"
        "Increment 0.1 establishes tooling and canonical hashing only; this "
        "command arrives in a later increment (see docs/STATUS.md). No work was "
        "performed and no output was written.",
        file=sys.stderr,
    )
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":  # pragma: no cover - covered via `python -m`
    raise SystemExit(main())
