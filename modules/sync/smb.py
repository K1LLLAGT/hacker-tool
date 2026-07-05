"""sync smb — push/pull files to SMB share using credentials from secrets store."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

def _get_secret(name: str) -> str | None:
    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location(
            "secrets", Path.home() / "hacker-tool/core/secrets.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.get_secret(name)
    except Exception:
        return None

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in ("push", "pull", "status"):
        print("Usage: sync smb <push|pull|status> [local_dir]")
        return 1

    cmd = argv[0]
    cfg_path = Path.home() / ".config/hacker-tool/config.toml"
    smb_host  = _get_secret("smb_host")  or "//server/share"
    smb_user  = _get_secret("smb_user")  or "guest"
    smb_pass  = _get_secret("smb_password") or ""
    local_dir = Path(argv[1]) if len(argv) > 1 else Path.home() / "hacker-tool/workspaces/remote"

    mount = Path("/tmp/ht_smb_mount")
    mount.mkdir(exist_ok=True)

    auth = f"username={smb_user},password={smb_pass}"
    try:
        subprocess.run(["mount", "-t", "cifs", smb_host, str(mount),
                        "-o", auth], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Mount failed: {e.stderr.decode().strip()}")
        print("Tip: run  htctl secrets set smb_host //your-server/share")
        return 1

    try:
        if cmd == "status":
            result = subprocess.run(["ls", "-la", str(mount)], capture_output=True, text=True)
            print(result.stdout)
        elif cmd == "push":
            subprocess.run(["rsync", "-av", str(local_dir) + "/", str(mount) + "/"], check=True)
            print("Push complete.")
        elif cmd == "pull":
            subprocess.run(["rsync", "-av", str(mount) + "/", str(local_dir) + "/"], check=True)
            print("Pull complete.")
    finally:
        subprocess.run(["umount", str(mount)], capture_output=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
