<!-- hacker-tool:generated -->
# modules/fs/archive.py

## Overview

fs/archive.py — tar.gz / zip pack, unpack, and list (stdlib tarfile/zipfile).

Format is inferred from the archive extension. Extraction is path-traversal
safe (rejects absolute paths and ``..`` escapes — Zip-Slip / tar-slip guard).

    python modules/fs/archive.py pack out.tar.gz src_dir
    python modules/fs/archive.py pack out.zip file1 file2 dir3
    python modules/fs/archive.py list out.tar.gz
    python modules/fs/archive.py unpack out.tar.gz dest_dir

## Key functions

### `_is_zip(path: str) -> bool`
No description available.

### `_safe_dest(base: str, name: str) -> str | None`
Return the resolved path if *name* stays inside *base*, else None.

### `pack(archive: str, sources: list[str]) -> int`
No description available.

### `list_contents(archive: str) -> list[tuple[str, int]]`
No description available.

### `unpack(archive: str, dest: str) -> int`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.fs import archive

result = archive.pack(...)
print(result)
```
