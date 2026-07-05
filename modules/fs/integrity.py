"""
fs/integrity.py — SHA-256 hash tree with baseline comparison (stdlib hashlib).

Build a hash manifest of a directory tree, save it as a baseline, and on later
runs report drift: ADDED / REMOVED / MODIFIED files. Tamper/change detection.

    python modules/fs/integrity.py .                      # compare vs baseline
    python modules/fs/integrity.py . --save               # (re)write baseline
    python modules/fs/integrity.py . --baseline b.json --algo sha512
    python modules/fs/integrity.py . --json               # emit the manifest
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_BASELINE = os.path.normpath(
    os.path.join(_HERE, "..", "..", "data", "integrity_baseline.json"))
DEFAULT_EXCLUDES = [".git", "__pycache__", "*.pyc", ".venv", "venvs",
                    "node_modules", ".audit-backups", "*.log"]


def _excluded(rel: str, patterns: list[str]) -> bool:
    parts = rel.split(os.sep)
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or any(fnmatch.fnmatch(p, pat) for p in parts):
            return True
    return False


def _hash_file(path: str, algo: str, chunk: int = 1 << 16) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def build_manifest(root: str, algo: str = "sha256",
                   excludes: list[str] | None = None) -> dict:
    excludes = excludes if excludes is not None else DEFAULT_EXCLUDES
    root = os.path.abspath(root)
    files: dict[str, dict] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [d for d in dirnames
                       if not _excluded(os.path.join(rel_dir, d).lstrip("./"), excludes)]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if _excluded(rel, excludes) or os.path.islink(full):
                continue
            try:
                st = os.stat(full)
                files[rel] = {"hash": _hash_file(full, algo),
                              "size": st.st_size}
            except OSError as e:
                files[rel] = {"error": str(e)}
    return {"root": root, "algo": algo, "count": len(files), "files": files}


def compare(baseline: dict, current: dict) -> dict:
    b, c = baseline.get("files", {}), current.get("files", {})
    added = sorted(set(c) - set(b))
    removed = sorted(set(b) - set(c))
    modified = sorted(f for f in set(b) & set(c)
                      if b[f].get("hash") != c[f].get("hash"))
    return {"added": added, "removed": removed, "modified": modified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fs integrity",
                                 description="SHA-256 hash tree + drift check.")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--save", action="store_true", help="write baseline instead of comparing")
    ap.add_argument("--baseline", default=_DEFAULT_BASELINE)
    ap.add_argument("--algo", default="sha256", help="hashlib algo (sha256/sha1/sha512/md5)")
    ap.add_argument("--exclude", action="append", default=None,
                    help="extra glob to skip (repeatable)")
    ap.add_argument("--json", action="store_true", help="print manifest as JSON")
    args = ap.parse_args(argv)

    excludes = DEFAULT_EXCLUDES + (args.exclude or [])
    try:
        manifest = build_manifest(args.root, args.algo, excludes)
    except (ValueError, OSError) as e:
        print(f"[integrity] {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    if args.save:
        os.makedirs(os.path.dirname(os.path.abspath(args.baseline)), exist_ok=True)
        with open(args.baseline, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, sort_keys=True)
        print(f"baseline saved: {manifest['count']} files "
              f"({args.algo}) -> {args.baseline}")
        return 0

    try:
        with open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except (OSError, json.JSONDecodeError):
        print(f"[integrity] no baseline at {args.baseline} — run with --save first",
              file=sys.stderr)
        return 2

    d = compare(baseline, manifest)
    total = len(d["added"]) + len(d["removed"]) + len(d["modified"])
    for f in d["modified"]:
        print(f"MODIFIED  {f}")
    for f in d["added"]:
        print(f"ADDED     {f}")
    for f in d["removed"]:
        print(f"REMOVED   {f}")
    if total == 0:
        print(f"clean — {manifest['count']} files match baseline")
        return 0
    print(f"; {total} change(s): {len(d['modified'])} modified, "
          f"{len(d['added'])} added, {len(d['removed'])} removed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
