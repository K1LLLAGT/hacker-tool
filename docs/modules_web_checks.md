<!-- hacker-tool:generated -->
# modules/web/checks.py

## Overview

modules/web/checks.py — basic HTTP health/link checks.

Online feature (opt-in). Intended for checking sites you own/operate
(e.g. gwthardwoodfloors.com deployment), not scanning third-party sites.

## Key functions

### `check_url(url: str, timeout: int) -> dict`
No description available.

### `check_links_on_page(url: str, timeout: int, same_domain_only: bool) -> dict`
Fetches a page and checks all <a href> links for status. Useful for

## Usage

```python
from modules.web import checks

result = checks.check_url(...)
print(result)
```
