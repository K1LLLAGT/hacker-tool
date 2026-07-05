<!-- hacker-tool:generated -->
# modules/net/arpwatch.py

## Overview

net/arpwatch.py — ARP neighbour snapshot & change detection (iproute2).

Uses `ip neigh show` (proot-safe — no raw sockets) to capture the IP<->MAC
table, saves a baseline, and on later runs flags:
  * NEW      — an IP/MAC not seen before
  * GONE     — a previously-seen entry now absent
  * CHANGED  — an IP whose MAC changed  (classic ARP-spoofing signal)

    python modules/net/arpwatch.py                 # snapshot + diff vs baseline
    python modules/net/arpwatch.py --save          # (re)write the baseline
    python modules/net/arpwatch.py --watch 30      # poll every 30s, alert on change

## Key functions

### `read_table() -> dict[str, dict]`
Return {ip: {mac, iface, state}} from `ip neigh show`.

### `diff(old: dict, new: dict) -> list[tuple[str, str, str]]`
Yield (kind, ip, detail).

### `_load_baseline() -> dict`
No description available.

### `_save_baseline(table: dict) -> None`
No description available.

### `_print_table(table: dict) -> None`
No description available.

### `_print_events(events) -> None`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import arpwatch

result = arpwatch.read_table(...)
print(result)
```
