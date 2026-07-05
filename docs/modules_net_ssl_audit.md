<!-- hacker-tool:generated -->
# modules/net/ssl_audit.py

## Overview

net/ssl_audit.py — TLS certificate & handshake audit (stdlib ssl).

Reports cert subject/issuer, validity window and days-to-expiry, SANs, the
negotiated protocol + cipher, and whether the site sends HSTS.

    python modules/net/ssl_audit.py example.com
    python modules/net/ssl_audit.py example.com:8443
    python modules/net/ssl_audit.py example.com --no-verify   # inspect anyway

## Key functions

### `_parse_cert_time(value: str) -> _dt.datetime`
No description available.

### `_decode_untrusted(der: bytes) -> dict`
Get a getpeercert()-style dict for a cert we didn't verify.

### `_flatten(pairs) -> dict`
No description available.

### `audit(host: str, port: int, timeout: float, verify: bool) -> dict`
No description available.

### `_check_hsts(host: str, port: int, timeout: float) -> bool | None`
Best-effort: HEAD / over TLS and look for Strict-Transport-Security.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import ssl_audit

result = ssl_audit.audit(...)
print(result)
```
