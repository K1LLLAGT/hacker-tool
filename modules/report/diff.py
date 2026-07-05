"""report diff — compare two report JSONs and highlight changes."""
from __future__ import annotations
import difflib, json, sys
from pathlib import Path

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) < 2:
        print("Usage: report diff <report_a.json> <report_b.json>")
        return 1
    a, b = Path(argv[0]), Path(argv[1])
    for p in (a, b):
        if not p.exists():
            print(f"Error: {p} not found"); return 1

    text_a = json.dumps(json.loads(a.read_text()), indent=2, sort_keys=True).splitlines(True)
    text_b = json.dumps(json.loads(b.read_text()), indent=2, sort_keys=True).splitlines(True)

    diff = list(difflib.unified_diff(text_a, text_b, fromfile=a.name, tofile=b.name))
    if not diff:
        print("Reports are identical — no changes detected.")
        return 0

    added   = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    print(f"Report diff: {a.name} → {b.name}")
    print(f"  +{added} lines added  |  -{removed} lines removed")
    print()
    for line in diff:
        print(line, end="")
    return 0

if __name__ == "__main__":
    sys.exit(main())
