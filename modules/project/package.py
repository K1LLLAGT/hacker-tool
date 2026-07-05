"""project package — bundle project into versioned tar.gz archive."""
from __future__ import annotations
import sys, tarfile, datetime
from pathlib import Path

EXCLUDES = {".git", ".venv", "__pycache__", "reports", "logs", ".ssh"}

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    root = Path(argv[0]) if argv else Path.home() / "hacker-tool"
    if not root.exists():
        print(f"Error: {root} not found"); return 1
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    version = (root / "VERSION").read_text().strip() if (root / "VERSION").exists() else "x.x.x"
    out = root.parent / f"hacker-tool-v{version}-{ts}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        for item in root.rglob("*"):
            if any(ex in item.parts for ex in EXCLUDES):
                continue
            tar.add(item, arcname=item.relative_to(root.parent))
    size_kb = out.stat().st_size // 1024
    print(f"Packaged → {out}  ({size_kb} KB)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
