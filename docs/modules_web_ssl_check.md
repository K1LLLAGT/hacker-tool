<!-- hacker-tool:generated -->
# modules/web/ssl_check.py

## Overview

web/ssl_check.py — quick cert-expiry check (stdlib ssl).

Deliberately lightweight: days-to-expiry, valid-until, SAN count. For the full
issuer/cipher/HSTS breakdown use `net-ssl_audit` instead — this is the fast
"is my cert about to lapse?" check for monitoring/cron.

    python modules/web/ssl_check.py example.com
    python modules/web/ssl_check.py example.com:8443 --warn 30

## Key functions

### `days_left(host: str, port: int, timeout: float) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.web import ssl_check

result = ssl_check.days_left(...)
print(result)
```
