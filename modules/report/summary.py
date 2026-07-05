"""report summary — terminal sparkline + key-metric dashboard from report JSON."""
from __future__ import annotations
import json, sys
from pathlib import Path

SPARKS = "▁▂▃▄▅▆▇█"

def sparkline(values: list[float]) -> str:
    if not values: return ""
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    return "".join(SPARKS[int((v - mn) / rng * (len(SPARKS) - 1))] for v in values)

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        # summarise all reports in reports/
        report_dir = Path.home() / "hacker-tool/reports"
        files = sorted(report_dir.glob("*.json")) if report_dir.exists() else []
        if not files:
            print("No report JSON files found in reports/"); return 0
        argv = [str(f) for f in files[-5:]]  # last 5

    for path_str in argv:
        src = Path(path_str)
        if not src.exists():
            print(f"  [skip] {src} not found"); continue
        data = json.loads(src.read_text())
        rows = data if isinstance(data, list) else [data]
        print(f"\n── {src.name} ──────────────────────────")
        print(f"  Records : {len(rows)}")

        # Collect numeric fields for sparklines
        numeric: dict[str, list[float]] = {}
        for row in rows:
            if isinstance(row, dict):
                for k, v in row.items():
                    if isinstance(v, (int, float)):
                        numeric.setdefault(k, []).append(float(v))

        if numeric:
            print("  Metrics :")
            for k, vals in list(numeric.items())[:6]:
                avg = sum(vals) / len(vals)
                spark = sparkline(vals)
                print(f"    {k:<20} avg={avg:>8.2f}  {spark}")
        else:
            # Show first 3 keys of first row
            if rows and isinstance(rows[0], dict):
                for k, v in list(rows[0].items())[:3]:
                    print(f"  {k}: {v}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
