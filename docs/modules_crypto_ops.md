<!-- hacker-tool:generated -->
# modules/crypto/ops.py

## Overview

modules/crypto/ops.py — local cryptographic utilities.

Offline-only. No network calls. Stdlib only.
Subcommands: hash, encode, decode, entropy, compare

## Key functions

### `_read_bytes(file: str, text: str) -> bytes`
No description available.

### `hash_data(file: str, text: str, algo: str) -> dict`
Hash a file or text string with the given algorithm.

### `encode_b64(file: str, text: str, url_safe: bool) -> dict`
Base64-encode a file or text string.

### `decode_b64(text: str, url_safe: bool) -> dict`
Base64-decode a string, printing as UTF-8 (lossy).

### `shannon_entropy(file: str) -> dict`
Shannon entropy of a file — high entropy signals encryption or packing.

### `compare_hashes(hash_a: str, hash_b: str) -> dict`
Constant-time comparison of two hex digest strings.

## Usage

```python
from modules.crypto import ops

result = ops.hash_data(...)
print(result)
```
