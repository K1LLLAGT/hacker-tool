<!-- hacker-tool:generated -->
# modules/net/wifi.py

## Overview

net/wifi.py — WiFi scan & connection info via termux-api (stdlib json/subprocess).

Wraps `termux-wifi-scaninfo` (nearby APs) and `termux-wifi-connectioninfo`
(current link). Requires the Termux:API app + `pkg install termux-api`.

    python modules/net/wifi.py            # current connection
    python modules/net/wifi.py --scan     # nearby access points

## Key functions

### `_run_json(cmd: list[str], timeout: float)`
No description available.

### `connection() -> dict`
No description available.

### `scan() -> list[dict]`
No description available.

### `_secpretty(caps: str) -> str`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import wifi

result = wifi.connection(...)
print(result)
```
