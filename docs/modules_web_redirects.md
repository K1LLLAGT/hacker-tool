<!-- hacker-tool:generated -->
# modules/web/redirects.py

## Overview

web/redirects.py — follow and log every HTTP redirect hop (stdlib urllib).

Disables auto-follow and walks the 3xx chain by hand so each hop is visible,
with a cap to catch loops.

    python modules/web/redirects.py http://github.com
    python modules/web/redirects.py example.com --max 15

## Key classes

### `_NoRedirect`
No description available.
- `redirect_request(req, fp, code, msg, headers, newurl)`

## Key functions

### `_opener()`
No description available.

### `_normalize(url: str) -> str`
No description available.

### `follow(url: str, max_hops: int, timeout: float) -> list[dict]`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.web import redirects

result = redirects.follow(...)
print(result)
```
