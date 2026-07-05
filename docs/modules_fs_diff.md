<!-- hacker-tool:generated -->
# modules/fs/diff.py

## Overview

fs/diff.py — compare two directory trees or two integrity manifests (stdlib).

Reports files only-in-A, only-in-B, and changed (by hash when comparing dirs,
by stored hash/size when comparing manifests). Optional unified content diff
for changed text files.

    python modules/fs/diff.py dirA dirB
    python modules/fs/diff.py dirA dirB --content          # show text diffs
    python modules/fs/diff.py old.json new.json            # two manifests

## Key functions

### `_hash(path: str) -> str`
No description available.

### `_tree(root: str) -> dict[str, str]`
No description available.

### `_manifest_hashes(path: str) -> dict[str, str]`
No description available.

### `_is_text(path: str) -> bool`
No description available.

### `diff_maps(a: dict[str, str], b: dict[str, str]) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.fs import diff

result = diff.diff_maps(...)
print(result)
```
