<!-- hacker-tool:generated -->
# modules/crypto/encode.py

## Overview

crypto/encode.py — base64 / base32 / hex / url / rot13 encode & decode (stdlib).

    python modules/crypto/encode.py base64 --text "hi there"
    python modules/crypto/encode.py base64 -d --text "aGkgdGhlcmU="
    python modules/crypto/encode.py hex --file blob.bin
    echo -n secret | python modules/crypto/encode.py url

## Key functions

### `_encode(fmt: str, data: bytes) -> str`
No description available.

### `_decode(fmt: str, text: str) -> bytes`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.crypto import encode

result = encode.main(...)
print(result)
```
