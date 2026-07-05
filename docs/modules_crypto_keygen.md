<!-- hacker-tool:generated -->
# modules/crypto/keygen.py

## Overview

crypto/keygen.py — CSPRNG secrets, tokens, UUIDs, passphrases, API keys.

Uses the `secrets` module (cryptographically secure), never `random`.

    python modules/crypto/keygen.py hex --bytes 32
    python modules/crypto/keygen.py token
    python modules/crypto/keygen.py uuid
    python modules/crypto/keygen.py passphrase --words 6
    python modules/crypto/keygen.py apikey --prefix ht
    python modules/crypto/keygen.py password --length 20

## Key functions

### `gen(kind: str) -> str`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.crypto import keygen

result = keygen.gen(...)
print(result)
```
