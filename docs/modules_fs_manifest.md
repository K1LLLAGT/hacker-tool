<!-- hacker-tool:generated -->
# modules/fs/manifest.py

## Overview

modules/fs/manifest.py — filesystem manifest + integrity hashing.

Offline-safe. No network calls.

## Key functions

### `_hash_file(path: Path, algo: str, chunk_size: int) -> str`
No description available.

### `build_manifest(root: str, exclude: list, hash_files: bool, algo: str) -> dict`
No description available.

### `save_manifest(manifest: dict, out_dir: Path, name: str) -> Path`
No description available.

### `diff_manifests(old: dict, new: dict) -> dict`
No description available.

## Usage

```python
from modules.fs import manifest

result = manifest.build_manifest(...)
print(result)
```
