"""sync schedule — create Termux:Boot hook for auto-sync."""
from __future__ import annotations
import sys
from pathlib import Path

BOOT_DIR = Path.home() / ".termux/boot"
HOOK_PATH = BOOT_DIR / "ht-sync.sh"

HOOK_CONTENT = """\
#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot — auto-sync hacker-tool workspaces on device boot
sleep 45  # wait for network
hackertool sync push >> ~/hacker-tool/logs/sync-boot.log 2>&1
"""

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "install"

    if cmd == "install":
        BOOT_DIR.mkdir(parents=True, exist_ok=True)
        HOOK_PATH.write_text(HOOK_CONTENT)
        HOOK_PATH.chmod(0o755)
        print(f"Termux:Boot sync hook installed → {HOOK_PATH}")
        print("Sync will run automatically on next device boot.")
    elif cmd == "remove":
        if HOOK_PATH.exists():
            HOOK_PATH.unlink()
            print("Boot sync hook removed.")
        else:
            print("No boot sync hook found.")
    elif cmd == "status":
        if HOOK_PATH.exists():
            print(f"Boot sync hook active: {HOOK_PATH}")
            print(HOOK_PATH.read_text())
        else:
            print("No boot sync hook installed.")
    else:
        print("Usage: sync schedule <install|remove|status>")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
