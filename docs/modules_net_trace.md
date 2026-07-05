<!-- hacker-tool:generated -->
# modules/net/trace.py

## Overview

net/trace.py — traceroute wrapper (stdlib subprocess).

Real traceroute needs ICMP/raw sockets (root), so this wraps whichever tool is
present, in preference order: traceroute -> tracepath -> nmap --traceroute.
Parses hops into a uniform table.

    python modules/net/trace.py 1.1.1.1
    python modules/net/trace.py example.com --max-hops 20

## Key functions

### `_tool() -> tuple[str, list[str]] | None`
No description available.

### `trace(target: str, max_hops: int, timeout: float) -> list[dict]`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import trace

result = trace.trace(...)
print(result)
```
