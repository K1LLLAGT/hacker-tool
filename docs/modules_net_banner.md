<!-- hacker-tool:generated -->
# modules/net/banner.py

## Overview

net/banner.py — TCP service banner grabber (stdlib socket).

Connects to one host across one or more ports, optionally sends a probe, and
reads whatever the service announces. Single-target by design — this is service
identification, not a mass scanner.

    python modules/net/banner.py 10.0.0.1
    python modules/net/banner.py example.com -p 22,80,443
    python modules/net/banner.py 10.0.0.1 -p 8080 --probe "GET / HTTP/1.0

"

## Key functions

### `grab(host: str, port: int, timeout: float, probe: str | None) -> dict`
No description available.

### `_parse_ports(spec: str) -> list[int]`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import banner

result = banner.grab(...)
print(result)
```
