<!-- hacker-tool:generated -->
# modules/net/scan.py

## Overview

modules/net/scan.py — thin wrappers around nmap/ping for LAN inventory.

Intended use: mapping devices on YOUR OWN network (e.g. confirming the
Pi 5's DHCP-assigned IP, checking what's alive on 192.168.1.0/24).
This module does not perform vulnerability scanning, exploitation, or
scanning of hosts outside a locally-scoped private range — it's an
inventory/audit tool, not an attack tool.

## Key functions

### `_is_private_range(cidr: str) -> bool`
No description available.

### `ping_sweep(cidr: str, timeout_s: float) -> list`
Simple ping sweep — works even without nmap installed.

### `nmap_scan(cidr: str, extra_args: list) -> str`
Delegates to nmap if installed; returns raw output text.

### `main(argv: list[str]) -> int`
CLI entry point: inventory hosts on a private (RFC1918) CIDR.

## Usage

```python
from modules.net import scan

result = scan.ping_sweep(...)
print(result)
```
