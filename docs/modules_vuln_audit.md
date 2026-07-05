<!-- hacker-tool:generated -->
# modules/vuln/audit.py

## Overview

modules/vuln/audit.py — local vulnerability surface checks.

Offline (ports, perms) + online opt-in (headers). Stdlib only.

## Key functions

### `check_headers(url: str, timeout: int) -> dict`
Fetch headers from a URL and audit security posture. Online — opt-in.

### `scan_ports(host: str, ports: list, timeout: float) -> dict`
TCP connect scan — restricted to localhost and RFC1918 ranges.

### `check_perms(root: str, max_findings: int) -> dict`
Walk a directory tree and flag world-writable, SUID, and SGID files.

## Usage

```python
from modules.vuln import audit

result = audit.check_headers(...)
print(result)
```
