"""
core/storage.py — Local + remote (SMB or plain mounted path) workspace abstraction.

Design: a "workspace" is just a named directory under either:
    <local_root>/workspaces/local/<name>
    <remote_root>/<name>            (remote_root may be an SMB mount or a
                                      plain shared folder path like
                                      /storage/emulated/0/SharedFolder)

Sync is deliberately simple (rsync-style copy), not a generic file-sync
daemon. Two backends are supported:

  - "path"  : remote_root is already a filesystem path (bind mount, cifs
              mount via mount.cifs, or an Android SAF-exposed shared folder)
  - "smb"   : remote_root is accessed on-demand via `smbclient` (no mount
              needed) — good for Termux without root/mount.cifs

Pick the backend that matches your setup in config.yml under remote_type.
"""
import shutil
import subprocess
from pathlib import Path


class StorageError(RuntimeError):
    pass


class Storage:
    def __init__(self, cfg: dict, logger):
        self.cfg = cfg
        self.logger = logger
        self.local_root = Path(cfg["local_root"])
        self.remote_root = cfg.get("remote_root", "")
        self.remote_type = cfg.get("remote_type", "path")

    # ---------- workspace paths ----------

    def local_workspace(self, name: str) -> Path:
        p = self.local_root / "workspaces" / "local" / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def remote_workspace_path(self, name: str) -> Path:
        """Only valid for remote_type == 'path'."""
        if self.remote_type != "path":
            raise StorageError("remote_workspace_path only valid for remote_type=path")
        p = Path(self.remote_root) / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ---------- sync ----------

    def push(self, name: str) -> None:
        """local -> remote"""
        src = self.local_workspace(name)
        if self.remote_type == "path":
            dst = self.remote_workspace_path(name)
            self._copy_tree(src, dst)
        elif self.remote_type == "smb":
            self._smb_put_tree(src, name)
        else:
            raise StorageError(f"Unknown remote_type: {self.remote_type}")
        self.logger.info(f"Pushed workspace '{name}' local -> remote")

    def pull(self, name: str) -> None:
        """remote -> local"""
        dst = self.local_workspace(name)
        if self.remote_type == "path":
            src = self.remote_workspace_path(name)
            self._copy_tree(src, dst)
        elif self.remote_type == "smb":
            self._smb_get_tree(name, dst)
        else:
            raise StorageError(f"Unknown remote_type: {self.remote_type}")
        self.logger.info(f"Pulled workspace '{name}' remote -> local")

    def status(self, name: str) -> dict:
        """Compare file counts/sizes between local and remote (path backend only,
        smb backend does a listing-based comparison)."""
        local = self.local_workspace(name)
        local_files = sorted(p.relative_to(local).as_posix() for p in local.rglob("*") if p.is_file())

        if self.remote_type == "path":
            remote = self.remote_workspace_path(name)
            remote_files = sorted(p.relative_to(remote).as_posix() for p in remote.rglob("*") if p.is_file())
        else:
            remote_files = self._smb_list(name)

        only_local = sorted(set(local_files) - set(remote_files))
        only_remote = sorted(set(remote_files) - set(local_files))
        common = sorted(set(local_files) & set(remote_files))

        return {
            "local_count": len(local_files),
            "remote_count": len(remote_files),
            "only_local": only_local,
            "only_remote": only_remote,
            "common": common,
        }

    # ---------- backends ----------

    @staticmethod
    def _copy_tree(src: Path, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.rglob("*"):
            rel = item.relative_to(src)
            target = dst / rel
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

    def _smb_put_tree(self, src: Path, name: str) -> None:
        smb = self.cfg.get("smb", {})
        self._require_smbclient()
        cmd = self._smb_base_cmd(smb)
        # smbclient can run a batch of commands via -c
        batch = f'mkdir "{name}"; cd "{name}"; recurse ON; prompt OFF; lcd "{src}"; mput *'
        self._run_smbclient(cmd, batch)

    def _smb_get_tree(self, name: str, dst: Path) -> None:
        smb = self.cfg.get("smb", {})
        self._require_smbclient()
        cmd = self._smb_base_cmd(smb)
        dst.mkdir(parents=True, exist_ok=True)
        batch = f'cd "{name}"; recurse ON; prompt OFF; lcd "{dst}"; mget *'
        self._run_smbclient(cmd, batch)

    def _smb_list(self, name: str) -> list:
        smb = self.cfg.get("smb", {})
        self._require_smbclient()
        cmd = self._smb_base_cmd(smb)
        batch = f'cd "{name}"; recurse ON; ls'
        out = self._run_smbclient(cmd, batch, capture=True)
        files = []
        for line in out.splitlines():
            line = line.strip()
            if line and not line.startswith(("smb:", "\\", "blocks")):
                parts = line.split()
                if parts:
                    files.append(parts[0])
        return files

    @staticmethod
    def _require_smbclient() -> None:
        if shutil.which("smbclient") is None:
            raise StorageError(
                "smbclient not found. Install with: pkg install samba-client "
                "(Termux) or apt install smbclient (Kali/Debian)"
            )

    @staticmethod
    def _smb_base_cmd(smb: dict) -> list:
        host = smb.get("host", "")
        share = smb.get("share", "")
        user = smb.get("user", "")
        domain = smb.get("domain", "")
        authfile = smb.get("authfile", "")
        target = f"//{host}/{share}"
        cmd = ["smbclient", target]
        if authfile and Path(authfile).exists():
            cmd += ["-A", authfile]
        elif user:
            userspec = f"{domain}\\{user}" if domain else user
            cmd += ["-U", userspec]
        return cmd

    @staticmethod
    def _run_smbclient(base_cmd: list, batch: str, capture: bool = False):
        cmd = base_cmd + ["-c", batch]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise StorageError(f"smbclient failed: {result.stderr.strip()}")
        return result.stdout if capture else None
