"""report schedule — install Termux:Boot hook to auto-generate reports on boot."""
from __future__ import annotations
import sys
from pathlib import Path

BOOT_DIR = Path.home() / ".termux/boot"
HOOK_PATH = BOOT_DIR / "ht-report.sh"

HOOK_CONTENT = """\
#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot — auto-generate hacker-tool report on device boot
sleep 60
hackertool report generate >> ~/hacker-tool/logs/report-boot.log 2>&1
"""

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "install"
    if cmd == "install":
        BOOT_DIR.mkdir(parents=True, exist_ok=True)
        HOOK_PATH.write_text(HOOK_CONTENT)
        HOOK_PATH.chmod(0o755)
        print(f"Report boot hook installed → {HOOK_PATH}")
    elif cmd == "remove":
        if HOOK_PATH.exists():
            HOOK_PATH.unlink()
            print("Report boot hook removed.")
        else:
            print("No report boot hook found.")
    elif cmd == "status":
        if HOOK_PATH.exists():
            print(f"Active: {HOOK_PATH}"); print(HOOK_PATH.read_text())
        else:
            print("No report boot hook installed.")
    else:
        print("Usage: report schedule <install|remove|status>"); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
