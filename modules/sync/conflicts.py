"""sync conflicts — compare local vs remote dir, surface collisions before sync."""
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
    if len(argv) < 2:
        print("Usage: sync conflicts <local_dir> <remote_dir>")
        return 1
    local  = Path(argv[0])
    remote = Path(argv[1])
    for d in (local, remote):
        if not d.exists():
            print(f"Error: {d} not found"); return 1

    local_files  = {p.relative_to(local):  p for p in local.rglob("*")  if p.is_file()}
    remote_files = {p.relative_to(remote): p for p in remote.rglob("*") if p.is_file()}

    conflicts = []
    only_local, only_remote = [], []

    for rel, lpath in local_files.items():
        if rel in remote_files:
            if file_hash(lpath) != file_hash(remote_files[rel]):
                conflicts.append(rel)
        else:
            only_local.append(rel)

    for rel in remote_files:
        if rel not in local_files:
            only_remote.append(rel)

    print(f"Conflict check: {local.name} ↔ {remote.name}")
    print(f"  Conflicts (both modified): {len(conflicts)}")
    for f in conflicts: print(f"    ⚡ {f}")
    print(f"  Only in local:  {len(only_local)}")
    print(f"  Only in remote: {len(only_remote)}")
    return 0 if not conflicts else 1

if __name__ == "__main__":
    sys.exit(main())
