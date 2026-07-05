<!-- hacker-tool:generated -->
# modules/fs/secrets_scan.py

## Overview

fs/secrets_scan.py — regex scan for committed secrets (stdlib re).

Finds accidentally-stored credentials in a tree: cloud keys, tokens, private
keys, JWTs, and generic secret assignments. Matches are REDACTED by default so
the scan output/logs don't themselves leak the secret. Defensive hygiene tool
(same job as git-secrets / gitleaks).

    python modules/fs/secrets_scan.py .
    python modules/fs/secrets_scan.py . --show          # reveal full match
    python modules/fs/secrets_scan.py . --json

## Key functions

### `_redact(s: str) -> str`
No description available.

### `_is_text(path: str) -> bool`
No description available.

### `scan_file(path: str, show: bool) -> list[dict]`
No description available.

### `scan_tree(root: str, show: bool, skip_dirs: set[str] | None) -> list[dict]`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.fs import secrets_scan

result = secrets_scan.scan_file(...)
print(result)
```
