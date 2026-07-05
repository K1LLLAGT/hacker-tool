"""
fs/diff.py — compare two directory trees or two integrity manifests (stdlib).

Reports files only-in-A, only-in-B, and changed (by hash when comparing dirs,
by stored hash/size when comparing manifests). Optional unified content diff
for changed text files.

    python modules/fs/diff.py dirA dirB
    python modules/fs/diff.py dirA dirB --content          # show text diffs
    python modules/fs/diff.py old.json new.json            # two manifests
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys

DEFAULT_EXCLUDES = {".git", "__pycache__", ".venv", "node_modules",
                    ".audit-backups"}
_TEXT_MAX = 512 * 1024   # only content-diff files under 512 KB


def _hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def _tree(root: str) -> dict[str, str]:
    out: dict[str, str] = {}
    root = os.path.abspath(root)
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in DEFAULT_EXCLUDES]
        for name in fns:
            full = os.path.join(dp, name)
            if os.path.islink(full):
                continue
            rel = os.path.relpath(full, root)
            try:
                out[rel] = _hash(full)
            except OSError:
                out[rel] = "?"
    return out


def _manifest_hashes(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {k: v.get("hash", "?") for k, v in data.get("files", {}).items()}


def _is_text(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(4096)
        return b"\x00" not in chunk
    except OSError:
        return False


def diff_maps(a: dict[str, str], b: dict[str, str]) -> dict:
    return {
        "only_a": sorted(set(a) - set(b)),
        "only_b": sorted(set(b) - set(a)),
        "changed": sorted(f for f in set(a) & set(b) if a[f] != b[f]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fs diff", description="Diff two trees or manifests.")
    ap.add_argument("a", help="dir or manifest.json")
    ap.add_argument("b", help="dir or manifest.json")
    ap.add_argument("--content", action="store_true",
                    help="show unified diff for changed text files (dir mode only)")
    args = ap.parse_args(argv)

    a_is_dir, b_is_dir = os.path.isdir(args.a), os.path.isdir(args.b)
    try:
        amap = _tree(args.a) if a_is_dir else _manifest_hashes(args.a)
        bmap = _tree(args.b) if b_is_dir else _manifest_hashes(args.b)
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print(f"[diff] {e}", file=sys.stderr)
        return 2

    d = diff_maps(amap, bmap)
    for f in d["changed"]:
        print(f"CHANGED   {f}")
    for f in d["only_a"]:
        print(f"ONLY A    {f}")
    for f in d["only_b"]:
        print(f"ONLY B    {f}")

    if args.content and a_is_dir and b_is_dir:
        for f in d["changed"]:
            pa, pb = os.path.join(args.a, f), os.path.join(args.b, f)
            if not (_is_text(pa) and _is_text(pb)):
                continue
            if os.path.getsize(pa) > _TEXT_MAX or os.path.getsize(pb) > _TEXT_MAX:
                continue
            with open(pa, encoding="utf-8", errors="replace") as fh:
                la = fh.readlines()
            with open(pb, encoding="utf-8", errors="replace") as fh:
                lb = fh.readlines()
            print(f"\n--- diff: {f} ---")
            sys.stdout.writelines(difflib.unified_diff(
                la, lb, fromfile=f"a/{f}", tofile=f"b/{f}"))

    total = sum(len(d[k]) for k in d)
    if total == 0:
        print("identical")
        return 0
    print(f"; {len(d['changed'])} changed, {len(d['only_a'])} only-A, "
          f"{len(d['only_b'])} only-B", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
