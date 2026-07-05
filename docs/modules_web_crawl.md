<!-- hacker-tool:generated -->
# modules/web/crawl.py

## Overview

web/crawl.py — map a site by following internal links (stdlib urllib + html.parser).

Breadth-first, same-host only, with depth and page caps plus an optional politeness
delay. Prints the discovered URL tree. For sites you operate.

    python modules/web/crawl.py https://example.com
    python modules/web/crawl.py https://example.com --depth 2 --max 50 --delay 0.3

## Key classes

### `_LinkExtractor`
No description available.
- `__init__()`
- `handle_starttag(tag, attrs)`

## Key functions

### `_normalize(url: str) -> str`
No description available.

### `_same_host(a: str, b: str) -> bool`
No description available.

### `_clean(url: str) -> str`
No description available.

### `crawl(start: str, depth: int, max_pages: int, delay: float, timeout: float) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.web import crawl

result = crawl.crawl(...)
print(result)
```
