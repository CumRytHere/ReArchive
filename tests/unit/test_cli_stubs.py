"""The CLI entry points must fail loudly rather than simulate work.

Increment 0.1 ships the console scripts and nothing behind them. The risk this
file guards against is the one CLAUDE.md calls out directly: a command that
exits 0, or prints something report-shaped, and is mistaken for completed work.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from rearchive import cli as product_cli
from rearchive_bench import cli as bench_cli

MODULES = pytest.mark.parametrize(
    ("module", "commands"),
    [
        (product_cli, product_cli.COMMANDS),
        (bench_cli, bench_cli.COMMANDS),
    ],
    ids=["rearchive", "rearchive-bench"],
)


@MODULES
def test_exit_status_is_non_zero_for_every_command(
    module: object, commands: tuple[str, ...]
) -> None:
    for command in commands:
        assert module.main([command]) != 0  # type: ignore[attr-defined]
        assert module.main([command]) == module.EXIT_NOT_IMPLEMENTED  # type: ignore[attr-defined]


@MODULES
def test_nothing_is_written_to_stdout(
    module: object, commands: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    """stdout is the channel the gate reads JSON from; it must stay empty."""
    for command in commands:
        module.main([command])  # type: ignore[attr-defined]
        captured = capsys.readouterr()
        assert captured.out == "", f"{command} wrote to stdout: {captured.out!r}"
        assert "not implemented" in captured.err.lower()


@MODULES
def test_stdout_is_not_parseable_as_json(
    module: object, commands: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    """A caller doing json.loads(stdout) must fail, not read a fake report."""
    for command in commands:
        module.main([command])  # type: ignore[attr-defined]
        with pytest.raises(json.JSONDecodeError):
            json.loads(capsys.readouterr().out)


@MODULES
def test_unknown_commands_are_a_usage_error(module: object, commands: tuple[str, ...]) -> None:
    del commands
    with pytest.raises(SystemExit) as excinfo:
        module.main(["definitely-not-a-command"])  # type: ignore[attr-defined]
    assert excinfo.value.code == 2


@MODULES
def test_exit_code_is_distinct_from_the_usage_error_code(
    module: object, commands: tuple[str, ...]
) -> None:
    del commands
    assert module.EXIT_NOT_IMPLEMENTED != 2  # type: ignore[attr-defined]
    assert module.EXIT_NOT_IMPLEMENTED != 0  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("module_path", "command"),
    [("rearchive.cli", "init"), ("rearchive_bench.cli", "generate")],
)
def test_running_the_module_propagates_the_exit_status(module_path: str, command: str) -> None:
    """The process exit status, not just the return value, must be non-zero."""
    proc = subprocess.run(
        [sys.executable, "-m", module_path, command],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "not implemented" in proc.stderr.lower()


@pytest.mark.parametrize("script", ["rearchive", "rearchive-bench"])
def test_console_scripts_are_installed(script: str) -> None:
    """The Gate A suite invokes these by name, so they must be on PATH."""
    assert shutil.which(script) is not None, (
        f"{script} is not on PATH; `uv sync` should install the console script"
    )


@pytest.mark.parametrize(
    ("script", "command"), [("rearchive", "report"), ("rearchive-bench", "score")]
)
def test_console_scripts_exit_non_zero(script: str, command: str) -> None:
    executable = shutil.which(script)
    assert executable is not None
    proc = subprocess.run([executable, command], capture_output=True, text=True, check=False)
    assert proc.returncode != 0
    assert proc.stdout == ""


def test_the_declared_command_surface_matches_the_gate_contract() -> None:
    """Keep the stub surface aligned with tests/acceptance/test_gate_a.py.

    This PARSES the gate's CLI-contract header rather than restating it, so
    adding a command there really does fail this test until the stub knows about
    it. An earlier version hard-coded the two sets and only claimed to enforce
    alignment; that claim was false, because nothing read the gate at all.

    The gate file is read, never written: it is the human-owned contract.
    """
    gate = Path(__file__).resolve().parents[1] / "acceptance" / "test_gate_a.py"
    contract = gate.read_text(encoding="utf-8").split('"""')[1]

    product: set[str] = set()
    bench: set[str] = set()
    for line in contract.splitlines():
        match = re.match(r"(rearchive-bench|rearchive)\s+([a-z][a-z0-9-]*)", line.strip())
        if match is None:
            continue
        (bench if match.group(1) == "rearchive-bench" else product).add(match.group(2))

    assert product, f"no `rearchive <cmd>` lines found in {gate}; contract format changed?"
    assert bench, f"no `rearchive-bench <cmd>` lines found in {gate}; format changed?"
    assert set(product_cli.COMMANDS) == product, (
        f"stub commands {sorted(product_cli.COMMANDS)} != gate contract {sorted(product)}"
    )
    assert set(bench_cli.COMMANDS) == bench, (
        f"stub commands {sorted(bench_cli.COMMANDS)} != gate contract {sorted(bench)}"
    )


def test_the_benchmark_cli_does_not_import_the_product() -> None:
    """D-012 at module level; the gate also checks this by AST scan."""
    source = __import__("inspect").getsource(bench_cli)
    assert "import rearchive\n" not in source
    assert "from rearchive " not in source
    assert "from rearchive." not in source
