<!-- hacker-tool:generated -->
# modules/fs/disk.py

## Overview

fs/disk.py — per-folder size breakdown + top-N largest files (stdlib os).

    python modules/fs/disk.py .
    python modules/fs/disk.py /sdcard --top 20
    python modules/fs/disk.py . --depth 2

## Key functions

### `_human(n: int) -> str`
No description available.

### `walk_sizes(root: str, skip: set[str])`
Yield (relpath, size) for every regular file, and total.

### `summarize(root: str, depth: int, top: int, skip: set[str] | None) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.fs import disk

result = disk.walk_sizes(...)
print(result)
```
