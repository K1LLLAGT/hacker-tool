"""
core/secrets.py — simple symmetric credential store using stdlib only.
Stores secrets encrypted at rest in ~/.config/hacker-tool/.secrets
Usage:
    from core.secrets import set_secret, get_secret
    set_secret("smb_password", "hunter2")
    get_secret("smb_password")
"""
from __future__ import annotations
import base64, hashlib, json, os, secrets as _secrets
from pathlib import Path

_STORE = Path.home() / ".config" / "hacker-tool" / ".secrets"
_KEY_FILE = Path.home() / ".config" / "hacker-tool" / ".key"


def _load_key() -> bytes:
    if _KEY_FILE.exists():
        return base64.b64decode(_KEY_FILE.read_bytes())
    key = _secrets.token_bytes(32)
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_bytes(base64.b64encode(key))
    _KEY_FILE.chmod(0o600)
    return key


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def set_secret(name: str, value: str) -> None:
    key = _load_key()
    store = json.loads(_STORE.read_text()) if _STORE.exists() else {}
    enc = base64.b64encode(_xor(value.encode(), key)).decode()
    store[name] = enc
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(store, indent=2))
    _STORE.chmod(0o600)


def get_secret(name: str) -> str | None:
    if not _STORE.exists():
        return None
    key = _load_key()
    store = json.loads(_STORE.read_text())
    if name not in store:
        return None
    return _xor(base64.b64decode(store[name]), key).decode()


def list_secrets() -> list[str]:
    if not _STORE.exists():
        return []
    return list(json.loads(_STORE.read_text()).keys())


def delete_secret(name: str) -> bool:
    if not _STORE.exists():
        return False
    store = json.loads(_STORE.read_text())
    if name not in store:
        return False
    del store[name]
    _STORE.write_text(json.dumps(store, indent=2))
    return True


def main(argv: list[str] | None = None) -> int:
    import sys
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: secrets <set|get|list|delete> [name] [value]")
        return 1
    cmd, *rest = argv
    if cmd == "set" and len(rest) == 2:
        set_secret(rest[0], rest[1])
        print(f"Secret '{rest[0]}' stored.")
    elif cmd == "get" and len(rest) == 1:
        v = get_secret(rest[0])
        print(v if v is not None else f"No secret named '{rest[0]}'")
    elif cmd == "list":
        for s in list_secrets(): print(s)
    elif cmd == "delete" and len(rest) == 1:
        print("Deleted." if delete_secret(rest[0]) else "Not found.")
    else:
        print("Usage: secrets <set|get|list|delete> [name] [value]")
        return 1
    return 0
