# hacker-tool:generated
"""Command line interface for the hacker-tool project.

Subcommands are discovered automatically from the modules present under
``core/`` and ``modules/`` -- the CLI adapts to whatever files exist
rather than assuming a fixed layout.  A module opts in to a real command
by exposing a callable ``main(argv)``; that callable is invoked with any
extra command-line arguments.  Modules without a ``main`` are still
listed, and running their subcommand prints their public functions so
the available surface is discoverable.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def discover_modules() -> list[str]:
    """Return dotted names of implementation modules in the project.

    Packages (``__init__.py``) and the audit/CLI scripts themselves are
    excluded.  Discovery is purely filesystem based, so no project code
    is imported until a subcommand actually runs.
    """
    names: list[str] = []
    for package in ("core", "modules"):
        base = ROOT / package
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            rel = path.relative_to(ROOT).with_suffix("")
            names.append(".".join(rel.parts))
    return sorted(names)


def command_name(dotted: str) -> str:
    """Turn ``modules.net.scan`` into the CLI name ``net-scan``."""
    parts = dotted.split(".")
    if parts and parts[0] == "modules":
        parts = parts[1:]
    return "-".join(parts)


def public_functions(module: Any) -> dict[str, str]:
    """Map public function names defined in *module* to signatures."""
    functions: dict[str, str] = {}
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_"):
            continue
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        functions[name] = str(inspect.signature(obj))
    return functions


def run_module(dotted: str, extra: list[str]) -> int:
    """Import *dotted* and run ``main(extra)`` or describe its API."""
    try:
        module = importlib.import_module(dotted)
    except Exception as exc:  # noqa: BLE001
        print(f"error importing {dotted}: {exc}", file=sys.stderr)
        return 1
    entry: Optional[Callable[..., Any]] = getattr(module, "main", None)
    if callable(entry):
        try:
            result = entry(extra)
        except TypeError:
            result = entry()
        return int(result) if isinstance(result, int) else 0
    info = {"module": dotted, "functions": public_functions(module)}
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level parser with one subcommand per module."""
    parser = argparse.ArgumentParser(
        prog="hacker-tool",
        description="Auto-discovered commands for the hacker-tool "
                    "project.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for dotted in discover_modules():
        child = sub.add_parser(
            command_name(dotted), help=f"Run or describe {dotted}.")
        child.add_argument(
            "args", nargs=argparse.REMAINDER,
            help="Arguments forwarded to the module's main(argv).")
        child.set_defaults(dotted=dotted)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point: parse arguments and dispatch to a module."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_module(args.dotted, list(args.args))


if __name__ == "__main__":
    raise SystemExit(main())
