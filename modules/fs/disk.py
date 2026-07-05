"""
fs/disk.py — per-folder size breakdown + top-N largest files (stdlib os).

    python modules/fs/disk.py .
    python modules/fs/disk.py /sdcard --top 20
    python modules/fs/disk.py . --depth 2
"""
from __future__ import annotations

import argparse
import os
import sys

DEFAULT_SKIP = {".git", "__pycache__", ".venv", "node_modules"}


def _human(n: int) -> str:
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < step:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= step
    return f"{n:.1f}PB"


def walk_sizes(root: str, skip: set[str]):
    """Yield (relpath, size) for every regular file, and total."""
    root = os.path.abspath(root)
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip]
        for name in fns:
            full = os.path.join(dp, name)
            if os.path.islink(full):
                continue
            try:
                size = os.stat(full).st_size
            except OSError:
                continue
            yield os.path.relpath(full, root), size


def summarize(root: str, depth: int = 1, top: int = 10,
              skip: set[str] | None = None) -> dict:
    skip = skip if skip is not None else DEFAULT_SKIP
    folder_totals: dict[str, int] = {}
    largest: list[tuple[str, int]] = []
    total = 0
    for rel, size in walk_sizes(root, skip):
        total += size
        parts = rel.split(os.sep)
        key = os.sep.join(parts[:depth]) if len(parts) > depth else (
            parts[0] if len(parts) > 1 else ".")
        folder_totals[key] = folder_totals.get(key, 0) + size
        largest.append((rel, size))
    largest.sort(key=lambda x: x[1], reverse=True)
    return {
        "total": total,
        "folders": sorted(folder_totals.items(), key=lambda x: x[1], reverse=True),
        "largest": largest[:top],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fs disk", description="Disk usage breakdown.")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--top", type=int, default=10, help="how many largest files to list")
    ap.add_argument("--depth", type=int, default=1, help="folder grouping depth")
    ap.add_argument("--skip", action="append", default=[])
    args = ap.parse_args(argv)

    if not os.path.isdir(args.root):
        print(f"[disk] not a directory: {args.root}", file=sys.stderr)
        return 2

    r = summarize(args.root, args.depth, args.top, DEFAULT_SKIP | set(args.skip))
    print(f"total   {_human(r['total'])}   ({args.root})\n")
    print("by folder:")
    for name, size in r["folders"]:
        bar = "#" * min(40, int(40 * size / r["total"])) if r["total"] else ""
        print(f"  {_human(size):>9}  {bar:<40}  {name}")
    print(f"\ntop {args.top} files:")
    for rel, size in r["largest"]:
        print(f"  {_human(size):>9}  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
