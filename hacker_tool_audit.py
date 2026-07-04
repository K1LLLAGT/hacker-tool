#!/usr/bin/env python3
"""hacker-tool structural audit.

Single-file, standard-library-only auditor for the ``~/hacker-tool``
project.  In one pass it:

* recursively scans the project tree,
* detects skeleton (empty / stub) modules,
* fills skeletons and missing files with real implementations,
* creates any missing directories and starter files,
* auto-generates ``unittest`` test files for every module,
* applies safe PEP-8 normalisation (whitespace, tabs, blank lines,
  a conservative leading-import sorter),
* prepares the codebase for mypy and writes ``mypy.ini``,
* builds Markdown documentation stubs, and
* generates an argparse CLI wired to every module.

The tool is deterministic and conservative: it never overwrites a
real, hand-written file.  It only replaces files that are detected as
skeletons or that carry the ``# hacker-tool:generated`` marker, and it
backs up anything it overwrites under ``.audit-backups/``.

Usage::

    python hacker_tool_audit.py                 # audit ~/hacker-tool
    python hacker_tool_audit.py --root ./demo   # audit another tree
    python hacker_tool_audit.py --dry-run       # preview only
"""
from __future__ import annotations

import argparse
import ast
import io
import os
import shutil
import sys
import tokenize
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PY_MARKER = "# hacker-tool:generated"
MD_MARKER = "<!-- hacker-tool:generated -->"
LINE_LIMIT = 79

# Absolute path to this audit script, so it never formats or audits
# itself when it happens to live inside the project being audited.
try:
    SELF_PATH: Optional[Path] = Path(__file__).resolve()
except NameError:  # pragma: no cover - __file__ always defined here
    SELF_PATH = None

# Directories that must exist under the project root.
EXPECTED_DIRS: tuple[str, ...] = (
    "core",
    "modules",
    "modules/fs",
    "modules/net",
    "modules/project",
    "modules/report",
    "modules/sync",
    "modules/web",
    "data",
    "reports",
    "workspaces",
    "workspaces/local",
    "workspaces/remote",
    "tests",
    "docs",
)

# Empty directories that should carry a keep-file so they persist.
KEEP_DIRS: tuple[str, ...] = (
    "data",
    "reports",
    "workspaces/local",
    "workspaces/remote",
)

CONFIG_YML = """# hacker-tool configuration
project: hacker-tool
log_level: INFO
storage: data/store.sqlite3
workspaces:
  local: workspaces/local
  remote: workspaces/remote
"""

MYPY_INI = """[mypy]
python_version = 3.13
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
ignore_missing_imports = True
"""


# ---------------------------------------------------------------------------
# Module implementation templates
#
# Stored WITHOUT the generated marker; ``_render_py`` prepends it.  Each
# template is a complete, working module with docstrings, type hints,
# error handling, logging where appropriate and deterministic output.
# ---------------------------------------------------------------------------

MODULE_TEMPLATES: dict[str, str] = {}

MODULE_TEMPLATES["core/__init__.py"] = '''"""Core package: config, logging and storage helpers."""
from __future__ import annotations

__all__: list[str] = ["config", "logging_setup", "storage"]
'''

MODULE_TEMPLATES["modules/__init__.py"] = '''"""Feature modules for the hacker-tool project."""
from __future__ import annotations

__all__: list[str] = [
    "fs",
    "net",
    "project",
    "report",
    "sync",
    "web",
]
'''

for _pkg in ("fs", "net", "project", "report", "sync", "web"):
    MODULE_TEMPLATES[f"modules/{_pkg}/__init__.py"] = (
        f'"""The {_pkg} feature module."""\n'
        "from __future__ import annotations\n"
        "\n"
        "__all__: list[str] = []\n"
    )

MODULE_TEMPLATES["core/config.py"] = '''"""Configuration loading for the hacker-tool project.

A small, dependency-free loader that understands JSON as well as a
restricted, deterministic subset of YAML (comments, ``key: value``
pairs and indentation-based nested mappings).  It is intentionally not
a general YAML implementation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "project": "hacker-tool",
    "log_level": "INFO",
    "storage": "data/store.sqlite3",
    "workspaces": {
        "local": "workspaces/local",
        "remote": "workspaces/remote",
    },
}


class ConfigError(Exception):
    """Raised when a configuration file cannot be parsed."""


def _coerce(value: str) -> Any:
    """Convert a scalar string into an int, float, bool, None or str."""
    text = value.strip()
    lowered = text.lower()
    if text == "" or lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    if len(text) >= 2 and text[0] in "\\"'" and text[-1] == text[0]:
        return text[1:-1]
    return text


def _parse_yaml(text: str) -> dict[str, Any]:
    """Parse a restricted subset of YAML into nested dictionaries."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, sep, value = line.strip().partition(":")
        if not sep:
            raise ConfigError(f"Malformed line: {raw!r}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ConfigError("Invalid indentation structure")
        parent = stack[-1][1]
        key = key.strip()
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce(value)
    return root


def load_config(path: str | Path) -> dict[str, Any]:
    """Load configuration from *path*.

    JSON is attempted first, then the minimal YAML parser.  A missing
    file yields a copy of :data:`DEFAULT_CONFIG`.
    """
    target = Path(path)
    if not target.exists():
        return dict(DEFAULT_CONFIG)
    raw = target.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return _parse_yaml(raw)
'''

MODULE_TEMPLATES["core/logging_setup.py"] = '''"""Logging configuration helpers."""
from __future__ import annotations

import logging

_CONFIGURED = False


def setup_logging(level: str = "INFO",
                  name: str = "hacker-tool") -> logging.Logger:
    """Return a configured :class:`logging.Logger`.

    The root stream handler is installed only once, so repeated calls
    are idempotent and therefore deterministic.
    """
    global _CONFIGURED
    logger = logging.getLogger(name)
    numeric = getattr(logging, str(level).upper(), logging.INFO)
    logger.setLevel(numeric)
    if not _CONFIGURED:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(handler)
        _CONFIGURED = True
    return logger
'''

MODULE_TEMPLATES["core/storage.py"] = '''"""A tiny persistent key/value store built on :mod:`sqlite3`."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator


class Storage:
    """Deterministic key/value storage backed by SQLite."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS kv ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()

    def set(self, key: str, value: Any) -> None:
        """Store *value* (JSON-encoded) under *key*."""
        payload = json.dumps(value, sort_keys=True)
        self._conn.execute(
            "INSERT INTO kv(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, payload),
        )
        self._conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value stored under *key* or *default*."""
        row = self._conn.execute(
            "SELECT value FROM kv WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def items(self) -> Iterator[tuple[str, Any]]:
        """Yield ``(key, value)`` pairs ordered by key."""
        cursor = self._conn.execute(
            "SELECT key, value FROM kv ORDER BY key ASC"
        )
        for key, value in cursor.fetchall():
            yield key, json.loads(value)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
'''

MODULE_TEMPLATES["modules/fs/manifest.py"] = '''"""Filesystem manifest building.

Builds a deterministic manifest of a directory tree, recording the
relative path, size and SHA-256 digest of every regular file.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def _hash_file(path: Path, chunk: int = 65536) -> str:
    """Return the SHA-256 hex digest of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root: str | Path) -> dict[str, Any]:
    """Return a deterministic manifest for *root*.

    The ``files`` list is sorted by path so repeated runs over an
    unchanged tree produce identical output.
    """
    base = Path(root)
    if not base.is_dir():
        raise NotADirectoryError(f"{base} is not a directory")
    entries: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            entries.append({
                "path": path.relative_to(base).as_posix(),
                "size": path.stat().st_size,
                "sha256": _hash_file(path),
            })
    return {
        "root": base.as_posix(),
        "count": len(entries),
        "files": entries,
    }
'''

MODULE_TEMPLATES["modules/net/reachability.py"] = '''"""Network reachability checks.

Simple TCP connection probes.  Network access is optional and unit
tests mock :func:`socket.create_connection`, so importing this module
never performs I/O.
"""
from __future__ import annotations

import socket


def is_valid_port(port: int) -> bool:
    """Return ``True`` when *port* is within the valid TCP range."""
    return isinstance(port, int) and 0 < port < 65536


def check_host(host: str, port: int = 80,
               timeout: float = 3.0) -> bool:
    """Return ``True`` if a TCP connection to *host:port* succeeds."""
    if not is_valid_port(port):
        raise ValueError(f"Invalid port: {port}")
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
'''

MODULE_TEMPLATES["modules/project/scanner.py"] = '''"""Project scanning utilities.

Produces a deterministic summary of a source tree, counting files by
extension and reporting the total size.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


def scan_project(root: str | Path) -> dict[str, Any]:
    """Return a deterministic summary of *root*."""
    base = Path(root)
    if not base.is_dir():
        raise NotADirectoryError(f"{base} is not a directory")
    by_ext: Counter[str] = Counter()
    total_size = 0
    file_count = 0
    for path in base.rglob("*"):
        if path.is_file():
            file_count += 1
            total_size += path.stat().st_size
            by_ext[path.suffix or "<none>"] += 1
    return {
        "root": base.as_posix(),
        "files": file_count,
        "total_size": total_size,
        "by_extension": dict(sorted(by_ext.items())),
    }
'''

MODULE_TEMPLATES["modules/report/generator.py"] = '''"""Report generation.

Turns a summary mapping into a deterministic Markdown report.
"""
from __future__ import annotations

from typing import Any, Mapping


def generate_report(data: Mapping[str, Any],
                    title: str = "Report") -> str:
    """Render *data* as a Markdown document.

    Keys are emitted in sorted order to guarantee determinism.
    """
    lines: list[str] = [f"# {title}", ""]
    for key in sorted(data):
        lines.append(f"- **{key}**: {data[key]}")
    lines.append("")
    return "\\n".join(lines)
'''

MODULE_TEMPLATES["modules/sync/commands.py"] = '''"""Workspace synchronisation commands.

Copies new or changed files from a source workspace to a destination
workspace on the local filesystem.  No network access is performed.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def sync_workspaces(source: str | Path,
                    dest: str | Path) -> dict[str, Any]:
    """Copy new or changed files from *source* into *dest*.

    Returns a deterministic summary listing the copied relative paths.
    """
    src = Path(source)
    dst = Path(dest)
    if not src.is_dir():
        raise NotADirectoryError(f"{src} is not a directory")
    dst.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(src.rglob("*")):
        if path.is_file():
            rel = path.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            changed = (not target.exists() or
                       target.stat().st_size != path.stat().st_size)
            if changed:
                shutil.copy2(path, target)
                copied.append(rel.as_posix())
    return {
        "source": src.as_posix(),
        "dest": dst.as_posix(),
        "copied": copied,
    }
'''

MODULE_TEMPLATES["modules/web/checks.py"] = '''"""Web checks.

A small HTTP status probe together with pure helpers that can be unit
tested without network access.
"""
from __future__ import annotations

import urllib.error
import urllib.request
from typing import Optional


def classify_status(code: int) -> str:
    """Classify an HTTP status *code* into a coarse category."""
    if 200 <= code < 300:
        return "success"
    if 300 <= code < 400:
        return "redirect"
    if 400 <= code < 500:
        return "client-error"
    if 500 <= code < 600:
        return "server-error"
    return "unknown"


def check_url(url: str, timeout: float = 5.0) -> Optional[int]:
    """Return the HTTP status code for *url* or ``None`` on failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return int(resp.status)
    except (urllib.error.URLError, ValueError):
        return None
'''


# ---------------------------------------------------------------------------
# Test bodies (imports + test classes).  ``_render_test`` wraps these in
# a common header and footer.  Keyed by module relative path.
# ---------------------------------------------------------------------------

TEST_BODIES: dict[str, str] = {}

TEST_BODIES["core/config.py"] = '''import tempfile

from core import config


class TestConfig(unittest.TestCase):
    def test_missing_returns_defaults(self) -> None:
        data = config.load_config("/no/such/file.yml")
        self.assertEqual(data["project"], "hacker-tool")

    def test_yaml_roundtrip(self) -> None:
        text = "project: demo\\nnested:\\n  count: 3\\n  flag: true\\n"
        with tempfile.NamedTemporaryFile(
                "w", suffix=".yml", delete=False) as handle:
            handle.write(text)
            name = handle.name
        try:
            data = config.load_config(name)
            self.assertEqual(data["project"], "demo")
            self.assertEqual(data["nested"]["count"], 3)
            self.assertIs(data["nested"]["flag"], True)
        finally:
            os.unlink(name)
'''

TEST_BODIES["core/logging_setup.py"] = '''import logging

from core import logging_setup


class TestLoggingSetup(unittest.TestCase):
    def test_returns_logger(self) -> None:
        log = logging_setup.setup_logging("DEBUG", "unit-test")
        self.assertIsInstance(log, logging.Logger)
        self.assertEqual(log.level, logging.DEBUG)

    def test_idempotent(self) -> None:
        logging_setup.setup_logging()
        before = len(logging.getLogger().handlers)
        logging_setup.setup_logging()
        after = len(logging.getLogger().handlers)
        self.assertEqual(before, after)
'''

TEST_BODIES["core/storage.py"] = '''from core.storage import Storage


class TestStorage(unittest.TestCase):
    def test_set_and_get(self) -> None:
        store = Storage(":memory:")
        store.set("alpha", {"n": 1})
        self.assertEqual(store.get("alpha"), {"n": 1})
        self.assertIsNone(store.get("missing"))
        store.close()

    def test_items_sorted(self) -> None:
        store = Storage(":memory:")
        store.set("b", 2)
        store.set("a", 1)
        keys = [key for key, _ in store.items()]
        self.assertEqual(keys, ["a", "b"])
        store.close()
'''

TEST_BODIES["modules/fs/manifest.py"] = '''import tempfile

from modules.fs import manifest


class TestManifest(unittest.TestCase):
    def test_build(self) -> None:
        base = tempfile.mkdtemp()
        with open(os.path.join(base, "a.txt"), "w") as handle:
            handle.write("hello")
        result = manifest.build_manifest(base)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["files"][0]["path"], "a.txt")
        self.assertEqual(len(result["files"][0]["sha256"]), 64)

    def test_deterministic(self) -> None:
        base = tempfile.mkdtemp()
        with open(os.path.join(base, "a.txt"), "w") as handle:
            handle.write("data")
        self.assertEqual(manifest.build_manifest(base),
                         manifest.build_manifest(base))
'''

TEST_BODIES["modules/net/reachability.py"] = '''from unittest import mock

from modules.net import reachability


class TestReachability(unittest.TestCase):
    def test_valid_port(self) -> None:
        self.assertTrue(reachability.is_valid_port(80))
        self.assertFalse(reachability.is_valid_port(0))
        self.assertFalse(reachability.is_valid_port(70000))

    def test_check_host_success(self) -> None:
        with mock.patch("socket.create_connection"):
            self.assertTrue(reachability.check_host("example", 80))

    def test_check_host_failure(self) -> None:
        with mock.patch("socket.create_connection",
                        side_effect=OSError):
            self.assertFalse(reachability.check_host("example", 80))

    def test_invalid_port_raises(self) -> None:
        with self.assertRaises(ValueError):
            reachability.check_host("example", 0)
'''

TEST_BODIES["modules/project/scanner.py"] = '''import tempfile

from modules.project import scanner


class TestScanner(unittest.TestCase):
    def test_scan(self) -> None:
        base = tempfile.mkdtemp()
        with open(os.path.join(base, "a.py"), "w") as handle:
            handle.write("x = 1\\n")
        result = scanner.scan_project(base)
        self.assertEqual(result["files"], 1)
        self.assertIn(".py", result["by_extension"])
'''

TEST_BODIES["modules/report/generator.py"] = '''from modules.report import generator


class TestGenerator(unittest.TestCase):
    def test_markdown(self) -> None:
        out = generator.generate_report({"b": 2, "a": 1}, "Title")
        self.assertIn("# Title", out)
        self.assertLess(out.index("**a**"), out.index("**b**"))
'''

TEST_BODIES["modules/sync/commands.py"] = '''import tempfile

from modules.sync import commands


class TestSync(unittest.TestCase):
    def test_sync(self) -> None:
        src = tempfile.mkdtemp()
        dst = tempfile.mkdtemp()
        with open(os.path.join(src, "f.txt"), "w") as handle:
            handle.write("hi")
        result = commands.sync_workspaces(src, dst)
        self.assertIn("f.txt", result["copied"])
        self.assertTrue(os.path.exists(os.path.join(dst, "f.txt")))
'''

TEST_BODIES["modules/web/checks.py"] = '''import urllib.error
from unittest import mock

from modules.web import checks


class TestChecks(unittest.TestCase):
    def test_classify(self) -> None:
        self.assertEqual(checks.classify_status(204), "success")
        self.assertEqual(checks.classify_status(301), "redirect")
        self.assertEqual(checks.classify_status(404), "client-error")
        self.assertEqual(checks.classify_status(503), "server-error")
        self.assertEqual(checks.classify_status(999), "unknown")

    def test_check_url(self) -> None:
        response = mock.MagicMock()
        response.status = 200
        ctx = mock.MagicMock()
        ctx.__enter__.return_value = response
        with mock.patch("urllib.request.urlopen", return_value=ctx):
            self.assertEqual(checks.check_url("http://example"), 200)

    def test_check_url_failure(self) -> None:
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("x")):
            self.assertIsNone(checks.check_url("http://example"))
'''

TEST_HEADER = (
    "import os\n"
    "import sys\n"
    "import unittest\n"
    "\n"
    "ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
    "if ROOT not in sys.path:\n"
    "    sys.path.insert(0, ROOT)\n"
    "\n\n"
)

TEST_FOOTER = '\n\nif __name__ == "__main__":\n    unittest.main()\n'


# ---------------------------------------------------------------------------
# CLI template
# ---------------------------------------------------------------------------

CLI_TEMPLATE = '''"""Command line interface for the hacker-tool project.

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
'''


# ---------------------------------------------------------------------------
# Audit report
# ---------------------------------------------------------------------------

@dataclass
class AuditReport:
    """Collects everything the audit did, for the final summary."""

    root: Path
    dry_run: bool
    stamp: str = ""
    scanned: list[str] = field(default_factory=list)
    skeletons: list[tuple[str, list[str]]] = field(default_factory=list)
    generated: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    dirs_created: list[str] = field(default_factory=list)
    tests_created: list[str] = field(default_factory=list)
    docs_created: list[str] = field(default_factory=list)
    cli_actions: list[str] = field(default_factory=list)
    format_changes: list[tuple[str, list[str]]] = field(
        default_factory=list)
    type_notes: list[tuple[str, list[str]]] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Skeleton detection
# ---------------------------------------------------------------------------

def _is_not_implemented(node: ast.Raise) -> bool:
    """Return ``True`` if *node* raises ``NotImplementedError``."""
    exc = node.exc
    if isinstance(exc, ast.Call):
        exc = exc.func
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def _is_trivial_body(body: list[ast.stmt]) -> bool:
    """Return ``True`` when a def/class body contains no real logic."""
    for node in body:
        if isinstance(node, ast.Expr) and isinstance(
                node.value, ast.Constant):
            continue  # docstring or bare constant
        if isinstance(node, ast.Pass):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Raise) and _is_not_implemented(node):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            if _is_trivial_body(node.body):
                continue
            return False
        return False
    return True


def is_skeleton(text: str) -> tuple[bool, list[str]]:
    """Classify *text* as a skeleton and return contributing reasons.

    A file is a skeleton when it contains no executable logic: only
    imports, docstrings, empty defs/classes, ``pass`` or
    ``NotImplementedError`` raises.  A stray TODO/FIXME marker is
    reported but never on its own forces a rewrite, so real files with
    a lingering TODO are protected.
    """
    reasons: list[str] = []
    if text.strip() == "":
        return True, ["empty file"]
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False, ["unparseable (left untouched)"]

    has_real_logic = False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(
                node.value, ast.Constant):
            continue  # module docstring
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            if not _is_trivial_body(node.body):
                has_real_logic = True
            continue
        has_real_logic = True  # assignment, call, if, for, ...

    if not has_real_logic:
        reasons.append("no executable logic")
    lowered = text.lower()
    for marker in ("todo", "fixme", "placeholder", "xxx"):
        if marker in lowered:
            reasons.append(f"contains {marker.upper()} marker")
            break
    return (not has_real_logic), reasons


# ---------------------------------------------------------------------------
# Safe PEP-8 formatter
# ---------------------------------------------------------------------------

def _protected_lines(text: str) -> set[int]:
    """Return 1-based line numbers that fall inside string literals."""
    protected: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.STRING or (
                    hasattr(tokenize, "FSTRING_MIDDLE")
                    and tok.type == tokenize.FSTRING_MIDDLE):
                for ln in range(tok.start[0], tok.end[0] + 1):
                    protected.add(ln)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return protected


def format_python(text: str) -> tuple[str, list[str]]:
    """Apply safe PEP-8 normalisation, returning text and change notes.

    Only whitespace-level, string-safe transforms are performed:
    leading tabs to spaces, trailing whitespace removal, collapsing
    3+ blank lines to 2 and a single trailing newline.  Over-long
    lines are reported but never auto-wrapped (that risks breaking
    code); generated files already respect the 79-column limit.
    """
    notes: list[str] = []
    try:
        ast.parse(text)
    except SyntaxError:
        return text, ["skipped formatting (syntax error)"]

    protected = _protected_lines(text)
    lines = text.split("\n")
    processed: list[str] = []
    tab_fixes = 0
    trail_fixes = 0

    for number, line in enumerate(lines, start=1):
        if number in protected:
            processed.append(line)
            continue
        new_line = line
        leading = len(new_line) - len(new_line.lstrip())
        head = new_line[:leading]
        if "\t" in head:
            new_line = head.replace("\t", "    ") + new_line[leading:]
            tab_fixes += 1
        stripped = new_line.rstrip()
        if stripped != new_line:
            trail_fixes += 1
        processed.append(stripped)

    # Collapse 3+ consecutive blank (unprotected) lines to 2.
    collapsed: list[str] = []
    blank_run = 0
    for number, line in enumerate(processed, start=1):
        is_blank = (line.strip() == "" and number not in protected)
        if is_blank:
            blank_run += 1
            if blank_run > 2:
                continue
        else:
            blank_run = 0
        collapsed.append(line)

    long_lines = sum(
        1 for number, line in enumerate(processed, start=1)
        if len(line) > LINE_LIMIT and number not in protected
    )

    result = "\n".join(collapsed).rstrip("\n") + "\n"
    if tab_fixes:
        notes.append(f"converted leading tabs on {tab_fixes} line(s)")
    if trail_fixes:
        notes.append(f"stripped trailing whitespace on {trail_fixes} "
                     "line(s)")
    if long_lines:
        notes.append(f"{long_lines} line(s) exceed {LINE_LIMIT} chars "
                     "(reported, not auto-wrapped)")
    return result, notes


def sort_imports(text: str) -> tuple[str, bool]:
    """Conservatively sort the leading contiguous import block.

    Only a clean run of single-line, top-level imports (optionally
    after the module docstring) is touched.  Anything unusual - a
    blank line, comment, decorator, parenthesised or continued import
    inside the block - aborts the transform, so semantics are never
    changed by reordering side-effecting imports.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text, False

    body = tree.body
    index = 0
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        index = 1
    start = index
    while index < len(body) and isinstance(
            body[index], (ast.Import, ast.ImportFrom)):
        index += 1
    block = body[start:index]
    if len(block) < 2:
        return text, False

    first_line = block[0].lineno
    last_line = block[-1].end_lineno or block[-1].lineno
    lines = text.split("\n")
    segment = lines[first_line - 1:last_line]
    for line in segment:
        stripped = line.strip()
        if stripped == "" or stripped.startswith(("#", "@")):
            return text, False
        if line.rstrip().endswith("\\"):
            return text, False
    for node in block:
        if (node.end_lineno or node.lineno) != node.lineno:
            return text, False

    def key_name(node: ast.stmt) -> str:
        if isinstance(node, ast.ImportFrom):
            return node.module or ""
        assert isinstance(node, ast.Import)
        return node.names[0].name

    def group(node: ast.stmt) -> int:
        top = key_name(node).split(".")[0]
        if top == "__future__":
            return 0
        if top in sys.stdlib_module_names:
            return 1
        return 2

    paired = list(zip(block, segment))
    paired.sort(key=lambda pair: (
        group(pair[0]),
        key_name(pair[0]).lower(),
        isinstance(pair[0], ast.ImportFrom),
    ))
    new_segment = [line for _, line in paired]
    if new_segment == segment:
        return text, False

    new_lines = lines[:first_line - 1] + new_segment + lines[last_line:]
    new_text = "\n".join(new_lines)
    try:
        ast.parse(new_text)
    except SyntaxError:
        return text, False
    return new_text, True


# ---------------------------------------------------------------------------
# Type-annotation reporting
# ---------------------------------------------------------------------------

def annotation_gaps(text: str) -> list[str]:
    """Return human-readable notes for functions missing annotations."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    gaps: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is None:
                gaps.append(f"{node.name}: missing return annotation")
            for arg in node.args.args:
                if arg.arg in ("self", "cls"):
                    continue
                if arg.annotation is None:
                    gaps.append(
                        f"{node.name}({arg.arg}): missing annotation")
    return gaps


# ---------------------------------------------------------------------------
# Documentation generation
# ---------------------------------------------------------------------------

def _signature(node: ast.stmt) -> str:
    """Render a compact, annotation-aware signature for a def."""
    assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    args = node.args
    parts: list[str] = []
    for arg in list(getattr(args, "posonlyargs", [])) + list(args.args):
        if arg.arg in ("self", "cls"):
            continue
        annotation = (f": {ast.unparse(arg.annotation)}"
                      if arg.annotation else "")
        parts.append(arg.arg + annotation)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{node.name}({', '.join(parts)}){returns}"


def _usage_bits(relpath: str,
                functions: list[ast.stmt]) -> tuple[str, str, Optional[str]]:
    """Return (import statement, module alias, first public function)."""
    parts = relpath[:-3].split("/")
    module = parts[-1]
    if module == "__init__":
        dotted = ".".join(parts[:-1])
        return f"import {dotted}", parts[-2], None
    package = ".".join(parts[:-1])
    statement = (f"from {package} import {module}"
                 if package else f"import {module}")
    first: Optional[str] = None
    for node in functions:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                first = node.name
                break
    return statement, module, first


def generate_doc(relpath: str, text: str) -> str:
    """Build a deterministic Markdown documentation stub for a module."""
    try:
        tree: Optional[ast.Module] = ast.parse(text)
    except SyntaxError:
        tree = None

    lines: list[str] = [MD_MARKER, f"# {relpath}", ""]
    docstring = ast.get_docstring(tree) if tree else None
    lines.append("## Overview")
    lines.append("")
    lines.append(docstring.strip() if docstring
                 else "No module description available.")
    lines.append("")

    classes: list[ast.ClassDef] = []
    functions: list[ast.stmt] = []
    if tree:
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)

    if classes:
        lines.append("## Key classes")
        lines.append("")
        for cls in classes:
            lines.append(f"### `{cls.name}`")
            cls_doc = ast.get_docstring(cls)
            lines.append(cls_doc.strip() if cls_doc
                         else "No description available.")
            for member in cls.body:
                if isinstance(member, (ast.FunctionDef,
                                       ast.AsyncFunctionDef)):
                    lines.append(f"- `{_signature(member)}`")
            lines.append("")

    if functions:
        lines.append("## Key functions")
        lines.append("")
        for func in functions:
            lines.append(f"### `{_signature(func)}`")
            func_doc = ast.get_docstring(func)
            summary = (func_doc.strip().splitlines()[0]
                       if func_doc else "No description available.")
            lines.append(summary)
            lines.append("")

    lines.append("## Usage")
    lines.append("")
    lines.append("```python")
    statement, alias, first = _usage_bits(relpath, functions)
    lines.append(statement)
    if first:
        lines.append("")
        lines.append(f"result = {alias}.{first}(...)")
        lines.append("print(result)")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _render_py(body: str) -> str:
    """Prepend the generated marker to a Python module body."""
    return f"{PY_MARKER}\n{body}"


def _render_test(report: AuditReport, relpath: str) -> str:
    """Return a full test file for the module at *relpath*.

    A rich, hand-written test body is only used when the target module
    is one this tool generated (identified by the marker).  A real
    user module that merely shares a canonical filename gets a safe
    import smoke-test instead, so the suite never asserts against an
    API the user's code does not actually provide.
    """
    module_path = report.root / relpath
    generated = False
    if module_path.exists():
        try:
            generated = _has_marker(
                module_path.read_text(encoding="utf-8"))
        except OSError:
            generated = False
    body = TEST_BODIES.get(relpath) if generated else None
    if body is None:
        statement, alias, _ = _usage_bits(relpath, [])
        body = (
            f"{statement}\n\n\n"
            "class TestGenerated(unittest.TestCase):\n"
            "    def test_importable(self) -> None:\n"
            f"        self.assertIsNotNone({alias})\n"
        )
    return _render_py(TEST_HEADER + body + TEST_FOOTER)


def _has_marker(text: str) -> bool:
    """Return ``True`` if *text* carries the generated marker."""
    head = text.lstrip().splitlines()[:2]
    return any(line.strip() == PY_MARKER
               or line.strip() == MD_MARKER for line in head)


def _flatten(relpath: str) -> str:
    """Turn ``modules/fs/manifest.py`` into ``modules_fs_manifest``."""
    return relpath[:-3].replace("/", "_")


def _commit(path: Path, content: str, report: AuditReport) -> None:
    """Write *content* to *path*, backing up any existing file."""
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if old == content:
            return
        _backup(path, report)
    if not report.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _backup(path: Path, report: AuditReport) -> None:
    """Copy *path* into the timestamped backup directory."""
    rel = path.relative_to(report.root)
    dest = report.root / ".audit-backups" / report.stamp / rel
    if not report.dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    report.backups.append(rel.as_posix())


# ---------------------------------------------------------------------------
# Audit phases
# ---------------------------------------------------------------------------

def phase_scan(report: AuditReport) -> None:
    """Record every file currently present under the root."""
    for path in sorted(report.root.rglob("*")):
        if path.is_file() and ".audit-backups" not in path.parts:
            report.scanned.append(
                path.relative_to(report.root).as_posix())


def phase_dirs(report: AuditReport) -> None:
    """Create any missing expected directories and keep-files."""
    for rel in EXPECTED_DIRS:
        target = report.root / rel
        if not target.exists():
            if not report.dry_run:
                target.mkdir(parents=True, exist_ok=True)
            report.dirs_created.append(rel)
    for rel in KEEP_DIRS:
        keep = report.root / rel / ".gitkeep"
        if not keep.exists() and not report.dry_run:
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_text("", encoding="utf-8")


def phase_config(report: AuditReport) -> None:
    """Create config.yml and mypy.ini when missing."""
    config_path = report.root / "config.yml"
    if not config_path.exists():
        if not report.dry_run:
            config_path.write_text(CONFIG_YML, encoding="utf-8")
        report.generated.append("config.yml")
    mypy_path = report.root / "mypy.ini"
    if not mypy_path.exists() or _safe_marker(mypy_path):
        current = (mypy_path.read_text(encoding="utf-8")
                   if mypy_path.exists() else None)
        if current != MYPY_INI:
            if not report.dry_run:
                mypy_path.write_text(MYPY_INI, encoding="utf-8")
            report.cli_actions.append("mypy.ini written")


def _safe_marker(path: Path) -> bool:
    """Return ``True`` if an existing file may be safely regenerated."""
    if not path.exists():
        return True
    try:
        return _has_marker(path.read_text(encoding="utf-8"))
    except OSError:
        return False


_PKG_DOCS: dict[str, str] = {
    "core/__init__.py":
        "Core package: config, logging and storage helpers.",
    "modules/__init__.py":
        "Feature modules for the hacker-tool project.",
}


def _package_has_real_module(pkg: Path, exclude: Path) -> bool:
    """Return ``True`` if *pkg* already holds a real implementation.

    A canonical template module is only injected into an empty package.
    If the user already implemented that area under a different filename
    (for example ``net/scan.py`` instead of ``net/reachability.py``),
    this returns ``True`` so the audit does not create a duplicate.
    """
    if not pkg.is_dir():
        return False
    for child in sorted(pkg.glob("*.py")):
        if child.name == "__init__.py" or child == exclude:
            continue
        try:
            text = child.read_text(encoding="utf-8")
        except OSError:
            continue
        skeleton, _ = is_skeleton(text)
        if not skeleton:
            return True
    return False


def _render_init(report: AuditReport, init_path: Path) -> str:
    """Render a package ``__init__.py`` from its actual contents.

    ``__all__`` reflects the sub-packages and modules genuinely present
    (plus any planned in this run, so ``--dry-run`` output is accurate),
    rather than a hard-coded canonical list.
    """
    root = report.root
    pkg = init_path.parent
    rel = init_path.relative_to(root).as_posix()
    names: set[str] = set()
    if pkg.is_dir():
        for child in pkg.iterdir():
            if child.is_dir() and (child / "__init__.py").exists():
                names.add(child.name)
            elif child.suffix == ".py" and child.name != "__init__.py":
                names.add(child.stem)
    for gen in report.generated:
        gpath = root / gen
        if gpath.name == "__init__.py":
            if gpath.parent.parent == pkg:
                names.add(gpath.parent.name)
        elif gpath.parent == pkg:
            names.add(gpath.stem)
    doc = _PKG_DOCS.get(rel, f"The {pkg.name} package.")
    body = [f'"""{doc}"""', "from __future__ import annotations", ""]
    if names:
        body.append("__all__: list[str] = [")
        body.extend(f'    "{name}",' for name in sorted(names))
        body.append("]")
    else:
        body.append("__all__: list[str] = []")
    return "\n".join(body) + "\n"


def _apply_template(report: AuditReport, relpath: str, content: str,
                    is_missing_ok: bool = True) -> None:
    """Write *content* to *relpath* respecting skeleton/marker rules."""
    path = report.root / relpath
    if not path.exists():
        if is_missing_ok:
            _commit(path, content, report)
            report.generated.append(relpath)
        return
    existing = path.read_text(encoding="utf-8")
    skeleton, reasons = is_skeleton(existing)
    if skeleton:
        report.skeletons.append((relpath, reasons))
        _commit(path, content, report)
        report.generated.append(relpath)
    elif _has_marker(existing):
        if existing != content:
            _commit(path, content, report)
            report.updated.append(relpath)
    else:
        report.skipped.append(f"{relpath} (real file, left as-is)")


def phase_modules(report: AuditReport) -> None:
    """Fill skeleton/missing modules, then render package inits."""
    root = report.root
    inits = [p for p in MODULE_TEMPLATES if p.endswith("__init__.py")]
    impls = [p for p in MODULE_TEMPLATES if not p.endswith("__init__.py")]

    # 1. Canonical implementation modules -- but never duplicate an area
    #    the user has already implemented under a different filename.
    for relpath in impls:
        path = root / relpath
        content = _render_py(MODULE_TEMPLATES[relpath])
        if not path.exists() and _package_has_real_module(path.parent,
                                                           path):
            report.skipped.append(
                f"{relpath} (package already implemented; not injected)")
            continue
        _apply_template(report, relpath, content)

    # 2. Any other skeleton .py under core/ or modules/ gets a generic
    #    fill (package __init__ files are handled separately below).
    for base in ("core", "modules"):
        base_dir = root / base
        if not base_dir.is_dir():
            continue
        for path in sorted(base_dir.rglob("*.py")):
            relpath = path.relative_to(root).as_posix()
            if relpath in MODULE_TEMPLATES or path.name == "__init__.py":
                continue
            existing = path.read_text(encoding="utf-8")
            skeleton, reasons = is_skeleton(existing)
            if skeleton and not _has_marker(existing):
                report.skeletons.append((relpath, reasons))
                _commit(path, _render_py(_generic_module(relpath)),
                        report)
                report.generated.append(relpath)

    # 3. Package __init__.py files, rendered from what now exists.
    for relpath in inits:
        content = _render_py(_render_init(report, root / relpath))
        _apply_template(report, relpath, content)


def _generic_module(relpath: str) -> str:
    """Return a deterministic generic implementation for a skeleton."""
    name = relpath[:-3].replace("/", ".")
    return (
        f'"""Generated implementation for the {name} module.\n\n'
        "This module was created by the hacker-tool audit because the\n"
        "original file was detected as a skeleton.  Replace the body\n"
        "with domain-specific logic as needed.\n"
        '"""\n'
        "from __future__ import annotations\n"
        "\n"
        "from typing import Any\n"
        "\n"
        "\n"
        "def run(payload: Any = None) -> dict[str, Any]:\n"
        '    """Return a deterministic summary of *payload*."""\n'
        '    return {"module": __name__,'
        ' "received": payload is not None}\n'
    )


def phase_tests(report: AuditReport) -> None:
    """Generate a unittest file for every implementation module."""
    modules = _implementation_modules(report)
    for relpath in modules:
        test_path = report.root / "tests" / f"test_{_flatten(relpath)}.py"
        content = _render_test(report, relpath)
        if not test_path.exists():
            _commit(test_path, content, report)
            report.tests_created.append(
                test_path.relative_to(report.root).as_posix())
        elif _safe_marker(test_path):
            if test_path.read_text(encoding="utf-8") != content:
                _commit(test_path, content, report)
                report.tests_created.append(
                    test_path.relative_to(report.root).as_posix())


def phase_docs(report: AuditReport) -> None:
    """Generate a Markdown stub for every implementation module."""
    for relpath in _implementation_modules(report):
        path = report.root / relpath
        if not path.exists():
            continue
        doc_path = report.root / "docs" / f"{_flatten(relpath)}.md"
        content = generate_doc(relpath, path.read_text(encoding="utf-8"))
        if not doc_path.exists() or _safe_marker(doc_path):
            existing = (doc_path.read_text(encoding="utf-8")
                        if doc_path.exists() else None)
            if existing != content:
                _commit(doc_path, content, report)
                report.docs_created.append(
                    doc_path.relative_to(report.root).as_posix())


def _implementation_modules(report: AuditReport) -> list[str]:
    """List non-package module paths under core/ and modules/."""
    found: list[str] = []
    for base in ("core", "modules"):
        root = report.root / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            found.append(path.relative_to(report.root).as_posix())
    return found


def phase_cli(report: AuditReport) -> None:
    """Write the argparse CLI entry point."""
    path = report.root / "cli.py"
    content = _render_py(CLI_TEMPLATE)
    if not path.exists():
        _commit(path, content, report)
        report.cli_actions.append("cli.py created")
    elif _has_marker(path.read_text(encoding="utf-8")):
        if path.read_text(encoding="utf-8") != content:
            _commit(path, content, report)
            report.cli_actions.append("cli.py updated")
    else:
        report.skipped.append("cli.py (real file, left as-is)")


def phase_format(report: AuditReport) -> None:
    """Apply safe PEP-8 normalisation and import sorting to .py files."""
    if report.dry_run:
        report.format_changes.append(
            ("(dry-run)", ["formatting preview skipped"]))
        return
    for path in sorted(report.root.rglob("*.py")):
        if ".audit-backups" in path.parts:
            continue
        if SELF_PATH is not None and path.resolve() == SELF_PATH:
            continue  # never reformat the audit tool itself
        relpath = path.relative_to(report.root).as_posix()
        try:
            original = path.read_text(encoding="utf-8")
        except OSError as exc:
            report.errors.append(f"read {relpath}: {exc}")
            continue
        sorted_text, sorted_flag = sort_imports(original)
        formatted, notes = format_python(sorted_text)
        if sorted_flag:
            notes.append("sorted leading import block")
        if formatted != original:
            _commit(path, formatted, report)  # backs up the original
            report.format_changes.append((relpath, notes or ["normalised"]))


def phase_types(report: AuditReport) -> None:
    """Report annotation gaps in pre-existing, non-generated files."""
    for path in sorted(report.root.rglob("*.py")):
        if ".audit-backups" in path.parts:
            continue
        if SELF_PATH is not None and path.resolve() == SELF_PATH:
            continue  # do not audit the audit tool itself
        relpath = path.relative_to(report.root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _has_marker(text):
            continue  # generated files are fully annotated
        gaps = annotation_gaps(text)
        if gaps:
            report.type_notes.append((relpath, gaps[:5]))


# ---------------------------------------------------------------------------
# Orchestration and reporting
# ---------------------------------------------------------------------------

def run_audit(root: Path, dry_run: bool, do_format: bool) -> AuditReport:
    """Execute every audit phase in order and return the report."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = AuditReport(root=root, dry_run=dry_run, stamp=stamp)
    root.mkdir(parents=True, exist_ok=True)

    phase_scan(report)
    phase_dirs(report)
    phase_config(report)
    phase_modules(report)
    phase_cli(report)
    phase_tests(report)
    phase_docs(report)
    if do_format:
        phase_format(report)
    phase_types(report)
    return report


def _print_section(title: str, items: list[str]) -> None:
    """Print a titled list section for the summary."""
    print(f"\n{title} ({len(items)})")
    print("-" * len(f"{title} ({len(items)})"))
    if not items:
        print("  (none)")
        return
    for item in items:
        print(f"  - {item}")


def print_summary(report: AuditReport) -> None:
    """Print the full, human-readable audit summary."""
    mode = "DRY-RUN (no changes written)" if report.dry_run else "APPLIED"
    print("=" * 70)
    print(f"hacker-tool audit summary  [{mode}]")
    print(f"root: {report.root}")
    print("=" * 70)

    _print_section("Files scanned", report.scanned)
    _print_section(
        "Skeleton files detected",
        [f"{name}: {', '.join(reasons)}"
         for name, reasons in report.skeletons],
    )
    _print_section("Files generated", report.generated)
    _print_section("Files updated", report.updated)
    _print_section("Directories created", report.dirs_created)
    _print_section("Unit tests generated", report.tests_created)
    _print_section("Documentation stubs generated", report.docs_created)
    _print_section("CLI / config actions", report.cli_actions)
    _print_section(
        "Formatting changes",
        [f"{name}: {', '.join(notes)}"
         for name, notes in report.format_changes],
    )
    _print_section(
        "Type-annotation gaps (existing files)",
        [f"{name}: {', '.join(notes)}"
         for name, notes in report.type_notes],
    )
    _print_section("Backups created", report.backups)
    _print_section("Skipped (protected real files)", report.skipped)
    if report.errors:
        _print_section("Errors", report.errors)

    print("\n" + "=" * 70)
    print("Done. Next steps you can run inside the project root:")
    print("  python -m unittest discover -s tests")
    print("  python cli.py --help")
    print("=" * 70)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments for the audit tool."""
    parser = argparse.ArgumentParser(
        description="Structural audit for the hacker-tool project.",
    )
    parser.add_argument(
        "--root", default="~/hacker-tool",
        help="Project root to audit (default: ~/hacker-tool).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview actions without writing anything.",
    )
    parser.add_argument(
        "--no-format", action="store_true",
        help="Skip the PEP-8 formatting phase.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Program entry point."""
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    try:
        report = run_audit(
            root=root,
            dry_run=args.dry_run,
            do_format=not args.no_format,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"fatal: {exc}", file=sys.stderr)
        return 1
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

