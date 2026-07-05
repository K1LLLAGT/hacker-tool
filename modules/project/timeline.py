"""project timeline — parse git log into JSON timeline of changes."""
from __future__ import annotations
import subprocess, json, sys, re
from pathlib import Path

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    root = Path(argv[0]) if argv else Path.home() / "hacker-tool"
    limit = int(argv[1]) if len(argv) > 1 else 20
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", f"-{limit}",
             "--pretty=format:%H|%an|%ae|%ai|%s"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"git error: {e.stderr.strip()}"); return 1

    entries = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            entries.append({
                "hash":    parts[0][:7],
                "author":  parts[1],
                "email":   parts[2],
                "date":    parts[3],
                "message": parts[4],
            })

    print(f"Timeline — last {len(entries)} commits in {root.name}:")
    print("-" * 60)
    for e in entries:
        print(f"[{e['date'][:10]}] {e['hash']}  {e['author']}: {e['message']}")

    out = root / "reports" / "timeline.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(entries, indent=2))
    print(f"\nJSON saved → {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
