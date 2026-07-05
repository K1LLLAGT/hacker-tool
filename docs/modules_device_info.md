<!-- hacker-tool:generated -->
# modules/device/info.py

## Overview

modules/device/info.py — Android / Termux device introspection.

Offline-only. Stdlib only. Reads /proc, /sys, and getprop.

## Key functions

### `_read(path: str, default: str) -> str`
No description available.

### `_getprop(key: str) -> str`
No description available.

### `_run() -> str`
No description available.

### `device_info() -> dict`
No description available.

### `storage_info() -> dict`
No description available.

### `battery_info() -> dict`
No description available.

### `network_interfaces() -> dict`
No description available.

### `cpu_info() -> dict`
No description available.

## Usage

```python
from modules.device import info

result = info.device_info(...)
print(result)
```
