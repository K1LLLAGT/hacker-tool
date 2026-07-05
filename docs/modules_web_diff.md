<!-- hacker-tool:generated -->
# modules/web/diff.py

## Overview

web/diff.py — detect page changes by diffing response bodies (stdlib).

Two modes:
  * one URL   -> fetch twice (optionally with --delay) to catch dynamic changes
  * two URLs  -> compare them (e.g. staging vs prod)

    python modules/web/diff.py https://example.com
    python modules/web/diff.py https://example.com --delay 5
    python modules/web/diff.py https://staging.site https://www.site

## Key functions

### `_normalize(url: str) -> str`
No description available.

### `fetch_text(url: str, timeout: float) -> list[str]`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.web import diff

result = diff.fetch_text(...)
print(result)
```
