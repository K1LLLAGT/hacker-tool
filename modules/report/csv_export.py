"""report csv_export — flatten any report JSON to CSV."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

def flatten(obj: dict, parent_key: str = "", sep: str = ".") -> dict:
    items: list = []
    for k, v in obj.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep).items())
        elif isinstance(v, list):
            items.append((new_key, "; ".join(str(i) for i in v)))
        else:
            items.append((new_key, v))
    return dict(items)

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: report csv_export <report.json> [output.csv]")
        return 1
    src = Path(argv[0])
    if not src.exists():
        print(f"Error: {src} not found"); return 1
    data = json.loads(src.read_text())
    rows = data if isinstance(data, list) else [data]
    rows = [flatten(r) if isinstance(r, dict) else {"value": r} for r in rows]
    dst = Path(argv[1]) if len(argv) > 1 else src.with_suffix(".csv")
    all_keys = list(dict.fromkeys(k for row in rows for k in row))
    with open(dst, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV exported → {dst}  ({len(rows)} rows, {len(all_keys)} columns)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
