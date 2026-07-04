"""
modules/project/snapshot.py — package a project directory into a timestamped
tarball snapshot, e.g. for gwthardwoodfloors or SAAB-SUITE before a risky change.
"""
from datetime import datetime, timezone
from pathlib import Path
import tarfile


def snapshot(project_dir: str, out_dir: Path, name: str = None, exclude: list = None) -> Path:
    project_path = Path(project_dir).expanduser().resolve()
    exclude_set = set(exclude or [".git", "node_modules", "__pycache__", ".venv"])
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = name or project_path.name
    out_path = out_dir / f"{label}_{ts}.tar.gz"

    def _filter(tarinfo):
        parts = Path(tarinfo.name).parts
        if any(part in exclude_set for part in parts):
            return None
        return tarinfo

    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(project_path, arcname=label, filter=_filter)

    return out_path
