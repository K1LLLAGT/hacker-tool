"""
modules/fs/manifest.py — filesystem manifest + integrity hashing.

Offline-safe. No network calls.
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone


def _hash_file(path: Path, algo: str = "sha256", chunk_size: int = 1 << 20) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: str, exclude: list, hash_files: bool = True, algo: str = "sha256") -> dict:
    root_path = Path(root).expanduser().resolve()
    exclude_set = set(exclude or [])

    entries = []
    for p in root_path.rglob("*"):
        if any(part in exclude_set for part in p.parts):
            continue
        if p.is_file():
            try:
                stat = p.stat()
                entry = {
                    "path": str(p.relative_to(root_path)),
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                }
                if hash_files:
                    entry["hash"] = f"{algo}:{_hash_file(p, algo)}"
                entries.append(entry)
            except (PermissionError, OSError):
                entries.append({"path": str(p.relative_to(root_path)), "error": "unreadable"})

    return {
        "root": str(root_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(entries),
        "excluded": sorted(exclude_set),
        "entries": entries,
    }


def save_manifest(manifest: dict, out_dir: Path, name: str = "manifest") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{name}_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return out_path


def diff_manifests(old: dict, new: dict) -> dict:
    old_map = {e["path"]: e for e in old["entries"] if "hash" in e}
    new_map = {e["path"]: e for e in new["entries"] if "hash" in e}

    added = sorted(set(new_map) - set(old_map))
    removed = sorted(set(old_map) - set(new_map))
    changed = sorted(
        path for path in set(old_map) & set(new_map)
        if old_map[path]["hash"] != new_map[path]["hash"]
    )
    return {"added": added, "removed": removed, "changed": changed}
