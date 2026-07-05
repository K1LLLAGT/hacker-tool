<!-- hacker-tool:generated -->
# modules/proc/monitor.py

## Overview

modules/proc/monitor.py — process inspection for Termux / Android.

Offline-only. Stdlib only. Reads /proc directly.

## Key functions

### `_read(path: str, default: str) -> str`
No description available.

### `_proc_pids() -> list`
No description available.

### `_proc_stat(pid: int) -> dict`
No description available.

### `_page_size() -> int`
No description available.

### `list_procs(filter_name: str) -> dict`
List all running processes visible under /proc.

### `top_procs(n: int, sort_by: str) -> dict`
Top N processes sorted by rss_kb, cpu_ticks, or pid.

### `find_proc(name: str) -> dict`
No description available.

### `kill_proc(pid: int, sig: str) -> dict`
Send TERM/KILL/HUP/INT to a process by PID.

### `mem_summary() -> dict`
Parse /proc/meminfo into a human-readable summary.

## Usage

```python
from modules.proc import monitor

result = monitor.list_procs(...)
print(result)
```
