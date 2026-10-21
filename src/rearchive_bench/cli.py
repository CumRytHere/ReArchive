"""Command-line entry point for ``rearchive-bench``.

Increment 0.1 provides the entry point only. Every command exits non-zero with
an explicit "not implemented" message and never simulates a successful run.

This module must not import :mod:`rearchive`. The benchmark reaches the product
only through its CLI and through files, so that hidden truth can never be
computed with product code (D-012, CLAUDE.md invariant 10). The small amount of
duplication with ``rearchive.cli`` is deliberate and load-bearing.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

#: Exit status used for a command that exists but is not implemented yet.
#: 70 is ``EX_SOFTWARE`` from ``sysexits.h``.
EXIT_NOT_IMPLEMENTED = 70

#: The command surface defined by the Gate A CLI contract, documented at the top
#: of ``tests/acceptance/test_gate_a.py``.
COMMANDS: tuple[str, ...] = (
    "generate",
    "score",
)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="rearchive-bench",
        description="ReArchive benchmark: generator, hidden truth and scoring.",
    )
    parser.add_argument("command", choices=COMMANDS, help="the command to run")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="arguments for the command (not parsed in this increment)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``rearchive-bench`` CLI, returning a process exit status."""
    parser = build_parser()
    namespace = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    print(
        f"rearchive-bench {namespace.command}: not implemented.\n"
        "Increment 0.1 establishes tooling and canonical hashing only; this "
        "command arrives in a later increment (see docs/STATUS.md). No work was "
        "performed and no output was written.",
        file=sys.stderr,
    )
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":  # pragma: no cover - covered via `python -m`
    raise SystemExit(main())
