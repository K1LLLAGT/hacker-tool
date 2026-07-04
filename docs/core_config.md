<!-- hacker-tool:generated -->
# core/config.py

## Overview

core/config.py — Config loading for hacker-tool

Reads $HOME/hacker-tool/config.yml (created on first run if missing).

## Key functions

### `ensure_dirs(cfg: dict) -> None`
No description available.

### `load_config() -> dict`
No description available.

### `save_config(cfg: dict) -> None`
No description available.

## Usage

```python
from core import config

result = config.ensure_dirs(...)
print(result)
```
