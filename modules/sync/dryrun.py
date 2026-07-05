"""sync dryrun — preview what push/pull would change without touching files."""
from __future__ import annotations
import hashlib, sys
from pathlib import Path

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) < 3 or argv[0] not in ("push", "pull"):
        print("Usage: sync dryrun <push|pull> <src_dir> <dst_dir>")
        return 1
    direction, src_dir, dst_dir = argv[0], Path(argv[1]), Path(argv[2])
    if not src_dir.exists():
        print(f"Error: {src_dir} not found"); return 1

    src_files = {p.relative_to(src_dir): p for p in src_dir.rglob("*") if p.is_file()}
    dst_files = {p.relative_to(dst_dir): p for p in dst_dir.rglob("*") if p.is_file()} \
        if dst_dir.exists() else {}

    to_add, to_update, unchanged = [], [], []
    for rel, spath in src_files.items():
        if rel not in dst_files:
            to_add.append(rel)
        elif file_hash(spath) != file_hash(dst_files[rel]):
            to_update.append(rel)
        else:
            unchanged.append(rel)

    arrow = "→" if direction == "push" else "←"
    print(f"Dry-run {direction}: {src_dir.name} {arrow} {dst_dir.name}")
    print(f"  Would add:    {len(to_add)}")
    for f in to_add: print(f"    + {f}")
    print(f"  Would update: {len(to_update)}")
    for f in to_update: print(f"    ~ {f}")
    print(f"  Unchanged:    {len(unchanged)}")
    print("No files were modified (dry-run only).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
