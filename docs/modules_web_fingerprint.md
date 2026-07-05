<!-- hacker-tool:generated -->
# modules/web/fingerprint.py

## Overview

web/fingerprint.py — identify server/CMS/framework from headers + HTML (stdlib).

Signature-based detection across response headers, cookies, and body markers.
Best-effort, not exhaustive — flags what it can see, doesn't guess wildly.

    python modules/web/fingerprint.py https://example.com
    python modules/web/fingerprint.py example.com --json

## Key functions

### `_normalize(url: str) -> str`
No description available.

### `fetch(url: str, timeout: float) -> dict`
No description available.

### `fingerprint(data: dict) -> list[str]`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.web import fingerprint

result = fingerprint.fetch(...)
print(result)
```
