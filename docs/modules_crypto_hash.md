<!-- hacker-tool:generated -->
# modules/crypto/hash.py

## Overview

crypto/hash.py — hash a string, file, or stdin (stdlib hashlib).

    python modules/crypto/hash.py --text "hello"
    python modules/crypto/hash.py --file report.pdf --algo sha512
    echo -n data | python modules/crypto/hash.py --algo sha256
    python modules/crypto/hash.py --file x --all

## Key functions

### `hash_bytes(data: bytes, algo: str) -> str`
No description available.

### `hash_file(path: str, algo: str, chunk: int) -> str`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.crypto import hash

result = hash.hash_bytes(...)
print(result)
```
