<!-- hacker-tool:generated -->
# modules/fs/integrity.py

## Overview

fs/integrity.py — SHA-256 hash tree with baseline comparison (stdlib hashlib).

Build a hash manifest of a directory tree, save it as a baseline, and on later
runs report drift: ADDED / REMOVED / MODIFIED files. Tamper/change detection.

    python modules/fs/integrity.py .                      # compare vs baseline
    python modules/fs/integrity.py . --save               # (re)write baseline
    python modules/fs/integrity.py . --baseline b.json --algo sha512
    python modules/fs/integrity.py . --json               # emit the manifest

## Key functions

### `_excluded(rel: str, patterns: list[str]) -> bool`
No description available.

### `_hash_file(path: str, algo: str, chunk: int) -> str`
No description available.

### `build_manifest(root: str, algo: str, excludes: list[str] | None) -> dict`
No description available.

### `compare(baseline: dict, current: dict) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.fs import integrity

result = integrity.build_manifest(...)
print(result)
```
