<!-- hacker-tool:generated -->
# core/secrets.py

## Overview

core/secrets.py — simple symmetric credential store using stdlib only.
Stores secrets encrypted at rest in ~/.config/hacker-tool/.secrets
Usage:
    from core.secrets import set_secret, get_secret
    set_secret("smb_password", "hunter2")
    get_secret("smb_password")

## Key functions

### `_load_key() -> bytes`
No description available.

### `_xor(data: bytes, key: bytes) -> bytes`
No description available.

### `set_secret(name: str, value: str) -> None`
No description available.

### `get_secret(name: str) -> str | None`
No description available.

### `list_secrets() -> list[str]`
No description available.

### `delete_secret(name: str) -> bool`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from core import secrets

result = secrets.set_secret(...)
print(result)
```
