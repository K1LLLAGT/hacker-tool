<!-- hacker-tool:generated -->
# core/storage.py

## Overview

core/storage.py — Local + remote (SMB or plain mounted path) workspace abstraction.

Design: a "workspace" is just a named directory under either:
    <local_root>/workspaces/local/<name>
    <remote_root>/<name>            (remote_root may be an SMB mount or a
                                      plain shared folder path like
                                      /storage/emulated/0/SharedFolder)

Sync is deliberately simple (rsync-style copy), not a generic file-sync
daemon. Two backends are supported:

  - "path"  : remote_root is already a filesystem path (bind mount, cifs
              mount via mount.cifs, or an Android SAF-exposed shared folder)
  - "smb"   : remote_root is accessed on-demand via `smbclient` (no mount
              needed) — good for Termux without root/mount.cifs

Pick the backend that matches your setup in config.yml under remote_type.

## Key classes

### `StorageError`
No description available.

### `Storage`
No description available.
- `__init__(cfg: dict, logger)`
- `local_workspace(name: str) -> Path`
- `remote_workspace_path(name: str) -> Path`
- `push(name: str) -> None`
- `pull(name: str) -> None`
- `status(name: str) -> dict`
- `_copy_tree(src: Path, dst: Path) -> None`
- `_smb_put_tree(src: Path, name: str) -> None`
- `_smb_get_tree(name: str, dst: Path) -> None`
- `_smb_list(name: str) -> list`
- `_require_smbclient() -> None`
- `_smb_base_cmd(smb: dict) -> list`
- `_run_smbclient(base_cmd: list, batch: str, capture: bool)`

## Usage

```python
from core import storage
```
