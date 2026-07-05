<!-- hacker-tool:generated -->
# modules/crypto/encrypt.py

## Overview

crypto/encrypt.py — file encryption, stdlib only.

Two modes:

  stream  (default)  A real password-based authenticated cipher built from
                     stdlib primitives: scrypt KDF -> HMAC-SHA256 keystream in
                     counter mode -> encrypt-then-MAC (HMAC-SHA256). Tamper is
                     detected on decrypt. Use this for anything you actually
                     want protected.

  xor                Repeating-key XOR. This is OBFUSCATION, NOT ENCRYPTION —
                     trivially breakable. Included only for compatibility with
                     the existing core/secrets.py engine and for CTF/testing.

    python modules/crypto/encrypt.py enc secret.txt secret.enc            # prompts for password
    python modules/crypto/encrypt.py dec secret.enc secret.out
    python modules/crypto/encrypt.py enc a.bin a.xor --mode xor --keystring hunter2

## Key functions

### `_derive(password: bytes, salt: bytes) -> tuple[bytes, bytes]`
No description available.

### `_keystream(enc_key: bytes, nonce: bytes, nbytes: int) -> bytes`
No description available.

### `_xor(data: bytes, key: bytes) -> bytes`
No description available.

### `encrypt_stream(plaintext: bytes, password: bytes) -> bytes`
No description available.

### `decrypt_stream(blob: bytes, password: bytes) -> bytes`
No description available.

### `_get_key_bytes(args) -> bytes`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.crypto import encrypt

result = encrypt.encrypt_stream(...)
print(result)
```
