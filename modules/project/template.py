"""project template — scaffold a new project from built-in skeleton."""
from __future__ import annotations
import sys, shutil
from pathlib import Path

SKELETON = {
    "README.md": "# {name}\n\nProject created with hacker-tool.\n",
    "src/__init__.py": "",
    "src/main.py": 'def main():\n    print("Hello from {name}")\n\nif __name__ == "__main__":\n    main()\n',
    "tests/__init__.py": "",
    "tests/test_main.py": 'from src.main import main\n\ndef test_main(capsys):\n    main()\n    out, _ = capsys.readouterr()\n    assert "{name}" in out\n',
    ".gitignore": "__pycache__/\n.venv/\n*.pyc\n",
    "requirements.txt": "# add runtime deps here\n",
}

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: project template <project-name> [destination]")
        return 1
    name = argv[0]
    dest = Path(argv[1]) / name if len(argv) > 1 else Path.cwd() / name
    if dest.exists():
        print(f"Error: {dest} already exists"); return 1
    for rel, content in SKELETON.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.format(name=name))
    print(f"Project '{name}' scaffolded at {dest}")
    print("  Files created:")
    for rel in SKELETON:
        print(f"    {rel}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
