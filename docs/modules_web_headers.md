<!-- hacker-tool:generated -->
# modules/web/headers.py

## Overview

web/headers.py — HTTP security-header audit (stdlib urllib).

Fetches a URL and grades the response for the headers that matter:
HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy. Online / opt-in — meant for sites you operate.

    python modules/web/headers.py https://example.com
    python modules/web/headers.py example.com --json

## Key functions

### `_normalize(url: str) -> str`
No description available.

### `fetch_headers(url: str, timeout: float) -> dict`
No description available.

### `audit(url: str, timeout: float) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.web import headers

result = headers.fetch_headers(...)
print(result)
```
