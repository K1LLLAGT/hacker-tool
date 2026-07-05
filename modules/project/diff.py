"""project diff — compare two project snapshots line by line."""
from __future__ import annotations
import difflib, json, sys
from pathlib import Path

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) < 2:
        print("Usage: project diff <snapshot_a> <snapshot_b>")
        return 1
    a, b = Path(argv[0]), Path(argv[1])
    if not a.exists() or not b.exists():
        print("Error: one or both snapshot files not found"); return 1
    lines_a = a.read_text().splitlines(keepends=True)
    lines_b = b.read_text().splitlines(keepends=True)
    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile=str(a), tofile=str(b)))
    if not diff:
        print("Snapshots are identical.")
        return 0
    print(f"Diff: {a.name} → {b.name}  ({len(diff)} changed lines)")
    for line in diff:
        print(line, end="")
    return 0

if __name__ == "__main__":
    sys.exit(main())
