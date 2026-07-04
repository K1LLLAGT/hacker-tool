<!-- hacker-tool:generated -->
# modules/report/generate.py

## Overview

modules/report/generate.py — turn any dict/list result into a Markdown
(and optionally HTML) report.

## Key functions

### `_to_markdown(title: str, data) -> str`
No description available.

### `write_report(title: str, data, out_dir: Path, name: str, fmt: str) -> Path`
No description available.

## Usage

```python
from modules.report import generate

result = generate.write_report(...)
print(result)
```
