<!-- hacker-tool:generated -->
# modules/project/snapshot.py

## Overview

modules/project/snapshot.py — package a project directory into a timestamped
tarball snapshot, e.g. for gwthardwoodfloors or SAAB-SUITE before a risky change.

## Key functions

### `snapshot(project_dir: str, out_dir: Path, name: str, exclude: list) -> Path`
No description available.

## Usage

```python
from modules.project import snapshot

result = snapshot.snapshot(...)
print(result)
```
