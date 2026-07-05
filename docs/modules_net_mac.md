<!-- hacker-tool:generated -->
# modules/net/mac.py

## Overview

net/mac.py — MAC address -> vendor via bundled OUI table (stdlib json).

Offline lookup against data/oui.json. Handles any separator style and MAC-48
or EUI-64. Also flags locally-administered / multicast addresses.

    python modules/net/mac.py 2C:CF:67:C8:96:9B
    python modules/net/mac.py 2ccf67c8969b
    python modules/net/mac.py --file addresses.txt

## Key functions

### `_normalize(mac: str) -> str`
No description available.

### `load_db(path: str) -> dict[str, str]`
No description available.

### `lookup(mac: str, db: dict[str, str]) -> dict`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import mac

result = mac.load_db(...)
print(result)
```
