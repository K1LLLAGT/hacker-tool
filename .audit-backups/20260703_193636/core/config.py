"""
core/config.py — Config loading for hacker-tool

Reads $HOME/hacker-tool/config.yml (created on first run if missing).
"""
import os
import yaml
from pathlib import Path

DEFAULT_HOME = os.environ.get("HOME", str(Path.home()))
CONFIG_DIR = Path(DEFAULT_HOME) / "hacker-tool"
CONFIG_PATH = CONFIG_DIR / "config.yml"

DEFAULT_CONFIG = {
    "local_root": str(CONFIG_DIR),
    "remote_root": "/storage/emulated/0/SharedFolder",
    "remote_type": "path",  # path | smb
    "smb": {
        "host": "",
        "share": "",
        "user": "",
        "domain": "",
        # never store a plaintext password here; use smbclient -A authfile
        "authfile": str(CONFIG_DIR / ".smb_authfile"),
    },
    "log_level": "INFO",
}


def ensure_dirs(cfg: dict) -> None:
    Path(cfg["local_root"]).mkdir(parents=True, exist_ok=True)
    (Path(cfg["local_root"]) / "data").mkdir(parents=True, exist_ok=True)
    (Path(cfg["local_root"]) / "reports").mkdir(parents=True, exist_ok=True)
    (Path(cfg["local_root"]) / "workspaces" / "local").mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, sort_keys=False)
        cfg = DEFAULT_CONFIG
    else:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        # merge in any missing defaults (forward-compatible upgrades)
        merged = {**DEFAULT_CONFIG, **cfg}
        cfg = merged
    ensure_dirs(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
