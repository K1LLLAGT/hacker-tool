<!-- hacker-tool:generated -->
# modules/crypto/verify.py

## Overview

crypto/verify.py — verify a file against a known-good hash (stdlib hashlib).

Provide the expected hash directly, a coreutils-style ``.sha256`` sidecar, or a
checksums file listing many entries. Algorithm is inferred from digest length
unless given. Uses a constant-time comparison.

    python modules/crypto/verify.py file.iso --sha256 ab12...ef
    python modules/crypto/verify.py file.iso --sidecar file.iso.sha256
    python modules/crypto/verify.py --checksums SHA256SUMS        # verify all

## Key functions

### `_hash_file(path: str, algo: str, chunk: int) -> str`
No description available.

### `_infer_algo(digest: str, override: str | None) -> str`
No description available.

### `verify_one(path: str, expected: str, algo: str | None) -> bool`
No description available.

### `_parse_checksums(text: str) -> list[tuple[str, str]]`
Parse '<hash>  <filename>' lines (coreutils format).

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.crypto import verify

result = verify.verify_one(...)
print(result)
```
